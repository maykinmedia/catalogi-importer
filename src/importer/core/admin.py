import os

from django import forms
from django.contrib import admin
from django.urls import reverse
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _

from solo.admin import SingletonModelAdmin

from importer.core.choices import JobState
from importer.core.models import CatalogConfig, Job, SelectielijstConfig
from importer.core.reporting import (
    transform_import_statistics,
    transform_precheck_statistics,
)
from importer.core.selectielijst import get_procestype_years
from importer.core.tasks import import_job_task, precheck_job_task
from importer.utils.forms import StaticHiddenField


@admin.register(SelectielijstConfig)
class SelectielijstConfigAdmin(SingletonModelAdmin):
    pass


@admin.register(CatalogConfig)
class CatalogConfigAdmin(admin.ModelAdmin):
    fields = [
        "service",
        "uuid",
        "label",
        "_cached_domein",
        "_cached_rsin",
    ]
    list_display = [
        "label",
        "uuid",
        "service",
        "_cached_domein",
        "_cached_rsin",
    ]
    readonly_fields = [
        "_cached_domein",
        "_cached_rsin",
    ]

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser


def get_procestype_year_choices():
    return [(str(y), str(y)) for y in get_procestype_years()]


def get_procestype_year_default():
    try:
        return max(get_procestype_years())
    except ValueError:
        return ""


class JobForm(forms.ModelForm):
    year = forms.TypedChoiceField(
        localize=False,
        coerce=int,
        choices=get_procestype_year_choices,
        initial=get_procestype_year_default,
    )

    class Meta:
        fields = (
            "catalog",
            "year",
            "source",
            "start_date",
            "close_published",
        )


class JobStateQueueForm(forms.ModelForm):
    state = StaticHiddenField(JobState.queued)

    class Meta:
        model = Job
        fields = ["state"]


@admin.register(Job)
class JobAdmin(admin.ModelAdmin):
    list_display = [
        "created_at",
        "catalog",
        "year_fmt",
        "state",
        "started_at",
        "stopped_at",
        "get_duration_display",
    ]
    list_filter = [
        "state",
        "catalog",
        "year",
    ]
    date_hierarchy = "created_at"
    ordering = [
        "-created_at",
    ]
    form = JobForm

    def get_fields(self, request, job=None):
        """
        everything is readonly except on creation or precheck, see also get_readonly_fields()
        """
        if not job:
            return [
                "catalog",
                "year",
                "source",
                "start_date",
                "close_published",
            ]
        else:
            return [
                "catalog_fmt",
                "year_fmt",
                "source_fmt",
                "state",
                "start_date",
                "close_published",
                "created_at",
                "started_at",
                "stopped_at",
            ]

    def get_readonly_fields(self, request, job=None):
        """
        everything readonly except on creation or precheck
        """
        fields = {
            "catalog",
            "year",
            "source",
            "state",
            "created_at",
            "started_at",
            "stopped_at",
            "catalog_fmt",
            "year_fmt",
            "source_fmt",
            "start_date",
            "close_published",
        }
        if not job:
            return fields - {
                "catalog",
                "year",
                "source",
                "start_date",
                "close_published",
            }
        elif job.state == JobState.precheck:
            return fields - {
                "state",
            }
        else:
            return fields

    def get_joblogs(self, job):
        return job.joblog_set.order_by("pk")

    def change_view(self, request, object_id, form_url="", context=None):
        job = Job.objects.get(id=object_id)

        context = context or {}
        context["title"] = "Job"

        if job.state == JobState.initialized:
            context["title"] = _("Waiting for precheck to start..")
            context["reload_time"] = 5000

        elif job.state == JobState.checking:
            context["title"] = _("Running precheck..")
            context["reload_time"] = 2500
            context["value_table"] = {
                "rows": transform_precheck_statistics(job.statistics),
            }
        elif job.state == JobState.precheck:
            context["title"] = _("Precheck completed")
            context["value_table"] = {
                "rows": transform_precheck_statistics(job.statistics),
            }
            context["joblog_table"] = {
                "rows": self.get_joblogs(job),
            }
        elif job.state == JobState.queued:
            context["title"] = _("Waiting for import to start..")
            context["reload_time"] = 2500

        elif job.state == JobState.running:
            context["title"] = _("Running import..")
            context["reload_time"] = 5000
            context["value_table"] = {
                "rows": transform_import_statistics(job.statistics),
            }
        elif job.state == JobState.completed:
            context["title"] = _("Import completed")
            context["value_table"] = {
                "title": _("Results"),
                "rows": transform_import_statistics(job.statistics),
            }
            context["joblog_table"] = {
                "rows": self.get_joblogs(job),
            }
        elif job.state == JobState.error:
            context["title"] = _("Import Error")
            context["value_table"] = {
                "title": _("Error"),
                "rows": transform_import_statistics(job.statistics),
            }
            context["joblog_table"] = {
                "show_timestamp": True,
                "rows": self.get_joblogs(job),
            }

        return super().change_view(request, object_id, form_url, extra_context=context)

    def get_form(self, request, obj=None, change=False, **kwargs):
        if obj and obj.state == JobState.precheck:
            return JobStateQueueForm
        else:
            return super().get_form(request, obj=obj, change=change, **kwargs)

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        if not change:
            if obj.state == JobState.initialized:
                precheck_job_task.apply_async((obj.id,), countdown=2)
        else:
            if obj.state == JobState.queued:
                import_job_task.apply_async((obj.id,), countdown=2)

    def message_user(self, *args):
        # kill automatic messages
        pass

    def has_delete_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        # precheck is the only state that needs user interaction to continue
        return obj and obj.state == JobState.precheck

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("catalog")

    def year_fmt(self, job):
        # Django insists on adding thousands separator to IntegerField's so stringify manually
        return str(job.year)

    year_fmt.short_description = _("Selectielijst year")
    year_fmt.admin_order_field = "year"

    def catalog_fmt(self, job):
        url = reverse(
            "admin:{}_{}_change".format(
                job.catalog._meta.app_label, job.catalog._meta.model_name
            ),
            args=[job.catalog.pk],
        )
        return format_html(
            '<a href="{url}">{text}</a>',
            url=url,
            text=str(job.catalog),
        )

    catalog_fmt.short_description = _("Catalogus")
    catalog_fmt.admin_order_field = "catalog"

    def source_fmt(self, job):
        url = reverse("staff_private_file", kwargs={"path": job.source.name})
        return format_html(
            '<a href="{url}" target="_blank">{text}</a>',
            url=url,
            text=os.path.basename(job.source.name),
        )

    source_fmt.short_description = _("XML File")

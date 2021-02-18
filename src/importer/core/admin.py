import os

from django import forms
from django.contrib import admin
from django.db import models
from django.urls import reverse
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _

from solo.admin import SingletonModelAdmin
from zgw_consumers.models import Service

from importer.core.choices import JobState
from importer.core.importer import precheck_import
from importer.core.models import CatalogConfig, Job, SelectielijstConfig
from importer.core.reporting import transform_statistics
from importer.core.tasks import import_job_task
from importer.utils.forms import StaticHiddenField


@admin.register(SelectielijstConfig)
class SelectielijstConfigAdmin(SingletonModelAdmin):
    pass


@admin.register(CatalogConfig)
class CatalogConfigAdmin(admin.ModelAdmin):
    fields = [
        "url",
        "label",
    ]
    list_display = [
        "__str__",
        "has_credentials",
    ]
    readonly_fields = [
        "has_credentials",
    ]

    def get_fields(self, request, catalog=None):
        fields = super().get_fields(request, catalog)
        if not catalog:
            return fields
        else:
            return fields + [
                "has_credentials",
            ]

    def has_credentials(self, catalog):
        return Service.get_service(catalog.url) is not None

    has_credentials.short_description = _("ZGW Service configured")
    has_credentials.boolean = True

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser


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
    formfield_overrides = {
        models.SmallIntegerField: {"widget": forms.TextInput},
    }

    def get_fields(self, request, job=None):
        """
        everything is readonly except on creation or precheck, see also get_readonly_fields()
        """
        if not job:
            return [
                "catalog",
                "year",
                "source",
            ]
        elif job.state == JobState.precheck:
            return [
                "state",
                "catalog_fmt",
                "year_fmt",
                "source_fmt",
                "created_at",
            ]
        else:
            return [
                "catalog_fmt",
                "year_fmt",
                "source_fmt",
                "state",
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
        }
        if not job:
            return fields - {
                "catalog",
                "year",
                "source",
            }
        elif job.state == JobState.precheck:
            return fields - {
                "state",
            }
        else:
            return fields

    def get_stopped_joblogs(self, job):
        return job.joblog_set.order_by("pk")

    def change_view(self, request, object_id, form_url="", context=None):
        # TODO do we really have to retrieve this ourselves?
        job = Job.objects.get(id=object_id)

        context = context or {}
        context["title"] = "Job"

        if job.state == JobState.precheck:
            session = precheck_import(job)

            context["title"] = _("Precheck")
            context["value_table"] = {
                "rows": transform_statistics(session.counter.get_data()),
            }
            context["joblog_table"] = {
                "show_timestamp": False,
                "rows": session.logs,
            }
        elif job.state == JobState.queued:
            context["title"] = _("Queued Job")

        elif job.state == JobState.running:
            context["title"] = _("Running..")
            context["value_table"] = {
                "rows": transform_statistics(job.statistics),
            }
        elif job.state == JobState.completed:
            context["title"] = _("Import completed")
            context["value_table"] = {
                "title": _("Results"),
                "rows": transform_statistics(job.statistics),
            }
            context["joblog_table"] = {
                # "show_timestamp": True,
                "rows": self.get_stopped_joblogs(job),
            }
        elif job.state == JobState.error:
            context["title"] = _("Import Error")
            context["value_table"] = {
                "title": _("Error"),
                "rows": transform_statistics(job.statistics),
            }
            context["joblog_table"] = {
                "show_timestamp": True,
                "rows": self.get_stopped_joblogs(job),
            }

        return super().change_view(request, object_id, form_url, extra_context=context)

    def get_form(self, request, obj=None, change=False, **kwargs):
        if obj and obj.state == JobState.precheck:
            return JobStateQueueForm
        else:
            return super().get_form(request, obj=obj, change=change, **kwargs)

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        if change and obj.state == JobState.queued:
            import_job_task.delay(obj.id)

    def message_user(self, *args):
        # kill automatic messages
        pass

    def has_delete_permission(self, request, obj=None):
        # TODO allow deletion for cleanup of failed prechecks?
        return False  # request.user.is_superuser

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

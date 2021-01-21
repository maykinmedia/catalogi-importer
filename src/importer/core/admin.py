import os

from django import forms
from django.contrib import admin
from django.db import models
from django.urls import reverse
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _

from solo.admin import SingletonModelAdmin
from zgw_consumers.models import Service

from .choices import JobState
from .models import CatalogConfig, Job, JobLog, SelectielijstConfig


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


@admin.register(JobLog)
class JobLogAdmin(admin.ModelAdmin):
    fields = [
        "job",
        "level",
        "timestamp",
        "message",
    ]
    readonly_fields = [
        "timestamp",
    ]
    list_display = [
        "timestamp",
        "job",
        "level",
        "message_trim_line",
    ]
    raw_id_fields = [
        "job",
    ]
    list_filter = [
        "level",
    ]
    date_hierarchy = "timestamp"
    ordering = [
        "-timestamp",
    ]
    search_fields = [
        "message",
        "job__id",
    ]

    # TODO setup permissions
    # def has_add_permission(self, request, obj=None):
    #     return False
    #
    # def has_change_permission(self, request, obj=None):
    #     return False
    #
    # def has_delete_permission(self, request, obj=None):
    #     return False


class JobLogInline(admin.TabularInline):
    template = "admin/core/job/joblog_tabular.html"
    model = JobLog
    fields = [
        "timestamp",
        "level",
        "message",
    ]
    readonly_fields = [
        "level",
        "timestamp",
        "message",
    ]
    ordering = [
        "-timestamp",
    ]

    def has_add_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


class StaticHiddenField(forms.Field):
    def __init__(self, value):
        self.value = value
        super().__init__(widget=forms.HiddenInput)

    def prepare_value(self, value):
        return self.value

    def to_python(self, value):
        return self.value


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
        everything readonly except on creation, see also get_readonly_fields()
        """
        if not job:
            return [
                "catalog",
                "year",
                "source",
            ]
        # readonly mode, adding fields as state flow progresses
        fields = [
            "catalog_fmt",
            "year_fmt",
            "source_fmt",
            "state",
            "created_at",
        ]
        if job.state == JobState.running:
            return fields + [
                "started_at",
            ]
        elif job.state in (JobState.completed, JobState.error):
            return fields + [
                "started_at",
                "stopped_at",
            ]
        elif job.state == JobState.precheck:
            return [
                # "catalog_fmt",
                # "year_fmt",
                # "source_fmt",
                "state",
                # "created_at",
            ]
        else:
            return fields

    def get_readonly_fields(self, request, job=None):
        """
        everything readonly except on creation
        """
        fields = self.get_fields(request, job=job)
        if not job:
            return set(fields) - {
                "catalog",
                "year",
                "source",
            }
        elif job.state == JobState.precheck:
            return set(fields) - {
                "state",
            }
        else:
            return fields

    def get_precheck_stats(self):
        # TODO implement
        return [
            ("Status", "OK"),
            ("IOTypen", "43"),
            ("Zaaktypen", "32"),
            ("Roltypen", "21 (7 warnings)"),
            ("Statustypes", "17"),
            ("Resultaattypen", "34"),
            ("Zaakinformatieobjecttypen", "23"),
        ]

    def get_progress_stats(self):
        # TODO implement
        return [
            ("IOTypen", "12 / 43"),
            ("Zaaktypen", "23 / 32"),
            ("Roltypen", "12 / 21 (7 warnings)"),
            ("Statustypes", "7 / 17"),
            ("Resultaattypen", "15 / 34"),
            ("Zaakinformatieobjecttypen", "23 / 23"),
        ]

    def get_completion_stats(self):
        # TODO implement
        return [
            ("Status", "OK"),
            ("IOTypen", "43"),
            ("Zaaktypen", "32"),
            ("Roltypen", "21 (7 warnings)"),
            ("Statustypes", "17"),
            ("Resultaattypen", "34"),
            ("Zaakinformatieobjecttypen", "23"),
        ]

    def get_joblogs(self, job):
        return {
            "rows": job.joblog_set.order_by("-timestamp"),
        }

    def change_view(self, request, object_id, form_url="", extra_context=None):
        extra_context = extra_context or {}
        job = Job.objects.get(id=object_id)

        if job.state == JobState.precheck:
            # TODO swap for precheck logs
            extra_context["joblog_table"] = self.get_joblogs(job)
            extra_context["value_table"] = {
                "title": _("Precheck results"),
                "rows": self.get_precheck_stats(),
            }
        elif job.state == JobState.running:
            extra_context["value_table"] = {
                "title": _("Progress"),
                "rows": self.get_progress_stats(),
            }
        elif job.state in JobState.completed:
            extra_context["joblog_table"] = self.get_joblogs(job)
            extra_context["value_table"] = {
                "title": _("Results"),
                "rows": self.get_completion_stats(),
            }

        return super().change_view(
            request, object_id, form_url, extra_context=extra_context
        )

    def get_form(self, request, obj=None, change=False, **kwargs):
        if obj and obj.state == JobState.precheck:
            return JobStateQueueForm
        else:
            return super().get_form(request, obj=obj, change=change, **kwargs)

    def has_delete_permission(self, request, obj=None):
        # TODO allow deletion for cleanup of failed prechecks?
        return False  # request.user.is_superuser

    def has_change_permission(self, request, obj=None):
        # precheck is the only state that needs user interaction to continue
        return obj and obj.state == JobState.precheck

    def year_fmt(self, job):
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

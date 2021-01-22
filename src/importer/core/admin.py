import os
import random

from django import forms
from django.contrib import admin
from django.db import models
from django.urls import reverse
from django.utils import timezone
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _

from faker import Faker
from solo.admin import SingletonModelAdmin
from zgw_consumers.models import Service

from importer.core.choices import JobLogLevel, JobState
from importer.core.constants import ObjectTypenKeys
from importer.core.models import CatalogConfig, Job, JobLog, SelectielijstConfig
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

    def has_add_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


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
        everything readonly except on creation or precheck, see also get_readonly_fields()
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
                "state",
            ]
        else:
            return fields

    def get_readonly_fields(self, request, job=None):
        """
        everything readonly except on creation or precheck
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

    def get_precheck_stats(self, job):
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

    def get_precheck_joblogs(self, job):
        # TODO implement
        f = Faker()
        return [
            JobLog(
                level=random.choice(list(JobLogLevel.values)),
                message=f.paragraph(),
                timestamp=timezone.now(),
            )
            for i in range(0, random.randint(2, 20))
        ]

    def get_stopped_joblogs(self, job):
        return job.joblog_set.order_by("-timestamp")

    def change_view(self, request, object_id, form_url="", extra_context=None):
        # TODO do we really have to retrieve this ourselves?
        job = Job.objects.get(id=object_id)

        extra_context = extra_context or {}
        extra_context["title"] = "Job"

        if job.state == JobState.precheck:
            extra_context["title"] = _("Precheck")
            extra_context["value_table"] = {
                "rows": self.get_precheck_stats(job),
            }
            extra_context["joblog_table"] = {
                "show_timestamp": False,
                "rows": self.get_precheck_joblogs(job),
            }
        elif job.state == JobState.queued:
            extra_context["title"] = _("Queued Job")

        elif job.state == JobState.running:
            extra_context["title"] = _("Running..")
            extra_context["value_table"] = {
                "rows": transform_statistics(job.results),
            }
        elif job.state in JobState.completed:
            extra_context["title"] = _("Import completed")
            extra_context["value_table"] = {
                "title": _("Results"),
                "rows": transform_statistics(job.results),
            }
            extra_context["joblog_table"] = {
                "show_timestamp": True,
                "rows": self.get_stopped_joblogs(job),
            }
        elif job.state in JobState.error:
            extra_context["title"] = _("Import Error")
            extra_context["value_table"] = {
                "title": _("Error"),
                "rows": transform_statistics(job.results),
            }
            extra_context["joblog_table"] = {
                "show_timestamp": True,
                "rows": self.get_stopped_joblogs(job),
            }

        return super().change_view(
            request, object_id, form_url, extra_context=extra_context
        )

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


def transform_statistics(raw_data):
    """
    Transform a dictionary of tuples with progress/result statistics into key/value rows for display

    {
        "data": {
            ObjectTypenKeys.roltypen: (10, 10),
            ObjectTypenKeys.statustypen: (20, 20),
            ObjectTypenKeys.resultaattypen: (30, 30, {JobLogLevel.warning: 2, JobLogLevel.error: 1}),
            ObjectTypenKeys.informatieobjecttypen: (40, 40, None),
            ObjectTypenKeys.zaakinformatieobjecttypen: (50, 50, {JobLogLevel.warning: 5}),
        },
    }

    Output something like:

    [
        ("Foo": "1 / 2"),
        ("Bar": "2 / 5 (4 warnings, 2 errors)"),
    ]
    """

    # generate table even if we dont have data
    if raw_data is None:
        raw_data = dict()
    data = raw_data.get("data", dict())

    rows = []
    for key in ObjectTypenKeys.values:
        label = ObjectTypenKeys.values[key]

        if key in data:
            # juggle 2-3 tuples
            value = data[key]
            if len(value) == 2:
                count, total = data[key]
                logstats = None
            else:
                count, total, logstats = data[key]
        else:
            # default
            count, total, logstats = (0, 0, None)

        # collect formatted
        info_fmt = format_logstats_dict(logstats)
        if info_fmt:
            info_fmt = " " + info_fmt

        stat_fmt = f"{count} / {total}{info_fmt}"

        rows.append((label, stat_fmt))

    return rows


def format_logstats_dict(info):
    """
    Format a dictionary of {log_level: count} into a readable one-line string

    {
        "warning", 10,
        "error", 2,
    }

    Output:

    (10 warnings, 2 errors)

    """
    if not info:
        return ""

    parts = []
    for level in JobLogLevel.values:
        if level in info:
            parts.append(f"{info[level]} {JobLogLevel.labels[level].lower()}s")

    if parts:
        return f"({', '.join(parts)})"
    else:
        return ""

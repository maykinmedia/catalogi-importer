from django import forms
from django.contrib import admin
from django.db import models
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _

from solo.admin import SingletonModelAdmin

from .choices import JobState
from .models import CatalogConfig, Job, SelectielijstConfig


@admin.register(SelectielijstConfig)
class SelectielijstConfigAdmin(SingletonModelAdmin):
    pass


@admin.register(CatalogConfig)
class CatalogConfigAdmin(admin.ModelAdmin):
    fields = [
        "url",
        "label",
        "has_credentials",
    ]
    list_display = [
        "__str__",
        "has_credentials",
    ]
    readonly_fields = [
        "has_credentials",
    ]

    def has_credentials(self, catalog):
        from zgw_consumers.models import Service

        return Service.get_service(catalog.url) is not None

    has_credentials.short_description = _("ZGW Service defined")
    has_credentials.boolean = True

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser


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
        "catalog",
        "state",
        "year",
    ]
    date_hierarchy = "created_at"
    ordering = [
        "created_at",
    ]

    formfield_overrides = {
        models.SmallIntegerField: {"widget": forms.TextInput},
    }

    def get_fields(self, request, job=None):
        if not job or job.id is None:
            return [
                "catalog",
                "year",
                "source",
            ]
        # readonly modes
        fields = [
            "catalog_fmt",
            "year_fmt",
            "source",
        ]
        if job.state == JobState.queued:
            return fields + [
                "state",
                "created_at",
            ]
        elif job.state == JobState.running:
            return fields + [
                "state",
                "created_at",
                "started_at",
            ]
        elif job.state in (JobState.completed, JobState.error):
            return fields + [
                "state",
                "created_at",
                "started_at",
                "complete_at",
            ]
        else:
            return fields + [
                "state",
            ]

    def get_readonly_fields(self, request, job=None):
        fields = self.get_fields(request, job=job)
        if not job or job.id is None:
            # explicitly allow when creating new
            return set(fields) - {
                "catalog",
                "year",
                "source",
            }
        else:
            return fields

    def year_fmt(self, instance):
        return str(instance.year)

    year_fmt.short_description = _("Selectielijst year")
    year_fmt.admin_order_field = "year"

    def catalog_fmt(self, instance):
        if instance.catalog.label:
            return format_html(
                '{label} (<a href="{url}" target="_blank" rel="noopener, noreferrer">{url}</a>)',
                label=instance.catalog.label,
                url=instance.catalog.url,
            )
        return str(instance.catalog.label)

    catalog_fmt.short_description = _("Catalogus")

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser

    def has_change_permission(self, request, obj=None):
        return False

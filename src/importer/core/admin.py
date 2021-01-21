from django import forms
from django.contrib import admin
from django.db import models
from django.urls import reverse
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _

from solo.admin import SingletonModelAdmin
from zgw_consumers.models import Service

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
        "-created_at",
    ]

    formfield_overrides = {
        models.SmallIntegerField: {"widget": forms.TextInput},
    }

    def get_fields(self, request, job=None):
        if not job:
            return [
                "catalog",
                "year",
                "source",
            ]
        # readonly mode
        fields = [
            "catalog_fmt",
            "year_fmt",
            "source",
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
        else:
            return fields

    def get_readonly_fields(self, request, job=None):
        fields = self.get_fields(request, job=job)
        if not job:
            return set(fields) - {
                "catalog",
                "year",
                "source",
            }
        else:
            return fields

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

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser

    def has_change_permission(self, request, obj=None):
        return False

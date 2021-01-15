from django.contrib import admin

from solo.admin import SingletonModelAdmin

from .models import CatalogConfig, Job, SelectielijstConfig


@admin.register(SelectielijstConfig)
class SelectielijstConfigAdmin(SingletonModelAdmin):
    pass


@admin.register(CatalogConfig)
class CatalogConfigAdmin(admin.ModelAdmin):
    pass


@admin.register(Job)
class JobAdmin(admin.ModelAdmin):
    pass

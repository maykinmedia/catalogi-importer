from django.contrib import admin

from solo.admin import SingletonModelAdmin

from .models import SelectielijstConfig


@admin.register(SelectielijstConfig)
class SubscriptionAdmin(SingletonModelAdmin):
    pass

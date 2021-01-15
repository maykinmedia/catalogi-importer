from django.core.validators import FileExtensionValidator
from django.db import models
from django.utils import timezone
from django.utils.encoding import force_text
from django.utils.translation import gettext_lazy as _

from solo.models import SingletonModel
from zgw_consumers.constants import APITypes

from importer.core.choices import JobState
from importer.utils.storage import private_storage


class SelectielijstConfigManager(models.Manager):
    def get_queryset(self):
        qs = super().get_queryset()
        return qs.select_related("service")


class SelectielijstConfig(SingletonModel):
    service = models.ForeignKey(
        "zgw_consumers.Service",
        null=True,
        on_delete=models.SET_NULL,
        limit_choices_to={"api_type": APITypes.orc},
    )

    objects = SelectielijstConfigManager()

    class Meta:
        verbose_name = _("Selectielijst configuration")

    def __str__(self):
        return force_text(self._meta.verbose_name)


class CatalogConfig(models.Model):
    url = models.URLField(
        _("Catalog URL"),
        max_length=255,
    )
    label = models.CharField(
        _("Label"),
        max_length=255,
        blank=True,
        help_text=_("Human readable label."),
    )

    class Meta:
        verbose_name = _("Catalog configuration")

    def __str__(self):
        return self.label or self.url

    def has_credentials(self):
        from zgw_consumers.models import Service

        return Service.get_service(self.url) is not None

    has_credentials.short_description = _("ZGW Service defined")
    has_credentials.boolean = True


def get_job_source_file_name(instance, filename):
    return f"jobs/{instance.id}/source/{filename}"


class JobQueryset(models.QuerySet):
    def filter_queued(self):
        return self.filter(state=JobState.queued).order_by("pk")


class Job(models.Model):
    catalog = models.ForeignKey(
        "core.CatalogConfig",
        on_delete=models.PROTECT,
    )

    year = models.IntegerField(
        _("Year"),
        help_text=_("Year to import to."),
    )

    source = models.FileField(
        _("File"),
        upload_to=get_job_source_file_name,
        storage=private_storage,
        validators=[FileExtensionValidator(["xml"])],
        help_text=_("i-Navigator XML export file."),
    )

    state = models.CharField(
        _("State"),
        max_length=32,
        default=JobState.queued,
        choices=JobState.choices,
        db_index=True,
    )

    # state_message = models.CharField(
    #     _("Status"),
    #     max_length=255,
    #     blank=True,
    # )

    created_at = models.DateTimeField(_("Date created"), auto_created=True)
    started_at = models.DateTimeField(_("Date started"), blank=True, null=True)
    stopped_at = models.DateTimeField(_("Date stopped"), blank=True, null=True)

    objects = JobQueryset.as_manager()

    class Meta:
        verbose_name = _("Job")

    def __str__(self):
        return f"{force_text(self._meta.verbose_name)}#{self.id}"

    def mark_running(self):
        # TODO harden checks
        self.state = JobState.running
        self.state_message = ""
        self.started_at = timezone.now()
        self.save()

    def mark_completed(self):
        # TODO harden checks
        self.state = JobState.completed
        self.state_message = ""
        self.stopped_at = timezone.now()
        self.save()

    def mark_error(self, message=""):
        # TODO harden checks
        self.state = JobState.error
        self.state_message = message[:255]
        self.stopped_at = timezone.now()
        self.save()

from django.core.validators import (
    FileExtensionValidator,
    MaxValueValidator,
    MinValueValidator,
)
from django.db import models
from django.utils import timezone
from django.utils.encoding import force_text
from django.utils.translation import gettext_lazy as _

from solo.models import SingletonModel
from zgw_consumers.constants import APITypes

from importer.core.choices import JobLogLevel, JobState
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
        if self.label:
            return f"{self.label} ({self.url})"
        return self.url


def get_job_source_file_name(instance, filename):
    return f"jobs/source/{filename}"


class JobQueryset(models.QuerySet):
    def filter_queued(self):
        return self.filter(state=JobState.queued).order_by("pk")


class Job(models.Model):
    catalog = models.ForeignKey(
        "core.CatalogConfig",
        on_delete=models.PROTECT,
    )

    year = models.SmallIntegerField(
        _("Selectielijst year"),
        help_text=_("Year to import to."),
        validators=[MinValueValidator(1000), MaxValueValidator(9999)],
    )

    source = models.FileField(
        _("XML File"),
        upload_to=get_job_source_file_name,
        storage=private_storage,
        validators=[FileExtensionValidator(["xml"])],
        help_text=_("i-Navigator XML export file."),
    )

    state = models.CharField(
        _("State"),
        max_length=32,
        default=JobState.precheck,
        choices=JobState.choices,
        db_index=True,
    )

    created_at = models.DateTimeField(
        _("Job created"), auto_now_add=True, db_index=True
    )
    started_at = models.DateTimeField(_("Job started"), blank=True, null=True)
    stopped_at = models.DateTimeField(_("Job stopped"), blank=True, null=True)

    objects = JobQueryset.as_manager()

    class Meta:
        verbose_name = _("Import Job")

    def __str__(self):
        return f"{force_text(self._meta.verbose_name)}#{self.id}"

    def mark_running(self):
        # TODO add checks, lock? (maybe at higher level)
        self.state = JobState.running
        self.started_at = timezone.now()
        self.save()

    def mark_completed(self):
        # TODO add checks, lock? (maybe at higher level)
        self.state = JobState.completed
        self.stopped_at = timezone.now()
        self.save()

    def mark_error(self):
        # TODO add checks, lock? (maybe at higher level)
        self.state = JobState.error
        self.stopped_at = timezone.now()
        self.save()


class JobLog(models.Model):
    job = models.ForeignKey(
        "core.Job",
        on_delete=models.CASCADE,
    )

    # TODO we dont need this
    timestamp = models.DateTimeField(_("Time"), auto_now_add=True, db_index=True)

    level = models.CharField(
        _("Level"),
        max_length=32,
        default=JobLogLevel.info,
        choices=JobLogLevel.choices,
        db_index=True,
    )

    message = models.TextField(_("Message"), default="")

    # TODO we probably want to register more fields, like the sub catalog, object uri etc

    def message_trim_line(self):
        return self.message.splitlines()[0][:32]

    message_trim_line.short_description = _("Message")
    message_trim_line.admin_order_field = "message"

    def get_level_icon(self):
        return JobLogLevel.get_icon(self.level)

    get_level_icon.short_description = _("Level")
    get_level_icon.admin_order_field = "level"

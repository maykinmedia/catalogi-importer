from urllib.parse import urljoin

from django.contrib.postgres.fields import JSONField
from django.core.exceptions import ValidationError
from django.core.validators import (
    FileExtensionValidator,
    MaxValueValidator,
    MinValueValidator,
)
from django.db import models
from django.utils import timezone
from django.utils.encoding import force_text
from django.utils.translation import gettext_lazy as _

from requests.exceptions import ConnectionError
from solo.models import SingletonModel
from zds_client import ClientError, get_operation_url
from zgw_consumers.constants import APITypes
from zgw_consumers.models import Service

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
    service = models.ForeignKey(
        "zgw_consumers.Service",
        on_delete=models.PROTECT,
        limit_choices_to={"api_type": APITypes.ztc},
    )
    uuid = models.UUIDField(
        _("UUID"),
        help_text=_("The UUID of the catalog in the Catalog API"),
    )
    label = models.CharField(
        _("Label"),
        max_length=255,
        help_text=_("Human readable label."),
    )
    url = models.URLField(
        _("Cached URL"),
        max_length=255,
        blank=True,
        editable=False,
    )
    _cached_domein = models.CharField(
        _("domein"),
        max_length=5,
        blank=True,
        editable=False,
    )
    _cached_rsin = models.CharField(
        _("rsin"),
        max_length=9,
        blank=True,
        editable=False,
    )

    class Meta:
        verbose_name = _("Catalog configuration")

    def clean(self):
        super().clean()

        try:
            client = self.service.build_client()
            path = get_operation_url(
                client.schema,
                "catalogus_read",
                base_url=client.base_url,
                uuid=self.uuid,
            )
            url = urljoin(client.base_url, path)
            catalog = client.retrieve("catalogus", url=url)
        except ConnectionError:
            raise ValidationError(
                _("Cannot verify Catalog: check the Service is configured correctly"),
                code="invalid",
            )
        except ClientError:
            raise ValidationError(
                _(
                    "Cannot verify Catalog: check UUID is valid and exists in the selected service"
                ),
                code="invalid",
            )
        else:
            self.url = url
            self._cached_rsin = catalog["rsin"]
            self._cached_domein = catalog["domein"]

    def __str__(self):
        return self.label


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
    statistics = JSONField(
        _("Statistics"),
        default=dict,
        blank=True,
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
        # validity is checked at higher level
        self.state = JobState.running
        self.started_at = timezone.now()
        self.save()

    def mark_completed(self):
        # validity is checked at higher level
        self.state = JobState.completed
        self.stopped_at = timezone.now()
        self.save()

    def mark_error(self):
        # validity is checked at higher level)
        self.state = JobState.error
        self.stopped_at = timezone.now()
        self.save()

    def add_log(self, level, message):
        assert level in JobLogLevel.values, f"'{level}' is not a valid {JobLogLevel}"
        self.joblog_set.create(level=level, message=message)

    def set_statistics(self, statistics):
        assert isinstance(statistics, dict)
        self.statistics = statistics
        self.save(update_fields=("statistics",))

    def get_duration(self):
        if self.started_at and self.stopped_at:
            return self.stopped_at - self.started_at
        else:
            return None

    get_duration.short_description = _("Job Duration")

    def get_duration_display(self):
        duration = self.get_duration()
        if duration:
            return str(duration)
        elif self.started_at:
            return ".."
        else:
            return "-"

    get_duration_display.short_description = _("Job Duration")


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

    def message_trim_line(self, length=32):
        return self.message.splitlines()[0][:length]

    message_trim_line.short_description = _("Message")
    message_trim_line.admin_order_field = "message"

    def get_level_icon(self):
        return JobLogLevel.get_icon(self.level)

    get_level_icon.short_description = _("Level")
    get_level_icon.admin_order_field = "level"

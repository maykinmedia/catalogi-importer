from datetime import timedelta
from random import randint

from django.utils import timezone

import factory
import pytz
from zgw_consumers.constants import APITypes
from zgw_consumers.models import Service

from importer.core.choices import JobLogLevel, JobState
from importer.core.constants import ObjectTypenKeys
from importer.core.models import CatalogConfig, Job, JobLog


class ZGWServiceFactory(factory.django.DjangoModelFactory):
    label = factory.Faker("words")
    api_root = "http://test/api/"
    oas = "http://test/api/schema.yaml"
    api_type = APITypes.ztc

    class Meta:
        model = Service
        django_get_or_create = ("api_root",)


class CatalogConfigFactory(factory.django.DjangoModelFactory):
    uuid = factory.Faker("uuid4")
    service = factory.SubFactory(ZGWServiceFactory)
    label = factory.Faker("words")

    class Meta:
        model = CatalogConfig


class JobFactory(factory.django.DjangoModelFactory):
    catalog = factory.SubFactory(CatalogConfigFactory)
    # TODO source should be a factory.FileField
    source = factory.Faker("file_name", category="text", extension="xml")
    year = 2020
    state = JobState.initialized

    created_at = factory.Faker(
        "date_time_between", start_date="-1d", end_date="-1h", tzinfo=pytz.utc
    )

    class Meta:
        model = Job


class CheckingJobFactory(JobFactory):
    state = JobState.running
    statistics = {
        "data": {
            ObjectTypenKeys.statustypen: {
                "created": 10,
                "updated": 20,
                "errored": 5,
                "counted": 35,
                "issues": {JobLogLevel.warning: 3},
            },
            ObjectTypenKeys.roltypen: {
                "created": 1,
                "updated": 2,
                "errored": 3,
                "counted": 6,
                "issues": {JobLogLevel.warning: 2, JobLogLevel.error: 1},
            },
        }
    }


class PrecheckJobFactory(CheckingJobFactory):
    state = JobState.precheck


class RunningJobFactory(CheckingJobFactory):
    state = JobState.running
    started_at = factory.LazyAttribute(
        lambda obj: obj.created_at + timedelta(minutes=randint(1, 15))
    )


class CompletedJobFactory(RunningJobFactory):
    state = JobState.completed
    stopped_at = factory.LazyAttribute(
        lambda obj: obj.started_at + timedelta(minutes=randint(1, 15))
    )


class ErrorJobFactory(CompletedJobFactory):
    state = JobState.error


class JobLogFactory(factory.django.DjangoModelFactory):
    job = factory.SubFactory(JobFactory)
    level = JobLogLevel.warning
    timestamp = timezone.now()
    message = "an important message"

    class Meta:
        model = JobLog

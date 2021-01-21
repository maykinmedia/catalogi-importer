from datetime import timedelta
from random import randint

import factory
import pytz

from importer.core.choices import JobState
from importer.core.models import CatalogConfig, Job


class CatalogConfigFactory(factory.django.DjangoModelFactory):
    url = factory.Faker("url")
    label = factory.Faker("words")

    class Meta:
        model = CatalogConfig


class JobFactory(factory.django.DjangoModelFactory):
    catalog = factory.SubFactory(CatalogConfigFactory)
    source = factory.Faker("file_name", category="text", extension="xml")
    year = factory.Faker("year")
    state = JobState.precheck

    created_at = factory.Faker(
        "date_time_between", start_date="-1d", end_date="-1h", tzinfo=pytz.utc
    )

    class Meta:
        model = Job


class QueuedJobFactory(JobFactory):
    state = JobState.queued


class RunningJobFactory(JobFactory):
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

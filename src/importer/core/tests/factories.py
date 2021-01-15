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
    state = JobState.queued

    created_at = factory.Faker("past_datetime", tzinfo=pytz.utc)

    class Meta:
        model = Job

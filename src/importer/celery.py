import logging

from celery import Celery

from importer.setup import setup_env

logger = logging.getLogger(__name__)


setup_env()

app = Celery("importer")

app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()

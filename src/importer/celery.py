import logging
import os

from celery import Celery
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

load_dotenv()

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "importer.conf.dev")

app = Celery("importer")

app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()

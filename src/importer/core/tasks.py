import logging
import random
import time

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from celery import shared_task
from faker import Faker

from importer.core.choices import JobLogLevel, JobState
from importer.core.models import Job

logger = logging.getLogger(__name__)


@shared_task
def import_job_task(job_id):
    """
    task wrapper to run the import as a task, manage state etc
    """
    start_time = time.monotonic()

    # acquire the lock on queued job and put in running state
    with transaction.atomic():
        try:
            job = Job.objects.only("id", "state").select_for_update().get(id=job_id)
        except Job.DoesNotExist:
            logger.warning(f"[Job#{job_id}] not found")
            return

        if job.state != JobState.queued:
            logger.warning(f"[Job#{job_id}] not in state 'queued'")
            return
        else:
            job.mark_running()
            logger.info(f"[Job#{job_id}] running")

    try:
        # fetch full job after the locking transaction
        job = Job.objects.select_related("catalog").get(id=job_id)

        import_job(job)
        # raise IOError('foo')
        job.mark_completed()
        logger.info(f"[Job#{job_id}] completed")

    except Exception:
        job.mark_error()
        logger.exception(f"[Job#{job_id}] exception")
        if settings.DEBUG:
            raise

    duration = time.monotonic() - start_time
    if duration > 300:
        duration = f"{round(duration/60)} minutes"
    else:
        duration = f"{round(duration)} seconds"

    logger.info(f"[Job#{job_id}] task duration {duration}")


def import_job(job):
    f = Faker()

    for i in range(0, random.randint(5, 20)):
        job.joblog_set.create(
            level=random.choice(list(JobLogLevel.values.keys())),
            message=f.paragraph(),
            timestamp=timezone.now(),
        )
        time.sleep(1)

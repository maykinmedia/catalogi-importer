import logging
import time

from django.conf import settings
from django.db import transaction

from celery import shared_task

from importer.core.choices import JobState
from importer.core.importer import precheck_import, run_import
from importer.core.models import Job

logger = logging.getLogger(__name__)


@shared_task
def precheck_job_task(job_id):
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

        if job.state != JobState.initialized:
            logger.warning(f"[Job#{job_id}] not in state 'initialized'")
            return
        else:
            job.mark_checking()
            logger.info(f"[Job#{job_id}] running")

    try:
        # fetch full job after the locking transaction
        job = Job.objects.select_related("catalog", "catalog__service").get(
            id=job_id, state=JobState.checking
        )

        # run the precheck
        precheck_import(job)

        job.mark_precheck()
        job.save()
        logger.info(f"[Job#{job_id}] prechecked")

    except Exception:
        job.mark_error()
        job.save()
        logger.exception(f"[Job#{job_id}] exception")
        if settings.DEBUG:
            raise

    duration = time.monotonic() - start_time
    logger.info(f"[Job#{job_id}] task duration {str(duration)}")


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
        job = Job.objects.select_related("catalog", "catalog__service").get(
            id=job_id, state=JobState.running
        )

        # run the importer
        run_import(job)

        job.mark_completed()
        job.save()
        logger.info(f"[Job#{job_id}] completed")

    except Exception:
        job.mark_error()
        job.save()
        logger.exception(f"[Job#{job_id}] exception")
        if settings.DEBUG:
            raise

    duration = time.monotonic() - start_time
    logger.info(f"[Job#{job_id}] task duration {str(duration)}")

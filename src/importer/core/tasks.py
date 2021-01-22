import logging
import random
import time

from django.conf import settings
from django.db import transaction

from celery import shared_task
from faker import Faker

from importer.core.choices import JobLogLevel, JobState
from importer.core.constants import ObjectTypenKeys
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
        job = Job.objects.select_related("catalog").get(
            id=job_id, state=JobState.running
        )

        # run the importer
        import_job(job)

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
    # TODO swap fake for real import
    f = Faker()

    lim = random.randint(10, 20)

    for i in range(0, lim + 1):
        job.add_log(random.choice(list(JobLogLevel.values.keys())), f.paragraph())
        r = i / lim
        results = {
            "data": {
                ObjectTypenKeys.roltypen: (round(r * 10), 10, None),
                ObjectTypenKeys.statustypen: (round(r * 33), 33, None),
                ObjectTypenKeys.resultaattypen: (
                    round(r * 23),
                    23,
                    {JobLogLevel.warning: round(r * 2)},
                ),
                ObjectTypenKeys.informatieobjecttypen: (round(r * 40), 40, None),
                ObjectTypenKeys.zaakinformatieobjecttypen: (
                    round(r * 50),
                    50,
                    {JobLogLevel.warning: round(r * 4)},
                ),
            },
        }
        job.set_results(results)
        time.sleep(1)

    results = {
        "data": {
            ObjectTypenKeys.roltypen: (10, 10, None),
            ObjectTypenKeys.statustypen: (20, 20, None),
            ObjectTypenKeys.resultaattypen: (
                30,
                30,
                {JobLogLevel.warning: 2, JobLogLevel.error: 1},
            ),
            ObjectTypenKeys.informatieobjecttypen: (40, 40, None),
            ObjectTypenKeys.zaakinformatieobjecttypen: (
                50,
                50,
                {JobLogLevel.warning: 5},
            ),
        },
    }
    job.set_results(results)
    time.sleep(1)

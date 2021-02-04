from django.core.management import BaseCommand

from importer.core.choices import JobState
from importer.core.models import Job
from importer.core.tasks import import_job_task


class Command(BaseCommand):
    help = "Manually start a 'queued' Job (for development and debugging purposes)"

    def add_arguments(self, parser):
        parser.add_argument("job_id", type=int)
        parser.add_argument("--run", action="store_true", default=False)

    def handle(self, **options):
        job_id = options["job_id"]
        if options["run"]:
            job = Job.objects.get(id=job_id)
            job.joblog_set.all().delete()
            job.state = JobState.queued
            job.save()
        import_job_task(job_id)

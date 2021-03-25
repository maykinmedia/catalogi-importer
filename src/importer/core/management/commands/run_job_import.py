from django.core.management import BaseCommand

from importer.core.choices import JobState
from importer.core.models import Job
from importer.core.tasks import import_job_task


class Command(BaseCommand):
    help = "Manually start a 'queued' Job (for development and debugging purposes)"

    def add_arguments(self, parser):
        parser.add_argument("job_id", type=int)
        parser.add_argument("--queue", action="store_true", default=False)

    def handle(self, **options):
        job_id = options["job_id"]
        try:
            job = Job.objects.get(id=job_id)
        except Job.DoesNotExist:
            self.stdout.print(f"Job {job_id} not found")
            exit(1)
        else:
            job.joblog_set.all().delete()
            job.state = JobState.queued
            job.save()

            if options["queue"]:
                import_job_task.delay(job_id)
            else:
                import_job_task(job_id)

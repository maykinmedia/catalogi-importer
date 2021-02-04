from django.core.management import BaseCommand

from importer.core.choices import JobState
from importer.core.models import Job
from importer.core.tasks import import_job_task


class Command(BaseCommand):
    help = "Manually reset Job state and optionally run (for development and debugging purposes)"

    def add_arguments(self, parser):
        parser.add_argument("job_id", action="store", type=int)
        parser.add_argument(
            "--state",
            action="store",
            default=JobState.precheck,
            choices=list(JobState.values.keys()),
        )
        parser.add_argument("--run", action="store_true", default=False)

    def handle(self, **options):
        job_id = options["job_id"]
        state = options["state"]
        if options["run"]:
            state = JobState.queued

        try:
            job = Job.objects.get(id=job_id)
        except Job.DoesNotExist:
            self.stderr.write(f"[Job#{job_id}] not found")
        else:
            job.state = state
            job.save()
            job.joblog_set.all().delete()
            if options["run"]:
                import_job_task.delay(job.id)

from django.core.management import BaseCommand

from importer.core.tasks import import_job_task


class Command(BaseCommand):
    help = "Manually start a 'queued' Job (for development and debugging purposes)"

    def add_arguments(self, parser):
        parser.add_argument("job_id", type=int)

    def handle(self, **options):
        job_id = options["job_id"]
        import_job_task(job_id)

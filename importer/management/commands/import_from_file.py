from django.core.management import BaseCommand

from ...importer import import_from_xml


class Command(BaseCommand):
    help = "Load data from xml file to Catalogi API"

    def add_arguments(self, parser):
        parser.add_argument("file")

    def handle(self, **options):
        file = options["file"]

        # parse to python primitives
        zaaktypen = import_from_xml(file)

        self.stdout.write(f"zaaktypen={zaaktypen}")

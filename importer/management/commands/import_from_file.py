from django.core.management import BaseCommand

from ...importer import import_from_xml


class Command(BaseCommand):
    help = "Load data from xml file to Catalogi API"

    def add_arguments(self, parser):
        parser.add_argument("file")
        parser.add_argument("catalogus")
        parser.add_argument("year")

    def handle(self, **options):
        file = options["file"]
        catalogus = options["catalogus"]
        year = int(options["year"])

        # parse to python primitives
        import_from_xml(file, catalogus, year)

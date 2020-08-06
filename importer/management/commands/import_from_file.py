from django.core.management import BaseCommand

from ...importer import import_from_xml


class Command(BaseCommand):
    help = "Load data from xml file to Catalogi API"

    def add_arguments(self, parser):
        parser.add_argument("file")
        parser.add_argument("catalogus")

    def handle(self, **options):
        file = options["file"]
        catalogus = options["catalogus"]

        # parse to python primitives
        import_from_xml(file, catalogus)

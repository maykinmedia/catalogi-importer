from django.apps import AppConfig


class UtilsConfig(AppConfig):
    name = "importer.utils"

    def ready(self):
        from . import checks  # noqa

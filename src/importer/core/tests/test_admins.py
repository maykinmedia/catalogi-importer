from django.contrib import admin
from django.test import TestCase

from zgw_consumers.models import Service

from importer.core.admin import CatalogConfigAdmin
from importer.core.models import CatalogConfig
from importer.core.tests.factories import CatalogConfigFactory


class CatalogConfigAdminTests(TestCase):
    def test_has_credentials(self):
        catalog = CatalogConfigFactory(url="https://foo/api/catalog")
        model_admin = CatalogConfigAdmin(CatalogConfig, admin.site)

        self.assertFalse(model_admin.has_credentials(catalog))

        # add matching Service and check again
        Service.objects.create(api_root="https://foo/api/")
        self.assertTrue(model_admin.has_credentials(catalog))

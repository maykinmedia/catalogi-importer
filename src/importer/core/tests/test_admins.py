from django.contrib import admin
from django.test import TestCase

from webtest import Upload
from zgw_consumers.models import Service

from importer.core.admin import CatalogConfigAdmin
from importer.core.choices import JobState
from importer.core.models import CatalogConfig, Job
from importer.core.tests.base import AdminWebTest
from importer.core.tests.factories import (
    CatalogConfigFactory,
    CompletedJobFactory,
    ErrorJobFactory,
    JobFactory,
    RunningJobFactory,
)


class CatalogConfigAdminViewTest(AdminWebTest):
    def test_list_view(self):
        self.assertAdminChangeList(CatalogConfig, check_search=False)

    def test_add_view(self):
        response = self.app.get(self.reverse_add_url(CatalogConfig))
        self.assertEqual(response.status_code, 200)

    def test_change_view(self):
        catalog = CatalogConfigFactory()
        response = self.app.get(self.reverse_change_url(catalog))
        self.assertEqual(response.status_code, 200)

    def test_has_credentials_helper(self):
        catalog = CatalogConfigFactory(url="https://foo/api/catalog")
        model_admin = CatalogConfigAdmin(CatalogConfig, admin.site)

        self.assertFalse(model_admin.has_credentials(catalog))

        # add matching Service and check again
        Service.objects.create(api_root="https://foo/api/")
        self.assertTrue(model_admin.has_credentials(catalog))


class JobAdminViewTest(AdminWebTest):
    def test_list_view(self):
        self.assertAdminChangeList(Job, check_search=False)

    def test_add_view(self):
        catalog = CatalogConfigFactory()

        response = self.app.get(self.reverse_add_url(Job))
        self.assertEqual(response.status_code, 200)

        form = response.form
        form["catalog"].select(value=catalog.id)
        form["year"] = 2021
        form["source"] = Upload("export.xml", b"data", "text/xml")

        response = form.submit()

        job = Job.objects.get()
        self.assertEqual(job.year, 2021)
        self.assertEqual(job.catalog, catalog)
        with job.source.open():
            content = job.source.read()
            self.assertEqual(content, b"data")

    def assertJobReadonlyFields(self, response):
        self.assertPyQueryNotExists(response, "input[type='submit']")
        form = response.form
        self.assertEqual(set(form.fields.keys()), {"csrfmiddlewaretoken"})

        self.assertRowExistsReadonly(response, "catalog_fmt")
        self.assertRowExistsReadonly(response, "year_fmt")
        self.assertRowExistsReadonly(response, "source")
        self.assertRowExistsReadonly(response, "state")
        self.assertRowExistsReadonly(response, "created_at")

    def test_change_queued(self):
        job = JobFactory()
        response = self.app.get(self.reverse_change_url(job))
        self.assertEqual(response.status_code, 200)

        # readonly mode
        self.assertJobReadonlyFields(response)
        self.assertRowNotExists(response, "started_at")
        self.assertRowNotExists(response, "stopped_at")

    def test_change_running(self):
        job = RunningJobFactory()
        response = self.app.get(self.reverse_change_url(job))
        self.assertEqual(response.status_code, 200)

        # readonly mode
        self.assertJobReadonlyFields(response)
        self.assertRowExistsReadonly(response, "started_at")
        self.assertRowNotExists(response, "stopped_at")

    def test_change_completed(self):
        job = CompletedJobFactory()
        response = self.app.get(self.reverse_change_url(job))
        self.assertEqual(response.status_code, 200)

        # readonly mode
        self.assertJobReadonlyFields(response)
        self.assertRowExistsReadonly(response, "started_at")
        self.assertRowExistsReadonly(response, "stopped_at")

    def test_change_error(self):
        job = ErrorJobFactory()
        response = self.app.get(self.reverse_change_url(job))
        self.assertEqual(response.status_code, 200)

        # readonly mode
        self.assertJobReadonlyFields(response)
        self.assertRowExistsReadonly(response, "started_at")
        self.assertRowExistsReadonly(response, "stopped_at")

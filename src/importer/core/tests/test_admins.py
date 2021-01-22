from io import BytesIO

from django.contrib import admin
from django.core.files import File

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
    JobLogFactory,
    QueuedJobFactory,
    RunningJobFactory,
)


class SelectielijstAdminViewTest(AdminWebTest):
    def test_list_view(self):
        self.assertAdminChangeList(CatalogConfig, check_search=False)

    def test_add_view(self):
        self.app.get(self.reverse_add_url(CatalogConfig))

    def test_change_view(self):
        catalog = CatalogConfigFactory()
        self.app.get(self.reverse_change_url(catalog))


class CatalogConfigAdminViewTest(AdminWebTest):
    def test_list_view(self):
        self.assertAdminChangeList(CatalogConfig, check_search=False)

    def test_add_view(self):
        self.app.get(self.reverse_add_url(CatalogConfig))

    def test_change_view(self):
        catalog = CatalogConfigFactory()
        self.app.get(self.reverse_change_url(catalog))

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

        form = response.form
        form["catalog"].select(value=catalog.id)
        form["year"] = 2021
        form["source"] = Upload("export.xml", b"data", "text/xml")

        response = form.submit()

        job = Job.objects.get()
        self.assertEqual(job.year, 2021)
        self.assertEqual(job.catalog, catalog)
        self.assertEqual(job.state, JobState.precheck)
        self.assertEqual(job.source.read(), b"data")

        # verify we use Save & Continue to return to change page
        self.assertRedirects(response, self.reverse_change_url(job))

    def test_source_link(self):
        job = CompletedJobFactory()
        job.source.save("foo.xml", File(BytesIO(b"data")))

        response = self.app.get(self.reverse_change_url(job))
        link = response.pyquery(".form-row.field-source_fmt div.readonly a")[0]
        url = link.attrib["href"]
        self.assertIn("/private_files/", url)
        response = self.app.get(url, status=200)
        self.assertEqual(response.body, b"data")

    def test_change_precheck(self):
        job = JobFactory()
        response = self.app.get(self.reverse_change_url(job))

        # readonly mode
        self.assertFormHasNoFields(response, allow_fields=["state", "_continue"])
        self.assertSubmitButtonExists(response)

        self.assertFormRowNotExists(response, "catalog_fmt")
        self.assertFormRowNotExists(response, "year_fmt")
        self.assertFormRowNotExists(response, "source_fmt")
        self.assertFormRowNotExists(response, "created_at")
        self.assertFormRowNotExists(response, "started_at")
        self.assertFormRowNotExists(response, "stopped_at")

        # TODO verify content
        self.assertPyQueryExists(response, ".value-display-table .form-row")
        self.assertPyQueryExists(response, ".joblog-display-table")

    def test_change_queued(self):
        job = QueuedJobFactory()
        response = self.app.get(self.reverse_change_url(job))

        # readonly mode
        self.assertFormHasNoFields(response)
        self.assertSubmitButtonNotExists(response)

        self.assertFormRowReadonly(response, "catalog_fmt")
        self.assertFormRowReadonly(response, "year_fmt")
        self.assertFormRowReadonly(response, "source_fmt")
        self.assertFormRowReadonly(response, "created_at")
        self.assertFormRowReadonly(response, "state")

        self.assertFormRowNotExists(response, "started_at")
        self.assertFormRowNotExists(response, "stopped_at")

        self.assertPyQueryNotExists(response, ".value-display-table")
        self.assertPyQueryNotExists(response, ".joblog-display-table")

    def test_change_running(self):
        job = RunningJobFactory()
        response = self.app.get(self.reverse_change_url(job))

        # readonly mode
        self.assertFormHasNoFields(response)
        self.assertSubmitButtonNotExists(response)

        self.assertFormRowReadonly(response, "catalog_fmt")
        self.assertFormRowReadonly(response, "year_fmt")
        self.assertFormRowReadonly(response, "source_fmt")
        self.assertFormRowReadonly(response, "created_at")
        self.assertFormRowReadonly(response, "state")
        self.assertFormRowReadonly(response, "started_at")

        self.assertFormRowNotExists(response, "stopped_at")

        # TODO verify content
        self.assertPyQueryExists(response, ".value-display-table .form-row")
        self.assertPyQueryNotExists(response, ".joblog-display-table")

    def test_change_completed(self):
        job = CompletedJobFactory()
        logs = [JobLogFactory(job=job) for _ in range(3)]
        response = self.app.get(self.reverse_change_url(job))

        # readonly mode
        self.assertFormHasNoFields(response)
        self.assertSubmitButtonNotExists(response)

        self.assertFormRowReadonly(response, "catalog_fmt")
        self.assertFormRowReadonly(response, "year_fmt")
        self.assertFormRowReadonly(response, "source_fmt")
        self.assertFormRowReadonly(response, "created_at")
        self.assertFormRowReadonly(response, "state")
        self.assertFormRowReadonly(response, "started_at")
        self.assertFormRowReadonly(response, "stopped_at")

        self.assertPyQueryExists(response, ".value-display-table .form-row")
        self.assertPyQueryExists(response, ".joblog-display-table")

    def test_change_error(self):
        job = ErrorJobFactory()
        logs = [JobLogFactory(job=job) for _ in range(3)]
        response = self.app.get(self.reverse_change_url(job))

        # readonly mode
        self.assertFormHasNoFields(response)
        self.assertSubmitButtonNotExists(response)

        self.assertFormRowReadonly(response, "catalog_fmt")
        self.assertFormRowReadonly(response, "year_fmt")
        self.assertFormRowReadonly(response, "source_fmt")
        self.assertFormRowReadonly(response, "created_at")
        self.assertFormRowReadonly(response, "state")
        self.assertFormRowReadonly(response, "started_at")
        self.assertFormRowReadonly(response, "stopped_at")

        self.assertPyQueryExists(response, ".value-display-table .form-row")
        self.assertPyQueryExists(response, ".joblog-display-table")

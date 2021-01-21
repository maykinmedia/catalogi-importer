from django.contrib import admin
from django.urls import reverse

from django_webtest import WebTest
from webtest import Upload
from zgw_consumers.models import Service

from importer.accounts.tests.factories import StaffUserFactory, UserFactory
from importer.core.admin import CatalogConfigAdmin
from importer.core.choices import JobState
from importer.core.models import CatalogConfig, Job
from importer.core.tests.base import AdminWebTest
from importer.core.tests.factories import (
    CatalogConfigFactory,
    CompletedJobFactory,
    ErrorJobFactory,
    JobFactory,
    QueuedJobFactory,
    RunningJobFactory,
)


class CatalogConfigAdminViewTest(AdminWebTest):
    def test_list_view(self):
        self.assertAdminChangeList(CatalogConfig, check_search=False)

    def test_add_view(self):
        response = self.app.get(self.reverse_add_url(CatalogConfig))

    def test_change_view(self):
        catalog = CatalogConfigFactory()
        response = self.app.get(self.reverse_change_url(catalog))

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

        # check the created object
        job = Job.objects.get()
        self.assertEqual(job.year, 2021)
        self.assertEqual(job.catalog, catalog)
        self.assertEqual(job.state, JobState.precheck)
        job.source.open("rb")
        content = job.source.read()
        self.assertEqual(content, b"data")

        # check if file is linked
        response = self.app.get(self.reverse_change_url(job))
        link = response.pyquery(".form-row.field-source_fmt div.readonly a")[0]
        url = link.attrib["href"]
        self.assertIn("private_files/", url)
        response = self.app.get(url, status=200)
        self.assertEqual(response.body, b"data")

    def assertSubmitButtonExists(self, response):
        self.assertPyQueryExists(response, "input[type='submit']")

    def assertSubmitButtonNotExists(self, response):
        self.assertPyQueryNotExists(response, "input[type='submit']")

    def assertJobCommonReadonlyFields(self, response, allow_fields=None):
        form = response.form
        expect_fields = {"csrfmiddlewaretoken"}
        if allow_fields:
            expect_fields |= set(allow_fields)

        self.assertEqual(set(form.fields.keys()), expect_fields)

        self.assertRowExistsReadonly(response, "catalog_fmt")
        self.assertRowExistsReadonly(response, "year_fmt")
        self.assertRowExistsReadonly(response, "source_fmt")
        self.assertRowExistsReadonly(response, "created_at")

    def test_change_precheck(self):
        job = JobFactory()
        response = self.app.get(self.reverse_change_url(job))

        # readonly mode
        self.assertSubmitButtonExists(response)
        self.assertJobCommonReadonlyFields(
            response, allow_fields=["state", "_continue"]
        )
        self.assertRowNotExists(response, "started_at")
        self.assertRowNotExists(response, "stopped_at")

        # TODO verify content
        self.assertPyQueryExists(response, ".value-display h1")
        self.assertPyQueryExists(response, ".value-display-table .form-row")

    def test_change_queued(self):
        job = QueuedJobFactory()
        response = self.app.get(self.reverse_change_url(job))

        # readonly mode
        self.assertSubmitButtonNotExists(response)
        self.assertJobCommonReadonlyFields(response)
        self.assertRowExistsReadonly(response, "state")
        self.assertRowNotExists(response, "started_at")
        self.assertRowNotExists(response, "stopped_at")

    def test_change_running(self):
        job = RunningJobFactory()
        response = self.app.get(self.reverse_change_url(job))

        # readonly mode
        self.assertSubmitButtonNotExists(response)
        self.assertJobCommonReadonlyFields(response)
        self.assertRowExistsReadonly(response, "state")
        self.assertRowExistsReadonly(response, "started_at")
        self.assertRowNotExists(response, "stopped_at")

        # TODO verify content
        self.assertPyQueryExists(response, ".value-display h1")
        self.assertPyQueryExists(response, ".value-display-table .form-row")

    def test_change_completed(self):
        job = CompletedJobFactory()
        response = self.app.get(self.reverse_change_url(job))

        # readonly mode
        self.assertSubmitButtonNotExists(response)
        self.assertJobCommonReadonlyFields(response)
        self.assertRowExistsReadonly(response, "state")
        self.assertRowExistsReadonly(response, "started_at")
        self.assertRowExistsReadonly(response, "stopped_at")

    def test_change_error(self):
        job = ErrorJobFactory()
        response = self.app.get(self.reverse_change_url(job))

        # readonly mode
        self.assertSubmitButtonNotExists(response)
        self.assertJobCommonReadonlyFields(response)
        self.assertRowExistsReadonly(response, "state")
        self.assertRowExistsReadonly(response, "started_at")
        self.assertRowExistsReadonly(response, "stopped_at")


class PrivateStorageTest(WebTest):
    def test_private_file_requires_staff(self):
        url = reverse("staff_private_file", kwargs=dict(path="x/y.z"))

        # anonymous
        self.app.get(url, status=403)

        # not staff
        self.app.set_user(UserFactory())
        self.app.get(url, status=403)

        # allowed, expect 404 because file doesn't exist
        self.app.set_user(StaffUserFactory())
        self.app.get(url, status=404)

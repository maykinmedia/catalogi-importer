import os
from io import BytesIO

from django.contrib import admin
from django.core.files import File
from django.core.files.base import ContentFile
from django.test import TestCase
from django.utils.translation import gettext as _

from webtest import Upload
from zgw_consumers.models import Service

from importer.core.admin import CatalogConfigAdmin, transform_statistics
from importer.core.choices import JobLogLevel, JobState
from importer.core.constants import ObjectTypenKeys
from importer.core.models import CatalogConfig, Job, SelectielijstConfig
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
        self.assertAdminChangeList(SelectielijstConfig, check_search=False)

    def test_change_view(self):
        catalog = SelectielijstConfig.objects.create()
        self.app.get(self.reverse_change_url(SelectielijstConfig))


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
    def get_test_data(self, file, mode="rb"):
        with open(os.path.join(os.path.dirname(__file__), "data", file), mode) as f:
            return f.read()

    def test_list_view(self):
        self.assertAdminChangeList(Job, check_search=False)

    def test_add_view(self):
        xml_data = self.get_test_data("minimal.xml")
        catalog = CatalogConfigFactory()

        response = self.app.get(self.reverse_add_url(Job))

        form = response.form
        form["catalog"].select(value=catalog.id)
        form["year"] = 2021
        form["source"] = Upload("export.xml", xml_data, "text/xml")

        response = form.submit()

        job = Job.objects.get()
        self.assertEqual(job.year, 2021)
        self.assertEqual(job.catalog, catalog)
        self.assertEqual(job.state, JobState.precheck)
        self.assertEqual(job.source.read(), xml_data)

        # verify we use Save & Continue to return to change page
        self.assertRedirects(response, self.reverse_change_url(job))

    def test_source_link(self):
        xml_data = self.get_test_data("minimal.xml")
        job = CompletedJobFactory()
        job.source.save("foo.xml", ContentFile(xml_data))

        response = self.app.get(self.reverse_change_url(job))
        link = response.pyquery(".form-row.field-source_fmt div.readonly a")[0]
        url = link.attrib["href"]
        self.assertIn("/private_files/", url)
        response = self.app.get(url, status=200)
        self.assertEqual(response.body, xml_data)

    def test_change_precheck(self):
        job = JobFactory()
        job.source.save("foo.xml", ContentFile(self.get_test_data("minimal.xml")))
        response = self.app.get(self.reverse_change_url(job))

        # readonly mode
        self.assertFormHasNoFields(response, allow_fields=["state", "_continue"])
        self.assertSubmitButtonExists(response)

        self.assertFormRowReadonly(response, "catalog_fmt")
        self.assertFormRowReadonly(response, "year_fmt")
        self.assertFormRowReadonly(response, "source_fmt")
        self.assertFormRowReadonly(response, "created_at")
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
        self.assertFormRowReadonly(response, "state")
        self.assertFormRowReadonly(response, "created_at")
        self.assertFormRowReadonly(response, "started_at", "-")
        self.assertFormRowReadonly(response, "stopped_at", "-")

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
        self.assertFormRowReadonly(response, "state")
        self.assertFormRowReadonly(response, "created_at")
        self.assertFormRowReadonly(response, "started_at")
        self.assertFormRowReadonly(response, "stopped_at", "-")

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


class JobAdminViewUtilsTest(TestCase):
    def test_transform_statistics(self):
        data = {
            "data": {
                ObjectTypenKeys.resultaattypen: (
                    28,
                    30,
                    {JobLogLevel.warning: 2, JobLogLevel.error: 1},
                ),
                ObjectTypenKeys.informatieobjecttypen: (38, 40, None),
                ObjectTypenKeys.zaakinformatieobjecttypen: (
                    48,
                    50,
                    {JobLogLevel.warning: 5},
                ),
                ObjectTypenKeys.zaaktypen: (1, 3),
                ObjectTypenKeys.roltypen: (8, 10),
                ObjectTypenKeys.statustypen: (18, 20),
            },
        }
        expected = [
            (_("Roltypen"), "8 / 10"),
            (_("Zaaktypen"), "1 / 3"),
            (_("Statustypen"), "18 / 20"),
            (_("Resultaattypen"), "28 / 30 (2 warnings, 1 errors)"),
            (_("Informatieobjecttypen"), "38 / 40"),
            (_("Zaakinformatieobjecttypen"), "48 / 50 (5 warnings)"),
        ]
        actual = transform_statistics(data)
        self.assertEqual(actual, expected)

    def test_transform_statistics_empty(self):
        expected = [
            (_("Roltypen"), "0 / 0"),
            (_("Zaaktypen"), "0 / 0"),
            (_("Statustypen"), "0 / 0"),
            (_("Resultaattypen"), "0 / 0"),
            (_("Informatieobjecttypen"), "0 / 0"),
            (_("Zaakinformatieobjecttypen"), "0 / 0"),
        ]
        actual = transform_statistics({})
        self.assertEqual(actual, expected)
        actual = transform_statistics({"data": {}})
        self.assertEqual(actual, expected)

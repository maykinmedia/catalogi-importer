from datetime import date

from django.core.files.base import ContentFile

import requests_mock
from webtest import Upload
from zgw_consumers.constants import APITypes

from importer.core.choices import JobState
from importer.core.models import CatalogConfig, Job, SelectielijstConfig
from importer.core.tests.base import AdminWebTest
from importer.core.tests.factories import (
    CatalogConfigFactory,
    CompletedJobFactory,
    ErrorJobFactory,
    JobFactory,
    JobLogFactory,
    RunningJobFactory,
    ZGWServiceFactory,
)

catalog_response = {
    "url": "http://test/api/catalogussen/7c0e6595-adbe-45b4-b092-31ba75c7dd74",
    "domein": "ABCDE",
    "rsin": "407287449",
    "contactpersoonBeheerNaam": "Foo",
    "contactpersoonBeheerTelefoonnummer": "0612345678",
    "contactpersoonBeheerEmailadres": "user@example.com",
    "zaaktypen": [],
    "besluittypen": [],
    "informatieobjecttypen": [],
}


class SelectielijstAdminViewTest(AdminWebTest):
    def test_list_view(self):
        self.assertAdminChangeList(SelectielijstConfig, check_search=False)

    def test_change_view(self):
        self.app.get(self.reverse_change_url(SelectielijstConfig))


class CatalogConfigAdminViewTest(AdminWebTest):
    def test_list_view(self):
        self.assertAdminChangeList(CatalogConfig, check_search=False)

    def test_add_view(self):
        self.app.get(self.reverse_add_url(CatalogConfig))

    @requests_mock.Mocker()
    def test_change_view(self, m):
        m.get(
            "http://test/api/schema.yaml",
            content=self.get_test_data("openzaak-openapi.yaml"),
        )
        m.get(
            "http://test/api/catalogussen/7c0e6595-adbe-45b4-b092-31ba75c7dd74",
            json=catalog_response,
        )
        service = ZGWServiceFactory(
            api_root="http://test/api/",
            oas="http://test/api/schema.yaml",
            api_type=APITypes.ztc,
        )
        catalog = CatalogConfigFactory(
            service=service, uuid="7c0e6595-adbe-45b4-b092-31ba75c7dd74"
        )
        response = self.app.get(self.reverse_change_url(catalog))

        # resubmit
        form = response.form
        form.submit().follow()
        catalog.refresh_from_db()

        # verify we reversed the URL from the service and schema
        self.assertEqual(
            catalog.url,
            "http://test/api/catalogussen/7c0e6595-adbe-45b4-b092-31ba75c7dd74",
        )
        self.assertEqual(catalog._cached_rsin, "407287449")
        self.assertEqual(catalog._cached_domein, "ABCDE")


class JobAdminViewTest(AdminWebTest):
    def test_list_view(self):
        self.assertAdminChangeList(Job, check_search=False)

    def test_add_view(self):
        xml_data = self.get_test_data("minimal.xml")
        catalog = CatalogConfigFactory()

        response = self.app.get(self.reverse_add_url(Job))

        form = response.form
        form["catalog"].select(value=catalog.id)
        form["year"] = 2020
        form["start_date"] = "2020-02-28"
        form["close_published"] = True
        form["source"] = Upload("export.xml", xml_data, "text/xml")

        response = form.submit()

        job = Job.objects.get()
        self.assertEqual(job.year, 2020)
        self.assertEqual(job.catalog, catalog)
        self.assertEqual(job.start_date, date(2020, 2, 28))
        self.assertEqual(job.close_published, True)
        self.assertEqual(job.state, JobState.initialized)
        self.assertEqual(job.source.read(), xml_data)

        # verify we use Save & Continue to return to change page
        self.assertRedirects(response, self.reverse_change_url(job))

    def test_add_view_without_selectielijst(self):
        config = SelectielijstConfig.get_solo()
        config.service = None
        config.save()
        response = self.app.get(self.reverse_add_url(Job))
        self.assertRedirects(response, self.reverse_change_url(config))

    def test_source_link(self):
        xml_data = self.get_test_data("minimal.xml")
        job = CompletedJobFactory()
        job.source.save("foo.xml", ContentFile(xml_data))

        response = self.app.get(self.reverse_change_url(job))
        link = response.pyquery(".form-row.field-source_fmt div.readonly a")[0]
        url = link.attrib["href"]
        self.assertIn("/private_media/", url)
        response = self.app.get(url, status=200)
        self.assertEqual(response.body, xml_data)

    def test_change_initialized(self):
        job = JobFactory()
        job.source.save("foo.xml", ContentFile(self.get_test_data("example.xml")))
        response = self.app.get(self.reverse_change_url(job))

        # readonly mode
        self.assertFormHasNoFields(response)
        self.assertSubmitButtonNotExists(response)

        self.assertPyQueryNotExists(response, ".value-display-table .form-row")
        self.assertPyQueryNotExists(response, ".joblog-display-table")

    def test_change_precheck(self):
        job = JobFactory(state=JobState.precheck)
        logs = [JobLogFactory(job=job) for _ in range(3)]
        job.source.save("foo.xml", ContentFile(self.get_test_data("example.xml")))
        response = self.app.get(self.reverse_change_url(job))

        # readonly mode
        self.assertFormHasNoFields(response, allow_fields=["state", "_continue"])
        self.assertSubmitButtonExists(response)

        self.assertFormRowReadonly(response, "catalog_fmt")
        self.assertFormRowReadonly(response, "year_fmt")
        self.assertFormRowReadonly(response, "source_fmt")
        self.assertFormRowReadonly(response, "created_at")

        self.assertPyQueryExists(response, ".value-display-table tr td")
        self.assertPyQueryExists(response, ".joblog-display-table")

    def test_change_queued(self):
        job = JobFactory(state=JobState.queued)
        response = self.app.get(self.reverse_change_url(job))

        # readonly mode
        self.assertFormHasNoFields(response)
        self.assertSubmitButtonNotExists(response)

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
        self.assertFormRowReadonly(response, "start_date")
        self.assertFormRowReadonly(response, "close_published")
        self.assertFormRowReadonly(response, "created_at")
        self.assertFormRowReadonly(response, "started_at")
        self.assertFormRowReadonly(response, "stopped_at", "-")

        self.assertPyQueryExists(response, ".value-display-table tr td")
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
        self.assertFormRowReadonly(response, "start_date")
        self.assertFormRowReadonly(response, "close_published")
        self.assertFormRowReadonly(response, "started_at")
        self.assertFormRowReadonly(response, "stopped_at")

        self.assertPyQueryExists(response, ".value-display-table tr td")
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
        self.assertFormRowReadonly(response, "start_date")
        self.assertFormRowReadonly(response, "close_published")
        self.assertFormRowReadonly(response, "started_at")
        self.assertFormRowReadonly(response, "stopped_at")

        self.assertPyQueryExists(response, ".value-display-table tr td")
        self.assertPyQueryExists(response, ".joblog-display-table")

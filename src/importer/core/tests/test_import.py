from django.core.files.base import ContentFile
from django.test import TestCase

import requests_mock
from zgw_consumers.constants import APITypes

from importer.core.choices import JobState
from importer.core.tasks import import_job_task
from importer.core.tests.base import TestCaseMixin
from importer.core.tests.factories import (
    CatalogConfigFactory,
    QueuedJobFactory,
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

empty_list_response = {
    "count": 0,
    "results": [],
    "next": None,
    "previous": None,
}

informatieobjecttype_response = {
    "url": "http://test/api/informatieobjecttypen/1",
    "omschrijving": "Onderzoeksstuk",
}
zaaktype_response = {
    "url": "http://test/api/zaaktypen/1",
    "identificatie": "foo",
}
roltype_response = {
    "url": "http://test/api/roltypen/1",
    "omschrijving": "foo",
}
statustype_response = {
    "url": "http://test/api/statustypen/1",
    "volgnummer": 1,
}
resultaattype_response = {
    "url": "http://test/api/resultaattypen/1",
    "omschrijving": "foo",
}
zaaktypeinformatieobjecttype_response = {
    "url": "http://test/api/zaaktypeinformatieobjecttypen/1",
    "zaaktype": "http://test/api/zaaktypen/1",
    "informatieobjecttype": "http://test/api/informatieobjecttypen/1",
    "volgnummer": 1,
}


class ImportTest(TestCaseMixin, TestCase):
    @requests_mock.Mocker()
    def test_positive_flow(self, m):
        self.setup_selectielijst_service()
        self.setup_selectielijst_mocks(m)

        m.get(
            "http://test/api/schema.yaml",
            content=self.get_test_data("openzaak-openapi.yaml"),
        )
        service = ZGWServiceFactory(
            api_root="http://test/api",
            oas="http://test/api/schema.yaml",
            api_type=APITypes.ztc,
        )

        m.get(
            "http://test/api/catalogussen/7c0e6595-adbe-45b4-b092-31ba75c7dd74",
            json=catalog_response,
        )
        catalog = CatalogConfigFactory(
            service=service, uuid="7c0e6595-adbe-45b4-b092-31ba75c7dd74"
        )
        catalog.clean()
        catalog.save()

        self.assertEqual(
            catalog.url,
            "http://test/api/catalogussen/7c0e6595-adbe-45b4-b092-31ba75c7dd74",
        )

        job = QueuedJobFactory(catalog=catalog)
        job.source.save(
            "foo.xml", ContentFile(self.get_test_data("example-stripped-single.xml"))
        )

        m.get(
            "http://test/api/informatieobjecttypen?catalogus=http%3A%2F%2Ftest%2Fapi%2Fcatalogussen%2F7c0e6595-adbe-45b4-b092-31ba75c7dd74&status=alles",
            json=empty_list_response,
        )
        m.post(
            "http://test/api/informatieobjecttypen",
            json=informatieobjecttype_response,
            status_code=201,
        )
        m.get(
            "http://test/api/zaaktypen?identificatie=B1796&catalogus=http%3A%2F%2Ftest%2Fapi%2Fcatalogussen%2F7c0e6595-adbe-45b4-b092-31ba75c7dd74&status=alles",
            json=empty_list_response,
        )
        m.post(
            "http://test/api/zaaktypen",
            json=zaaktype_response,
            status_code=201,
        )
        m.get(
            "http://test/api/roltypen?zaaktype=http%3A%2F%2Ftest%2Fapi%2Fzaaktypen%2F1&status=alles",
            json=empty_list_response,
        )
        m.post(
            "http://test/api/roltypen",
            json=roltype_response,
            status_code=201,
        )
        m.get(
            "http://test/api/statustypen?zaaktype=http%3A%2F%2Ftest%2Fapi%2Fzaaktypen%2F1&status=alles",
            json=empty_list_response,
        )
        m.post(
            "http://test/api/statustypen",
            json=statustype_response,
            status_code=201,
        )
        m.get(
            "http://test/api/resultaattypen?zaaktype=http%3A%2F%2Ftest%2Fapi%2Fzaaktypen%2F1&status=alles",
            json=empty_list_response,
        )
        m.post(
            "http://test/api/resultaattypen",
            json=statustype_response,
            status_code=201,
        )
        m.get(
            "http://test/api/zaaktype-informatieobjecttypen?zaaktype=http%3A%2F%2Ftest%2Fapi%2Fzaaktypen%2F1&status=alles",
            json=empty_list_response,
        )
        m.post(
            "http://test/api/zaaktype-informatieobjecttypen",
            json=zaaktypeinformatieobjecttype_response,
            status_code=201,
        )

        # for debugging run the import function
        # run_import(job)

        # # test the Celery task function
        import_job_task(job.id)

        # see what happened
        job.refresh_from_db()
        logs = list(job.joblog_set.all())

        logs = chop_precheck_from_logs(logs)
        self.assertEqual(len(logs), 6)  # we got 6 types of resources

        messages = [log.message for log in logs]
        expected = [
            "informatieobjecttype 'Onderzoeksstuk' created new",
            "zaaktype B1796 created",
            "zaaktype B1796: roltype omschrijving='Initiator' created new",
            "zaaktype B1796: statustype volgnummer='1' created new",
            "zaaktype B1796: resultaattype omschrijving='Geweigerd' created new",
            "zaaktype B1796: zaakinformatieobjecttype volgnummer='1' created new",
        ]
        self.assertEqual(messages, expected)

        self.assertEqual(job.state, JobState.completed)


def chop_precheck_from_logs(logs):
    seen = False
    result = []
    for log in logs:
        if seen:
            result.append(log)
        elif log.message.startswith("End of precheck"):
            seen = True
    return result

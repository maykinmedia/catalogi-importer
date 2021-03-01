from pprint import pprint

from django.core.files.base import ContentFile
from django.test import TestCase

import requests_mock
from zgw_consumers.constants import APITypes

from importer.core.choices import JobState
from importer.core.importer import run_import
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
    "concept": False,
}
informatieobjecttype_response_concept = {
    "url": "http://test/api/informatieobjecttypen/2",
    "omschrijving": "Onderzoeksstuk",
    "concept": True,
}
informatieobjecttype_list_response = {
    "count": 1,
    "results": [
        informatieobjecttype_response,
    ],
    "next": None,
    "previous": None,
}
informatieobjecttype_list_response_concept = {
    "count": 1,
    "results": [
        informatieobjecttype_response_concept,
    ],
    "next": None,
    "previous": None,
}

zaaktype_response = {
    "url": "http://test/api/zaaktypen/1",
    "identificatie": "foo",
    "concept": False,
}
zaaktype_response2 = {
    "url": "http://test/api/zaaktypen/2",
    "identificatie": "foo",
    "concept": False,
}
zaaktype_response_concept = {
    "url": "http://test/api/zaaktypen/2",
    "identificatie": "foo",
    "concept": True,
}
zaaktype_list_response = {
    "count": 1,
    "results": [
        zaaktype_response,
    ],
    "next": None,
    "previous": None,
}
zaaktype_list_response_concept = {
    "count": 1,
    "results": [
        zaaktype_response_concept,
    ],
    "next": None,
    "previous": None,
}

roltype_response = {
    "url": "http://test/api/roltypen/1",
    "omschrijving": "Initiator",
}
roltype_list_response = {
    "count": 1,
    "results": [
        roltype_response,
    ],
    "next": None,
    "previous": None,
}

statustype_response = {
    "url": "http://test/api/statustypen/1",
    "volgnummer": 1,
}
statustype_list_response = {
    "count": 1,
    "results": [
        statustype_response,
    ],
    "next": None,
    "previous": None,
}

resultaattype_response = {
    "url": "http://test/api/resultaattypen/1",
    "omschrijving": "Geweigerd",
}
resultaattype_list_response = {
    "count": 1,
    "results": [
        resultaattype_response,
    ],
    "next": None,
    "previous": None,
}

zaaktypeinformatieobjecttype_response = {
    "url": "http://test/api/zaaktypeinformatieobjecttypen/1",
    "zaaktype": "http://test/api/zaaktypen/1",
    "informatieobjecttype": "http://test/api/informatieobjecttypen/1",
    "volgnummer": 1,
}
zaaktypeinformatieobjecttype_list_response = {
    "count": 1,
    "results": [
        zaaktypeinformatieobjecttype_response,
    ],
    "next": None,
    "previous": None,
}


class ImportTest(TestCaseMixin, TestCase):
    @requests_mock.Mocker()
    def test_positive_create_flow(self, m):
        """
        Test an mocked import on an empty catalog
        """
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
        # run the url reverse
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

        logs = chop_precheck_from_logs(job.joblog_set.all())
        messages = [log.message for log in logs]
        pprint(messages)
        self.assertEqual(len(messages), 6)  # we got 6 types of resources

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

    @requests_mock.Mocker()
    def test_positive_update_flow(self, m):
        """
        Test an mocked import on an catalog with existing published items
        """
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
        # run the url reverse
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
            json=informatieobjecttype_list_response,
        )
        # close and create
        m.patch(
            "http://test/api/informatieobjecttypen/1",
            json=informatieobjecttype_response,
            status_code=200,
        )
        m.post(
            "http://test/api/informatieobjecttypen",
            json=informatieobjecttype_response_concept,
            status_code=201,
        )

        m.get(
            "http://test/api/zaaktypen?identificatie=B1796&catalogus=http%3A%2F%2Ftest%2Fapi%2Fcatalogussen%2F7c0e6595-adbe-45b4-b092-31ba75c7dd74&status=alles",
            json=zaaktype_list_response,
        )
        # close and create
        m.patch(
            "http://test/api/zaaktypen/1",
            json=zaaktype_response,
            status_code=200,
        )
        m.post(
            "http://test/api/zaaktypen",
            json=zaaktype_response_concept,
            status_code=201,
        )

        m.get(
            "http://test/api/roltypen?zaaktype=http%3A%2F%2Ftest%2Fapi%2Fzaaktypen%2F2&status=alles",
            json=roltype_list_response,
        )
        m.put(
            "http://test/api/roltypen/1",
            json=roltype_response,
            status_code=200,
        )
        m.get(
            "http://test/api/statustypen?zaaktype=http%3A%2F%2Ftest%2Fapi%2Fzaaktypen%2F2&status=alles",
            json=statustype_list_response,
        )
        m.put(
            "http://test/api/statustypen/1",
            json=statustype_response,
            status_code=200,
        )
        m.get(
            "http://test/api/resultaattypen?zaaktype=http%3A%2F%2Ftest%2Fapi%2Fzaaktypen%2F2&status=alles",
            json=resultaattype_list_response,
        )
        m.put(
            "http://test/api/resultaattypen/1",
            json=statustype_response,
            status_code=200,
        )
        m.get(
            "http://test/api/zaaktype-informatieobjecttypen?zaaktype=http%3A%2F%2Ftest%2Fapi%2Fzaaktypen%2F2&status=alles",
            json=zaaktypeinformatieobjecttype_list_response,
        )
        m.put(
            "http://test/api/zaaktypeinformatieobjecttypen/1",
            json=zaaktypeinformatieobjecttype_response,
            status_code=200,
        )

        # for debugging run the import function
        # run_import(job)

        # # test the Celery task function
        import_job_task(job.id)

        # see what happened
        job.refresh_from_db()

        logs = chop_precheck_from_logs(job.joblog_set.all())
        messages = [log.message for log in logs]
        self.assertEqual(len(messages), 8)  # we got 6 types of resources and closed 2

        expected = [
            "informatieobjecttype 'Onderzoeksstuk' closed old resource on 2020-07-06: http://test/api/informatieobjecttypen/1",
            "informatieobjecttype 'Onderzoeksstuk' created new version",
            "zaaktype B1796 closed old resource on 2020-07-06: http://test/api/zaaktypen/1",
            "zaaktype B1796 created new version",
            "zaaktype B1796: roltype omschrijving='Initiator' updated existing",
            "zaaktype B1796: statustype volgnummer='1' updated existing",
            "zaaktype B1796: resultaattype omschrijving='Geweigerd' updated existing",
            "zaaktype B1796: zaakinformatieobjecttype volgnummer='1' updated existing",
        ]
        self.assertEqual(messages, expected)

        self.assertEqual(job.state, JobState.completed)

    @requests_mock.Mocker()
    def test_positive_update_flow_concepts(self, m):
        """
        Test an mocked import on an catalog with existing concept items
        """
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
        # run the url reverse
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
            json=informatieobjecttype_list_response_concept,
        )
        # close and create
        m.put(
            "http://test/api/informatieobjecttypen/2",
            json=informatieobjecttype_response,
            status_code=200,
        )

        m.get(
            "http://test/api/zaaktypen?identificatie=B1796&catalogus=http%3A%2F%2Ftest%2Fapi%2Fcatalogussen%2F7c0e6595-adbe-45b4-b092-31ba75c7dd74&status=alles",
            json=zaaktype_list_response_concept,
        )
        # close and create
        m.put(
            "http://test/api/zaaktypen/2",
            json=zaaktype_response,
            status_code=200,
        )

        m.get(
            "http://test/api/roltypen?zaaktype=http%3A%2F%2Ftest%2Fapi%2Fzaaktypen%2F1&status=alles",
            json=roltype_list_response,
        )
        m.put(
            "http://test/api/roltypen/1",
            json=roltype_response,
            status_code=200,
        )
        m.get(
            "http://test/api/statustypen?zaaktype=http%3A%2F%2Ftest%2Fapi%2Fzaaktypen%2F1&status=alles",
            json=statustype_list_response,
        )
        m.put(
            "http://test/api/statustypen/1",
            json=statustype_response,
            status_code=200,
        )
        m.get(
            "http://test/api/resultaattypen?zaaktype=http%3A%2F%2Ftest%2Fapi%2Fzaaktypen%2F1&status=alles",
            json=resultaattype_list_response,
        )
        m.put(
            "http://test/api/resultaattypen/1",
            json=statustype_response,
            status_code=200,
        )
        m.get(
            "http://test/api/zaaktype-informatieobjecttypen?zaaktype=http%3A%2F%2Ftest%2Fapi%2Fzaaktypen%2F1&status=alles",
            json=zaaktypeinformatieobjecttype_list_response,
        )
        m.put(
            "http://test/api/zaaktypeinformatieobjecttypen/1",
            json=zaaktypeinformatieobjecttype_response,
            status_code=200,
        )

        # for debugging run the import function
        # run_import(job)

        # # test the Celery task function
        import_job_task(job.id)

        # see what happened
        job.refresh_from_db()

        logs = chop_precheck_from_logs(job.joblog_set.all())
        messages = [log.message for log in logs]
        self.assertEqual(len(messages), 6)  # we got 6 types of resources

        expected = [
            "informatieobjecttype 'Onderzoeksstuk' updated existing concept",
            "zaaktype B1796 updated existing concept",
            "zaaktype B1796: roltype omschrijving='Initiator' updated existing",
            "zaaktype B1796: statustype volgnummer='1' updated existing",
            "zaaktype B1796: resultaattype omschrijving='Geweigerd' updated existing",
            "zaaktype B1796: zaakinformatieobjecttype volgnummer='1' updated existing",
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

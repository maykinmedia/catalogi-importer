from datetime import date

from django.core.files.base import ContentFile
from django.test import TestCase, override_settings

import requests_mock
from freezegun import freeze_time
from zgw_consumers.constants import APITypes

from importer.core.choices import JobState
from importer.core.tasks import import_job_task
from importer.core.tests.base import MockMatcherCheck, TestCaseMixin
from importer.core.tests.factories import (
    CatalogConfigFactory,
    JobFactory,
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

error_response = {
    "type": "http://localhost:9000/ref/fouten/ValidationError/",
    "code": "invalid",
    "title": "Error title.",
    "status": 400,
    "detail": "",
    "instance": "urn:uuid:51e15b8d-98e7-4284-9869-94cbcef00dxx",
    "invalidParams": [
        {
            "name": "nonFieldErrors",
            "code": "unique",
            "reason": "Foo-bar-reason",
        }
    ],
}

TEST_CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.dummy.DummyCache",
    }
}


class ImportTest(TestCaseMixin, TestCase):
    maxDiff = None

    def setup_import_job(self, m, xml_file):
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

        job = JobFactory(state=JobState.queued, catalog=catalog)
        job.source.save("foo.xml", ContentFile(self.get_test_data(xml_file)))
        return job

    @override_settings(CACHES=TEST_CACHES)
    @requests_mock.Mocker()
    def test_positive_create_flow(self, m):
        """
        Test a mocked import on an empty catalog
        """
        job = self.setup_import_job(m, "example-stripped-single.xml")
        match_check = MockMatcherCheck(m, ignore_predefined=True)

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

        if not match_check.all_called():
            self.fail(match_check.get_diff())

        logs = chop_precheck_from_logs(job.joblog_set.all())
        messages = [log.message for log in logs]
        expected = [
            "informatieobjecttype 'Onderzoeksstuk' created new concept",
            "zaaktype B1796 created new concept",
            "zaaktype B1796: roltype omschrijving='Initiator' created new",
            "zaaktype B1796: statustype volgnummer='1' created new",
            "zaaktype B1796: resultaattype omschrijving='Geweigerd' created new",
            "zaaktype B1796: zaakinformatieobjecttype volgnummer='1' created new",
        ]
        self.assertEqual(messages, expected)

        # one of everything
        created_one = {
            "counted": 1,
            "created": 1,
            "errored": 0,
            "issues": {},
            "updated": 0,
        }
        self.assertEqual(
            job.statistics,
            {
                "data": {
                    "rt": created_one,
                    "st": created_one,
                    "zt": created_one,
                    "iot": created_one,
                    "rst": created_one,
                    "ziot": created_one,
                }
            },
        )
        self.assertEqual(job.state, JobState.completed)

    @override_settings(CACHES=TEST_CACHES)
    @requests_mock.Mocker()
    def test_positive_update_flow(self, m):
        """
        Test a mocked import on an catalog with existing published items
        """
        job = self.setup_import_job(m, "example-stripped-single.xml")
        match_check = MockMatcherCheck(m, ignore_predefined=True)

        m.get(
            "http://test/api/informatieobjecttypen?catalogus=http%3A%2F%2Ftest%2Fapi%2Fcatalogussen%2F7c0e6595-adbe-45b4-b092-31ba75c7dd74&status=alles",
            json=informatieobjecttype_list_response,
        )
        # we don't close the existing but only create new
        m.post(
            "http://test/api/informatieobjecttypen",
            json=informatieobjecttype_response_concept,
            status_code=201,
        )

        m.get(
            "http://test/api/zaaktypen?identificatie=B1796&catalogus=http%3A%2F%2Ftest%2Fapi%2Fcatalogussen%2F7c0e6595-adbe-45b4-b092-31ba75c7dd74&status=alles",
            json=zaaktype_list_response,
        )
        # we don't close the existing but only create new
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

        if not match_check.all_called():
            self.fail(match_check.get_diff())

        logs = chop_precheck_from_logs(job.joblog_set.all())
        messages = [log.message for log in logs]
        expected = [
            "informatieobjecttype 'Onderzoeksstuk' existing published stays active",
            "informatieobjecttype 'Onderzoeksstuk' created new concept",
            "zaaktype B1796 existing published stays active",
            "zaaktype B1796 created new concept",
            "zaaktype B1796: roltype omschrijving='Initiator' updated existing",
            "zaaktype B1796: statustype volgnummer='1' updated existing",
            "zaaktype B1796: resultaattype omschrijving='Geweigerd' updated existing",
            "zaaktype B1796: zaakinformatieobjecttype volgnummer='1' updated existing",
        ]
        self.assertEqual(messages, expected)

        # one of everything
        updated_one = {
            "counted": 1,
            "created": 0,
            "errored": 0,
            "issues": {},
            "updated": 1,
        }
        self.assertEqual(
            job.statistics,
            {
                "data": {
                    "rt": updated_one,
                    "st": updated_one,
                    "zt": updated_one,
                    "iot": updated_one,
                    "rst": updated_one,
                    "ziot": updated_one,
                }
            },
        )
        self.assertEqual(job.state, JobState.completed)

    @override_settings(CACHES=TEST_CACHES)
    @requests_mock.Mocker()
    def test_positive_update_flow_concepts(self, m):
        """
        Test a mocked import on an catalog with existing concept items
        """
        job = self.setup_import_job(m, "example-stripped-single.xml")
        match_check = MockMatcherCheck(m, ignore_predefined=True)

        m.get(
            "http://test/api/informatieobjecttypen?catalogus=http%3A%2F%2Ftest%2Fapi%2Fcatalogussen%2F7c0e6595-adbe-45b4-b092-31ba75c7dd74&status=alles",
            json=informatieobjecttype_list_response_concept,
        )
        # we don't create new but update concept
        m.put(
            "http://test/api/informatieobjecttypen/2",
            json=informatieobjecttype_response,
            status_code=200,
        )

        m.get(
            "http://test/api/zaaktypen?identificatie=B1796&catalogus=http%3A%2F%2Ftest%2Fapi%2Fcatalogussen%2F7c0e6595-adbe-45b4-b092-31ba75c7dd74&status=alles",
            json=zaaktype_list_response_concept,
        )
        # we don't create new but update concept
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

        if not match_check.all_called():
            self.fail(match_check.get_diff())

        logs = chop_precheck_from_logs(job.joblog_set.all())
        messages = [log.message for log in logs]
        expected = [
            "informatieobjecttype 'Onderzoeksstuk' updated existing concept",
            "zaaktype B1796 updated existing concept",
            "zaaktype B1796: roltype omschrijving='Initiator' updated existing",
            "zaaktype B1796: statustype volgnummer='1' updated existing",
            "zaaktype B1796: resultaattype omschrijving='Geweigerd' updated existing",
            "zaaktype B1796: zaakinformatieobjecttype volgnummer='1' updated existing",
        ]
        self.assertEqual(messages, expected)

        # one of everything
        updated_one = {
            "counted": 1,
            "created": 0,
            "errored": 0,
            "issues": {},
            "updated": 1,
        }
        self.assertEqual(
            job.statistics,
            {
                "data": {
                    "rt": updated_one,
                    "st": updated_one,
                    "zt": updated_one,
                    "iot": updated_one,
                    "rst": updated_one,
                    "ziot": updated_one,
                }
            },
        )
        self.assertEqual(job.state, JobState.completed)

    @override_settings(CACHES=TEST_CACHES)
    @freeze_time("2021-03-01")
    @requests_mock.Mocker()
    def test_positive_update_options_flow(self, m):
        """
        Test a mocked import on an catalog with existing published items
        """
        job = self.setup_import_job(m, "example-stripped-single.xml")
        job.close_published = True
        job.start_date = date(2021, 4, 1)
        job.save()

        match_check = MockMatcherCheck(m, ignore_predefined=True)

        m.get(
            "http://test/api/informatieobjecttypen?catalogus=http%3A%2F%2Ftest%2Fapi%2Fcatalogussen%2F7c0e6595-adbe-45b4-b092-31ba75c7dd74&status=alles",
            json=informatieobjecttype_list_response,
        )
        # close and create
        io_close = m.patch(
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
        zt_close = m.patch(
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

        if not match_check.all_called():
            self.fail(match_check.get_diff())

        io_close_data = io_close.request_history[0].json()
        self.assertEqual("2021-04-01", io_close_data["eindeGeldigheid"])
        zt_close_data = zt_close.request_history[0].json()
        self.assertEqual("2021-04-01", zt_close_data["eindeGeldigheid"])

        logs = chop_precheck_from_logs(job.joblog_set.all())
        messages = [log.message for log in logs]
        expected = [
            "informatieobjecttype 'Onderzoeksstuk' closed existing published on '2021-04-01'",
            "informatieobjecttype 'Onderzoeksstuk' created new concept",
            "zaaktype B1796 closed existing published on '2021-04-01'",
            "zaaktype B1796 created new concept",
            "zaaktype B1796: roltype omschrijving='Initiator' updated existing",
            "zaaktype B1796: statustype volgnummer='1' updated existing",
            "zaaktype B1796: resultaattype omschrijving='Geweigerd' updated existing",
            "zaaktype B1796: zaakinformatieobjecttype volgnummer='1' updated existing",
        ]
        self.assertEqual(messages, expected)

        # one of everything
        updated_one = {
            "counted": 1,
            "created": 0,
            "errored": 0,
            "issues": {},
            "updated": 1,
        }
        self.assertEqual(
            job.statistics,
            {
                "data": {
                    "rt": updated_one,
                    "st": updated_one,
                    "zt": updated_one,
                    "iot": updated_one,
                    "rst": updated_one,
                    "ziot": updated_one,
                }
            },
        )
        self.assertEqual(job.state, JobState.completed)

    @override_settings(CACHES=TEST_CACHES)
    @requests_mock.Mocker()
    def test_negative_init_flow(self, m):
        job = self.setup_import_job(m, "example-stripped-single.xml")
        match_check = MockMatcherCheck(m, ignore_predefined=True)

        m.get(
            "http://test/api/informatieobjecttypen?catalogus=http%3A%2F%2Ftest%2Fapi%2Fcatalogussen%2F7c0e6595-adbe-45b4-b092-31ba75c7dd74&status=alles",
            json=error_response,
            status_code=404,
        )

        # for debugging run the import function
        # run_import(job)

        # # test the Celery task function
        import_job_task(job.id)

        # see what happened
        job.refresh_from_db()

        if not match_check.all_called():
            self.fail(match_check.get_diff())

        logs = chop_precheck_from_logs(job.joblog_set.all())
        messages = [log.message for log in logs]
        expected = [
            "informatieobjecttypen can't be created: Error title: Foo-bar-reason",
        ]
        self.assertEqual(messages, expected)

        counted_one = {
            "counted": 1,
            "created": 0,
            "errored": 0,
            "issues": {},
            "updated": 0,
        }
        self.assertEqual(
            job.statistics,
            {
                "data": {
                    "rt": counted_one,
                    "st": counted_one,
                    "zt": counted_one,
                    "iot": {
                        "counted": 1,
                        "created": 0,
                        "errored": 0,
                        "issues": {"error": 1},
                        "updated": 0,
                    },
                    "rst": counted_one,
                    "ziot": counted_one,
                }
            },
        )
        self.assertEqual(job.state, JobState.completed)

    @override_settings(CACHES=TEST_CACHES)
    @requests_mock.Mocker()
    def test_negative_create_flow(self, m):
        """
        Test a mocked import on an empty catalog
        """
        job = self.setup_import_job(m, "example-stripped-single.xml")
        match_check = MockMatcherCheck(m, ignore_predefined=True)

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
            json=error_response,
            status_code=400,
        )
        # for debugging run the import function
        # run_import(job)

        # # test the Celery task function
        import_job_task(job.id)

        # see what happened
        job.refresh_from_db()

        if not match_check.all_called():
            self.fail(match_check.get_diff())

        logs = chop_precheck_from_logs(job.joblog_set.all())
        messages = [log.message for log in logs]
        expected = [
            "informatieobjecttype 'Onderzoeksstuk' created new concept",
            "zaaktype B1796: can't be created: Error title: Foo-bar-reason",
        ]
        self.assertEqual(messages, expected)

        counted_one = {
            "counted": 1,
            "created": 0,
            "errored": 0,
            "issues": {},
            "updated": 0,
        }
        self.assertEqual(
            job.statistics,
            {
                "data": {
                    "rt": counted_one,
                    "st": counted_one,
                    "zt": {
                        "counted": 1,
                        "created": 0,
                        "errored": 1,
                        "issues": {"error": 1},
                        "updated": 0,
                    },
                    "iot": {
                        "counted": 1,
                        "created": 1,
                        "errored": 0,
                        "issues": {},
                        "updated": 0,
                    },
                    "rst": counted_one,
                    "ziot": counted_one,
                }
            },
        )
        self.assertEqual(job.state, JobState.completed)

    @requests_mock.Mocker()
    def test_error_malformed_xml(self, m):
        job = self.setup_import_job(m, "invalid-malformed.xml")

        # for debugging run the import function
        # run_import(job)

        # # test the Celery task function
        import_job_task(job.id)

        # see what happened
        job.refresh_from_db()

        messages = [log.message for log in job.joblog_set.all()]
        expected = ["XML parse error"]
        self.assertEqual(messages, expected)

        self.assertEqual(job.statistics, {})
        self.assertEqual(job.state, JobState.error)

    @requests_mock.Mocker()
    def test_error_schema_xml(self, m):
        job = self.setup_import_job(m, "invalid-schema.xml")

        # for debugging run the import function
        # run_import(job)

        # # test the Celery task function
        import_job_task(job.id)

        # see what happened
        job.refresh_from_db()

        messages = [log.message for log in job.joblog_set.all()]
        expected = ["non supported XML format"]
        self.assertEqual(messages, expected)

        self.assertEqual(job.statistics, {})
        self.assertEqual(job.state, JobState.error)

    @requests_mock.Mocker()
    def test_error_version_xml(self, m):
        job = self.setup_import_job(m, "invalid-version.xml")

        # for debugging run the import function
        # run_import(job)

        # # test the Celery task function
        import_job_task(job.id)

        # see what happened
        job.refresh_from_db()

        messages = [log.message for log in job.joblog_set.all()]
        expected = ["non supported XML version 'ICR1.3.13' (expected 'ICR1.5.x')"]
        self.assertEqual(messages, expected)

        self.assertEqual(job.statistics, {})
        self.assertEqual(job.state, JobState.error)


def chop_precheck_from_logs(logs):
    seen = False
    result = []
    for log in logs:
        if seen:
            result.append(log)
        elif log.message.startswith("End of precheck"):
            seen = True
    return result

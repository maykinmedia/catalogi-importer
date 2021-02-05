import json

from django.test import TestCase
from django.utils.translation import gettext as _

from zds_client import ClientError

from importer.core.choices import JobLogLevel
from importer.core.constants import ObjectTypenKeys
from importer.core.reporting import (
    ImportSession,
    format_exception,
    transform_statistics,
)
from importer.core.tests.factories import JobFactory


class ImportSessionUtilsTest(TestCase):
    def test_importsession_precheck_logs(self):
        job = JobFactory()
        session = ImportSession(job)
        session.log_info("foo-info")
        session.log_warning("foo-warning")
        session.log_error("foo-error")
        self.assertEqual(job.joblog_set.all().count(), 0)

    def test_importsession_import_Logs(self):
        job = JobFactory()
        session = ImportSession(job, save_logs=True)
        session.log_info("foo-info")
        session.log_warning("foo-warning")
        session.log_error("foo-error")
        logs = list(job.joblog_set.values("level", "message"))
        self.assertEqual(
            logs,
            [
                {"level": JobLogLevel.info, "message": "foo-info"},
                {"level": JobLogLevel.warning, "message": "foo-warning"},
                {"level": JobLogLevel.error, "message": "foo-error"},
            ],
        )

    def test_importsession_log_stats(self):
        job = JobFactory()
        session = ImportSession(job)
        session.log_info("foo-info", ObjectTypenKeys.zaaktypen)
        session.log_warning("foo-warning", ObjectTypenKeys.zaaktypen)
        session.log_error("foo-error", ObjectTypenKeys.zaaktypen)
        session.log_error("foo-error2", ObjectTypenKeys.zaaktypen)

        expected = {
            "data": {
                ObjectTypenKeys.zaaktypen: [
                    0,
                    0,
                    {JobLogLevel.warning: 1, JobLogLevel.error: 2},
                ]
            }
        }
        data = session.counter.get_data()
        # downcast tuples/defaultdicts to array/dict
        simple = json.loads(json.dumps(data))
        self.assertEqual(simple, expected)

        # check if we have this in database
        job.refresh_from_db()
        session.flush_counts()
        self.assertEqual(data, job.statistics)

    def test_importsession_counter_stats(self):
        job = JobFactory()
        session = ImportSession(job, save_logs=True)

        session.counter.set_count(ObjectTypenKeys.roltypen, 2)
        session.counter.set_total(ObjectTypenKeys.roltypen, 3)

        session.counter.increment_count(ObjectTypenKeys.zaaktypen)
        session.counter.increment_count(ObjectTypenKeys.zaaktypen)

        session.counter.increment_issue_count(
            ObjectTypenKeys.statustypen, JobLogLevel.info
        )
        session.counter.increment_issue_count(
            ObjectTypenKeys.statustypen, JobLogLevel.warning
        )
        session.counter.increment_issue_count(
            ObjectTypenKeys.statustypen, JobLogLevel.error
        )
        session.counter.increment_issue_count(
            ObjectTypenKeys.statustypen, JobLogLevel.error
        )

        expected = {
            "data": {
                ObjectTypenKeys.roltypen: [
                    2,
                    3,
                    None,
                ],
                ObjectTypenKeys.zaaktypen: [
                    2,
                    0,
                    None,
                ],
                ObjectTypenKeys.statustypen: [
                    0,
                    0,
                    {JobLogLevel.warning: 1, JobLogLevel.error: 2, JobLogLevel.info: 1},
                ],
            }
        }
        data = session.counter.get_data()
        # downcast tuples/defaultdicts
        simple = json.loads(json.dumps(data))
        self.assertEqual(simple, expected)

        # check if we have this in database
        job.refresh_from_db()
        session.flush_counts()
        self.assertEqual(data, job.statistics)


class ResportingUtilsTest(TestCase):
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
                ObjectTypenKeys.zaaktypen: (1, 3, None),
                ObjectTypenKeys.roltypen: (8, 10, None),
                ObjectTypenKeys.statustypen: (18, 20, None),
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


class FormatUtilTest(TestCase):
    def test_format_exception_single(self):
        exc = ClientError(
            {
                "type": "http://localhost:9000/ref/fouten/ValidationError/",
                "code": "invalid",
                "title": "Invalid input.",
                "status": 400,
                "detail": "",
                "instance": "urn:uuid:51e15b8d-98e7-4284-9869-94cbcef00d1f",
                "invalidParams": [
                    {
                        "name": "beginGeldigheid",
                        "code": "overlap",
                        "reason": "Dit zaaktype komt al voor binnen de catalogus en opgegeven geldigheidsperiode.",
                    },
                ],
            }
        )

        actual = format_exception(exc)
        expected = "Invalid input: Dit zaaktype komt al voor binnen de catalogus en opgegeven geldigheidsperiode (beginGeldigheid)."
        self.assertEqual(actual, expected)

    def test_format_exception_multiple(self):
        exc = ClientError(
            {
                "type": "http://localhost:9000/ref/fouten/ValidationError/",
                "code": "invalid",
                "title": "Invalid input.",
                "status": 400,
                "detail": "",
                "instance": "urn:uuid:51e15b8d-98e7-4284-9869-94cbcef00d1f",
                "invalidParams": [
                    {
                        "name": "beginGeldigheid",
                        "code": "overlap",
                        "reason": "Dit zaaktype komt al voor binnen de catalogus en opgegeven geldigheidsperiode.",
                    },
                    {
                        "name": "nonFieldErrors",
                        "code": "unique",
                        "reason": "De velden catalogus, omschrijving moeten een unieke set zijn.",
                    },
                ],
            }
        )

        actual = format_exception(exc)
        expected = "Invalid input: 1) Dit zaaktype komt al voor binnen de catalogus en opgegeven geldigheidsperiode (beginGeldigheid). 2) De velden catalogus, omschrijving moeten een unieke set zijn."
        self.assertEqual(actual, expected)

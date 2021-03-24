import json

from django.core.exceptions import ValidationError
from django.test import TestCase
from django.utils.translation import gettext as _

from requests import HTTPError
from zds_client import ClientError

from importer.core.choices import JobLogLevel
from importer.core.constants import ObjectTypenKeys
from importer.core.reporting import (
    ImportSession,
    format_exception,
    transform_import_statistics,
    transform_precheck_statistics,
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
                ObjectTypenKeys.zaaktypen: {
                    "created": 0,
                    "updated": 0,
                    "errored": 0,
                    "counted": 0,
                    "issues": {JobLogLevel.warning: 1, JobLogLevel.error: 2},
                }
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

        session.counter.increment_updated(ObjectTypenKeys.roltypen)
        session.counter.increment_created(ObjectTypenKeys.roltypen)
        session.counter.increment_counted(ObjectTypenKeys.roltypen)
        session.counter.increment_errored(ObjectTypenKeys.roltypen)

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
                ObjectTypenKeys.roltypen: {
                    "created": 1,
                    "updated": 1,
                    "errored": 1,
                    "counted": 1,
                    "issues": {},
                },
                ObjectTypenKeys.statustypen: {
                    "created": 0,
                    "updated": 0,
                    "errored": 0,
                    "counted": 0,
                    "issues": {
                        JobLogLevel.warning: 1,
                        JobLogLevel.info: 1,
                        JobLogLevel.error: 2,
                    },
                },
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
    def test_transform_precheck_statistics(self):
        data = {
            "data": {
                ObjectTypenKeys.resultaattypen: {
                    "created": 999,  # not used here
                    "updated": 999,  # not used here
                    "errored": 5,
                    "counted": 35,
                    "issues": {JobLogLevel.warning: 2, JobLogLevel.error: 1},
                },
            },
        }
        expected = [
            ["", "errored", "counted", ""],
            [_("Roltypen"), 0, 0, ""],
            [_("Zaaktypen"), 0, 0, ""],
            [_("Statustypen"), 0, 0, ""],
            [_("Resultaattypen"), 5, 35, "(2 warnings, 1 errors)"],
            [_("Informatieobjecttypen"), 0, 0, ""],
            [_("Zaakinformatieobjecttypen"), 0, 0, ""],
        ]
        actual = transform_precheck_statistics(data)
        self.assertEqual(actual, expected)

    def test_transform_precheck_statistics_empty(self):
        expected = [
            ["", "errored", "counted", ""],
            [_("Roltypen"), 0, 0, ""],
            [_("Zaaktypen"), 0, 0, ""],
            [_("Statustypen"), 0, 0, ""],
            [_("Resultaattypen"), 0, 0, ""],
            [_("Informatieobjecttypen"), 0, 0, ""],
            [_("Zaakinformatieobjecttypen"), 0, 0, ""],
        ]
        actual = transform_precheck_statistics({})
        self.assertEqual(actual, expected)
        actual = transform_precheck_statistics({"data": {}})
        self.assertEqual(actual, expected)

    def test_transform_import_statistics(self):
        data = {
            "data": {
                ObjectTypenKeys.resultaattypen: {
                    "created": 10,
                    "updated": 20,
                    "errored": 5,
                    "counted": 35,
                    "issues": {JobLogLevel.warning: 2, JobLogLevel.error: 1},
                },
            },
        }
        expected = [
            ["", "updated", "created", "errored", "total", ""],
            [_("Roltypen"), 0, 0, 0, 0, ""],
            [_("Zaaktypen"), 0, 0, 0, 0, ""],
            [_("Statustypen"), 0, 0, 0, 0, ""],
            [_("Resultaattypen"), 20, 10, 5, 35, "(2 warnings, 1 errors)"],
            [_("Informatieobjecttypen"), 0, 0, 0, 0, ""],
            [_("Zaakinformatieobjecttypen"), 0, 0, 0, 0, ""],
        ]
        actual = transform_import_statistics(data)
        self.assertEqual(actual, expected)

    def test_transform_import_statistics_empty(self):
        expected = [
            ["", "updated", "created", "errored", "total", ""],
            [_("Roltypen"), 0, 0, 0, 0, ""],
            [_("Zaaktypen"), 0, 0, 0, 0, ""],
            [_("Statustypen"), 0, 0, 0, 0, ""],
            [_("Resultaattypen"), 0, 0, 0, 0, ""],
            [_("Informatieobjecttypen"), 0, 0, 0, 0, ""],
            [_("Zaakinformatieobjecttypen"), 0, 0, 0, 0, ""],
        ]
        actual = transform_import_statistics({})
        self.assertEqual(actual, expected)
        actual = transform_import_statistics({"data": {}})
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

    def test_format_generic_error(self):
        exc = HTTPError("problem")

        actual = format_exception(exc)
        expected = "problem"
        self.assertEqual(actual, expected)

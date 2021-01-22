from datetime import datetime, timedelta

from django.test import TestCase

import pytz

from importer.core.choices import JobLogLevel, JobState
from importer.core.models import Job
from importer.core.tests.factories import JobFactory, JobLogFactory


class JobTests(TestCase):
    def test_queryset_filter_queued(self):
        job_queued_1 = JobFactory(state=JobState.queued)
        job_queued_2 = JobFactory(state=JobState.queued)

        JobFactory(state=JobState.precheck)
        JobFactory(state=JobState.running)
        JobFactory(state=JobState.completed)
        JobFactory(state=JobState.error)

        jobs = list(Job.objects.filter_queued())
        self.assertEqual([job_queued_1, job_queued_2], jobs)

    def test_state_change(self):
        job = JobFactory()
        self.assertEqual(job.state, JobState.precheck)
        self.assertIsNotNone(job.created_at)
        self.assertIsNone(job.started_at)
        self.assertIsNone(job.stopped_at)

        job.state = JobState.queued
        job.save()

        job.mark_running()
        self.assertEqual(job.state, JobState.running)
        self.assertIsNotNone(job.created_at)
        self.assertIsNotNone(job.started_at)
        self.assertIsNone(job.stopped_at)

        job.mark_completed()
        self.assertEqual(job.state, JobState.completed)
        self.assertIsNotNone(job.created_at)
        self.assertIsNotNone(job.started_at)
        self.assertIsNotNone(job.stopped_at)

        job = JobFactory()
        job.mark_running()
        job.mark_error()
        self.assertEqual(job.state, JobState.error)
        self.assertIsNotNone(job.created_at)
        self.assertIsNotNone(job.started_at)
        self.assertIsNotNone(job.stopped_at)

    def test_add_log(self):
        job = JobFactory()

        job.add_log(JobLogLevel.warning, "foo")
        job.add_log(JobLogLevel.error, "bar")

        logs = list(job.joblog_set.all())
        self.assertEqual(logs[0].level, JobLogLevel.warning)
        self.assertEqual(logs[0].message, "foo")

        self.assertEqual(logs[1].level, JobLogLevel.error)
        self.assertEqual(logs[1].message, "bar")

        with self.assertRaises(AssertionError):
            job.add_log("bad", "foo")

    def test_set_results(self):
        job = JobFactory()
        self.assertEqual(job.results, dict())
        self.assertFalse(job.results)
        job.set_results({"aa": 1, "bb": 2})

        job = job = Job.objects.get(id=job.id)
        self.assertEqual(job.results, {"aa": 1, "bb": 2})

    def test_duration(self):
        with self.subTest("no start"):
            job = JobFactory(
                started_at=None,
                stopped_at=None,
            )
            self.assertEqual(job.get_duration(), None)
            self.assertEqual(job.get_duration_display(), "-")

        with self.subTest("no stop"):
            job = JobFactory(
                started_at=datetime(2021, 1, 1, 12, 0, tzinfo=pytz.utc),
                stopped_at=None,
            )
            self.assertEqual(job.get_duration(), None)
            self.assertEqual(job.get_duration_display(), "..")

        with self.subTest("complete, short"):
            job = JobFactory(
                started_at=datetime(2021, 1, 1, 12, 0, tzinfo=pytz.utc),
                stopped_at=datetime(2021, 1, 1, 12, 3, tzinfo=pytz.utc),
            )
            self.assertEqual(job.get_duration(), timedelta(minutes=3))
            self.assertEqual(job.get_duration_display(), "180s")

        with self.subTest("complete, long"):
            job = JobFactory(
                started_at=datetime(2021, 1, 1, 12, 0, tzinfo=pytz.utc),
                stopped_at=datetime(2021, 1, 1, 12, 10, tzinfo=pytz.utc),
            )
            self.assertEqual(job.get_duration(), timedelta(minutes=10))
            self.assertEqual(job.get_duration_display(), "10m")


class JobLogTests(TestCase):
    def test_message(self):
        log = JobLogFactory(message="0123456789abcdef")
        self.assertEqual(log.message_trim_line(length=10), "0123456789")

        # clip at first linebreak
        log = JobLogFactory(message="012345\n6789abcdef")
        self.assertEqual(log.message_trim_line(length=10), "012345")

    def test_icons(self):
        log = JobLogFactory(level=JobLogLevel.warning, message="0123456789abcdef")
        self.assertEqual(log.get_level_icon(), "⚠️️")

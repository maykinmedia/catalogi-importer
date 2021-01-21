from django.test import TestCase

from importer.core.choices import JobState
from importer.core.models import Job
from importer.core.tests.factories import JobFactory


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

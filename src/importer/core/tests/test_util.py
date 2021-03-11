from django.test import TestCase

import requests
import requests_mock

from importer.core.tests.base import MockMatcherCheck


class TestMockMatcherCheck(TestCase):
    @requests_mock.Mocker()
    def test_called(self, m):
        match_check = MockMatcherCheck(m)
        m.get(
            "http://test/api/foo",
            text="response",
        )
        requests.get("http://test/api/foo")
        self.assertTrue(match_check.all_called())
        self.assertEqual("all called", match_check.get_diff())

    @requests_mock.Mocker()
    def test_not_called(self, m):
        match_check = MockMatcherCheck(m)
        m.get(
            "http://test/api/missing",
            text="response",
        )
        self.assertFalse(match_check.all_called())

        diff = "not called:\n  GET   http://test/api/missing"
        self.assertEqual(diff, match_check.get_diff())

    @requests_mock.Mocker()
    def test_called_with_ignore_predefined(self, m):
        m.get(
            "http://test/api/missing-ignored",
            text="response",
        )
        match_check = MockMatcherCheck(m, ignore_predefined=True)
        m.get(
            "http://test/api/foo",
            text="response",
        )
        requests.get("http://test/api/foo")
        self.assertTrue(match_check.all_called())

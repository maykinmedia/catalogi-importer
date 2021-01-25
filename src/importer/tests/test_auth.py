from unittest import skip

from django.test import TestCase


class AuthTests(TestCase):
    def test_pass(self):
        pass

    @skip
    def test_fail(self):
        self.fail("please implement tests")

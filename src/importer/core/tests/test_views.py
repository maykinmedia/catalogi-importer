from django.urls import reverse

from django_webtest import WebTest

from importer.accounts.tests.factories import StaffUserFactory, UserFactory


class PrivateStorageTest(WebTest):
    def test_private_file_requires_staff(self):
        url = reverse("staff_private_file", kwargs=dict(path="x/y.z"))

        # anonymous
        self.app.get(url, status=403)

        # not staff
        self.app.set_user(UserFactory())
        self.app.get(url, status=403)

        # allowed, expect 404 because file doesn't exist
        self.app.set_user(StaffUserFactory())
        self.app.get(url, status=404)

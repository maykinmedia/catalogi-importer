import os

from django.urls import reverse

from django_webtest import WebTest

from importer.accounts.tests.factories import SuperUserFactory
from importer.core.models import SelectielijstConfig
from importer.core.tests.factories import ZGWServiceFactory


class AdminWebTest(WebTest):
    def setUp(self):
        super().setUp()
        self.user = SuperUserFactory()
        self.app.set_user(self.user)
        service = ZGWServiceFactory(
            api_root="https://selectielijst.openzaak.nl/api/v1/",
            oas="https://selectielijst.openzaak.nl/api/v1/schema/openapi.yaml",
        )
        selection = SelectielijstConfig.get_solo()
        selection.service = service
        selection.save()

    def get_test_data(self, file, mode="rb"):
        with open(os.path.join(os.path.dirname(__file__), "data", file), mode) as f:
            return f.read()

    def reverse_list_url(self, model_class):
        return reverse(
            "admin:{}_{}_changelist".format(
                model_class._meta.app_label, model_class._meta.model_name
            ),
        )

    def reverse_add_url(self, model_class):
        return reverse(
            "admin:{}_{}_add".format(
                model_class._meta.app_label, model_class._meta.model_name
            ),
        )

    def reverse_change_url(self, model_instance):
        return reverse(
            "admin:{}_{}_change".format(
                model_instance._meta.app_label, model_instance._meta.model_name
            ),
            args=[model_instance.pk],
        )

    def assertAdminChangeList(self, model_class, check_search=True):
        """
        test for basic configuration errors
        """
        url = self.reverse_list_url(model_class)
        response = self.app.get(url)
        self.assertEqual(response.status_code, 200)

        # check if the search lookups are configured correctly
        if check_search:
            form = response.forms["changelist-search"]
            form["q"] = "foo"
            response = form.submit()
            self.assertEqual(response.status_code, 200, "search error")

    def assertPyQueryExists(self, response, query):
        pq = response.pyquery(query)
        pl = len(pq)
        if not pl:
            self.fail(f"zero matching elements found for: {query}")
        return pq

    def assertPyQueryNotExists(self, response, query):
        pl = len(response.pyquery(query))
        if pl:
            self.fail(
                f"expected zero elements but found {pl} matching elements for: {query}"
            )

    def assertPyQueryOnce(self, response, query):
        pl = len(response.pyquery(query))
        if pl != 1:
            self.fail(
                f"expected exactly one but found {pl} matching elements for: {query}"
            )

    def assertPyQueryCount(self, response, query, count):
        pl = len(response.pyquery(query))
        if pl != count:
            self.fail(
                f"expected exactly {count} but found {pl} matching elements for: {query}"
            )

    def assertSubmitButtonExists(self, response):
        self.assertPyQueryExists(response, "input[type='submit']")

    def assertSubmitButtonNotExists(self, response):
        self.assertPyQueryNotExists(response, "input[type='submit']")

    def assertFormRowReadonly(self, response, field_name, text=None):
        self.assertPyQueryExists(response, f".form-row.field-{field_name} label")
        self.assertPyQueryExists(response, f".form-row.field-{field_name} div.readonly")
        if text is not None:
            elem = response.pyquery(f".form-row.field-{field_name} div.readonly")[0]
            self.assertEqual(str(elem.text).strip(), str(text))

    def assertFormRowNotExists(self, response, field_name):
        self.assertPyQueryNotExists(response, f".form-row.field-{field_name}")

    def assertFormHasNoFields(self, response, allow_fields=None):
        # check no fields are exposed accidentally
        form = response.form
        expect_fields = {"csrfmiddlewaretoken", "_continue", "_submit"}
        if allow_fields is not None:
            expect_fields |= set(allow_fields)
        self.assertEqual(set(), set(form.fields.keys()) - expect_fields)

import re

from django.test import TestCase

import requests_mock
from lxml import etree

from importer.core.choices import JobLogLevel
from importer.core.parser import (
    DEFAULT_RESULTAATTYPE_OMSCHRIJVINGEN,
    get_resultaat_number,
    get_resultaattype_omschrijving,
    parse_xml,
)
from importer.core.reporting import ImportSession
from importer.core.tests.base import TestCaseMixin
from importer.core.tests.factories import JobFactory


class SelectielijstTests(TestCaseMixin, TestCase):
    """
    checks based on feedback from 1.0 and DSP-export 2021.03.30T21.21.36.xml
    """

    def test_get_resultaat_number_match(self):
        """
        test some specific examples
        """
        tree = etree.fromstring(self.get_test_data("resultaattypen-part.xml"))
        result_types = list(tree.findall("resultaattypen/resultaattype"))

        with self.subTest("0: example regular"):
            result_type = result_types[0]
            number = get_resultaat_number(result_type)
            self.assertEqual(number, "11.2")

        with self.subTest("1: example modified"):
            result_type = result_types[1]
            number = get_resultaat_number(result_type)
            self.assertEqual(number, "11.2")

        with self.subTest("2: example modified"):
            result_type = result_types[2]
            number = get_resultaat_number(result_type)
            self.assertEqual(number, "11.1")

        with self.subTest("3: problem modified"):
            result_type = result_types[3]
            number = get_resultaat_number(result_type)
            self.assertEqual(number, "11.1")

    def test_get_resultaat_number_bulk(self):
        """
        see if we can get values from feedback example
        """
        tree = etree.fromstring(
            self.get_test_data("DSP-export 2021.03.30T21.21.36.xml")
        )
        result_types = list(
            tree.findall("processen/proces/resultaattypen/resultaattype")
        )

        self.assertEqual(len(result_types), 216)
        for result_type in result_types:
            number = get_resultaat_number(result_type)
            self.assertNotEqual(number, "")
            self.assertRegexpMatches(number, r"^\d+\.\d+(?:\.\d+)*$")

    @requests_mock.Mocker()
    def test_get_resultaattype_omschrijving(self, m):
        self.setup_selectielijst_service()
        self.setup_selectielijst_mocks(m)

        tree = etree.fromstring(self.get_test_data("resultaattypen-part.xml"))
        result_types = list(tree.findall("resultaattypen/resultaattype"))
        result_type = result_types[0]

        job = JobFactory()
        session = ImportSession(job)
        omschrijving = get_resultaattype_omschrijving(session, "dummy", result_type)
        self.assertNotEqual(omschrijving, DEFAULT_RESULTAATTYPE_OMSCHRIJVINGEN)

    @requests_mock.Mocker()
    def test_get_example_bulk(self, m):
        self.setup_selectielijst_service()
        self.setup_selectielijst_mocks(m)
        """
        see if we can get values from feedback example
        """
        tree = etree.fromstring(
            self.get_test_data("DSP-export 2021.03.30T21.21.36.xml")
        )
        job = JobFactory()
        session = ImportSession(job)
        zaaktypen, iotypen = parse_xml(session, tree, job.year)
        logs = [
            log.message
            for log in session.logs
            if log.level in (JobLogLevel.warning, JobLogLevel.error)
        ]
        exp = re.compile(r"zaaktype \w+\d+: ")
        logs = [exp.sub("", log) for log in logs]
        logs = list(sorted(set(logs)))
        self.assertEqual(
            logs,
            [
                'Imported resultaattype \'MRT0001071\' cannot be parsed: Imported "resultaat" does not contain a valid combination of resultaat number (11.1) and processType (https://selectielijst.openzaak.nl/api/v1/procestypen/c844637e-6393-4202-b030-e1bffb08a9b0) to match "volledigNummer" and "procesType" in the Selectielijst API.'
            ],
        )

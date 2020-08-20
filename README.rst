=================
Catalogi Importer
=================

:Version: 0.1.0
:Source: https://github.com/maykinmedia/catalogi-importer
:Keywords: Zaakgericht Werken, Common Ground
:PythonVersion: 3.7

|black|

|python-versions| |django-versions| |pypi-version|

Migrate your Catalogi data from Navigator to Catalogi API


.. contents::

.. section-numbering::

Features
========

* import data from iNavigator xml into Catalogi API

Installation
============

Requirements
------------

* Python 3.7 or above
* setuptools 30.3.0 or above
* Django 2.2 or newer


Install
-------

.. code-block:: bash

    pip install importer


Usage
=====

Prerequisites
-------------

* Exported process types as XML file
* Creadentials of Selectielijst API
* Year to which process types belongs in Selectielijst API
* Creadentials of Catalogi API
* URL of target catalog in Catalogi API


import_from_file command
------------------------

- Run django server of the application (the easiest way is to use ``runserver`` command) and access django admin page

  - add credentials for Catalogi API in "Services" admin page
  - add credentials for Selectielijst API in "Services" admin page
  - choose the configured in previous step service in "Selectielijst" admin page

- Execute command ``import_from_file`` specifying the path of XML file, the url of target catalog in Catalogi API and the year of procestypen in Selectielijst API

For example:

.. code-block:: bash

    python manage.py import_from_file path/to/file.xml http://some.catalogi.nl/api/v1/catalogussen/e7f987eb-c30f-4a09-832a-9370e9f37631 2020


.. |black| image:: https://img.shields.io/badge/code%20style-black-000000.svg
    :target: https://github.com/psf/black

.. |python-versions| image:: https://img.shields.io/pypi/pyversions/importer.svg

.. |django-versions| image:: https://img.shields.io/pypi/djversions/importer.svg

.. |pypi-version| image:: https://img.shields.io/pypi/v/importer.svg
    :target: https://pypi.org/project/importer/

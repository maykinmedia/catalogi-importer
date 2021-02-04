=================
Catalogi Importer
=================

:Version: 0.1.0
:Source: https://github.com/maykinmedia/catalogi-importer
:Keywords: ztc, i-navigator, zaaktypen, catalogi-api

|build-status| |code-quality| |docs| |black| |python-versions|

Eenvoudig i-Navigator exports importeren in een Catalogi API, zoals die in 
`Open Zaak`_ zit.
(`English version`_)

Ontwikkeld door `Maykin Media B.V.`_ voor Gemeente Delft


Introductie
===========

De `Catalogi API`_ is de bron om alle zaaktypen te ontsluiten als er gebruik
wordt gemaakt van de `API's voor Zaakgericht Werken`_, onderdeel in het
`Common Ground`_ landschap. Veel gemeenten gebruiken op dit moment echter het
i-Navigator product.

Om het importeren zo geautomatiseerd mogelijk te maken, kan de Catalogi
Importer een i-Navigator export inladen in elke catalogus die beschikbaar is via
een Catalogi API. Alle zaaktypen worden aangemaakt als concept zodat achteraf
nog eenvoudig wijzigingen kunnen worden gemaakt.


Quickstart
==========

Om het startprocess van de Catalogi Importer te vereenvoudigen, is er een `docker-compose-quickstart.yml`_ beschikbaar.
Voer de volgende commando's uit om de containers te starten:

    .. code:: shell

        $ wget https://raw.githubusercontent.com/maykinmedia/catalogi-importer/master/docker-compose-quickstart.yml
        $ docker-compose -f docker-compose-quickstart.yml up -d
        $ docker-compose exec web src/manage.py createsuperuser

Ga daarna naar ``http://127.0.0.1:8000/`` en log in met de inloggegevens die je zojuist hebt gemaakt.

.. _docker-compose-quickstart.yml: docker-compose-quickstart.yml


Licentie
========

Copyright © Maykin Media, 2021

Licensed under the `EUPL`_.

Referenties
===========

* `Documentatie <https://catalogi-importer.readthedocs.io/>`_
* `Issues <https://github.com/maykinmedia/catalogi-importer/issues>`_
* `Code <https://github.com/maykinmedia/catalogi-importer>`_
* `Community <https://commonground.nl/groups/view/54478547/archiefbeheercomponent>`_
* `Docker image <https://hub.docker.com/r/maykinmedia/catalogi-importer>`_

.. _`English version`: README.rst
.. _`Maykin Media B.V.`: https://www.maykinmedia.nl
.. _`Open Zaak`: https://opengem.nl/producten/open-zaak/
.. _`API's voor Zaakgericht Werken`: https://github.com/VNG-Realisatie/gemma-zaken
.. _`Common Ground`: https://commonground.nl/
.. _`Catalogi API`: https://vng-realisatie.github.io/gemma-zaken/standaard/catalogi/index
.. _`EUPL`: LICENSE.md

.. |build-status| image:: https://github.com/maykinmedia/catalogi-importer/workflows/Run%20CI/badge.svg?branch=master
    :alt: Build status
    :target: https://github.com/maykinmedia/catalogi-importer/actions?query=branch%3Amaster+workflow%3A%22Run+CI%22

.. |black| image:: https://img.shields.io/badge/code%20style-black-000000.svg
    :alt: Code style
    :target: https://github.com/psf/black

.. |python-versions| image:: https://img.shields.io/badge/python-3.7-blue.svg
    :alt: Supported Python version

.. |code-quality| image:: https://github.com/maykinmedia/catalogi-importer/workflows/Code%20quality%20checks/badge.svg
     :alt: Code quality checks
     :target: https://github.com/maykinmedia/catalogi-importer/actions?query=workflow%3A%22Code+quality+checks%22

.. |docs| image:: https://readthedocs.org/projects/catalogi-importer/badge/?version=latest
    :target: https://catalogi-importer.readthedocs.io/
    :alt: Documentation Status

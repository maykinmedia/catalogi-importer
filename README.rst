=================
Catalogi Importer
=================

:Version: 1.0.0
:Source: https://github.com/maykinmedia/catalogi-importer
:Keywords: ztc, i-navigator, zaaktypen, catalogi-api

|build-status| |code-quality| |docs| |black| |python-versions|

Easily import i-Navigator exports into the Catalogi API, such as the one in 
`Open Zaak`_.
(`Nederlandse versie`_)

Developed by `Maykin Media B.V.`_ and commissioned by the municipality of Delft.


Introduction
============

The `Catalogi API`_ is the main place to store your zaaktypes when using the 
`API's voor Zaakgericht Werken`_, part of the `Common Ground`_ landscape. 
However, many municipalities currently have their zaaktypes stored in 
i-Navigator.

To keep the manual overhead to a minimum, the Catalogi Importer can load 
i-Navigator exports into any catalog present in a Catalogi API. All zaaktypes
are created as concepts, so you can easily make additional changes afterwards 
if needed.


Quickstart
==========

A `docker-compose-quickstart.yml`_ is provided to get up and running quickly. To run the container:

    .. code:: shell

        $ wget https://raw.githubusercontent.com/maykinmedia/catalogi-importer/master/docker-compose-quickstart.yml
        $ docker-compose -f docker-compose-quickstart.yml up -d
        $ docker-compose exec web src/manage.py createsuperuser

Then, navigate to ``http://127.0.0.1:8000/`` and log in with the credentials created.

.. _docker-compose-quickstart.yml: docker-compose-quickstart.yml


License
=======

Copyright © Maykin Media, 2021

Licensed under the `EUPL`_.

References
==========

* `Documentation <https://catalogi-importer.readthedocs.io/>`_
* `Issues <https://github.com/maykinmedia/catalogi-importer/issues>`_
* `Code <https://github.com/maykinmedia/catalogi-importer>`_
* `Docker image <https://hub.docker.com/r/maykinmedia/catalogi-importer>`_

.. _`Nederlandse versie`: README.NL.rst
.. _`Maykin Media B.V.`: https://www.maykinmedia.nl
.. _`Open Zaak`: https://opengem.nl/producten/open-zaak/
.. _`API's voor Zaakgericht Werken`: https://github.com/VNG-Realisatie/gemma-zaken
.. _`Common Ground`: https://commonground.nl/
.. _`Catalogi API`: https://vng-realisatie.github.io/gemma-zaken/standaard/catalogi/index
.. _`EUPL`: LICENSE.md

.. |build-status| image:: https://github.com/maykinmedia/catalogi-importer/workflows/ci/badge.svg?branch=master
    :alt: Build status
    :target: https://github.com/maykinmedia/catalogi-importer/actions?query=branch%3Amaster+workflow%3A%22ci%22

.. |black| image:: https://img.shields.io/badge/code%20style-black-000000.svg
    :alt: Code style
    :target: https://github.com/psf/black

.. |python-versions| image:: https://img.shields.io/badge/python-3.7-blue.svg
    :alt: Supported Python version

.. |code-quality| image:: https://github.com/maykinmedia/catalogi-importer/workflows/code-quality/badge.svg
     :alt: Code quality checks
     :target: https://github.com/maykinmedia/catalogi-importer/actions?query=workflow%3A%22code-quality%22

.. |docs| image:: https://readthedocs.org/projects/catalogi-importer/badge/?version=latest
    :target: https://catalogi-importer.readthedocs.io/
    :alt: Documentation Status

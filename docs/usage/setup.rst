.. _setup_index:

Configuration
=============

Before the Catalogi Importer can be used we need to setup credentials for the 
backend services. If you just need to add a new catalog in a pre-configured
Open Zaak installation, skip to :ref:`add_a_catalog`.

Configure Open Zaak
-------------------

To be able to connect from Catalogi Importer to Open Zaak we need to create API 
credentials in Open Zaak:

   a. Navigate to **API Autorisaties > Applicaties**
   b. Click **Applicatie toevoegen**.
   c. Fill out the form:

      - **Label**: *For example:* ``Catalogi Importer``
      - **Client ID**: *For example:* ``catalogi-importer``
      - **Secret**: *Some random string. You will need this later on!*

   d. Click **Opslaan en opnieuw bewerken**.
   e. Click **Beheer autorisaties**.
   f. Select component **Catalogi API** and scopes **catalogi.lezen** en **catalogi.schrijven**.
   g. Click **Opslaan**


Configure Catalogi Importer
---------------------------

Next, we need to add these credentials to the Catalogi Importer:

   a. Navigate to **Importer > Services**
   b. Click **Add Service**.
   c. Fill out the form:

      - **Label**: *For example:* ``Open Zaak Productie``
      - **Type**: ``ZTC (Zaaktypen)``
      - **API Root URL**: *For example:* ``https://openzaak.gemeente.nl/catalogi/api/v1/``
      - **Client id:**: *Same as above*
      - **Secret:**: *Same as above*
      - **Authorization type:**: ``ZGW Client id and secret``
      - **OAS**: ``https://openzaak.gemeente.nl/catalogi/api/v1/schema/openapi.yaml``

   d. Click **Save**.


The Catalogi Importer uses the VNG Selectielijst (such as the one provided by 
Open Zaak):
   
      a. Navigate to **Importer > Services**
      b. Click **Add Service**.
      c. Fill out the form:
   
         - **Label**: *For example:* ``Selectielijst``
         - **Type**: ``ORC (overige)``
         - **API Root URL**: ``https://selectielijst.openzaak.nl/api/v1/``
         - **Authorization type:**: ``No authorisation``
         - **OAS**: ``https://selectielijst.openzaak.nl/api/v1/schema/openapi.yaml``
   
      d. Click **Save**.
   
      e. Navigate to **Importer > Selectielijst configuration**
      f. In the pull-down menu select the record with the label we just created.
      g. Click **Save**.


.. _add_a_catalog:

Add a catalog
~~~~~~~~~~~~~

We need to retrieve the UUID of the Open Zaak Catalog we want to import to from the Open Zaak admin:

   a. Navigate to **Gegevens > Catalogi**
   b. Select the Catalogus we want to import to, or create a new one for testing purposes.
   c. Copy the **UUID** value from the form.

Then we configure this Catalog in Catalogi Importer:

   a. Navigate to **Importer > Catalog configurations**
   b. Click **Add Catalog configuration**.
   c. Fill out the form:

      - Select the **Service** that with the label we configured earlier.
      - Paste the **UUID** we copied from Open Zaak.
      - Enter a descriptive **Label**, ideally matching the Catalog in Open Zaak.

   d. Click **Save**.
   e. The system will validate the **UUID** at the selected **Service**.

      - If the details are correct the RSIN and domain will be retrieved and printed

This catalog is now configured in Catalogi Importer to accept one or more **Import Jobs**.


This is a one-time configuration that is valid for all catalogs in this Open 
Zaak installation.

Additional Open Zaak installations like a testing or acceptation environment can
be added following the same pattern.

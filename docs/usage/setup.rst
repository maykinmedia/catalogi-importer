.. _setup_index:

Setup backend
=============

Before the Catalogi Importer can be used we need to setup credentials for the backend services.


Configure Selectielijst
-----------------------

The Catalogi Importer and Open Zaak use the VNG Selectielijst:

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


Configure Open Zaak credentials:
--------------------------------

To be able to connect from Catalogi Importer to Open Zaak we need to create API credentials in Open Zaak:

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

Next we need to add these credentials to the Catalogi Importer:

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


This is a one-time configuration that is valid for all catalogs in this Open Zaak installation.

Additional Open Zaak installations like a testing or acceptation stage can be added following the same pattern.

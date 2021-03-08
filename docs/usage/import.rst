.. _import_index:

Run Import
============

After the _setup_index of the credentials we can define **Catalog configurations** and run **Import Jobs**:


Define a Catalog
----------------

We need to retrieve the Uuid of the Open Zaak Catalog we want to import to from the Open Zaak admin:

   a. Navigate to **Gegevens > Catalogi**
   b. Select the Catalogus we want to import to, or create a new one for testing purposes.
   c. Copy the **Uuid** value from the form.

Then we configure this Catalog in Catalogi Importer:

   a. Navigate to **Importer > Catalog configurations**
   b. Click **Add Catalog configuration**.
   c. Fill out the form:

      - Select the **Service** that with the label we configured earlier.
      - Paste the **Uuid** we copied from Open Zaak.
      - Enter a descriptive **Label**, ideally matching the Catalog in Open Zaak.

   d. Click **Save**.
   e. The system will validate the **Uuid** at the selected **Service**.

      - If the details are correct the RSIN and domain will be retrieved and printed

This catalog is now configured in Catalogi Importer to accept one or more **Import Jobs**.


Create an Import Job
--------------------

Every import operation is represented as an **Import Job** and sets the Catalog, the Selectielijst-year and the iNavigator XML-file to use, plus some parameters for the import.

   a. Navigate to **Importer > Import jobs**
   b. Click **Add Import job**.
   c. Fill out the form:

      - Select the **Catalog** we configured earlier.
      - Select the *Selectielijst year* to use.
      - Click **Browse** and select the iNavigator **XML file** to import.
      - Optionally override **Start date** to set the begin date of the new records (eg: `beginGeldigheid` in Open Zaak).
      - Select "Close published" to close currently published Zaaktypen or InformatieObjecttypen on the above date. Note this means there won't be active records after this date until you publish the newly imported records.

   d. Click **Continue**.
   e. The system runs a pre-check on the XML and reports potential issues.

      - Carefully take note of the reported issues.
      - Some of these need to be solved in iNavigator and exported again and run in a new Import Job, and some can be fixed later in Open Zaak.

   f. If the report is acceptable click **Continue** and a long running background task is started to run the import.

      - The screen will periodically update the counters but the job will continue even if you close the browser tab.

   g. When the import is done the report will display with the results of the actual import.

      - This report will be saved with the ** Import Job** and can be accessed later for review.

   h. Open this Catalog in your Open Zaak admin or other client software and review the new records.

To monitor progress or review an earlier precheck or import report:

   a. Navigate to **Importer > Import jobs**
   b. Select the **Import job** you're interested in from the list.

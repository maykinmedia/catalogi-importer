.. _import_index:

Importing i-Navigator files
===========================

Make sure you have an XML export of i-Navigator ready and :ref:`configured <setup_index>` the 
Catalog Importer correctly.

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

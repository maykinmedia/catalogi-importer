.. _resources_index:


Open Zaak resources
===================

Catalogi Importer improteerd de volgende resources in Open Zaak


Zaaktype
--------
Matched with existing records on their **indentificatie**/**id** field (B-Nummer).

Additional note for importing: If the i-Navigator record does not have a 'resultaat nummer' for the Selectielijst to determine the Zaaktype's 'selectielijstProcestype'; the 'toelichting' field can be used to add a value so the import can complete.

Use the format ``nummer, toelichting``, eg ``123, voorbeeld tekst``.


InformatieObjecttype / documenttype
-----------------------------------

Matched with existing records on their **omschrijving** field.


Roltype
-------
Matched with existing records in this Zaaktype on their **omschrijving** field.


Statustype
----------
Matched with existing records in this Zaaktype on their **volgnummer** field.


Resultaatype
------------
Matched with existing records in this Zaaktype on their **omschrijving** field.

Additional note for importing: If the i-Navigator record does not have a 'resultaat nummer' for the Selectielijstto determine the Resultaattype's 'resultaattypeomschrijving and 'selectielijstklasse'; the 'toelichting' field can be used to add a value so the import can complete.



Use the format ``nummer, toelichting``, eg ``123, voorbeeld tekst``.


Zaaktypeinformatieobjecttype
----------------------------
(connection between Zaaktype en InformatieObjecttype)

Matched with existing records in this Zaaktype and InformatieObjecttype on their **omschrijving** field.

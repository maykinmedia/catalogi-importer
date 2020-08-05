from lxml import etree

# /dsp/processen/*/proces
ZAAKTYPE = {
    # "url": "http://example.com",  # Generated
    'identificatie': '@id',

    # velden
    'omschrijving': 'kernomschrijving',
    'omschrijvingGeneriek': 'model-kernomschrijving',
    "vertrouwelijkheidaanduiding": "vertrouwelijkheid",
    "doel": "naam",
    "aanleiding": "aanleiding",
    "toelichting": "toelichting-proces",
    "indicatieInternOfExtern": "zaaktype-categorie",
    "handelingInitiator": "zaaktype-naam/structuur/handeling-initiator",
    "onderwerp": "zaaktype-naam/structuur/onderwerp",
    "handelingBehandelaar": "zaaktype-naam/structuur/handeling-behandelaar",
    "doorlooptijd": "afdoeningstermijn",  # See afdoeningstermijn-eenheid for unit
    # "servicenorm": "string",
    "opschortingEnAanhoudingMogelijk": "aanhouden-mogelijk",
    "verlengingMogelijk": "beroep-mogelijk",
    # "verlengingstermijn": "string",
    "trefwoorden": "lokale-trefwoorden",  # ???
    "publicatieIndicatie": "publicatie-indicatie",
    "publicatietekst": "publicatietekst",
    "verantwoordingsrelatie": "verantwoordingsrelatie",  # ???
    # "productenOfDiensten": [
    # "http://example.com"
    # ],
    "selectielijstProcestype": "",  # Infer URL from first resultaattype.selectielijstklasse number (like 8.2). The processtype is then 8.
    # "referentieproces": {
    # "naam": "string",
    # "link": "http://example.com"
    # },
    # "catalogus": "http://example.com",  # Provided
    # "statustypen": [
    # "http://example.com"
    # ],
    # "resultaattypen": [
    # "http://example.com"
    # ],
    # "eigenschappen": [
    # "http://example.com"
    # ],
    # "informatieobjecttypen": [
    # "http://example.com"
    # ],
    # "roltypen": [
    # "http://example.com"
    # ],
    # "besluittypen": [
    # "http://example.com"
    # ],
    # "deelzaaktypen": [
    # "http://example.com"
    # ],
    # "gerelateerdeZaaktypen": [
    # {}
    # ],
    "beginGeldigheid": "actueel-van",
    "eindeGeldigheid": "actueel-tot",
    "versiedatum": "actueel-van",
    # "concept": true  # Use default
}

# /dsp/processen/*/proces/roltypen/*
# We could also use /dsp/rolsoorten/*/rolsoort, it doesn't matter much for our
# case.

ROLTYPE = {
    # "url": "http://example.com",  # Generated

    # velden
    # "zaaktype": "http://example.com",  # Parent
    "omschrijving": "naam",
    "omschrijvingGeneriek": "naam-model"
}

# /dsp/processen/*/proces/documenttypen/*
# Typically, the IO-attributes should come from @soort-id ref to 
# "documentsoort" but it doesn't map well. Better use "omschrijving" as unique
# identifier to see if it already exists.
INFORMATIEOBJECTTYPE = {
    # "url": "http://example.com",  # Generated
    # "catalogus": "http://example.com",  # Provided

    # velden
    "omschrijving": "naam",
    "vertrouwelijkheidaanduiding": "vertrouwelijkheid",
    "beginGeldigheid": "actueel-van",
    "eindeGeldigheid": "actueel-tot",
    # "concept": true  # Use default
}

# /dsp/processen/*/proces/documenttypen/*
# Relation information is in the same definition as above
ZAAKTYPE_INFORMATIEOBJECTTYPE = {
    # "url": "http://example.com",  # Generated
    # "zaaktype": "http://example.com",  # Parent
    # "informatieobjecttype": "http://example.com",  # See above
    "volgnummer": "@volgnummer",

    # velden
    "richting": "type",
    # "statustype": "http://example.com"
}


# /dsp/processen/*/proces/statustypen/*
STATUSTYPE = {
    # "url": "http://example.com",
    "volgnummer": "@volgnummer",

    # velden
    "omschrijving": "naam",
    "omschrijvingGeneriek": "naam-model",
    "statustekst": "bericht",
    # "zaaktype": "http://example.com",  # Parent
    "isEindstatus": "",  # Generated
    # "informeren": true
}

# /dsp/processen/*/proces/resultaattypen/*
RESULTAATTYPE = {
    # "url": "http://example.com",  # Generated
    # "zaaktype": "http://example.com",  # Parent
    
    # velden
    "omschrijving": "naam",
    "resultaattypeomschrijving": "naam-model",  # Infer URL from this field I guess?
    "omschrijvingGeneriek": "naam-model",
    "selectielijstklasse": "vernietigingsgrondslag/list[0]/fields/field['NAAM']",  # Infer URL from the number (like 8.2) in this field.
    "toelichting": "toelichting",
    "archiefnominatie": "waardering",
    "archiefactietermijn": "bewaartermijn",  # See bewaartermijn-eenheid for unit
    "brondatumArchiefprocedure": {
        "afleidingswijze": "brondatum-archiefprocedure",
        # OH OH, this can cause troubles...
        # "datumkenmerk": "string",
        # "einddatumBekend": true,
        # "objecttype": "adres",
        # "registratie": "string",
        # "procestermijn": "string"
    }
}

# /dsp/processen/*/proces/besluittypen/*
BESLUITTYPE = {}  # None so far



def init():
    with open('example.xml', 'r') as f:
        tree = etree.parse(f)

    res = tree.xpath('/dsp/processen')

if __name__ == "__main__":
    init()
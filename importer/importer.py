from lxml import etree


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


def find(el: etree.ElementBase, path: str) -> str:
    """find child element and return its text"""
    return el.find(path).text


def get_duration(value: str, units: str) -> str:
    # fixme in example there is only Dag unit. The format of other units is unknown
    iso_units = ""
    if units.lower() == "dag":
        iso_units = "D"
    return f'P{value}{iso_units}'


def get_boolean(value: str) -> bool:
    return True if value.lower() == 'ja' else False


def get_array(value: str) -> list:
    if not value:
        return []

    # fixme in the example all list elements are empty. The format of the separator is unknown
    return value.split(',')


def parse_xml(file: str) -> list:
    with open(file, 'r') as f:
        tree = etree.parse(f)

    zaaktypen = []
    processen = tree.xpath('/dsp/processen')[0]
    for process in processen:
        fields = process.find("velden")
        zaaktype = {
            "identificatie": process.get("id"),
            'omschrijving': find(fields, 'kernomschrijving'),
            'omschrijvingGeneriek': find(fields, 'model-kernomschrijving'),
            # fixme choice field
            "vertrouwelijkheidaanduiding": find(fields, 'vertrouwelijkheid'),
            "doel": find(fields, 'naam'),
            "aanleiding": find(fields, 'aanleiding'),
            "toelichting": find(fields, 'toelichting-proces'),
            # fixme choice field
            "indicatieInternOfExtern": find(fields, 'zaaktype-categorie'),
            "handelingInitiator": find(fields,"zaaktype-naam/structuur/handeling-initiator"),
            "onderwerp": find(fields, "zaaktype-naam/structuur/onderwerp"),
            "handelingBehandelaar": find(fields, "zaaktype-naam/structuur/handeling-behandelaar"),
            "doorlooptijd": get_duration(find(fields, "afdoeningstermijn"), find(fields, "afdoeningstermijn-eenheid")),
            "opschortingEnAanhoudingMogelijk": get_boolean(find(fields, "aanhouden-mogelijk")),
            "verlengingMogelijk":  get_boolean(find(fields, "beroep-mogelijk")),
            "trefwoorden": get_array(find(fields, "lokale-trefwoorden")),  # always empty?
            "publicatieIndicatie": get_boolean(find(fields, "publicatie-indicatie")),
            "publicatietekst": find(fields, "publicatietekst"),
            "verantwoordingsrelatie": get_array(find(fields, "verantwoordingsrelatie")),  # always empty?
            # todo !!!
            "selectielijstProcestype": "", # Infer URL from first resultaattype.selectielijstklasse number (like 8.2). The processtype is then 8.
            # fixme !!! no mapping for required field
            "referentieproces": {
                "naam": "string",
            },
            # todo "catalogus": "",
            "besluittypen": [],
            "beginGeldigheid": "actueel-van",
            "eindeGeldigheid": "actueel-tot",
            "versiedatum": "actueel-van",

            # todo no mapping for required field
            "productenOfDiensten": [],
            "gerelateerdeZaaktypen": [],

            # todo no mapping for non-required fields
            # "verlengingstermijn": None,
            # "deelzaaktypen": [],
            # "servicenorm": None,
        }

        zaaktypen.append(zaaktype)

    return zaaktypen

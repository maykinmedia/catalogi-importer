import datetime
import re
from typing import Optional

from lxml import etree
from zgw_consumers.api_models.constants import (
    RolOmschrijving,
    VertrouwelijkheidsAanduidingen,
)

from .constants import Archiefnominatie, BrondatumArchiefprocedureAfleidingswijze
from .selectielijst import (
    get_procestypen,
    get_resultaaten,
    get_resultaattype_omschrijvingen,
)

DEFAULT_VERTROUWELIJKHEID = VertrouwelijkheidsAanduidingen.openbaar
DEFAULT_ROL_OMSCHRIVING = RolOmschrijving.adviseur
DEFAULT_ARCHIEFNOMINATIE = Archiefnominatie.vernietigen
DEFAULT_AFLEIDINGSWIJZE = BrondatumArchiefprocedureAfleidingswijze.afgehandeld

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


# /dsp/processen/*/proces/besluittypen/*
BESLUITTYPE = {}  # None so far


def find(el: etree.ElementBase, path: str) -> str:
    """find child element and return its text"""
    return el.find(path).text or ""


def get_duration(value: str, units: str) -> str:
    # fixme in example there is only Dag unit. The format of other units is unknown
    iso_units = ""
    if units.lower() == "dag":
        iso_units = "D"
    return f"P{value}{iso_units}"


def get_boolean(value: str) -> bool:
    return True if value.lower() == "ja" else False


def get_array(value: str) -> list:
    if not value:
        return []

    # fixme in the example all list elements are empty. The format of the separator is unknown
    return value.split(",")


def get_date(value: str) -> Optional[str]:
    if not value:
        return None

    return datetime.datetime.fromisoformat(value).date().isoformat()


def get_choice_field(value: str, choices: dict, default="") -> str:
    if value.lower() in choices:
        return value.lower()

    return default


def get_procestype(process: etree.ElementBase) -> str:
    # use vernietigingsgrondslag from the first resultaattype of this zaaktype
    xpath = "resultaattypen/resultaattype/velden/vernietigingsgrondslag/list/fields/field[@naam='NAAM']"
    resultaat_name = find(process, xpath)
    if not resultaat_name:
        return ""

    procestype_number = int(re.match(r"Resultaat (\d+)\.\d+", resultaat_name).group(1))
    procestype = [p for p in get_procestypen() if p["nummer"] == procestype_number][0]

    return procestype["url"]


def get_resultaattype_omschrijving(resultaattype: etree.ElementBase) -> str:
    # Infer URL from naam-model
    omschriving = find(resultaattype, "velden/naam-model")
    resultaattype_omschrijvingen = get_resultaattype_omschrijvingen()
    filtered_omschrijvingen = [
        r for r in resultaattype_omschrijvingen if r["omschrijving"] == omschriving
    ]
    if not filtered_omschrijvingen:
        return ""

    return filtered_omschrijvingen[0]["url"]


def get_resultaat(resultaattype: etree.ElementBase) -> str:
    xpath = "velden/vernietigingsgrondslag/list/fields/field[@naam='NAAM']"
    resultaat_name = find(resultaattype, xpath)
    if not resultaat_name:
        return ""

    volledig_nummer = re.match(r"Resultaat (\d+\.\d+\.?\d*)", resultaat_name).group(1)
    resultaaten = [
        r for r in get_resultaaten() if r["volledigNummer"] == volledig_nummer
    ]
    if not resultaaten:
        return ""

    return resultaaten[0]["url"]


def construct_zaaktype_data(process: etree.ElementBase) -> dict:
    fields = process.find("velden")

    indicatie_intern_of_extern = (
        "extern" if "extern" in find(fields, "zaaktype-categorie").lower() else "intern"
    )
    return {
        "identificatie": process.get("id"),
        "omschrijving": find(fields, "kernomschrijving"),
        "omschrijvingGeneriek": find(fields, "model-kernomschrijving"),
        "vertrouwelijkheidaanduiding": get_choice_field(
            find(fields, "vertrouwelijkheid"),
            VertrouwelijkheidsAanduidingen.values,
            DEFAULT_VERTROUWELIJKHEID,
        ),
        "doel": find(fields, "naam"),
        "aanleiding": find(fields, "aanleiding"),
        "toelichting": find(fields, "toelichting-proces"),
        "indicatieInternOfExtern": indicatie_intern_of_extern,
        "handelingInitiator": find(
            fields, "zaaktype-naam/structuur/handeling-initiator"
        ),
        "onderwerp": find(fields, "zaaktype-naam/structuur/onderwerp"),
        "handelingBehandelaar": find(
            fields, "zaaktype-naam/structuur/handeling-behandelaar"
        ),
        "doorlooptijd": get_duration(
            find(fields, "afdoeningstermijn"),
            find(fields, "afdoeningstermijn-eenheid"),
        ),
        "opschortingEnAanhoudingMogelijk": get_boolean(
            find(fields, "aanhouden-mogelijk")
        ),
        # fixme cam't be set without verlengingstermijn field
        # "verlengingMogelijk": get_boolean(find(fields, "beroep-mogelijk")),
        "verlengingMogelijk": False,
        "trefwoorden": get_array(find(fields, "lokale-trefwoorden")),  # always empty?
        "publicatieIndicatie": get_boolean(find(fields, "publicatie-indicatie")),
        "publicatietekst": find(fields, "publicatietekst"),
        "verantwoordingsrelatie": get_array(
            find(fields, "verantwoordingsrelatie")
        ),  # always empty?
        "selectielijstProcestype": get_procestype(process),
        "referentieproces": {"naam": find(fields, "ztc-procestype")},
        # todo "catalogus": "",
        "beginGeldigheid": get_date(find(fields, "actueel-van")),
        "eindeGeldigheid": get_date(find(fields, "actueel-tot")),
        "versiedatum": get_date(find(fields, "actueel-van")),
        # todo no mapping for required field
        "productenOfDiensten": [],
        "gerelateerdeZaaktypen": [],
        "besluittypen": [],
        # todo no mapping for non-required fields
        # "verlengingstermijn": None,
        # "deelzaaktypen": [],
        # "servicenorm": None,
    }


def construct_roltype_data(roltype: etree.ElementBase) -> dict:
    # We could also use /dsp/rolsoorten/*/rolsoort, it doesn't matter much for our
    # case.
    fields = roltype.find("velden")
    return {
        "omschrijving": find(fields, "naam"),
        "omschrijvingGeneriek": get_choice_field(
            find(fields, "naam-model"), RolOmschrijving.values, DEFAULT_ROL_OMSCHRIVING
        ),
    }


def construct_statustype_data(statustype: etree.ElementBase) -> dict:
    fields = statustype.find("velden")
    return {
        "volgnummer": statustype.get("volgnummer"),
        "omschrijving": find(fields, "naam"),
        "omschrijvingGeneriek": find(fields, "naam-model"),
        "statustekst": find(fields, "bericht"),
        # todo no mapping for non-required fields
        # "informeren": true
    }


def construct_resultaattype_data(resultaattype: etree.ElementBase) -> dict:
    fields = resultaattype.find("velden")
    return {
        "omschrijving": find(fields, "naam"),
        "resultaattypeomschrijving": get_resultaattype_omschrijving(resultaattype),
        "selectielijstklasse": get_resultaat(resultaattype),
        "toelichting": find(fields, "toelichting"),
        "archiefnominatie": get_choice_field(
            find(fields, "waardering"),
            Archiefnominatie.values,
            DEFAULT_ARCHIEFNOMINATIE,
        ),
        "archiefactietermijn": get_duration(
            find(fields, "bewaartermijn"), find(fields, "bewaartermijn-eenheid")
        ),
        "brondatumArchiefprocedure": {
            "afleidingswijze": get_choice_field(
                find(fields, "brondatum-archiefprocedure"),
                BrondatumArchiefprocedureAfleidingswijze.values,
                DEFAULT_AFLEIDINGSWIJZE,
            )
            # todo no mapping for non-required fields
            # "datumkenmerk": "string",
            # "einddatumBekend": true,
            # "objecttype": "adres",
            # "registratie": "string",
            # "procestermijn": "string"
        },
    }


def parse_xml(file: str) -> list:
    with open(file, "r") as f:
        tree = etree.parse(f)

    zaaktypen_data = []
    for process in tree.xpath("/dsp/processen")[0]:
        zaaktype_data = construct_zaaktype_data(process)

        roltypen_data = [
            construct_roltype_data(roltype) for roltype in process.find("roltypen")
        ]
        statustype_data = [
            construct_statustype_data(statustype)
            for statustype in process.find("statustypen")
        ]
        resultaattypen_data = [
            construct_resultaattype_data(resultaattype)
            for resultaattype in process.find("resultaattypen")
        ]

        zaaktype_data["_children"] = {
            "roltypen": roltypen_data,
            "statustypen": statustype_data,
            "resultaattypen": resultaattypen_data,
        }

        zaaktypen_data.append(zaaktype_data)

    return zaaktypen_data

import datetime
import logging
import re
from typing import Optional, Tuple

from lxml import etree
from zgw_consumers.api_models.constants import (
    RolOmschrijving,
    VertrouwelijkheidsAanduidingen,
)

from .constants import (
    Archiefnominatie,
    BrondatumArchiefprocedureAfleidingswijze,
    RichtingChoices,
)
from .selectielijst import (
    get_procestypen,
    get_resultaaten,
    get_resultaattype_omschrijvingen,
)

DEFAULT_VERTROUWELIJKHEID = VertrouwelijkheidsAanduidingen.openbaar
DEFAULT_ROL_OMSCHRIVING = RolOmschrijving.adviseur
DEFAULT_ARCHIEFNOMINATIE = Archiefnominatie.vernietigen
DEFAULT_AFLEIDINGSWIJZE = BrondatumArchiefprocedureAfleidingswijze.afgehandeld


logger = logging.getLogger(__name__)


class ParserException(Exception):
    pass


def find(el: etree.ElementBase, path: str) -> str:
    """find child element and return its text"""
    return el.find(path).text or ""


def get_duration(value: str, units: str) -> str:
    iso_units = ""
    if units.lower() == "dag":
        iso_units = "D"
    elif units.lower() == "week":
        iso_units = "W"
    elif units.lower() == "maand":
        iso_units = "M"
    elif units.lower() == "jaar":
        iso_units = "Y"
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


def get_procestype(process: etree.ElementBase, processtype_year: int) -> str:
    # use vernietigingsgrondslag from the first resultaattype of this zaaktype
    xpath = "resultaattypen/resultaattype/velden/vernietigingsgrondslag/list/fields/field[@naam='NAAM']"
    resultaat_name = find(process, xpath)
    if not resultaat_name:
        return ""

    procestype_number = int(re.match(r"Resultaat (\d+)\.\d+", resultaat_name).group(1))
    procestype = [
        p for p in get_procestypen(processtype_year) if p["nummer"] == procestype_number
    ][0]

    return procestype["url"]


def get_resultaattype_omschrijving(resultaattype: etree.ElementBase) -> str:
    # Infer URL from naam-model
    omschriving = find(resultaattype, "velden/naam-model")
    resultaattype_omschrijvingen = get_resultaattype_omschrijvingen()
    filtered_omschrijvingen = [
        r for r in resultaattype_omschrijvingen if r["omschrijving"] == omschriving
    ]

    if not filtered_omschrijvingen:
        raise ParserException(
            f"selectielijst API doesn't have matching resultaattypeomschrijving = {omschriving}"
        )

    return filtered_omschrijvingen[0]["url"]


def get_resultaat(resultaattype: etree.ElementBase, processtype: str) -> str:
    xpath = "velden/vernietigingsgrondslag/list/fields/field[@naam='NAAM']"
    resultaat_name = find(resultaattype, xpath)
    if not resultaat_name:
        return ""

    volledig_nummer = re.match(r"Resultaat (\d+\.\d+\.?\d*)", resultaat_name).group(1)
    resultaten = get_resultaaten()
    filtered_resultaaten = [
        r
        for r in resultaten
        if r["volledigNummer"] == volledig_nummer and r["procesType"] == processtype
    ]
    if not filtered_resultaaten:
        raise ParserException(
            f"selectielijst API doesn't have matching resultaat with volledig_nummer = {volledig_nummer}"
        )

    return filtered_resultaaten[0]["url"]


def construct_zaaktype_data(process: etree.ElementBase, processtype_year: int) -> dict:
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
        "selectielijstProcestype": get_procestype(process, processtype_year),
        "referentieproces": {"naam": find(fields, "ztc-procestype")},
        # Set during `load_data`
        # "catalogus": "",
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


def construct_resultaattype_data(
    resultaattype: etree.ElementBase, processtype: str
) -> dict:
    fields = resultaattype.find("velden")
    resultaattype_data = {}
    try:
        resultaattype_data = {
            "omschrijving": find(fields, "naam"),
            "resultaattypeomschrijving": get_resultaattype_omschrijving(resultaattype),
            "selectielijstklasse": get_resultaat(resultaattype, processtype),
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
                ),
                # fixme fixed values are set to prevent 500 error
                "datumkenmerk": "",
                "einddatumBekend": False,
                "objecttype": "",
                "registratie": "",
                "procestermijn": None,
            },
        }
    #  fixme what to do with resultaattypen which don't match with selectielijst data?
    except ParserException as exc:
        logger.warning(f"the resultaattype can't be parsed due to: {exc}")
        print(f"the resultaattype can't be parsed due to: {exc}")
    return resultaattype_data


def construct_iotype_data(document: etree.ElementBase) -> dict:
    fields = document.find("velden")
    return {
        "omschrijving": find(fields, "naam"),
        # fixme this field is always empty in the example xml
        "vertrouwelijkheidaanduiding": get_choice_field(
            find(fields, "vertrouwelijkheid"),
            VertrouwelijkheidsAanduidingen.values,
            DEFAULT_VERTROUWELIJKHEID,
        ),
        "beginGeldigheid": get_date(find(fields, "actueel-van")),
        "eindeGeldigheid": get_date(find(fields, "actueel-tot")),
    }


def construct_ziotype_data(document: etree.ElementBase) -> dict:
    fields = document.find("velden")
    return {
        "informatieobjecttype_omschrijving": find(fields, "naam"),
        "volgnummer": document.get("volgnummer"),
        "richting": get_choice_field(find(fields, "type"), RichtingChoices.values),
        # todo no mapping for non-required fields
        # "statustype": "http://example.com"
    }


def parse_xml(file: str, processtype_year: int) -> Tuple[list, list]:
    with open(file, "r") as f:
        tree = etree.parse(f)

    zaaktypen_data = []
    iotypen_dict = {}
    for process in tree.xpath("/dsp/processen")[0]:
        zaaktype_data = construct_zaaktype_data(process, processtype_year)

        roltypen_data = [
            construct_roltype_data(roltype) for roltype in process.find("roltypen")
        ]
        statustype_data = [
            construct_statustype_data(statustype)
            for statustype in process.find("statustypen")
        ]
        resultaattypen_data = [
            construct_resultaattype_data(
                resultaattype, zaaktype_data["selectielijstProcestype"]
            )
            for resultaattype in process.find("resultaattypen")
        ]
        resultaattypen_data = [r for r in resultaattypen_data if r]

        iotypen_data = [
            construct_iotype_data(document)
            for document in process.find("documenttypen")
        ]
        ziotypen_data = [
            construct_ziotype_data(document)
            for document in process.find("documenttypen")
        ]

        zaaktype_data["_children"] = {
            "roltypen": roltypen_data,
            "statustypen": statustype_data,
            "resultaattypen": resultaattypen_data,
            "zaakinformatieobjecttypen": ziotypen_data,
        }

        zaaktypen_data.append(zaaktype_data)

        for iotype_data in iotypen_data:
            if (
                iotype_data["omschrijving"] in iotypen_dict
                and iotype_data != iotypen_dict[iotype_data["omschrijving"]]
            ):
                raise ParserException(
                    f"there are different informatieobjectypen with the same omschriving: {iotype_data['omschrijving']}"
                )
            iotypen_dict[iotype_data["omschrijving"]] = iotype_data

    return zaaktypen_data, list(iotypen_dict.values())

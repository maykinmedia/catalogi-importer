import logging
import re
from typing import Optional, Tuple

from dateutil.parser import isoparse
from lxml import etree
from zgw_consumers.api_models.constants import (
    RolOmschrijving,
    VertrouwelijkheidsAanduidingen,
)

from .constants import (
    Archiefnominatie,
    BrondatumArchiefprocedureAfleidingswijze,
    ObjectTypenKeys,
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
DEFAULT_RESULTAATTYPE_OMSCHRIJVINGEN = "https://selectielijst.openzaak.nl/api/v1/resultaattypeomschrijvingen/50060769-96b3-4993-ae6a-35ae5fd14604"
DEFAULT_HANDELING_INITIATOR = "n.v.t."
DEFATUL_AANLEIDING = "n.v.t."
DEFAULT_ONDERWERP = "n.v.t."
DEFAULT_HANDELING_BEHANDELAAR = "n.v.t."
DEFAULT_RICHTING = RichtingChoices.intern

logger = logging.getLogger(__name__)


class ParserException(Exception):
    pass


def find(el: etree.ElementBase, path: str, required=True) -> str:
    """find child element and return its text"""
    result = el.find(path).text
    if not result and required:
        raise ParserException(f"the element with path {path} is empty")
    return result or ""


def get_duration(value: str, units: str) -> Optional[str]:
    if not value:
        return None

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

    # FIXME in the example all list elements are empty. The format of the separator is unknown
    return value.split(",")


def get_date(value: str) -> Optional[str]:
    if not value:
        return None

    return isoparse(value).date().isoformat()


def get_choice_field(value: str, choices: dict, default="") -> str:
    formatted_value = value.lower().replace(" ", "_")
    if formatted_value in choices:
        return formatted_value

    return default


def get_resultaat_number(resultaattype: etree.ElementBase) -> str:
    xpath = "velden/vernietigingsgrondslag/list/fields/field[@naam='NAAM']"
    try:
        resultaat_name = find(resultaattype, xpath, False)
    except AttributeError:
        resultaat_name = ""

    if resultaat_name and re.match(r"Resultaat (\d+\.\d+\.?\d*)", resultaat_name):
        return re.match(r"Resultaat (\d+\.\d+\.?\d*)", resultaat_name).group(1)

    try:
        toechlichting = find(resultaattype, "velden/toelichting", False)
    except AttributeError:
        toechlichting = None

    if toechlichting and re.match(r"(.*?), .*", toechlichting):
        return re.match(r"(.*?), .*", toechlichting).group(1)

    return ""


def get_procestype(process: etree.ElementBase, processtype_year: int) -> str:
    # use vernietigingsgrondslag from the first resultaattype of this zaaktype
    resultaattype = process.find("resultaattypen/resultaattype")
    resultaat_number = get_resultaat_number(resultaattype)

    if not resultaat_number:
        return ""

    p = get_procestypen(processtype_year)

    procestype_number = int(resultaat_number.split(".")[0])
    procestype = [
        p for p in get_procestypen(processtype_year) if p["nummer"] == procestype_number
    ][0]

    return procestype["url"]


def get_resultaattype_omschrijving(session, resultaattype: etree.ElementBase) -> str:
    # Infer URL from naam-model
    omschriving = find(resultaattype, "velden/naam-model", False)
    resultaattype_omschrijvingen = get_resultaattype_omschrijvingen()
    filtered_omschrijvingen = [
        r for r in resultaattype_omschrijvingen if r["omschrijving"] == omschriving
    ]

    if not filtered_omschrijvingen:
        session.log_warning(
            f"selectielijst API doesn't have matching resultaattypeomschrijving = {omschriving}, using default {DEFAULT_RESULTAATTYPE_OMSCHRIJVINGEN}",
            ObjectTypenKeys.resultaattypen,
        )
        return DEFAULT_RESULTAATTYPE_OMSCHRIJVINGEN

    return filtered_omschrijvingen[0]["url"]


def get_resultaat(session, resultaattype: etree.ElementBase, processtype: str) -> str:
    resultaat_number = get_resultaat_number(resultaattype)
    if not resultaat_number:
        session.log_error(
            "the resultaattype doesn't have selectielijst resultaat number",
            ObjectTypenKeys.resultaattypen,
        )
        # TODO what to do here? (do we even need the log above?)
        raise ParserException(
            "the resultaattype doesn't have selectielijst resultaat number"
        )

    resultaten = get_resultaaten()
    filtered_resultaaten = [
        r
        for r in resultaten
        if r["volledigNummer"] == resultaat_number and r["procesType"] == processtype
    ]
    if not filtered_resultaaten:
        session.log_error(
            f"selectielijst API doesn't have matching resultaat with volledig_nummer = {resultaat_number}",
            ObjectTypenKeys.resultaattypen,
        )
        raise ParserException(
            f"selectielijst API doesn't have matching resultaat with volledig_nummer = {resultaat_number}"
        )

    return filtered_resultaaten[0]["url"]


def construct_zaaktype_data(
    session, process: etree.ElementBase, processtype_year: int
) -> dict:
    fields = process.find("velden")

    # TODO report more default value usage

    indicatie_intern_of_extern = (
        "extern"
        if "extern" in find(fields, "zaaktype-categorie", False).lower()
        else "intern"
    )
    handeling_initiator = (
        find(fields, "zaaktype-naam/structuur/handeling-initiator", False)
        or DEFAULT_HANDELING_INITIATOR
    )
    aanleiding = find(fields, "aanleiding", False) or DEFATUL_AANLEIDING
    onderwerp = (
        find(fields, "zaaktype-naam/structuur/onderwerp", False) or DEFAULT_ONDERWERP
    )
    handeling_behandelaar = (
        find(fields, "zaaktype-naam/structuur/handeling-behandelaar", False)
        or DEFAULT_HANDELING_BEHANDELAAR
    )

    doorlooptijd = get_duration(
        find(fields, "afdoeningstermijn", False),
        find(fields, "afdoeningstermijn-eenheid", False),
    )
    if not doorlooptijd:
        doorlooptijd = get_duration(
            find(fields, "wettelijke-afdoeningstermijn"),
            find(fields, "wettelijke-afdoeningstermijn-eenheid"),
        )

    return {
        "identificatie": process.get("id"),
        "omschrijving": find(fields, "kernomschrijving"),
        "omschrijvingGeneriek": find(fields, "model-kernomschrijving", False),
        "vertrouwelijkheidaanduiding": get_choice_field(
            find(fields, "vertrouwelijkheid", False),
            VertrouwelijkheidsAanduidingen.values,
            DEFAULT_VERTROUWELIJKHEID,
        ),
        "doel": find(fields, "naam"),
        "aanleiding": aanleiding,
        "toelichting": find(fields, "toelichting-proces", False),
        "indicatieInternOfExtern": indicatie_intern_of_extern,
        "handelingInitiator": handeling_initiator,
        "onderwerp": onderwerp,
        "handelingBehandelaar": handeling_behandelaar,
        "doorlooptijd": doorlooptijd,
        "opschortingEnAanhoudingMogelijk": get_boolean(
            find(fields, "aanhouden-mogelijk", False)
        ),
        # FIXME cam't be set without verlengingstermijn field
        # "verlengingMogelijk": get_boolean(find(fields, "beroep-mogelijk")),
        "verlengingMogelijk": False,
        "trefwoorden": get_array(
            find(fields, "lokale-trefwoorden", False)
        ),  # always empty?
        "publicatieIndicatie": get_boolean(find(fields, "publicatie-indicatie", False)),
        "publicatietekst": find(fields, "publicatietekst", False),
        "verantwoordingsrelatie": get_array(
            find(fields, "verantwoordingsrelatie", False)
        ),  # always empty?
        "selectielijstProcestype": get_procestype(process, processtype_year),
        "referentieproces": {"naam": find(fields, "ztc-procestype")},
        # Set during `load_data`
        # "catalogus": "",
        "beginGeldigheid": get_date(find(fields, "actueel-van")),
        "eindeGeldigheid": get_date(find(fields, "actueel-tot", False)),
        "versiedatum": get_date(find(fields, "actueel-van")),
        # TODO no mapping for required field
        "productenOfDiensten": [],
        "gerelateerdeZaaktypen": [],
        "besluittypen": [],
        # TODO no mapping for non-required fields
        # "verlengingstermijn": None,
        # "deelzaaktypen": [],
        # "servicenorm": None,
    }


def construct_roltype_data(session, roltype: etree.ElementBase) -> dict:
    # We could also use /dsp/rolsoorten/*/rolsoort, it doesn't matter much for our
    # case.
    fields = roltype.find("velden")
    return {
        "omschrijving": find(fields, "naam"),
        "omschrijvingGeneriek": get_choice_field(
            find(fields, "naam-model", False),
            RolOmschrijving.values,
            DEFAULT_ROL_OMSCHRIVING,
        ),
    }


def construct_statustype_data(session, statustype: etree.ElementBase) -> dict:
    fields = statustype.find("velden")
    return {
        "volgnummer": statustype.get("volgnummer"),
        "omschrijving": find(fields, "naam"),
        "omschrijvingGeneriek": find(fields, "naam-model", False),
        "statustekst": find(fields, "bericht", False),
        # TODO no mapping for non-required fields
        # "informeren": true
    }


def construct_resultaattype_data(
    session, resultaattype: etree.ElementBase, processtype: str
) -> dict:
    fields = resultaattype.find("velden")
    toelichting = find(fields, "toelichting", False)
    afleidingswijze = get_choice_field(
        find(fields, "brondatum-archiefprocedure", False),
        BrondatumArchiefprocedureAfleidingswijze.values,
        DEFAULT_AFLEIDINGSWIJZE,
    )

    if afleidingswijze == BrondatumArchiefprocedureAfleidingswijze.afgehandeld:
        datumkenmerk = ""
    elif ":" in toelichting:
        datumkenmerk = toelichting.split(":")[0]
    else:
        datumkenmerk = toelichting.split(",")[-1].strip()

    resultaattype_data = {
        "omschrijving": find(fields, "naam")[:20],
        "resultaattypeomschrijving": get_resultaattype_omschrijving(
            session, resultaattype
        ),
        "selectielijstklasse": get_resultaat(session, resultaattype, processtype),
        "toelichting": toelichting,
        "archiefnominatie": get_choice_field(
            find(fields, "waardering", False),
            Archiefnominatie.values,
            DEFAULT_ARCHIEFNOMINATIE,
        ),
        "archiefactietermijn": get_duration(
            find(fields, "bewaartermijn", False),
            find(fields, "bewaartermijn-eenheid", False),
        ),
        "brondatumArchiefprocedure": {
            "afleidingswijze": afleidingswijze,
            "datumkenmerk": datumkenmerk[:80],
            # FIXME fixed values are set to prevent 500 error
            "einddatumBekend": False,
            "objecttype": "",
            "registratie": "",
            "procestermijn": None,
        },
    }
    brondatum_params = resultaattype_data["brondatumArchiefprocedure"]
    if brondatum_params["afleidingswijze"] == "ander_datumkenmerk":
        session.log_info(
            f"resultaattype {resultaattype_data['omschrijving']} doesn't have "
            f"brondatumArchiefprocedure.objecttype. It will be set as 'overige'",
            ObjectTypenKeys.resultaattypen,
        )
        session.log_info(
            f"resultaattype {resultaattype_data['omschrijving']} doesn't have "
            f"brondatumArchiefprocedure.registratie. It will be set as 'TODO'",
            ObjectTypenKeys.resultaattypen,
        )

    return resultaattype_data


def construct_iotype_data(session, document: etree.ElementBase) -> dict:
    fields = document.find("velden")
    iotype_data = {
        "omschrijving": find(fields, "naam")[:80].strip(),
        # FIXME this field is always empty in the example xml
        "vertrouwelijkheidaanduiding": get_choice_field(
            find(fields, "vertrouwelijkheid", False),
            VertrouwelijkheidsAanduidingen.values,
            DEFAULT_VERTROUWELIJKHEID,
        ),
        # begin data whould be set during merging different iotypen later
        "beginGeldigheid": get_date(find(fields, "actueel-van", False)),
        "eindeGeldigheid": get_date(find(fields, "actueel-tot", False)),
    }
    if not iotype_data["beginGeldigheid"]:
        session.log_info(
            f"iotype {iotype_data['omschrijving']} doesn't have beginGeldigheid. It will be set to today.",
            ObjectTypenKeys.informatieobjecttypen,
        )
    return iotype_data


def construct_ziotype_data(session, document: etree.ElementBase) -> dict:
    fields = document.find("velden")
    return {
        "informatieobjecttype_omschrijving": find(fields, "naam")[:80].strip(),
        "volgnummer": document.get("volgnummer"),
        "richting": get_choice_field(
            find(fields, "type", False), RichtingChoices.values, DEFAULT_RICHTING
        ),
        # TODO no mapping for non-required fields
        # "statustype": "http://example.com"
    }


def parse_xml(
    session, tree: etree.ElementTree, processtype_year: int
) -> Tuple[list, list]:
    zaaktypen_data = []
    iotypen_dict = {}
    for process in tree.xpath("/dsp/processen")[0]:
        try:
            zaaktype_data = construct_zaaktype_data(session, process, processtype_year)
        except ParserException as exc:
            session.log_error(
                f"zaaktype {process.get('id')} can't be parsed due to: {exc}",
                ObjectTypenKeys.zaaktypen,
            )
            continue

        roltypen_data = [
            construct_roltype_data(session, roltype)
            for roltype in process.find("roltypen")
        ]
        statustype_data = [
            construct_statustype_data(session, statustype)
            for statustype in process.find("statustypen")
        ]
        resultaattypen_data = []
        for resultaattype in process.find("resultaattypen"):
            try:
                resultaatype_data = construct_resultaattype_data(
                    session, resultaattype, zaaktype_data["selectielijstProcestype"]
                )
            except ParserException as exc:
                session.log_error(
                    f"zaaktype {process.get('id')} resultaattype {resultaattype.get('id')} can't be parsed due to: {exc}",
                    ObjectTypenKeys.resultaattypen,
                )
                continue
            else:
                resultaattypen_data.append(resultaatype_data)

        iotypen_data = [
            construct_iotype_data(session, document)
            for document in process.find("documenttypen")
        ]
        ziotypen_data = [
            construct_ziotype_data(session, document)
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
                and iotypen_dict[iotype_data["omschrijving"]]["beginGeldigheid"]
            ):
                session.log_warning(
                    f"there are different informatieobjectypen with the same omschrijving: {iotype_data['omschrijving']}",
                    ObjectTypenKeys.informatieobjecttypen,
                )
            else:
                iotypen_dict[iotype_data["omschrijving"]] = iotype_data

    return zaaktypen_data, list(iotypen_dict.values())


def extract_counts(zaaktypen_data, iotypen_data):
    count = {
        ObjectTypenKeys.roltypen: 0,
        ObjectTypenKeys.zaaktypen: len(zaaktypen_data),
        ObjectTypenKeys.statustypen: 0,
        ObjectTypenKeys.resultaattypen: 0,
        ObjectTypenKeys.informatieobjecttypen: len(iotypen_data),
        ObjectTypenKeys.zaakinformatieobjecttypen: 0,
    }
    for zaaktype in zaaktypen_data:
        children = zaaktype["_children"]
        count[ObjectTypenKeys.roltypen] += len(children["roltypen"])
        count[ObjectTypenKeys.statustypen] += len(children["statustypen"])
        count[ObjectTypenKeys.resultaattypen] += len(children["resultaattypen"])
        count[ObjectTypenKeys.zaakinformatieobjecttypen] += len(
            children["zaakinformatieobjecttypen"]
        )

    return count

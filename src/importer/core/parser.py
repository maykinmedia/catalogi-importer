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
from .reporting import format_exception
from .selectielijst import (
    get_procestypen,
    get_resultaaten,
    get_resultaattype_omschrijvingen,
)

DEFAULT_VERTROUWELIJKHEID = VertrouwelijkheidsAanduidingen.openbaar
DEFAULT_ROL_OMSCHRIVING = RolOmschrijving.adviseur
DEFAULT_ARCHIEFNOMINATIE = Archiefnominatie.blijvend_bewaren
DEFAULT_AFLEIDINGSWIJZE = BrondatumArchiefprocedureAfleidingswijze.afgehandeld
DEFAULT_RESULTAATTYPE_OMSCHRIJVINGEN = "https://selectielijst.openzaak.nl/api/v1/resultaattypeomschrijvingen/50060769-96b3-4993-ae6a-35ae5fd14604"
DEFAULT_HANDELING_INITIATOR = "n.v.t."
DEFAULT_AANLEIDING = "n.v.t."
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
    else:
        return result or ""


def value_or_default(session, log_scope, value, default):
    """return value if set, else log and return default"""
    if not value:
        session.log_info(f"{log_scope} not defined. It will be set as '{default}'")
        return default
    else:
        return value


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


def quote_join(seq):
    return ", ".join(sorted(f"'{v}'" for v in seq))


def get_choice_field(
    session, log_scope, value: str, choices: dict, default="", required=False
) -> str:
    formatted_value = value.lower().replace(" ", "_")
    if formatted_value in choices:
        return formatted_value

    if not value:
        if required:
            session.log_error(
                f"{log_scope} not defined but marked as required. If continued, this will be set as '{default}'"
            )
        else:
            session.log_info(f"{log_scope} not defined. It will be set as '{default}'")
    else:
        session.log_warning(
            f"{log_scope} cannot find '{formatted_value}' in options {quote_join(choices)}. It will be set as '{default}'"
        )
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

    # fallback naar toelichting veld
    if toechlichting and re.match(r"(.*?), .*", toechlichting):
        return re.match(r"(.*?), .*", toechlichting).group(1)

    return ""


def get_procestype(process: etree.ElementBase, processtype_year: int) -> str:
    # use vernietigingsgrondslag from the first resultaattype of this zaaktype
    resultaattype = process.find("resultaattypen/resultaattype")
    resultaat_number = get_resultaat_number(resultaattype)

    if not resultaat_number:
        # TODO what to do here?
        return ""

    p = get_procestypen(processtype_year)

    procestype_number = int(resultaat_number.split(".")[0])
    procestype = [
        p for p in get_procestypen(processtype_year) if p["nummer"] == procestype_number
    ][0]

    return procestype["url"]


def get_resultaattype_omschrijving(
    session, log_scope, resultaattype: etree.ElementBase
) -> str:
    # Infer URL from naam-model
    omschrijving = find(resultaattype, "velden/naam-model", False)
    resultaattype_omschrijvingen = get_resultaattype_omschrijvingen()
    filtered_omschrijvingen = [
        r for r in resultaattype_omschrijvingen if r["omschrijving"] == omschrijving
    ]

    if not filtered_omschrijvingen:
        session.log_warning(
            f'{log_scope} Used default value for "Resultaattype.omschrijving" ({DEFAULT_RESULTAATTYPE_OMSCHRIJVINGEN}): Import contains a "naam-model" ({omschrijving}) that is not in the Selectielijst API doesn\'t have matching resultaattypeomschrijving.',
            ObjectTypenKeys.resultaattypen,
        )
        return DEFAULT_RESULTAATTYPE_OMSCHRIJVINGEN

    return filtered_omschrijvingen[0]["url"]


def get_resultaat(
    session, log_scope, resultaattype: etree.ElementBase, processtype: str
) -> str:
    resultaat_number = get_resultaat_number(resultaattype)
    if not resultaat_number:
        raise ParserException(
            f'{log_scope} Imported "resultaat" does not contain a resultaat number to find a matching entry in the Selectielijst API.'
        )

    resultaten = get_resultaaten()
    filtered_resultaaten = [
        r
        for r in resultaten
        if r["volledigNummer"] == resultaat_number and r["procesType"] == processtype
    ]
    if not filtered_resultaaten:
        raise ParserException(
            f'{log_scope} Imported "resultaat" does not contain a valid resultaat number ({resultaat_number}) to match "volledigNummer" in the Selectielijst API.'
        )

    return filtered_resultaaten[0]["url"]


def construct_zaaktype_data(
    session, log_scope, process: etree.ElementBase, processtype_year: int
) -> dict:
    fields = process.find("velden")

    # TODO report more default value usage

    indicatie_intern_of_extern = (
        "extern"
        if "extern" in find(fields, "zaaktype-categorie", False).lower()
        else "intern"
    )
    handeling_initiator = value_or_default(
        session,
        f"{log_scope} handelingInitiator",
        find(fields, "zaaktype-naam/structuur/handeling-initiator", False),
        DEFAULT_HANDELING_INITIATOR,
    )
    aanleiding = value_or_default(
        session,
        f"{log_scope} aanleiding",
        find(fields, "aanleiding", False),
        DEFAULT_AANLEIDING,
    )
    onderwerp = value_or_default(
        session,
        f"{log_scope} onderwerp",
        find(fields, "zaaktype-naam/structuur/onderwerp", False),
        DEFAULT_ONDERWERP,
    )
    handeling_behandelaar = value_or_default(
        session,
        f"{log_scope} handeling_behandelaar",
        find(fields, "zaaktype-naam/structuur/handeling-behandelaar", False),
        DEFAULT_HANDELING_BEHANDELAAR,
    )

    servicenorm = get_duration(
        find(fields, "afdoeningstermijn"),
        find(fields, "afdoeningstermijn-eenheid"),
    )
    doorlooptijd = get_duration(
        find(fields, "wettelijke-afdoeningstermijn", False),
        find(fields, "wettelijke-afdoeningstermijn-eenheid", False),
    )
    if not doorlooptijd:
        doorlooptijd = get_duration(
            find(fields, "afdoeningstermijn"),
            find(fields, "afdoeningstermijn-eenheid"),
        )
        session.log_warning(
            f'{log_scope} Used "afdoeningstermijn" ({doorlooptijd}) for "Zaaktype.doorlooptijd": Import has no value for "wettelijke-afdoeningstermijn".'
        )

    # FIXME cam't be set without verlengingstermijn field
    verlengingMogelijk = get_boolean(find(fields, "beroep-mogelijk"))
    if verlengingMogelijk:
        session.log_error(
            f'{log_scope} Cannot set "Zaaktype.verlengingMogelijk" to True: Import indicated "beroep-mogelijk" is True but Open Zaak requires "Zaaktype.verlengingstermijn" to be filled when "Zaaktype.verlengingMogelijk" is True.'
        )
        # set to false to complete
        verlengingMogelijk = False

    return {
        "identificatie": process.get("id"),
        "omschrijving": find(fields, "kernomschrijving"),
        "omschrijvingGeneriek": find(fields, "model-kernomschrijving", False),
        "vertrouwelijkheidaanduiding": get_choice_field(
            session,
            f"{log_scope} vertrouwelijkheidaanduiding",
            find(fields, "vertrouwelijkheid", False),
            VertrouwelijkheidsAanduidingen.values,
            default=DEFAULT_VERTROUWELIJKHEID,
            required=True,
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
        "verlengingMogelijk": verlengingMogelijk,
        # "verlengingstermijn": None, # FIXME no source
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
        "beginGeldigheid": session.job.start_date.isoformat(),
        "eindeGeldigheid": None,
        "versiedatum": get_date(find(fields, "actueel-van")),
        "servicenorm": servicenorm,
        # TODO no mapping for required field
        "productenOfDiensten": [],
        "gerelateerdeZaaktypen": [],
        "besluittypen": [],
        # TODO no mapping for non-required fields
        # "deelzaaktypen": [],
    }


def construct_roltype_data(session, log_scope, roltype: etree.ElementBase) -> dict:
    # We could also use /dsp/rolsoorten/*/rolsoort, it doesn't matter much for our
    # case.
    fields = roltype.find("velden")
    return {
        "omschrijving": find(fields, "naam"),
        "omschrijvingGeneriek": get_choice_field(
            session,
            f"{log_scope} omschrijvingGeneriek",
            find(fields, "naam-model", False),
            RolOmschrijving.values,
            DEFAULT_ROL_OMSCHRIVING,
        ),
    }


def construct_statustype_data(
    session, log_scope, statustype: etree.ElementBase
) -> dict:
    fields = statustype.find("velden")
    return {
        "volgnummer": int(statustype.get("volgnummer")),
        "omschrijving": find(fields, "naam"),
        "omschrijvingGeneriek": find(fields, "naam-model", False),
        "statustekst": find(fields, "bericht", False),
        # TODO no mapping for non-required fields
        # "informeren": true
    }


def construct_resultaattype_data(
    session, log_scope, resultaattype: etree.ElementBase, processtype: str
) -> dict:
    fields = resultaattype.find("velden")
    toelichting = find(fields, "toelichting", False)
    afleidingswijze = get_choice_field(
        session,
        f"{log_scope} afleidingswijze",
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
            session, log_scope, resultaattype
        ),
        "selectielijstklasse": get_resultaat(
            session, log_scope, resultaattype, processtype
        ),
        "toelichting": toelichting,
        "archiefnominatie": get_choice_field(
            session,
            f"{log_scope} archiefnominatie",
            find(fields, "waardering", False),
            Archiefnominatie.values,
            DEFAULT_ARCHIEFNOMINATIE,
        ),
        "archiefactietermijn": get_duration(
            find(fields, "bewaartermijn", False),
            find(fields, "bewaartermijn-eenheid", False),
        ),
        # TODO report trimming datumkenmerk
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
        brondatum_params["objecttype"] = "overige"
        brondatum_params["registratie"] = "TODO"
        session.log_info(
            f"{log_scope} resultaattype '{resultaattype_data['omschrijving']}' doesn't have "
            f"brondatumArchiefprocedure.objecttype. It will be set as 'overige'",
            ObjectTypenKeys.resultaattypen,
        )
        session.log_info(
            f"{log_scope} resultaattype '{resultaattype_data['omschrijving']}' doesn't have "
            f"brondatumArchiefprocedure.registratie. It will be set as 'TODO'",
            ObjectTypenKeys.resultaattypen,
        )

    return resultaattype_data


def construct_iotype_data(session, log_scope, document: etree.ElementBase) -> dict:
    fields = document.find("velden")
    # TODO report trimming string length
    omschrijving = find(fields, "naam")[:80].strip()

    log_scope = f"{log_scope} iotype '{omschrijving}'"

    iotype_data = {
        "omschrijving": omschrijving,
        # FIXME this field is always empty in the example xml
        "vertrouwelijkheidaanduiding": get_choice_field(
            session,
            f"{log_scope} vertrouwelijkheidaanduiding",
            find(fields, "vertrouwelijkheid", False),
            VertrouwelijkheidsAanduidingen.values,
            DEFAULT_VERTROUWELIJKHEID,
        ),
        # begin data would be set during merging different iotypen later
        "beginGeldigheid": session.job.start_date.isoformat(),
        "eindeGeldigheid": None,
    }
    return iotype_data


def construct_ziotype_data(session, log_scope, document: etree.ElementBase) -> dict:
    fields = document.find("velden")
    return {
        # TODO warn on trim naam
        "informatieobjecttype_omschrijving": find(fields, "naam")[:80].strip(),
        "volgnummer": int(document.get("volgnummer")),
        "richting": get_choice_field(
            session,
            f"{log_scope} richting",
            find(fields, "type", False),
            RichtingChoices.values,
            DEFAULT_RICHTING,
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
        log_scope = f"zaaktype {process.get('id')}:"

        try:
            zaaktype_data = construct_zaaktype_data(
                session, log_scope, process, processtype_year
            )
            session.counter.increment_counted(ObjectTypenKeys.zaaktypen)
        except ParserException as exc:
            session.counter.increment_errored(ObjectTypenKeys.zaaktypen)
            session.log_error(
                format_exception(exc),
                ObjectTypenKeys.zaaktypen,
            )
            continue

        roltypen_data = []
        for roltype in process.find("roltypen"):
            try:
                rolype_data = construct_roltype_data(session, log_scope, roltype)
                roltypen_data.append(rolype_data)
                session.counter.increment_counted(ObjectTypenKeys.roltypen)
            except ParserException as exc:
                session.counter.increment_errored(ObjectTypenKeys.roltypen)
                session.log_error(
                    f"{log_scope} Imported roltype '{roltype.get('omschrijving')}' cannot be parsed: {format_exception(exc)}",
                    ObjectTypenKeys.roltypen,
                )
                continue

        statustypen_data = []
        for statustype in process.find("statustypen"):
            try:
                statusype_data = construct_statustype_data(
                    session, log_scope, statustype
                )
                statustypen_data.append(statusype_data)
                session.counter.increment_counted(ObjectTypenKeys.statustypen)
            except ParserException as exc:
                session.counter.increment_errored(ObjectTypenKeys.statustypen)
                session.log_error(
                    f"{log_scope} Imported statustype '{statustype.get('volgnummer')}' cannot be parsed: {format_exception(exc)}",
                    ObjectTypenKeys.statustypen,
                )
                continue

        resultaattypen_data = []
        for resultaattype in process.find("resultaattypen"):
            try:
                resultaatype_data = construct_resultaattype_data(
                    session,
                    log_scope,
                    resultaattype,
                    zaaktype_data["selectielijstProcestype"],
                )
                resultaattypen_data.append(resultaatype_data)
                session.counter.increment_counted(ObjectTypenKeys.resultaattypen)
            except ParserException as exc:
                session.counter.increment_errored(ObjectTypenKeys.resultaattypen)
                session.log_error(
                    f"{log_scope} Imported resultaattype '{resultaattype.get('id')}' cannot be parsed: {format_exception(exc)}",
                    ObjectTypenKeys.resultaattypen,
                )
                continue

        iotypen_data = []
        for iotype in process.find("documenttypen"):
            try:
                ioype_data = construct_iotype_data(session, log_scope, iotype)
                iotypen_data.append(ioype_data)
                session.counter.increment_counted(ObjectTypenKeys.informatieobjecttypen)
            except ParserException as exc:
                session.counter.increment_errored(ObjectTypenKeys.informatieobjecttypen)
                session.log_error(
                    f"{log_scope} Imported documenttype '{iotype.get('omschrijving')}' cannot be parsed: {format_exception(exc)}",
                    ObjectTypenKeys.informatieobjecttypen,
                )
                continue

        ziotypen_data = []
        for ziotype in process.find("documenttypen"):
            try:
                zioype_data = construct_ziotype_data(session, log_scope, ziotype)
                ziotypen_data.append(zioype_data)
                session.counter.increment_counted(
                    ObjectTypenKeys.zaakinformatieobjecttypen
                )
            except ParserException as exc:
                session.counter.increment_errored(
                    ObjectTypenKeys.zaakinformatieobjecttypen
                )
                session.log_error(
                    f"{log_scope} Imported documenttype-zaaktype relatie '{ziotype.get('volgnummer')}' cannot be parsed: {format_exception(exc)}",
                    ObjectTypenKeys.zaakinformatieobjecttypen,
                )
                continue

        zaaktype_data["_children"] = {
            "roltypen": roltypen_data,
            "statustypen": statustypen_data,
            "resultaattypen": resultaattypen_data,
            "zaakinformatieobjecttypen": ziotypen_data,
        }

        zaaktypen_data.append(zaaktype_data)

        for iotype_data in iotypen_data:
            omschrijving = iotype_data["omschrijving"]

            if (
                omschrijving in iotypen_dict
                and iotype_data != iotypen_dict[omschrijving]
                and iotypen_dict[omschrijving]["beginGeldigheid"]
            ):
                session.log_warning(
                    f"{log_scope} Skipping creation of \"Informatieobjectype\" ({omschrijving}): Import contains multiple \"documenttypen\" with the same omschrijving ({iotype_data['omschrijving']})",
                    ObjectTypenKeys.informatieobjecttypen,
                )
            else:
                iotypen_dict[omschrijving] = iotype_data

    return zaaktypen_data, list(iotypen_dict.values())

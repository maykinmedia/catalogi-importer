import logging
from datetime import date
from typing import Dict, List

from zds_client.client import ClientError
from zgw_consumers.models import Service
from zgw_consumers.service import get_paginated_results

logger = logging.getLogger(__name__)


def client_from_url(url):
    client = Service.get_client(url)
    assert client, "A service must be configured first"
    return client


def force_delete_iotypen(catalogus: str, iotypen_data: List[dict]):
    omschrijvings = [iotype_data["omschrijving"] for iotype_data in iotypen_data]
    client = client_from_url(catalogus)
    existed_iotypen = get_paginated_results(
        client,
        "informatieobjecttype",
        query_params={"catalogus": catalogus, "status": "alles"},
    )
    filtered_iotypen = [
        iotype for iotype in existed_iotypen if iotype["omschrijving"] in omschrijvings
    ]
    if filtered_iotypen:
        logger.info(f"{len(filtered_iotypen)} informatieobjecttypen will be overridden")

    for iotype in filtered_iotypen:
        try:
            client.delete("informatieobjecttype", url=iotype["url"])
        except ClientError as exc:
            logger.warning(
                f"informatieobjecttype {iotype['url']} can't be deleted: {exc}"
            )
            continue


def force_delete_zaaktypen(catalogus: str, zaaktypen_data: List[dict]):
    identificaties = [
        zaaktype_data["identificatie"] for zaaktype_data in zaaktypen_data
    ]
    client = client_from_url(catalogus)
    existed_zaaktypen = get_paginated_results(
        client, "zaaktype", query_params={"catalogus": catalogus, "status": "alles"}
    )
    filtered_zaaktypen = [
        iotype
        for iotype in existed_zaaktypen
        if iotype["identificatie"] in identificaties
    ]
    if filtered_zaaktypen:
        logger.info(f"{len(filtered_zaaktypen)} zaaktypen will be overridden")

    for zaaktype in filtered_zaaktypen:
        try:
            client.delete("zaaktype", url=zaaktype["url"])
        except ClientError as exc:
            logger.warning(f"zaaktype {zaaktype['url']} can't be deleted: {exc}")
            continue


def create_zaaktype_children(children_data: List[dict], zaaktype: dict, resource: str):
    zaaktype_url = zaaktype["url"]
    client = client_from_url(zaaktype_url)

    children = []
    for child_data in children_data:
        child_data["zaaktype"] = zaaktype_url

        try:
            child = client.create(resource, data=child_data)
        except ClientError as exc:
            logger.warning(
                f"zaaktype {zaaktype['identificatie']} {resource} {child_data.get('omschrijving')} can't be created: {exc}"
            )
            continue

        children.append(child)

    return children


def create_resultaattypen(resultaattypen_data: List[dict], zaaktype: dict):
    for resultaattype_data in resultaattypen_data:
        brondatum_params = resultaattype_data["brondatumArchiefprocedure"]
        if brondatum_params["afleidingswijze"] == "ander_datumkenmerk":
            brondatum_params["objecttype"] = "overige"
            brondatum_params["registratie"] = "TODO"
            logger.warning(
                f"resultaattype {resultaattype_data['omschrijving']} doesn't have "
                f"brondatumArchiefprocedure.objecttype. It's set as 'overige'"
            )
            logger.warning(
                f"resultaattype {resultaattype_data['omschrijving']} doesn't have "
                f"brondatumArchiefprocedure.registratie. It's set as 'TODO'"
            )
    return create_zaaktype_children(resultaattypen_data, zaaktype, "resultaattype")


def create_zaaktype(zaaktype_data, catalogus):
    client = client_from_url(catalogus)

    zaaktype_data["catalogus"] = catalogus
    zaaktype = client.create("zaaktype", data=zaaktype_data)

    return zaaktype


def create_informatieobjecttype(iotype_data, catalogus, client=None):
    client = client or client_from_url(catalogus)

    iotype_data["catalogus"] = catalogus
    if not iotype_data["beginGeldigheid"]:
        today = date.today().isoformat()
        iotype_data["beginGeldigheid"] = today
        logger.warning(
            f"iotype {iotype_data['omschrijving']} doesn't have beginGeldigheid. It's set as {today}"
        )
    iotype = client.create("informatieobjecttype", data=iotype_data)

    return iotype


def create_zaaktype_informatieobjecttypen(
    ziotypen_data: List[dict], iotypen_urls: Dict[str, str], zaaktype: dict
):
    zaaktype_url = zaaktype["url"]
    client = client_from_url(zaaktype_url)

    ziotypen = []
    for ziotype_data in ziotypen_data:
        iotype_omschriving = ziotype_data.pop("informatieobjecttype_omschrijving")
        ziotype_data["informatieobjecttype"] = iotypen_urls[iotype_omschriving]
        ziotype_data["zaaktype"] = zaaktype_url
        ziotype = client.create("zaakinformatieobjecttype", data=ziotype_data)

        ziotypen.append(ziotype)

    return ziotypen


def load_data(
    zaaktypen_data: List[dict], iotypen_data: List[dict], catalogus: str, force: bool
):
    if force:
        force_delete_iotypen(catalogus, iotypen_data)
        force_delete_zaaktypen(catalogus, zaaktypen_data)

    iotypen = []

    for iotype_data in iotypen_data:

        try:
            iotype = create_informatieobjecttype(iotype_data, catalogus)
        except ClientError as exc:
            logger.warning(
                f"informatieobjecttype {iotype_data['omschrijving']} can't be created: {exc}"
            )
            continue
        else:
            iotypen.append(iotype)

    iotypen_urls = {iotype["omschrijving"]: iotype["url"] for iotype in iotypen}

    for zaaktype_data in zaaktypen_data:
        children = zaaktype_data.pop("_children")

        try:
            zaaktype = create_zaaktype(zaaktype_data, catalogus)
        except ClientError as exc:
            logger.warning(
                f"zaaktype {zaaktype_data['identificatie']} can't be created: {exc}"
            )
            continue

        # create zaaktype relative objects
        create_zaaktype_children(children["roltypen"], zaaktype, "roltype")
        create_zaaktype_children(children["statustypen"], zaaktype, "statustype")
        create_resultaattypen(children["resultaattypen"], zaaktype)
        create_zaaktype_informatieobjecttypen(
            children["zaakinformatieobjecttypen"], iotypen_urls, zaaktype
        )

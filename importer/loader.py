import logging
from datetime import date
from typing import Dict, List

from zgw_consumers.models import Service

logger = logging.getLogger(__name__)


def client_from_url(url):
    client = Service.get_client(url)
    assert client, "A service must be configured first"
    return client


def create_zaaktype_children(children_data: List[dict], zaaktype: str, resource: str):
    client = client_from_url(zaaktype)

    children = []
    for child_data in children_data:
        child_data["zaaktype"] = zaaktype

        child = client.create(resource, data=child_data)
        children.append(child)

    return children


def create_zaaktype(zaaktype_data, catalogus):
    client = client_from_url(catalogus)

    zaaktype_data["catalogus"] = catalogus
    zaaktype = client.create("zaaktype", data=zaaktype_data)

    return zaaktype


def create_informatieobjecttype(iotype_data, catalogus):
    client = client_from_url(catalogus)

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
    ziotypen_data: List[dict], iotypen_urls: Dict[str, str], zaaktype: str
):
    client = client_from_url(zaaktype)

    ziotypen = []
    for ziotype_data in ziotypen_data:
        iotype_omschriving = ziotype_data.pop("informatieobjecttype_omschrijving")
        ziotype_data["informatieobjecttype"] = iotypen_urls[iotype_omschriving]
        ziotype_data["zaaktype"] = zaaktype
        ziotype = client.create("zaakinformatieobjecttype", data=ziotype_data)

        ziotypen.append(ziotype)

    return ziotypen


def load_data(zaaktypen_data: List[dict], iotypen_data: List[dict], catalogus: str):
    iotypen = [
        create_informatieobjecttype(iotype_data, catalogus)
        for iotype_data in iotypen_data
    ]
    iotypen_urls = {iotype["omschrijving"]: iotype["url"] for iotype in iotypen}

    for zaaktype_data in zaaktypen_data:
        children = zaaktype_data.pop("_children")

        zaaktype = create_zaaktype(zaaktype_data, catalogus)
        zaaktype_url = zaaktype["url"]

        # create zaaktype relative objects
        create_zaaktype_children(children["roltypen"], zaaktype_url, "roltype")
        create_zaaktype_children(children["statustypen"], zaaktype_url, "statustype")
        create_zaaktype_children(
            children["resultaattypen"], zaaktype_url, "resultaattype"
        )
        create_zaaktype_informatieobjecttypen(
            children["zaakinformatieobjecttypen"], iotypen_urls, zaaktype_url
        )

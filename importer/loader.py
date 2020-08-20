from typing import List

from zgw_consumers.models import Service


def client_from_url(url):
    client = Service.get_client(url)
    assert client, "A service must be configured first"
    return client


def create_zaaktype_children(children_data: List[dict], zaaktype: str, resource: str):
    client = client_from_url(zaaktype)

    urls = []
    for child_data in children_data:
        child_data["zaaktype"] = zaaktype

        child = client.create(resource, data=child_data)
        urls.append(child["url"])

    print(f"created {resource}: {urls}")

    return urls


def create_zaaktype(zaaktype_data, catalogus):
    client = client_from_url(catalogus)

    zaaktype_data["catalogus"] = catalogus
    zaaktype = client.create("zaaktype", data=zaaktype_data)

    print(f"create zaaktype={zaaktype['url']}")

    return zaaktype["url"]


def load_data(zaaktypen_data: List[dict], catalogus: str):
    for zaaktype_data in zaaktypen_data:
        children = zaaktype_data.pop("_children")

        zaaktype_url = create_zaaktype(zaaktype_data, catalogus)

        # create zaaktype relative objects
        create_zaaktype_children(children["roltypen"], zaaktype_url, "roltype")
        create_zaaktype_children(children["statustypen"], zaaktype_url, "statustype")
        create_zaaktype_children(
            children["resultaattypen"], zaaktype_url, "resultaattype"
        )

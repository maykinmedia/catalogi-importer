from typing import List

from zgw_consumers.models import Service


def client_from_url(url):
    client = Service.get_client(url)
    assert client, "A service must be configured first"
    return client


def create_zaaktype(zaaktype_data, catalogus):
    client = client_from_url(catalogus)

    zaaktype_data["catalogus"] = catalogus
    zaaktype = client.create("zaaktype", data=zaaktype_data)

    return zaaktype["url"]


def load_data(zaaktypen_data: List[dict], catalogus: str):
    for zaaktype_data in zaaktypen_data:
        children_data = zaaktype_data.pop("_children")

        zaaktype_url = create_zaaktype(zaaktype_data, catalogus)

        print("url=", zaaktype_url)

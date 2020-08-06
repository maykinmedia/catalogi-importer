from typing import List

from zgw_consumers.client import ZGWClient
from zgw_consumers.service import get_paginated_results


def get_client() -> ZGWClient:
    from .models import SelectielijstConfig

    config = SelectielijstConfig.get_solo()
    assert config.service, "A service must be configured first"
    return config.service.build_client()


def get_procestypen() -> List[dict]:
    client = get_client()
    return client.list("procestype")


def get_resultaattype_omschrijvingen() -> List[dict]:
    client = get_client()
    return client.list("resultaattypeomschrijvinggeneriek")


def get_resultaaten() -> List[dict]:
    client = get_client()
    return get_paginated_results(client, "resultaat")

from typing import List

from zgw_consumers.client import ZGWClient
from zgw_consumers.service import get_paginated_results

from .cache import cache


def get_client() -> ZGWClient:
    from .models import SelectielijstConfig

    config = SelectielijstConfig.get_solo()
    assert config.service, "A Selectielijst service must be configured first"
    return config.service.build_client()


@cache("selectielijst:procestypen", timeout=60 * 60 * 24)
def get_procestypen() -> List[dict]:
    client = get_client()
    return client.list("procestype")


@cache("selectielijst:resultaattypeomschrijvingen", timeout=60 * 60 * 24)
def get_resultaattype_omschrijvingen() -> List[dict]:
    client = get_client()
    return client.list("resultaattypeomschrijvinggeneriek")


@cache("selectielijst:resultaaten", timeout=60 * 60 * 24)
def get_resultaaten() -> List[dict]:
    client = get_client()
    return get_paginated_results(client, "resultaat")

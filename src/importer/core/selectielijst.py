from typing import List

from zgw_consumers.client import ZGWClient
from zgw_consumers.service import get_paginated_results

from importer.utils.cache import cache


def get_client() -> ZGWClient:
    from .models import SelectielijstConfig

    config = SelectielijstConfig.get_solo()
    assert config.service, "A Selectielijst service must be configured first"
    return config.service.build_client()


@cache("selectielijst:procestypen", timeout=60 * 60 * 24)
def get_procestypen(processtype_year: int = None) -> List[dict]:
    client = get_client()
    query_params = {"jaar": processtype_year} if processtype_year else None
    return client.list("procestype", query_params=query_params)


@cache("selectielijst:resultaattypeomschrijvingen", timeout=60 * 60 * 24)
def get_resultaattype_omschrijvingen() -> List[dict]:
    client = get_client()
    return client.list("resultaattypeomschrijvinggeneriek")


@cache("selectielijst:resultaaten", timeout=60 * 60 * 24)
def get_resultaaten() -> List[dict]:
    client = get_client()
    return get_paginated_results(client, "resultaat")

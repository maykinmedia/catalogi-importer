import logging
from datetime import date
from typing import Dict, List

from requests import HTTPError
from zds_client.client import ClientError
from zgw_consumers.service import get_paginated_results

from importer.core.constants import ObjectTypenKeys
from importer.core.reporting import format_exception

logger = logging.getLogger(__name__)


class LoaderException(Exception):
    pass


def retrieve_zaaktype(client, log_scope, catalogus, identificatie):
    """
    to retrieve a zaaktype by identificatie we need to do a list search
    """
    result = client.list(
        "zaaktype",
        query_params={
            "identificatie": identificatie,
            "catalogus": catalogus,
            "status": "alles",
        },
    )
    if result["count"] > 1:
        # TODO what?
        raise LoaderException(f"{log_scope} found multiple conflicting resources")
    elif result["count"] == 1:
        return result["results"][0]
    else:
        return None


def update_zaaktype(session, zaaktype_data, catalogus):
    """
    update/create a single zaaktype (closing if published)
    """
    client = session.client_from_url(catalogus)
    log_scope = f"zaaktype {zaaktype_data['identificatie']}"

    zaaktype_data["catalogus"] = catalogus

    remote = retrieve_zaaktype(
        client, log_scope, catalogus, zaaktype_data["identificatie"]
    )
    if not remote:
        # create new
        zaaktype = client.create("zaaktype", data=zaaktype_data)
        session.log_info(f"{log_scope} created")
    elif remote["concept"]:
        # update old resource which is still in concept
        zaaktype = client.update("zaaktype", zaaktype_data, url=remote["url"])
        session.log_info(f"{log_scope} updated existing concept: {remote['url']}")
    else:
        # close old resource with start-date of the new resource
        client.partial_update(
            "zaaktype",
            {"eindeGeldigheid": zaaktype_data["beginGeldigheid"]},
            url=remote["url"],
        )
        session.log_info(
            f"{log_scope} closed old resource on {zaaktype_data['beginGeldigheid']}: {remote['url']}"
        )
        # create new resource
        zaaktype = client.create("zaaktype", data=zaaktype_data)
        session.log_info(f"{log_scope} created new version")

    return zaaktype


def update_informatieobjecttypen(session, iotypen_data, catalogus):
    """
    update/create list of informatieobjecttypen

    this is messy because we need to:
    1) backfill some fields
    2) fetch existing resources and create lookup map to match for update/create (API can't search)
    3) run the update/create logic on all items
    """
    client = session.client_from_url(catalogus)

    # pre-process and backfill
    for iotype_data in iotypen_data:
        iotype_data["catalogus"] = catalogus
        if not iotype_data["beginGeldigheid"]:
            today = date.today().isoformat()
            iotype_data["beginGeldigheid"] = today
            session.log_info(
                f"iotype '{iotype_data['omschrijving']}' doesn't have beginGeldigheid. It's set as today ({today})."
            )

    # fetch existing and create lookup
    remote_list = get_paginated_results(
        client,
        "informatieobjecttype",
        query_params={"catalogus": catalogus, "status": "alles"},
    )
    remote_map = {iotype["omschrijving"]: iotype for iotype in remote_list}

    iotypen = []

    # update/create resources
    for iotype_data in iotypen_data:
        log_scope = f"informatieobjecttype '{iotype_data['omschrijving']}'"
        try:
            remote = remote_map.get(iotype_data["omschrijving"])
            if not remote:
                # new resource
                iotype = client.create("informatieobjecttype", data=iotype_data)
                session.log_info(f"{log_scope} created new")
            elif remote["concept"]:
                iotype = client.update(
                    "informatieobjecttype", iotype_data, url=remote["url"]
                )
                session.log_info(
                    f"{log_scope} updated existing concept: {remote['url']}"
                )
            else:
                # close old resource with start-date of the new resource
                client.partial_update(
                    "informatieobjecttype",
                    {"eindeGeldigheid": iotype_data["beginGeldigheid"]},
                    url=remote["url"],
                )
                # create new resource
                iotype = client.create("informatieobjecttype", data=iotype_data)
                session.log_info(
                    f"{log_scope} closed published resource and started new concept"
                )
        except (ClientError, HTTPError) as exc:
            session.log_error(
                f"{log_scope} can't be created: {format_exception(exc)}",
                ObjectTypenKeys.informatieobjecttypen,
            )
            continue
        else:
            iotypen.append(iotype)
            session.counter.increment_count(ObjectTypenKeys.informatieobjecttypen)

    session.flush_counts()

    return iotypen


def update_zaaktype_children(
    session,
    log_scope,
    children_data: List[dict],
    zaaktype: dict,
    resource: str,
    type_key: str,
    match_field: str,
):
    """
    generically update/create a list of zaaktype child-resources
    """
    zaaktype_url = zaaktype["url"]
    client = session.client_from_url(zaaktype_url)

    # fetch existing and make lookup
    remote_list = get_paginated_results(
        client,
        resource,
        query_params={"zaaktype": zaaktype_url, "status": "alles"},
    )
    remote_map = {o[match_field]: o for o in remote_list}

    objects = []

    # update/create resources
    for i, child_data in enumerate(children_data):
        _log_scope = f"{log_scope} {resource} {match_field}='{child_data[match_field]}'"
        child_data["zaaktype"] = zaaktype_url
        try:
            # check the lookup for existing resource
            remote = remote_map.get(child_data[match_field])
            if remote:
                obj = client.update(resource, child_data, url=remote["url"])
                session.log_info(f"{_log_scope} updated existing concept")
            else:
                obj = client.create(resource, child_data)
                session.log_info(f"{_log_scope} created new")
        except (ClientError, HTTPError) as exc:
            session.log_error(
                f"{_log_scope} can't be created: {format_exception(exc)}", type_key
            )
            continue
        else:
            objects.append(obj)
            session.counter.increment_count(type_key)

    session.flush_counts()

    return objects


def update_zaaktype_informatieobjecttypen(
    session,
    log_scope,
    ziotypen_data: List[dict],
    iotypen_urls: Dict[str, str],
    zaaktype: dict,
):
    """
    update/create a list of zaaktype_informatieobjecttypen connecting resources
    """
    for ziotype_data in ziotypen_data:
        iotype_omschriving = ziotype_data.pop("informatieobjecttype_omschrijving")
        ziotype_data["informatieobjecttype"] = iotypen_urls[iotype_omschriving]
        ziotype_data["zaaktype"] = zaaktype["url"]

    # reuse generic
    return update_zaaktype_children(
        session,
        log_scope,
        ziotypen_data,
        zaaktype,
        "zaakinformatieobjecttype",
        ObjectTypenKeys.zaakinformatieobjecttypen,
        "volgnummer",
    )


def load_data(
    session,
    zaaktypen_data: List[dict],
    iotypen_data: List[dict],
    catalogus: str,
):
    """
    load data to catalog
    """
    try:
        iotypen = update_informatieobjecttypen(session, iotypen_data, catalogus)
    except (ClientError, HTTPError) as exc:
        session.log_error(
            f"informatieobjecttypen can't be created: {format_exception(exc)}",
            ObjectTypenKeys.informatieobjecttypen,
        )
        # bail?
        return

    iotypen_urls = {iotype["omschrijving"]: iotype["url"] for iotype in iotypen}

    for zaaktype_data in zaaktypen_data:
        log_scope = f"zaaktype {zaaktype_data['identificatie']}:"

        children = zaaktype_data.pop("_children")
        try:
            zaaktype = update_zaaktype(session, zaaktype_data, catalogus)
        except (ClientError, HTTPError) as exc:
            session.log_error(
                f"{log_scope} can't be created: {format_exception(exc)}",
                ObjectTypenKeys.zaaktypen,
            )
            continue
        else:
            session.counter.increment_count(ObjectTypenKeys.zaaktypen)

        session.flush_counts()

        # create zaaktype relative objects
        update_zaaktype_children(
            session,
            log_scope,
            children["roltypen"],
            zaaktype,
            "roltype",
            ObjectTypenKeys.roltypen,
            "omschrijving",
        )

        update_zaaktype_children(
            session,
            log_scope,
            children["statustypen"],
            zaaktype,
            "statustype",
            ObjectTypenKeys.statustypen,
            "volgnummer",
        )

        update_zaaktype_children(
            session,
            log_scope,
            children["resultaattypen"],
            zaaktype,
            "resultaattype",
            ObjectTypenKeys.resultaattypen,
            "omschrijving",
        )

        update_zaaktype_informatieobjecttypen(
            session,
            log_scope,
            children["zaakinformatieobjecttypen"],
            iotypen_urls,
            zaaktype,
        )

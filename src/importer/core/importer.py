import logging

from lxml import etree
from lxml.etree import LxmlError
from zds_client import ClientError

from importer.core.constants import ObjectTypenKeys
from importer.core.loader import client_from_url, load_data
from importer.core.parser import extract_counts, parse_xml
from importer.core.reporting import ImportSession

logger = logging.getLogger(__name__)


def check_job(job, session):
    """
    very basic shared check
    """
    # TODO verify and print a nice error for SelectieLijst and its get_client()
    try:
        client = client_from_url(job.catalog.url)
    except ClientError as exc:
        session.log_error(str(exc))
        return False

    try:
        catalog = client.retrieve("catalogus", url=job.catalog.url)
    except ClientError as exc:
        session.log_error(f"cannot find catalog with URI '{job.catalog.url}'")
        return False

    return True


def precheck_import(job):
    """
    run the precheck on a job and return additional information in the session
    """
    session = ImportSession(job)
    if not check_job(job, session):
        return session

    try:
        tree = etree.fromstring(job.source.read())
    except LxmlError:
        session.log_error("XML parse error.")
        return session

    # TODO XML version (1.5?)
    # TODO XML schema

    zaaktypen, iotypen = parse_xml(session, tree, job.year)

    counts = extract_counts(zaaktypen, iotypen)
    session.counter.set_count_and_total_from_dict(counts)

    for obj in zaaktypen:
        session.log_info(
            f"zaaktype {obj['identificatie']} '{obj['omschrijving']}'",
            ObjectTypenKeys.zaaktypen,
        )

    session.flush_counts()

    return session


def run_import(job):
    """
    run the actual import for a job and write additional information in the database through the session
    """
    session = ImportSession(job, save_logs=True)
    if not check_job(job, session):
        return session

    try:
        tree = etree.fromstring(job.source.read())
    except LxmlError:
        session.log_error("XML parse error.")
        return session

    zaaktypen, iotypen = parse_xml(session, tree, job.year)

    # keep issues but reset counters
    counts = extract_counts(zaaktypen, iotypen)
    session.counter.set_total_from_dict(counts)
    session.flush_counts()

    # do actual loading
    load_data(session, zaaktypen, iotypen, job.catalog.url)

    # TODO more!

    session.flush_counts()

    return session

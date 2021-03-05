import logging

from lxml import etree
from lxml.etree import LxmlError
from zds_client import ClientError

from importer.core.constants import ObjectTypenKeys
from importer.core.loader import load_data
from importer.core.parser import parse_xml
from importer.core.reporting import ImportSession

logger = logging.getLogger(__name__)


class ImporterException(Exception):
    pass


def check_job(job, session):
    """
    very basic shared check
    """
    # TODO verify and print a nice error for SelectieLijst and its get_client()
    try:
        client = session.client_from_url(job.catalog.url)
    except ClientError as exc:
        session.log_error(str(exc))
        return False

    try:
        catalog = client.retrieve("catalogus", url=job.catalog.url)
    except ClientError as exc:
        session.log_error(f"cannot find catalog with URI '{job.catalog.url}'")
        return False

    return True


def check_xml(tree, session):
    try:
        version = tree.xpath("/dsp/preambule/specificatieversie")[0].text
    except IndexError:
        session.log_error("non supported XML format")
        return False
    else:
        if not version.startswith("ICR1.5."):
            session.log_error(
                f"non supported XML version '{version}' (expected 'ICR1.5.x')"
            )
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

    if not check_xml(tree, session):
        return session

    zaaktypen, iotypen = parse_xml(session, tree, job.year)

    session.flush_counts()

    for obj in zaaktypen:
        session.log_info(
            f"zaaktype {obj['identificatie']} '{obj['omschrijving']}'",
            ObjectTypenKeys.zaaktypen,
        )

    return session


def run_import(job):
    """
    run the actual import for a job and write additional information in the database through the session
    """
    session = ImportSession(job, save_logs=True)
    if not check_job(job, session):
        raise ImporterException("failed precheck")

    try:
        tree = etree.fromstring(job.source.read())
    except LxmlError:
        session.log_error("XML parse error")
        raise ImporterException("XML parse error.")

    if not check_xml(tree, session):
        raise ImporterException("failed XML check")

    zaaktypen, iotypen = parse_xml(session, tree, job.year)

    # keep issues but reset counters
    session.counter.reset_numbers()
    session.flush_counts()

    session.log_info("End of precheck, start loading..")

    # do actual loading
    load_data(session, zaaktypen, iotypen)

    session.flush_counts()

    return session

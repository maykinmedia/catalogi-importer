import logging
from collections import defaultdict
from dataclasses import dataclass, field

from django.conf import settings

from lxml import etree
from lxml.etree import LxmlError
from zds_client import ClientError

from importer.core.choices import JobLogLevel
from importer.core.constants import ObjectTypenKeys
from importer.core.loader import client_from_url, load_data
from importer.core.models import JobLog
from importer.core.parser import extract_counts, parse_xml

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
    for key, count in counts.items():
        session.set_type_count(key, count, set_total=True)

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

    # # keep totals but clear any counts
    session.reset_counts()

    for obj in zaaktypen:
        session.log_info(
            f"zaaktype {obj['identificatie']} '{obj['omschrijving']}'",
            ObjectTypenKeys.zaaktypen,
        )

    # set expected totals
    counts = extract_counts(zaaktypen, iotypen)
    for key, count in counts.items():
        session.set_type_total(key, count)
    session.flush_counts()

    # do actual loading
    load_data(session, zaaktypen, iotypen, job.catalog.url)

    # TODO more!

    session.flush_counts()

    return session


@dataclass()
class LogStats:
    count: int = 0
    total: int = 0
    info: dict = field(default_factory=lambda: defaultdict(int))


class ImportSession:
    """
    helper object to hold and process logs, stats etc during parsing and loading, keeps import code cleaner.

    1) the log feature is a just a list of JobLog objects.

    2) the count/total and log-stats form this structure,
        eg: a key with a tuple with count, a total and a dict of loglevels and counts

    {
        ObjectTypenKeys.roltypen: (10, 10),
        ObjectTypenKeys.zaaktypen: (20, 20),
        ObjectTypenKeys.statustypen: (20, 20),
        ObjectTypenKeys.resultaattypen: (30, 30, {JobLogLevel.warning: 2, JobLogLevel.error: 1}),
        ObjectTypenKeys.informatieobjecttypen: (40, 40, None),
        ObjectTypenKeys.zaakinformatieobjecttypen: (50, 50, {JobLogLevel.warning: 5}),
    }

    """

    def __init__(self, job, save_logs=False):
        self.job = job
        self.logs = list()
        self.stats = defaultdict(LogStats)
        self.save_logs = save_logs

    def add_log(self, level, message):
        assert level in JobLogLevel.values
        self.logs.append(JobLog(level=level, message=message))
        if self.save_logs:
            self.job.add_log(level, message)

    def log_info(self, message, type_key=None):
        self.add_log(JobLogLevel.info, message)
        logger.info(message)
        # lets not count info level but keep the 'type_key' argument for uniformity

    def log_warning(self, message, type_key=None):
        self.add_log(JobLogLevel.warning, message)
        logger.warning(message)
        if type_key:
            self.increment_type_log_count(type_key, JobLogLevel.warning)

    def log_error(self, message, type_key=None):
        self.add_log(JobLogLevel.error, message)
        logger.error(message)
        if type_key:
            self.increment_type_log_count(type_key, JobLogLevel.error)

    def set_type_count(self, type_key, count, set_total=False):
        assert type_key in ObjectTypenKeys.values
        self.stats[type_key].count = count
        if set_total:
            self.stats[type_key].total = count

    def increment_type_count(self, type_key):
        assert type_key in ObjectTypenKeys.values
        self.stats[type_key].count += 1

    def set_type_total(self, type_key, total):
        assert type_key in ObjectTypenKeys.values
        self.stats[type_key].total = total

    def increment_type_log_count(self, type_key, level):
        assert type_key in ObjectTypenKeys.values
        assert level in JobLogLevel.values
        self.stats[type_key].info[level] += 1

    def flush_counts(self):
        counts = self.get_count_data()
        self.job.set_results(counts)

    def reset_counts(self):
        for v in self.stats.values():
            v.count = 0

    def get_count_data(self):
        results = {
            "data": {
                k: (v.count, v.total, v.info or None) for k, v in self.stats.items()
            }
        }
        return results

import logging
from collections import defaultdict
from dataclasses import dataclass, field

from zds_client import ClientError
from zgw_consumers.client import ZGWClient
from zgw_consumers.models import Service

from importer.core.choices import JobLogLevel
from importer.core.constants import ObjectTypenKeys
from importer.core.models import JobLog

logger = logging.getLogger(__name__)


class ImportSession:
    """
    helper object to hold and process logs, stats etc during parsing and loading, keeps import code cleaner.

    the log feature is a just a list of JobLog objects.
    """

    def __init__(self, job, save_logs=False):
        self.job = job
        self.logs = list()
        self.save_logs = save_logs
        self.counter = TypeCounter()
        self._clients = dict()

    @property
    def catalogus_url(self):
        return self.job.catalog.url

    def client_from_url(self, url) -> ZGWClient:
        if url in self._clients:
            return self._clients[url]
        client = Service.get_client(url)
        if not client:
            raise ClientError(f"a ZGW service must be configured first for url '{url}'")
        self._clients[url] = client
        return client

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
            self.counter.increment_issue_count(type_key, JobLogLevel.warning)

    def log_error(self, message, type_key=None):
        self.add_log(JobLogLevel.error, message)
        logger.error(message)
        if type_key:
            self.counter.increment_issue_count(type_key, JobLogLevel.error)

    def flush_counts(self):
        counts = self.counter.get_data()
        self.job.set_statistics(counts)


@dataclass()
class TypeCounterData:
    updated: int = 0
    created: int = 0
    errored: int = 0
    counted: int = 0
    issues: dict = field(default_factory=lambda: defaultdict(int))

    def get_data(self):
        return {
            "updated": self.updated,
            "created": self.created,
            "errored": self.errored,
            "counted": self.counted,
            "issues": self.issues,
        }


class TypeCounter:
    """
    holds a nested counter structure.

    for every ObjectTypenKey we keep a structure to track the number of objects we
     updated, created, errored and a map counting different issue levels
    """

    def __init__(self):
        self.data = defaultdict(TypeCounterData)

    def increment_updated(self, type_key):
        assert type_key in ObjectTypenKeys.values
        self.data[type_key].updated += 1

    def increment_created(self, type_key):
        assert type_key in ObjectTypenKeys.values
        self.data[type_key].created += 1

    def increment_errored(self, type_key):
        assert type_key in ObjectTypenKeys.values
        self.data[type_key].errored += 1

    def increment_counted(self, type_key):
        assert type_key in ObjectTypenKeys.values
        self.data[type_key].counted += 1

    def increment_issue_count(self, type_key, level):
        assert type_key in ObjectTypenKeys.values
        assert level in JobLogLevel.values
        self.data[type_key].issues[level] += 1

    def reset_numbers(self):
        for data in self.data.values():
            data.updated = 0
            data.created = 0
            data.errored = 0

    def reset_issues(self):
        for data in self.data.values():
            for level in data.issues:
                del data.issues[level]

    def get_data(self):
        data = {"data": {k: v.get_data() for k, v in self.data.items()}}
        return data


def transform_precheck_statistics(raw_data):
    """
    Transform a dictionary with progress/result statistics into key/value rows for display

    Output something like:

    [
        ("Roltypen": "1 / 2"),
        ("Zaaktypen": "2 / 5 (4 warnings, 2 errors)"),
        ...
    ]
    """
    # generate table even if we dont have data
    if raw_data is None:
        raw_data = dict()
    data = raw_data.get("data", dict())

    rows = [("", "errored, counted")]
    for key in ObjectTypenKeys.values:
        label = ObjectTypenKeys.values[key]
        value = data[key] if key in data else dict()

        info_fmt = _format_logstats_dict(value.get("issues"))
        stat_fmt = f"{value.get('errored', 0)} / {value.get('counted', 0)}{info_fmt}"

        rows.append((label, stat_fmt))

    return rows


def transform_import_statistics(raw_data):
    """
    Transform a dictionary with progress/result statistics into key/value rows for display
    """

    # generate table even if we dont have data
    if raw_data is None:
        raw_data = dict()
    data = raw_data.get("data", dict())

    rows = [("", "updated, created, errored of total")]
    for key in ObjectTypenKeys.values:
        label = ObjectTypenKeys.values[key]
        value = data[key] if key in data else dict()

        info_fmt = _format_logstats_dict(value.get("issues"))
        stat_fmt = f"{value.get('updated', 0)} / {value.get('created', 0)} / {value.get('errored', 0)} of {value.get('counted', 0)}{info_fmt}"

        rows.append((label, stat_fmt))

    return rows


def _format_logstats_dict(info):
    """
    Format a dictionary of {log_level: count} into a readable one-line string

    {
        "warning", 10,
        "error", 2,
    }

    Output:

    (10 warnings, 2 errors)

    """
    if not info:
        return ""

    parts = []
    for level in JobLogLevel.values:
        if level in info:
            parts.append(f"{info[level]} {JobLogLevel.labels[level].lower()}s")

    if parts:
        return f" ({', '.join(parts)})"
    else:
        return ""


def format_exception(exc):
    """
    Format a readable single-line summary from an Exception, usually a ZGW ClientError for a ValidationError
    """
    if isinstance(exc, ClientError):
        return format_zgw_client_error(exc)
    else:
        return str(exc)


def format_zgw_client_error(exc):
    """
    Format a readable single-line summary from an ClientError, usually a ValidationError

    ValidationError example:

    {
        "type": "http://localhost:9000/ref/fouten/ValidationError/",
        "code": "invalid",
        "title": "Invalid input.",
        "status": 400,
        "detail": "",
        "instance": "urn:uuid:51e15b8d-98e7-4284-9869-94cbcef00d1f",
        "invalidParams": [
            {
                "name": "beginGeldigheid",
                "code": "overlap",
                "reason": "Dit zaaktype komt al voor binnen de catalogus en opgegeven geldigheidsperiode.",
            },
            {
                "name": "nonFieldErrors",
                "code": "unique",
                "reason": "De velden catalogus, omschrijving moeten een unieke set zijn.",
            }
        ],
    }

    > Invalid input: 1) Dit zaaktype komt al voor binnen de catalogus en opgegeven geldigheidsperiode (beginGeldigheid). 2) De velden catalogus, omschrijving moeten een unieke set zijn.

    """
    info = exc.args[0]
    if info["code"] == "invalid":
        params = info["invalidParams"]

        # lets add 1) numbers to multiple 2) errors
        if len(params) == 1:
            message = format_zgw_invalid_param(params[0])
        else:
            message = " ".join(
                f"{i}) {format_zgw_invalid_param(p)}"
                for i, p in enumerate(info["invalidParams"], start=1)
            )

        title = info["title"].rstrip(".")
        return f"{title}: {message}"
    else:
        # TODO support more types
        return f"{info['title']}"


def format_zgw_invalid_param(param):
    """
    Format a single invalid item from format_zgw_client_error(exc) above

    - hide 'nonFieldErrors' as field name
    - inject field name before the final dot of the reason for readability of multiple errors
    """
    reason = param["reason"]
    if param["name"] == "nonFieldErrors":
        return f"{reason}"
    reason = reason.rstrip(".")
    return f"{reason} ({param['name']})."

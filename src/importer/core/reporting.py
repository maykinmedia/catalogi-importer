import logging
from collections import defaultdict
from dataclasses import dataclass, field

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
    count: int = 0
    total: int = 0
    issues: dict = field(default_factory=lambda: defaultdict(int))


class TypeCounter:
    """
    holds a nested counter structure.

    for every ObjectTypenKey we keep a structure to track the total number of objects,
     how many we've seen and a map counting different issue levels

    {
        ObjectTypenKeys.roltypen: (10, 10, None),
        ObjectTypenKeys.zaaktypen: (20, 20, None),
        ObjectTypenKeys.statustypen: (20, 20, None),
        ObjectTypenKeys.resultaattypen: (30, 30, {JobLogLevel.warning: 2, JobLogLevel.error: 1}),
        ObjectTypenKeys.informatieobjecttypen: (40, 40, None),
        ObjectTypenKeys.zaakinformatieobjecttypen: (50, 50, {JobLogLevel.warning: 5}),
    }
    """

    def __init__(self):
        self.data = defaultdict(TypeCounterData)

    def increment_count(self, type_key):
        assert type_key in ObjectTypenKeys.values
        self.data[type_key].count += 1

    def set_count(self, type_key, value):
        assert type_key in ObjectTypenKeys.values
        self.data[type_key].count = value

    def set_total(self, type_key, total):
        assert type_key in ObjectTypenKeys.values
        self.data[type_key].total = total

    def increment_issue_count(self, type_key, level):
        assert type_key in ObjectTypenKeys.values
        assert level in JobLogLevel.values
        self.data[type_key].issues[level] += 1

    def reset_counts(self):
        for data in self.data.values():
            data.count = 0

    def reset_totals(self):
        for data in self.data.values():
            data.total = 0

    def reset_numbers(self):
        for data in self.data.values():
            data.count = 0
            data.total = 0

    def reset_issues(self):
        for data in self.data.values():
            for level in data.issues:
                del data.issues[level]

    def set_total_from_dict(self, count_dict):
        for key, value in count_dict.items():
            self.set_count(key, 0)
            self.set_total(key, value)

    def set_count_and_total_from_dict(self, count_dict):
        for key, value in count_dict.items():
            self.set_count(key, value)
            self.set_total(key, value)

    def get_data(self):
        data = {
            "data": {
                k: (v.count, v.total, v.issues or None) for k, v in self.data.items()
            }
        }
        return data


def transform_statistics(raw_data):
    """
    Transform a dictionary of tuples with progress/result statistics into key/value rows for display

    {
        "data": {
            ObjectTypenKeys.roltypen: (10, 10),
            ObjectTypenKeys.zaaktypen: (20, 20),
            ObjectTypenKeys.statustypen: (20, 20),
            ObjectTypenKeys.resultaattypen: (30, 30, {JobLogLevel.warning: 2, JobLogLevel.error: 1}),
            ObjectTypenKeys.informatieobjecttypen: (40, 40, None),
            ObjectTypenKeys.zaakinformatieobjecttypen: (50, 50, {JobLogLevel.warning: 5}),
        },
    }

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

    rows = []
    for key in ObjectTypenKeys.values:
        label = ObjectTypenKeys.values[key]

        # check if we got a value or show 0/0
        if key in data:
            count, total, logstats = data[key]
        else:
            # default
            count, total, logstats = (0, 0, None)

        # collect formatted
        info_fmt = _format_logstats_dict(logstats)
        if info_fmt:
            info_fmt = " " + info_fmt
        stat_fmt = f"{count} / {total}{info_fmt}"

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
        return f"({', '.join(parts)})"
    else:
        return ""

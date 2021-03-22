from django.utils.translation import ugettext_lazy as _

from djchoices import ChoiceItem, DjangoChoices


class JobState(DjangoChoices):
    initialized = ChoiceItem("initialized", _("Initialized"))
    checking = ChoiceItem("checking", _("Checking"))
    precheck = ChoiceItem("precheck", _("Precheck"))

    queued = ChoiceItem("queued", _("Queued"))
    running = ChoiceItem("running", _("Running"))
    completed = ChoiceItem("completed", _("Completed"))

    error = ChoiceItem("error", _("Error"))


class JobLogLevel(DjangoChoices):
    info = ChoiceItem("info", _("Info"))
    warning = ChoiceItem("warning", _("Warning"))
    error = ChoiceItem("error", _("Error"))

    ICONS = {
        "info": "ℹ",
        "warning": "⚠️️",
        "error": "❌",
        "default": "❓",
    }

    @classmethod
    def get_icon(cls, level):
        return cls.ICONS.get(level) or cls.ICONS["default"]

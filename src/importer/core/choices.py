from django.utils.translation import ugettext_lazy as _

from djchoices import ChoiceItem, DjangoChoices


class JobState(DjangoChoices):
    precheck = ChoiceItem("precheck", _("Precheck"))
    queued = ChoiceItem("queued", _("Queued"))
    running = ChoiceItem("running", _("Running"))
    completed = ChoiceItem("completed", _("Completed"))
    error = ChoiceItem("error", _("Error"))

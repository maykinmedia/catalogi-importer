import logging

from django.core.exceptions import PermissionDenied
from django.views import View

from django_sendfile import sendfile

from importer.utils.storage import private_storage

logger = logging.getLogger(__name__)


class StaffPrivateFileView(View):
    def get(self, request, path):
        if request.user.is_authenticated and request.user.is_staff:
            fs_path = private_storage.path(path)
            logger.info(f"private file access: user_id={request.user.id} path={path}")
            return sendfile(request, fs_path, attachment=True)

        raise PermissionDenied

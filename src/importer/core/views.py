from django.core.exceptions import PermissionDenied
from django.views import View

from sendfile import sendfile

from importer.utils.storage import private_storage


class StaffPrivateFileView(View):
    def get(self, request, path):
        if request.user.is_authenticated and request.user.is_staff:
            fs_path = private_storage.path(path)
            # TODO add access logging?
            return sendfile(request, fs_path, attachment=True)

        raise PermissionDenied

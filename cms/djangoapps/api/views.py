from rest_framework.decorators import api_view, parser_classes, authentication_classes
from rest_framework.parsers import FileUploadParser
from rest_framework.response import Response
from rest_framework import status
import shutil
from django.conf import settings
from openedx.core.lib.api.authentication import OAuth2AuthenticationAllowInactiveUser

import logging

log = logging.getLogger(__name__)

@api_view(['PUT'])
@parser_classes([FileUploadParser])
@authentication_classes((OAuth2AuthenticationAllowInactiveUser, ))
def request_upload_local_file(request, upload_video_name):
    upload_video = request.data['file']
    if hasattr(settings, 'VIDEO_PIPELINE_LOCAL'):
        destination_video = settings.VIDEO_PIPELINE_LOCAL['UPLOAD_FOLDER'] + upload_video_name
        shutil.copy(upload_video.temporary_file_path(), destination_video)
        return Response(status=status.HTTP_200_OK)
    else:
        return Response(status=status.HTTP_500_INTERNAL_SERVER_ERROR)



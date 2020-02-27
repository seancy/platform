from django.conf.urls import include, url
from . import views

urlpatterns = [
    url(r'^v1/', include('cms.djangoapps.api.v1.urls', namespace='v1')),
    url(r'^upload_local/(?P<upload_video_name>.+)$', views.request_upload_local_file, name='upload_local_file'),
]

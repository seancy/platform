# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.conf import settings
from django.conf.urls import url

from . import views

urlpatterns = [
    url(r'^transcript/$', views.my_transcript_view, name='analytics_my_transcript'),
    url(r'^learner_transcript/(?P<user_id>\w+)$', views.transcript_view, name='analytics_learner_transcript'),

    url(r'^transcript/waiver-request/$', views.waiver_request_view, name='waiver_request'),
    url(r'^transcript/{}/process-waiver-request/(?P<waiver_id>[0-9]+)'.format(settings.COURSE_ID_PATTERN),
        views.process_waiver_request, name='process_waiver_request'),

    url(r'^global/$', views.microsite_view, name='analytics_microsite'),

    url(r'^course/$', views.course_view, name='analytics_course'),
    url(r'^course/progress/json/$', views.course_progress_data, name='analytics_course_progress_data'),
    url(r'^course/time_spent/json/$', views.course_time_spent_data, name='analytics_course_time_spent_data'),


    url(r'^learner/$', views.learner_view, name='analytics_learner'),
    url(r'^learner/json/$', views.learner_view_data, name='analytics_learner_data'),
    url(r'^learner/export/json/$', views.learner_export_data, name='analytics_learner_export_data'),
    url(r'^common/get_properties/json/$', views.learner_get_properties, name='analytics_learner_get_properties'),

    url(r'^list_table_downloads/(?P<report>my_transcript|transcript|learner|course|ilt|global|customized)(?:/{})?/$'.format(settings.COURSE_ID_PATTERN),
        views.list_table_downloads, name='list_table_downloads'),
    url(r'^transcript/export/$', views.my_transcript_export_table, name='analytics_my_transcript_export'),
    url(r'^learner_transcript/(?P<user_id>\w+)/export/$', views.transcript_export_table, name='analytics_transcript_export'),
    url(r'^learner/export/$', views.learner_export_table, name='analytics_learner_export'),
    url(r'^course/export/$', views.course_export_table, name='analytics_course_export'),

    url(r'^ilt/$', views.ilt_view, name='analytics_ilt'),
    url(r'^ilt/export/$', views.ilt_export_table, name='analytics_ilt_export'),

    url(r'^customized/$', views.customized_view, name='analytics_customized'),
    url(r'^customized/export/$', views.customized_export_table, name='analytics_customized_export'),
]

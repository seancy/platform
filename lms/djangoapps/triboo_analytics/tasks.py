# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from celery import task
from django.conf import settings

from lms.djangoapps.instructor.enrollment import send_mail_to_student, send_custom_waiver_email


@task(routing_key=settings.HIGH_PRIORITY_QUEUE)
def send_waiver_request_email(users, kwargs):
    for user in users:
        param_dict = {
            'message': kwargs['email_type'],
            'name': user['name'],
            'sections': kwargs['sections'],
            'course_name': kwargs['course_name'],
            'learner_name': kwargs['learner_name'],
            'username': kwargs['username'],
            'country': kwargs['country'],
            'location': kwargs['location'],
            'description': kwargs['description'],
            'accept_link': kwargs['accept_link'],
            'deny_link': kwargs['deny_link'],
            'platform_name': kwargs['platform_name'],
            'site_name': None
        }
        if kwargs['email_type'] == 'forced_waiver_request':
            param_dict.update({'site_theme': kwargs['site_theme']})
            send_custom_waiver_email(user['email'], param_dict)
        else:
            send_mail_to_student(user['email'], param_dict, language=user['language'])
# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import hashlib
import os
from functools import partial
import json
from celery import task
from six import text_type
from django.conf import settings
from django.utils import timezone
from datetime import datetime
import pytz
from django_tables2.export import TableExport
from eventtracking import tracker
from lms.djangoapps.instructor.enrollment import send_mail_to_student, send_custom_waiver_email
from lms.djangoapps.instructor_task.models import ReportStore
from lms.djangoapps.instructor_task.tasks_base import BaseInstructorTask, TASK_LOG
from lms.djangoapps.instructor_task.tasks_helper.runner import run_main_task
from lms.djangoapps.instructor_task.tasks_helper.utils import REPORT_REQUESTED_EVENT_NAME
from opaque_keys.edx.keys import CourseKey
from student.models import CourseEnrollment
from util.file import course_filename_prefix_generator
import models
import tables
from django.http import HttpResponseNotFound
from openedx.core.djangoapps.content.course_overviews.models import CourseOverview
from openedx.core.djangoapps.site_configuration import helpers as configuration_helpers
from django.db.models import Q


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


def path_to(course_key, user_id, filename=''):
    if course_key:
        prefix = hashlib.sha1(text_type(course_key) + str(user_id)).hexdigest()
    else:
        prefix = hashlib.sha1(str(user_id)).hexdigest()
    return os.path.join(prefix, filename)


def links_for_all(storage, user):
    orgs = configuration_helpers.get_current_site_orgs()
    if not orgs:
        return HttpResponseNotFound()
    course_overviews = CourseOverview.objects.none()

    for org in orgs:
        org_course_overviews = CourseOverview.objects.filter(org=org, start__lte=timezone.now())
        course_overviews = course_overviews | org_course_overviews

    course_ids = [o.id for o in course_overviews]
    files = []
    for course_id in course_ids:
        report_dir = path_to(course_id, user.id)
        try:
            _, filenames = storage.listdir(report_dir)
        except OSError:
            filenames = []
        if filenames:
            files.extend([(filename, os.path.join(report_dir, filename)) for filename in filenames])

    report_dir = path_to(None, user.id)
    try:
        _, filenames = storage.listdir(report_dir)
    except OSError:
        filenames = []
    for report in ['course_summary', 'learner', 'ilt', 'my_transcript']:
        filename_start = report
        if report == "my_transcript":
            filename_start = "transcript_%s" % user.username
        for filename in filenames:
            if filename.startswith(filename_start):
                files.append((filename, os.path.join(report_dir, filename)))

    files.sort(key=lambda f: storage.modified_time(f[1]), reverse=True)
    return [(filename, storage.url(full_path)) for filename, full_path in files]


def upload_file_to_store(user_id, course_key, filename, export_format, content, username=None):
    report_store = ReportStore.from_config('TRIBOO_ANALYTICS_REPORTS')
    if filename == "transcript":
        _filename = "{}_{}_{}.{}".format(filename,
                                         username,
                                         timezone.now().strftime("%Y-%m-%d-%H%M"),
                                         export_format)
    else:
        _filename = "{}_{}.{}".format(filename,
                                      timezone.now().strftime("%Y-%m-%d-%H%M"),
                                      export_format)
        if course_key:
            _filename = "{}_{}".format(course_filename_prefix_generator(course_key),
                                  _filename)
        if not course_key and filename.startswith('summary'):
            _filename = "{}_{}_{}.{}".format('course',
                                             filename,
                                             timezone.now().strftime("%Y-%m-%d-%H%M"),
                                             export_format)

    path = path_to(course_key, user_id, _filename)
    report_store.store_content(
        path,
        content
    )
    tracker.emit(REPORT_REQUESTED_EVENT_NAME, {"report_type": _filename})


def convert_period_format(kwargs):
    date_tuple = json.loads(kwargs['start__range'])
    from_date = pytz.utc.localize(datetime.strptime(date_tuple[0], "%Y-%m-%d %H:%M:%S %Z"))
    to_date = pytz.utc.localize(datetime.strptime(date_tuple[1], "%Y-%m-%d %H:%M:%S %Z"))
    kwargs['start__range'] = (from_date, to_date)
    return kwargs


def upload_export_table(_xmodule_instance_args, _entry_id, course_id, _task_input, action_name):
    from .views import (
        get_transcript_table,
        get_table_data,
        get_progress_table_data,
        get_time_spent_table_data,
        get_ilt_global_table_data,
        get_ilt_learner_table_data,
        get_customized_table,
    )

    if not TableExport.is_valid_format(_task_input['export_format']):
        raise UnsupportedExportFormatError()

    table = []
    kwargs = _task_input['report_args']['filter_kwargs']
    exclude = _task_input['report_args']['exclude']

    if 'date_time' in kwargs.keys():
        kwargs['date_time'] = datetime.strptime(kwargs['date_time'], "%Y-%m-%d")

    if 'course_id' in kwargs.keys(): 
        kwargs['course_id'] = CourseKey.from_string(kwargs['course_id'])

    if _task_input['report_name'] == "summary_report":
        report_cls = getattr(models, _task_input['report_args']['report_cls'])
        table_cls = getattr(tables, _task_input['report_args']['table_cls'])
        table = get_table_data(report_cls, table_cls, kwargs, exclude)

    elif _task_input['report_name'] == "progress_report":
        table, _ = get_progress_table_data(kwargs['course_id'], kwargs, exclude)

    elif _task_input['report_name'] == "time_spent_report":
        table, _ = get_time_spent_table_data(kwargs['course_id'], kwargs, exclude)

    elif _task_input['report_name'] == "learner_report":
        report_cls = getattr(models, _task_input['report_args']['report_cls'])
        table_cls = getattr(tables, _task_input['report_args']['table_cls'])
        table = get_table_data(report_cls, table_cls, kwargs, exclude, by_period=True)

    elif _task_input['report_name'] == "ilt_global_report":
        table = get_ilt_global_table_data(kwargs)

    elif _task_input['report_name'] == "ilt_learner_report":
        table = get_ilt_learner_table_data(kwargs, exclude)

    elif _task_input['report_name'] == "transcript":
        if _task_input['report_args']['last_update'].endswith('UTC'):
            datetime_format = "%Y-%m-%d %H:%M:%S UTC"
        else:
            datetime_format = "%Y-%m-%d"
        table, _ = get_transcript_table(_task_input['report_args']['orgs'],
                                        _task_input['report_args']['user_id'],
                                        datetime.strptime(_task_input['report_args']['last_update'], datetime_format))
    else:
        date_time = _task_input['report_args'].get('date_time', None)
        # customized course summary report
        if date_time:
            day = datetime.strptime(date_time, "%Y-%m-%d").date()
            courses_selected = _task_input['report_args'].get('courses_selected', None)
            course_keys = [CourseKey.from_string(id) for id in courses_selected.split(',')]
            course_filter = Q()
            for course_key in course_keys:
                course_filter |= Q(**{'course_id': course_key})
            filters = Q(**{'created': day}) & Q(**kwargs) & course_filter
            report_cls = getattr(models, _task_input['report_args']['report_cls'])
            table_cls = getattr(tables, _task_input['report_args']['table_cls'])
            table, _ = get_customized_table(report_cls, kwargs, filters, table_cls, exclude)


    exporter = TableExport(_task_input['export_format'], table)
    content = exporter.export()

    if _task_input['export_format'] == "json":
        content = json.dumps(json.loads(content), ensure_ascii=False, encoding='utf-8').encode('utf-8')

    if _task_input['report_name'] == "transcript":
        upload_file_to_store(_task_input['user_id'],
                             course_id,
                             _task_input['report_name'],
                             _task_input['export_format'],
                             content,
                             _task_input['report_args']['username'])
    else:
        upload_file_to_store(_task_input['user_id'],
                             course_id,
                             _task_input['report_name'],
                             _task_input['export_format'],
                             content)


@task(base=BaseInstructorTask, routing_key=settings.HIGH_PRIORITY_QUEUE)  # pylint: disable=not-callable
def generate_export_table(entry_id, xmodule_instance_args):
    action_name = 'triboo_analytics_exported'
    TASK_LOG.info(
        u"Task: %s, Triboo Analytics Task ID: %s, Task type: %s, Preparing for task execution",
        xmodule_instance_args.get('task_id'), entry_id, action_name
    )

    task_fn = partial(upload_export_table, xmodule_instance_args)
    return run_main_task(entry_id, task_fn, action_name)



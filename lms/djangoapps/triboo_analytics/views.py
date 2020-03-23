# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import hashlib
import json
import logging
import operator
import collections
import models
import tables
from datetime import datetime
from six import text_type
from pytz import utc
from datetime import datetime, timedelta

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.core.exceptions import ObjectDoesNotExist, PermissionDenied
from django.core.urlresolvers import reverse
from django.db import transaction
from django.http import HttpResponseNotFound, Http404
from django.shortcuts import redirect
from django.utils import timezone
from django.utils.translation import ugettext as _
from django.views.decorators.cache import cache_control
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_GET, require_POST
from django_countries import countries
from django_tables2 import RequestConfig
from django_tables2.export import TableExport
from edxmako.shortcuts import render_to_response
from opaque_keys import InvalidKeyError
from opaque_keys.edx.keys import CourseKey, UsageKey
from openedx.core.djangoapps.content.course_overviews.models import CourseOverview
from openedx.core.djangoapps.content.course_structures.api.v0 import api
from openedx.core.djangoapps.site_configuration import helpers as configuration_helpers
from courseware.courses import get_course_by_id
from courseware.module_render import toc_for_course
from lms.djangoapps.grades.constants import ScoreDatabaseTableEnum
from lms.djangoapps.grades.course_data import CourseData
from lms.djangoapps.grades.course_grade_factory import CourseGradeFactory
from lms.djangoapps.grades.events import SUBSECTION_GRADE_CALCULATED, subsection_grade_calculated
from lms.djangoapps.grades.models import (
    PersistentSubsectionGrade,
    PersistentSubsectionGradeOverride,
    PersistentSubsectionGradeOverrideHistory,
)
from lms.djangoapps.grades.signals.signals import GRADE_EDITED
from lms.djangoapps.grades.subsection_grade import CreateSubsectionGrade
from lms.djangoapps.grades.tasks import recalculate_subsection_grade_v3
from lms.djangoapps.instructor.enrollment import get_user_email_language, send_mail_to_student
from lms.djangoapps.instructor.views.api import require_level
from lms.djangoapps.instructor_task.api_helper import submit_task, AlreadyRunningError
from lms.djangoapps.instructor_task.models import ReportStore
from student.models import CourseEnrollment, WaiverRequest, PendingRequestExitsError, RequestAlreadyApprovedError
from student.roles import CourseInstructorRole, CourseStaffRole
from track.event_transaction_utils import (
    create_new_event_transaction_id,
    get_event_transaction_id,
    get_event_transaction_type,
    set_event_transaction_type
)
from util.json_request import JsonResponse, JsonResponseBadRequest
from util.date_utils import to_timestamp
from opaque_keys.edx.django.models import CourseKeyField
from xmodule.modulestore.django import modulestore
from forms import (
    UserPropertiesHelper,
    TableFilterForm,
    UserPropertiesForm,
    TimePeriodForm,
    AVAILABLE_CHOICES,
)
from models import (
    ANALYTICS_ACCESS_GROUP,
    ANALYTICS_LIMITED_ACCESS_GROUP,
    get_combined_org,
    TrackingLogHelper,
    ReportLog,
    LearnerCourseDailyReport,
    LearnerDailyReport,
    CourseDailyReport,
    LearnerSectionReport,
    MicrositeDailyReport,
    CountryDailyReport,
    IltSession,
    IltLearnerReport
)
from tasks import generate_export_table as generate_export_table_task, links_for_all, \
    send_waiver_request_email
from tables import (
    get_progress_table_class,
    get_time_spent_table_class,
    TranscriptTable,
    LearnerDailyTable,
    CourseTable,
    IltTable,
    IltLearnerTable,
    CustomizedCourseTable,
    UserBaseTable,
)
from django.db.models import Q
from datetime import datetime


logger = logging.getLogger('triboo_analytics')


def analytics_on(func):
    def wrapper(request, *args, **kwargs):
        if not configuration_helpers.get_value('ENABLE_ANALYTICS', settings.FEATURES.get('ENABLE_ANALYTICS', False)):
            raise Http404
        else:
            return func(request, *args, **kwargs)
    return wrapper


def analytics_member_required(func):
    def wrapper(request, *args, **kwargs):
        user_groups = [group.name for group in request.user.groups.all()]
        if (ANALYTICS_ACCESS_GROUP in user_groups or ANALYTICS_LIMITED_ACCESS_GROUP in user_groups):
            return func(request, *args, **kwargs)
        raise PermissionDenied
    return wrapper


def analytics_full_member_required(func):
    def wrapper(request, *args, **kwargs):
        if not ANALYTICS_ACCESS_GROUP in [group.name for group in request.user.groups.all()]:
            raise PermissionDenied
        else:
            return func(request, *args, **kwargs)
    return wrapper


def day2str(day):
    return day.strftime("%Y-%m-%d")


def dt2str(daytime):
    return daytime.strftime("%Y-%m-%d %H:%M:%S %Z")


def config_tables(request, *tables):
    config = RequestConfig(request, paginate={'per_page': 50})
    for t in tables:
        config.configure(t)


def get_transcript_table(orgs, user_id, last_update):
    queryset = LearnerCourseDailyReport.objects.none()
    for org in orgs:
        new_queryset = LearnerCourseDailyReport.filter_by_day(date_time=last_update, org=org, user_id=user_id)
        queryset = queryset | new_queryset
    return TranscriptTable(queryset), queryset


def _transcript_view(user, request, template, report_type):
    orgs = configuration_helpers.get_current_site_orgs()
    if not orgs:
        return HttpResponseNotFound()

    if len(orgs) == 1:
        org = orgs[0]
    else:
        org = get_combined_org(orgs)


    learner_report_enrollments = 0
    learner_report_average_final_score = 0
    learner_report_badges = "0 / 0"
    learner_report_posts = 0
    learner_report_finished = 0
    learner_report_failed = 0
    learner_report_in_progress = 0
    learner_report_not_started = 0
    learner_report_total_time_spent = 0

    last_reportlog = ReportLog.get_latest()
    if last_reportlog:
        last_update = last_reportlog.created

        learner_report = LearnerDailyReport.get_by_day(date_time=last_update, user=user, org=org)
        if learner_report:
            learner_report_enrollments = learner_report.enrollments
            learner_report_average_final_score = learner_report.average_final_score
            learner_report_badges = learner_report.badges
            learner_report_posts = learner_report.posts
            learner_report_finished = learner_report.finished
            learner_report_failed = learner_report.failed
            learner_report_not_started = learner_report.not_started
            learner_report_in_progress = learner_report.in_progress
            learner_report_total_time_spent = learner_report.total_time_spent

        learner_course_table, learner_course_reports = get_transcript_table(orgs, user.id, last_update)
        config_tables(request, learner_course_table)

        courses = []
        all_overviews = CourseOverview.objects.all()
        report_courses = [report.course_id for report in learner_course_reports]
        for overview in all_overviews:
            if overview.id in report_courses:
                courses.append({'id': overview.id, 'display_name': overview.display_name_with_default})

        course_contents = {}
        if configuration_helpers.get_value("ENABLE_WAIVER_REQUEST", False) and report_type == "my_transcript":
            for report in learner_course_reports:
                content = toc_for_course(
                            user, request, modulestore().get_course(report.course_id), None, None, None)
                if 'chapters' in content:
                    for chapter in content['chapters']:
                        chapter['disabled'] = True
                        for section in chapter['sections']:
                            section.pop('due', None)
                            if section['graded']:
                                chapter['disabled'] = False
                                break

                    course_contents[unicode(report.course_id)] = content
            course_contents = json.dumps(course_contents)

    return render_to_response(
            template,
            {
                'course_contents': course_contents,
                'courses': courses,
                'last_update': dt2str(last_update),
                'learner_report_enrollments': learner_report_enrollments if learner_report_enrollments else None,
                'learner_report_average_final_score': learner_report_average_final_score,
                'learner_report_badges': learner_report_badges,
                'learner_report_posts': learner_report_posts,
                'learner_report_finished': learner_report_finished,
                'learner_report_failed': learner_report_failed,
                'learner_report_in_progress': learner_report_in_progress,
                'learner_report_not_started': learner_report_not_started,
                'learner_report_total_time_spent': learner_report_total_time_spent,
                'learner_course_table': learner_course_table,
                'list_table_downloads_url': reverse('list_table_downloads', kwargs={'report': report_type}),
                'user_profile_name': user.profile.name
            }
        )


@analytics_on
@login_required
@ensure_csrf_cookie
def my_transcript_view(request):
    return _transcript_view(request.user, request, "triboo_analytics/my_transcript.html", "my_transcript")


@analytics_on
@login_required
@ensure_csrf_cookie
def transcript_view(request, user_id):
    try:
        user = User.objects.get(id=user_id)
    except (ValueError, User.DoesNotExist):
        return render_to_response(
                "triboo_analytics/transcript.html",
                {"error_message": _("Invalid User ID")}
            )
    return _transcript_view(user, request, "triboo_analytics/transcript.html", "transcript")


@require_POST
@login_required
@ensure_csrf_cookie
def waiver_request_view(request):
    """
    This request accepts POST method only, it creates a waiver request,
    and send email to instructor
    """
    course_id = request.POST.get('course_id')
    sections = request.POST.get('sections')
    description = request.POST.get('description')

    try:
        enrollment = CourseEnrollment.get_enrollment(request.user, CourseKey.from_string(course_id))
        waiver_request = WaiverRequest.create_waiver_request(enrollment=enrollment,
                                                             description=description,
                                                             sections=sections)
        course_key = CourseKey.from_string(course_id)

        # if instructor information is set in site conf, we send email to that instructor
        instructor_name = configuration_helpers.get_value('INSTRUCTOR_NAME', "")
        instructor_email = configuration_helpers.get_value('INSTRUCTOR_EMAIL', None)
        if instructor_email:
            users = [{'name': instructor_name, 'email': instructor_email,
                      'language': None}]
            email_type = 'forced_waiver_request'
        else:
            email_type = 'waiver_request'
            instructors = CourseInstructorRole(course_key).users_with_role()
            users = []
            if instructors:
                for user in instructors:
                    users.append({'name': user.profile.name, 'email': user.email,
                                  'language': get_user_email_language(user)})
            else:
                staffs = CourseStaffRole(course_key).users_with_role()
                for user in staffs:
                    users.append({'name': user.profile.name, 'email': user.email,
                                  'language': get_user_email_language(user)})

        sections = json.loads(sections)
        if isinstance(sections, list):
            sections = None
        else:
            sections = ', '.join(sections)

        param_dict = {'course_name': enrollment.course.display_name_with_default,
                      'site_theme': request.site_theme.id,
                      'sections': sections,
                      'description': description,
                      'email_type': email_type,
                      'learner_name': request.user.profile.name,
                      'username': request.user.username,
                      'country': request.user.profile.lt_custom_country or request.user.profile.country or 'Unknown',
                      'location': request.user.profile.location or 'Unknown',
                      'platform_name': configuration_helpers.get_value('PLATFORM_NAME', settings.PLATFORM_NAME),
                      'accept_link': request.build_absolute_uri(reverse('process_waiver_request', kwargs={
                          'course_id': course_id,
                          'waiver_id': waiver_request.id
                      })) + '?accept=1',
                      'deny_link': request.build_absolute_uri(reverse('process_waiver_request', kwargs={
                          'course_id': course_id,
                          'waiver_id': waiver_request.id
                      })) + '?accept=0'}
        send_waiver_request_email.delay(users, param_dict)
    except PendingRequestExitsError:
        message = _("There can only be one exiting pending task!")
        return JsonResponse({"message": message}, status=409)
    except RequestAlreadyApprovedError:
        message = _("The request is already approved by the instructor!")
        return JsonResponse({"message": message}, status=409)
    except Exception:
        message = _("Unknown error. Please contact the support!")
        return JsonResponse({"message": message}, status=400)

    return JsonResponse({"message": _("Request sent successfully!")}, status=201)


@require_GET
@login_required
@require_level('staff')
def process_waiver_request(request, course_id, waiver_id):
    """
    The view process the waiver request, and send notification email to learner.

    It will return to the processing waiver request page to show the result and
    then redirect to the transcript page
    """
    waiver_request = WaiverRequest.objects.get(id=waiver_id)
    accept_state = request.GET.get('accept')
    instructor = request.user

    if waiver_request.approved is None:
        enrollment = waiver_request.enrollment
        request_sections = json.loads(waiver_request.sections)
        if isinstance(request_sections, dict):
            usage_ids = []
            sections = ', '.join(request_sections)
            for i in request_sections:
                usage_ids += request_sections[i]
        else:
            usage_ids = request_sections
            sections = None
        if accept_state == '1':
            course_key = CourseKey.from_string(course_id)
            course = get_course_by_id(course_key, depth=None)
            grade_models = []
            user = enrollment.user

            for requested_usage_id in usage_ids:
                try:
                    usage_key = UsageKey.from_string(requested_usage_id)
                except InvalidKeyError as exc:
                    logger.info("GradeOverride for User: {} has failed, Reason: {}".format(
                        user.id,
                        exc
                    ))
                    continue
                try:
                    subsection_grade_model = PersistentSubsectionGrade.objects.get(
                        user_id=user.id,
                        course_id=course_key,
                        usage_key=usage_key
                    )
                    if subsection_grade_model.earned_all == subsection_grade_model.possible_all and \
                            subsection_grade_model.earned_graded == subsection_grade_model.possible_graded and \
                            subsection_grade_model.earned_all == subsection_grade_model.earned_graded:
                        usage_ids.remove(requested_usage_id)
                        continue
                    else:
                        grade_models.append(subsection_grade_model)
                except PersistentSubsectionGrade.DoesNotExist:
                    subsection = course.get_child(usage_key)
                    if subsection:
                        subsection_grade_model = create_subsection_grade(user, course, subsection)
                        if subsection_grade_model.earned_all == subsection_grade_model.possible_all and \
                                subsection_grade_model.earned_graded == subsection_grade_model.possible_graded and \
                                subsection_grade_model.earned_all == subsection_grade_model.earned_graded:
                            usage_ids.remove(requested_usage_id)
                            continue
                        else:
                            grade_models.append(subsection_grade_model)
                    else:
                        continue
            if grade_models:
                for obj in grade_models:
                    override_data = {
                        "earned_all_override": obj.possible_all,
                        "possible_all_override": obj.possible_all,
                        "earned_graded_override": obj.possible_all,
                        "possible_graded_override": obj.possible_all
                    }
                    override = create_override(instructor, obj, **override_data)
                    logger.info("GradeOverride succeeded for User: {}, Usage_id: {}, Instrucotr: {}".format(
                        user.id,
                        obj.usage_key,
                        instructor.id
                    ))

            waiver_request.approved = True
            waiver_request.instructor = instructor
            waiver_request.save()
            message = _("The waiver request has been accepted!")
            send_mail_to_student(enrollment.user.email, {'message': 'waiver_request_approved',
                                                         'name': enrollment.user.profile.name,
                                                         'sections': sections,
                                                         'course_name': enrollment.course.display_name_with_default,
                                                         'transcript': request.build_absolute_uri(
                                                             reverse('analytics_my_transcript')),
                                                         'site_name': None
                                                         },
                                 language=get_user_email_language(enrollment.user))

        elif accept_state == '0':
            waiver_request.approved = False
            waiver_request.instructor = instructor
            waiver_request.save()
            message = _("The waiver request has been denied!")
            send_mail_to_student(enrollment.user.email, {'message': 'waiver_request_denied',
                                                         'name': enrollment.user.profile.name,
                                                         'sections': sections,
                                                         'course_name': enrollment.course.display_name_with_default,
                                                         'site_name': None
                                                         },
                                 language=get_user_email_language(enrollment.user))
        else:
            return redirect('spoc_gradebook', course_id)

    else:
        if waiver_request.approved:
            message = _("The waiver request is already accepted by {name}").format(
                name=waiver_request.instructor.profile.name
            )
        else:
            message = _("The waiver request is already denied by {name}").format(
                name=waiver_request.instructor.profile.name
            )

    grade_page_url = reverse('spoc_gradebook', kwargs={'course_id': course_id})
    return render_to_response(
        'triboo_analytics/process_waiver_request.html',
        {
            'message': message,
            'grade_page_url': grade_page_url
        }
    )


def create_subsection_grade(user, course, subsection):
    course_data = CourseData(user, course=course)
    subsection_grade = CreateSubsectionGrade(subsection, course_data.structure, {}, {})
    return subsection_grade.update_or_create_model(user, force_update_subsections=True)


def create_override(request_user, subsection_grade_model, **override_data):
    """
    Helper method to create a `PersistentSubsectionGradeOverride` object
    and send a `GRADE_EDITED` signal.
    """
    override = PersistentSubsectionGradeOverride.update_or_create_override(
        requesting_user=request_user,
        subsection_grade_model=subsection_grade_model,
        feature=PersistentSubsectionGradeOverrideHistory.GRADEBOOK,
        **override_data
    )

    GRADE_EDITED.send(
        sender=None,
        user_id=subsection_grade_model.user_id,
        course_id=subsection_grade_model.course_id,
        modified=override.modified,
    )

    set_event_transaction_type(SUBSECTION_GRADE_CALCULATED)
    create_new_event_transaction_id()

    recalculate_subsection_grade_v3.apply(
        kwargs=dict(
            user_id=subsection_grade_model.user_id,
            anonymous_user_id=None,
            course_id=text_type(subsection_grade_model.course_id),
            usage_id=text_type(subsection_grade_model.usage_key),
            only_if_higher=False,
            expected_modified_time=to_timestamp(override.modified),
            score_deleted=False,
            event_transaction_id=unicode(get_event_transaction_id()),
            event_transaction_type=unicode(get_event_transaction_type()),
            score_db_table=ScoreDatabaseTableEnum.overrides,
            force_update_subsections=True,
        )
    )
    # Emit events to let our tracking system to know we updated subsection grade
    subsection_grade_calculated(subsection_grade_model)
    return override


@analytics_on
@analytics_member_required
@ensure_csrf_cookie
@cache_control(no_cache=True, no_store=True, must_revalidate=True)
def list_table_downloads(_request, report='', course_id=None):
    report_store = ReportStore.from_config(config_name='TRIBOO_ANALYTICS_REPORTS')
    links = links_for_all(report_store.storage, _request.user)
    response_payload = {'download': links}
    return JsonResponse(response_payload)


class UnsupportedExportFormatError(Exception):
    pass


def _export_table(request, course_key, report_name, report_args):
    try:
        task_type = 'triboo_analytics_export_table'
        task_class = generate_export_table_task
        format = request.POST.get('format', None) if request.method == "POST" else request.GET.get('_export', None)
        if format is None:
            body_data = request.body.decode('utf-8')
            data = json.loads(body_data)
            format = data.get('format', None)
        task_input = {
            'user_id': request.user.id,
            'report_name': report_name,
            'export_format': format,
            'report_args': report_args
        }
        task_key = ""
        submit_task(request, task_type, task_class, course_key, task_input, task_key)

    except UnsupportedExportFormatError:
        return JsonResponseBadRequest({"message": _("Invalid export format.")})
    except AlreadyRunningError:
        return JsonResponse({'message': 'task is already running.'})

    return JsonResponse({"message": _("The export report is currently being created. "
                                      "When it's ready, the report will appear in your report "
                                      "list at the bottom of the page. "
                                      "You will be able to download the report when "
                                      "it is complete, it can take several minutes to appear.")})


def _transcript_export_table(request, user):
    orgs = configuration_helpers.get_current_site_orgs()
    if not orgs:
        return HttpResponseNotFound()

    last_reportlog = ReportLog.get_latest()
    if last_reportlog:
        report_args = {
            'orgs': orgs,
            'user_id': user.id,
            'username': user.username,
            'last_update': dt2str(last_reportlog.created)
        }
        return _export_table(request, CourseKeyField.Empty, 'transcript', report_args)
    return JsonResponseBadRequest({"message": _("No report to export.")})


@transaction.non_atomic_requests
@analytics_on
@analytics_full_member_required
@ensure_csrf_cookie
@cache_control(no_cache=True, no_store=True, must_revalidate=True)
def my_transcript_export_table(request):
    return _transcript_export_table(request, request.user)


@transaction.non_atomic_requests
@analytics_on
@analytics_full_member_required
@ensure_csrf_cookie
@cache_control(no_cache=True, no_store=True, must_revalidate=True)
def transcript_export_table(request, user_id):
    try:
        user = User.objects.get(id=user_id)
    except (ValueError, User.DoesNotExist):
        return render_to_response(
            "triboo_analytics/transcript.html",
            {'error_message': _("Invalid User ID")}
        )
    return _transcript_export_table(request, user)


def get_query_dict(request):
    query_dict = collections.OrderedDict()
    if request.method == 'POST':
        data = request.POST.copy()
        for key, value in data.items():
            if 'queried_field_' in key or 'query_string_' in key:
                query_dict[key] = value
        return query_dict
    data = request.GET.copy()
    if data.has_key('clear'):
        return query_dict
    if data.has_key('queried_field'):
        for key, value in data.items():
            if 'queried_field_' in key or 'query_string_' in key:
                query_dict[key] = value
        changed = 0
        # New query will not be added to old queries. One in old queries will be deleted or updated
        current_string, current_field = data['query_string'], data['queried_field']
        for k, v in query_dict.items():
            if v == current_field:
                _, i = k.rsplit('_', 1)
                corresponding_str_key = 'query_string_' + i
                if data.has_key('delete'):
                    del query_dict[k]
                    del query_dict[corresponding_str_key]
                else:
                    query_dict[corresponding_str_key] = data['query_string']
                changed = 1
                break
        # New query will be added to old queries
        if changed == 0:
            query_dict.clear()
            if data.has_key('queried_field_1'):
                for key, value in data.items():
                    if 'queried_field_' in key:
                        _, i = key.rsplit('_', 1)
                        new_key = 'queried_field_' + str(int(i) + 1)
                        new_string_key = 'query_string_' + str(int(i) + 1)
                        new_string_value = data['query_string_' + i]
                        query_dict[new_key] = value
                        query_dict[new_string_key] = new_string_value
            else:
                for key, value in data.items():
                    if 'queried_field_' in key or 'query_string_' in key:
                        query_dict[key] = value
            query_dict['queried_field_1'] = data['queried_field']
            query_dict['query_string_1'] = data['query_string']
    return query_dict


def new_request_copy(request_copy):
    if request_copy.has_key('clear') or request_copy.has_key('delete'):
        for k in request_copy.keys():
            if 'queried_field' in k or 'query_string' in k:
                del request_copy[k]
    return request_copy


def get_filter_kwargs_with_table_exclude(request):
    kwargs = {}
    analytics_user_properties = configuration_helpers.get_value('ANALYTICS_USER_PROPERTIES',
                                                                settings.FEATURES.get('ANALYTICS_USER_PROPERTIES', {}))
    user_properties_helper = UserPropertiesHelper(analytics_user_properties)

    request_copy = request.GET.copy()
    request_copy = new_request_copy(request_copy)
    query_dict = get_query_dict(request)
    if request.method == "POST":
        request_copy = request.POST.copy()
        query_dict = request_copy
    filter_form = TableFilterForm(request_copy, user_properties_helper.get_possible_choices())
    if filter_form.is_valid():
        query_tuples = []
        for key, value in query_dict.items():
            if 'query_string' in key:
                suffix = '_' + key.split('_')[-1] if 'query_string_' in key else ''
                query_field_key = 'queried_field' + suffix
                query_tuples.append((value, query_dict[query_field_key]))

        for query_string, queried_field in query_tuples:
            if query_string:
                if queried_field == "user__profile__country":
                    queried_country = query_string.lower()
                    country_code_by_name = {name.lower(): code for code, name in list(countries)}
                    country_codes = []
                    for country_name in country_code_by_name.keys():
                        if queried_country in country_name:
                            country_codes.append(country_code_by_name[country_name])
                    if country_codes:
                        kwargs['user__profile__country__in'] = country_codes
                    else:
                        kwargs['invalid'] = True
                elif queried_field == "user__profile__lt_gdpr":
                    queried_str = query_string.lower()
                    if queried_str == "true":
                        kwargs[queried_field] = True
                    elif queried_str == "false":
                        kwargs[queried_field] = False
                    else:
                        kwargs['invalid'] = True
                else:
                    kwargs[queried_field + '__icontains'] = query_string

    time_period_form = TimePeriodForm(request_copy)
    from_day = request_copy.get('from_day', None)
    to_day = request_copy.get('to_day', None)
    if from_day and to_day:
        from_date = utc.localize(datetime.strptime(from_day, '%Y-%m-%d'))
        to_date = utc.localize(datetime.strptime(to_day, '%Y-%m-%d')) + timedelta(days=1)
        kwargs['start__range'] = (from_date, to_date)

    exclude = []
    user_properties_form = UserPropertiesForm(request_copy,
                                              user_properties_helper.get_possible_choices(False),
                                              user_properties_helper.get_initial_choices())
    if user_properties_form.is_valid():
        data = user_properties_form.cleaned_data
        if 'user_name' in data['excluded_properties']:
            new_excluded_properties = list(set(data['excluded_properties']) - {'user_name'})
            exclude = new_excluded_properties
        else:
            exclude = data['excluded_properties']

    return filter_form, user_properties_form, time_period_form, kwargs, exclude, query_dict


def get_learner_table_filters(request, orgs, as_string=False):
    learner_report_org = orgs[0]
    if len(orgs) > 1:
        learner_report_org = get_combined_org(orgs)

    last_reportlog = ReportLog.get_latest()
    if last_reportlog:
        last_update = last_reportlog.created
        filter_form, user_properties_form, time_period_form, filter_kwargs, exclude, query_dict = get_filter_kwargs_with_table_exclude(request)
        filter_kwargs.update({
            'org': learner_report_org,
            'date_time': day2str(last_update) if as_string else last_update
        })
        return filter_form, user_properties_form, time_period_form, filter_kwargs, exclude, last_update, query_dict

    return None, None, None, None, None, None, None


def get_course_summary_table_filters(request, course_key, last_update, as_string=False):
    filter_form, user_properties_form, time_period_form, filter_kwargs, exclude, query_dict = get_filter_kwargs_with_table_exclude(request)
    filter_kwargs.update({
        'date_time': day2str(last_update) if as_string else last_update,
        'course_id': "%s" % course_key if as_string else course_key
    })
    return filter_form, user_properties_form, time_period_form, filter_kwargs, exclude, query_dict


def get_ilt_table_filters(request, as_string=False):
    filter_form, user_properties_form, time_period_form, filter_kwargs, exclude, query_dict = get_filter_kwargs_with_table_exclude(request)
    if as_string and 'start__range' in filter_kwargs:
        from_date = filter_kwargs['start__range'][0]
        to_date = filter_kwargs['start__range'][1]
        filter_kwargs['start__range'] = json.dumps((dt2str(from_date), dt2str(to_date)))
    return filter_form, user_properties_form, time_period_form, filter_kwargs, exclude, query_dict


def get_table(report_cls, filter_kwargs, table_cls, exclude):
    if filter_kwargs.pop('invalid', False):
        return table_cls([]), 0

    queryset = report_cls.filter_by_day(**filter_kwargs).prefetch_related('user__profile')
    row_count = queryset.count()
    table = table_cls(queryset, exclude=exclude)
    return table, row_count


def get_customized_table(report_cls, filter_kwargs, filters, table_cls, exclude):
    if filter_kwargs.pop('invalid', False):
        return table_cls([]), 0

    querysets = report_cls.objects.filter(filters).prefetch_related('user__profile')
    row_count = querysets.count()
    table = table_cls(querysets, exclude=exclude)
    return table, row_count


def get_query_triples(query_dict):
    query_triples = []
    for key, value in query_dict.items():
        if 'query_string' in key and value:
            suffix = '_' + key.split('_')[-1] if 'query_string_' in key else ''
            query_field_key = 'queried_field' + suffix
            value_key = query_dict[query_field_key]
            value_choice_key = value_key.split('__')[-1]
            field_name = AVAILABLE_CHOICES[value_choice_key]
            query_triples.append((value, field_name, value_key))
    return query_triples


def get_all_courses(request, orgs):
    course_overviews = CourseOverview.objects.none()

    for org in orgs:
        org_course_overviews = CourseOverview.objects.filter(org=org, start__lte=timezone.now())
        course_overviews = course_overviews | org_course_overviews

    overviews = []
    if ANALYTICS_LIMITED_ACCESS_GROUP in [group.name for group in request.user.groups.all()]:
        for overview in course_overviews:
            instructors = set(CourseInstructorRole(overview.id).users_with_role())
            # staff should be a superset of instructors. Do a union to ensure.
            staff = set(CourseStaffRole(overview.id).users_with_role()).union(instructors)
            if request.user in staff:
                overviews.append(overview)
    else:
        overviews = course_overviews

    courses = {"%s" % overview.id: overview.display_name_with_default for overview in overviews}
    courses_list = sorted(courses.items(), key=operator.itemgetter(1))

    return courses, courses_list


def get_course_triples(course_tuples, last_update):
    triples = []
    for course_id, course_name in course_tuples:
        course_key = CourseKey.from_string(course_id)
        course_report = CourseDailyReport.get_by_day(date_time=last_update, course_id=course_key)
        triple = (course_id, course_name, course_report.enrollments if course_report else None)
        triples.append(triple)
    return triples


@login_required
@analytics_on
@analytics_full_member_required
@ensure_csrf_cookie
def learner_view(request):
    orgs = configuration_helpers.get_current_site_orgs()
    if not orgs:
        return HttpResponseNotFound()

    row_count = 0
    learner_table = None
    filter_form, user_properties_form, time_period_form, filter_kwargs, exclude, last_update, query_dict = get_learner_table_filters(request, orgs)
    if last_update:
        learner_table, row_count = get_table(LearnerDailyReport, filter_kwargs, LearnerDailyTable, exclude)
        config_tables(request, learner_table)
        last_update = dt2str(last_update)
        query_dict = query_dict
        query_triples = get_query_triples(query_dict)

    analytics_user_properties = configuration_helpers.get_value('ANALYTICS_USER_PROPERTIES',
                                                                settings.FEATURES.get('ANALYTICS_USER_PROPERTIES', {}))
    user_properties_helper = UserPropertiesHelper(analytics_user_properties)
    filters_data = user_properties_helper.get_possible_choices()
    show_base = 'false'
    if request.GET and request.GET.get('show_base', 'false') == 'true':
        show_base = 'true'

    return render_to_response(
        "triboo_analytics/learner.html",
        {
            'show_base': show_base,
            'row_count': row_count,
            'learner_table': learner_table,
            'filter_form': filter_form,
            'filters_data': filters_data,
            'query_dict': query_dict,
            'query_triples': query_triples,
            'user_properties_form': user_properties_form,
            'time_period_form': time_period_form,
            'list_table_downloads_url': reverse('list_table_downloads', kwargs={'report': 'learner'}),
            'last_update': last_update
        }
    )


@transaction.non_atomic_requests
@analytics_on
@analytics_full_member_required
@ensure_csrf_cookie
@cache_control(no_cache=True, no_store=True, must_revalidate=True)
def learner_export_table(request):
    orgs = configuration_helpers.get_current_site_orgs()
    if not orgs:
        return HttpResponseNotFound()

    unused_filter_form, unused_prop_form, time_period_form, filter_kwargs, exclude, unused_update, query_dict = get_learner_table_filters(
                                                                                    request,
                                                                                    orgs,
                                                                                    as_string=True)
    report_args = {
        'report_cls': LearnerDailyReport.__name__,
        'filter_kwargs': filter_kwargs,
        'table_cls': LearnerDailyTable.__name__,
        'exclude': list(exclude)
    }
    return _export_table(request, CourseKeyField.Empty, 'learner_report', report_args)


def get_course_progress_table(course_key, enrollments, filter_kwargs, exclude):
    if filter_kwargs.pop('invalid', False):
        return get_progress_table_class([]), 0

    progress_dataset = []
    trophies = {}
    trophies_order = []
    for enrollment in enrollments:
        course_descriptor = modulestore().get_course(course_key)
        if course_descriptor:
            progress_summary = CourseGradeFactory().get_progress(enrollment.user, course_descriptor)
            progress_row = {'user': enrollment.user}
            for chapter in progress_summary['trophies_by_chapter']:
                for trophy in chapter['trophies']:
                    m = hashlib.md5()
                    m.update(trophy['section_format'].encode('utf-8'))
                    trophy_column = m.hexdigest()
                    if not trophy_column in trophies_order:
                        trophies[trophy_column] = trophy['section_format']
                        trophies_order.append(trophy_column)
                    progress_row[trophy_column] = {
                        'result': trophy['result'],
                        'threshold': trophy['threshold']
                    }
            progress_dataset.append(progress_row)

    ordered_trophies = []
    for trophy_column in trophies_order:
        ordered_trophies.append((trophy_column, trophies[trophy_column]))
    ProgressTable = get_progress_table_class(ordered_trophies)
    table = ProgressTable(progress_dataset, exclude=exclude)
    row_count = len(progress_dataset)
    return table, row_count


def get_course_sections(course_key):
    chapters = []
    sections = {}
    course_structure = api.course_structure(course_key)

    for block in course_structure['blocks'].keys():
        if course_structure['blocks'][block]['type'] == "chapter":
            chapter_url = TrackingLogHelper.get_chapter_url(course_structure['blocks'][block]['id'])
            chapter_name = course_structure['blocks'][block]['display_name']
            sections[chapter_url] = {'name': chapter_name, 'sections': []}
            for child in course_structure['blocks'][block]['children']:
                section_url = TrackingLogHelper.get_section_url(child)
                section_key = "%s/%s" % (chapter_url, section_url)
                sections[chapter_url]['sections'].append((section_key, chapter_name))
        else:
            if course_structure['blocks'][block]['type'] == "course":
                for child in course_structure['blocks'][block]['children']:
                    chapters.append(TrackingLogHelper.get_chapter_url(child))
    ordered_chapters = []
    ordered_sections = []
    for chapter in chapters:
        chapter_name = sections[chapter]['name']
        nb_sections_in_chapter = len(sections[chapter]['sections'])
        ordered_chapters.append({'key': chapter, 'name': chapter_name, 'colspan': nb_sections_in_chapter})
        ordered_sections += sections[chapter]['sections']
    return ordered_chapters, ordered_sections


def get_course_time_spent_table(course_key, filter_kwargs, exclude):
    user_times_spent = {}
    time_spent_dataset = []
    sections = {}
    if filter_kwargs.pop('invalid', False):
        reports = CourseEnrollment.objects.none()
    else:
        reports = LearnerSectionReport.objects.filter(course_id=course_key, **filter_kwargs).prefetch_related('user')
    for report in reports:
        if report.user.id not in user_times_spent.keys():
            user_times_spent[report.user.id] = {'user': report.user}
        user_times_spent[report.user.id][report.section_key] = report.time_spent
        sections[report.section_key] = report.section_name
    for user_id, row in user_times_spent.iteritems():
        time_spent_dataset.append(row)

    ordered_chapters, ordered_sections = get_course_sections(course_key)
    table_sections = []
    for section_key, chapter_name in ordered_sections:
        if section_key in sections.keys():
            section_name = sections[section_key]
            table_sections.append({'key': section_key,
                                   'name': section_name,
                                   'chapter': chapter_name})

    TimeSpentTable = get_time_spent_table_class(ordered_chapters, table_sections)
    table = TimeSpentTable(time_spent_dataset, exclude=exclude)
    row_count = len(time_spent_dataset)
    return table, row_count


@login_required
@analytics_on
@analytics_member_required
@ensure_csrf_cookie
def course_view(request):
    report = request.GET.get('report', "summary")
    if report not in ['summary', 'progress', 'time_spent']:
        report = "summary"

    orgs = configuration_helpers.get_current_site_orgs()
    if not orgs:
        return HttpResponseNotFound()

    course_overviews = CourseOverview.objects.none()

    for org in orgs:
        org_course_overviews = CourseOverview.objects.filter(org=org, start__lte=timezone.now())
        course_overviews = course_overviews | org_course_overviews

    overviews = []
    if ANALYTICS_LIMITED_ACCESS_GROUP in [group.name for group in request.user.groups.all()]:
        for overview in course_overviews:
            instructors = set(CourseInstructorRole(overview.id).users_with_role())
            # staff should be a superset of instructors. Do a union to ensure.
            staff = set(CourseStaffRole(overview.id).users_with_role()).union(instructors)
            if request.user in staff:
                overviews.append(overview)
    else:
        overviews = course_overviews

    courses = {"%s" % overview.id: overview.display_name_with_default for overview in overviews}
    courses_list = sorted(courses.items(), key=operator.itemgetter(1))

    course_id = request.GET.get('course_id', None)
    if not course_id:
        return render_to_response(
                'triboo_analytics/course.html',
                {
                    'courses': courses_list,
                    'list_table_downloads_url': reverse('list_table_downloads', kwargs={'report': 'course'}),
                }
            )


    if course_id in courses.keys():
        course_key = CourseKey.from_string(course_id)

        course_report = None
        unique_visitors_csv_data = None
        summary_table = False
        progress_table = False
        time_spent_table = False
        filter_form = None
        user_properties_form = None
        row_count = 0
        last_update = None

        last_reportlog = ReportLog.get_latest()
        if last_reportlog:
            last_update = last_reportlog.course
            course_report = CourseDailyReport.get_by_day(date_time=last_update, course_id=course_key)

            from_date = request.GET.get('from_day')
            from_date = datetime.strptime(from_date, "%Y-%m-%d").date() if from_date else None
            to_date = request.GET.get('to_day')
            to_date = datetime.strptime(to_date, "%Y-%m-%d").date() if to_date else None
            unique_visitors_csv_data = CourseDailyReport.get_unique_visitors_csv_data(course_key, from_date, to_date)

            if report == "summary":
                filter_form, user_properties_form, time_period_form, filter_kwargs, exclude, query_dict = get_course_summary_table_filters(
                                                                                            request,
                                                                                            course_key,
                                                                                            last_update)
                summary_table, row_count = get_table(LearnerCourseDailyReport, filter_kwargs, CourseTable, exclude)
                config_tables(request, summary_table)

            else:
                filter_form, user_properties_form, time_period_form, filter_kwargs, exclude, query_dict = get_filter_kwargs_with_table_exclude(
                                                                                            request)
                report_args = {
                    'filter_kwargs': filter_kwargs,
                    'exclude': exclude
                }
                if report == "progress":
                    if filter_kwargs.pop('invalid', False):
                        enrollments = CourseEnrollment.objects.none()
                    else:
                        enrollments = CourseEnrollment.objects.filter(is_active=True,
                                                                      course_id=course_key,
                                                                      user__is_active=True,
                                                                      **filter_kwargs).prefetch_related('user')
                    nb_enrollments = len(enrollments)
                    if nb_enrollments >= 10000:
                        enrollments = CourseEnrollment.objects.none()

                    progress_table, row_count = get_course_progress_table(course_key, enrollments,
                                                                          filter_kwargs, exclude)
                    config_tables(request, progress_table)

                    if nb_enrollments >= 10000:
                        row_count = -1

                elif report == "time_spent":
                    time_spent_table, row_count = get_course_time_spent_table(course_key, filter_kwargs, exclude)
                    config_tables(request, time_spent_table)

            last_update = dt2str(last_update)
            query_dict = query_dict
            query_triples = get_query_triples(query_dict)

        show_base = 'false'
        if request.GET and request.GET.get('show_base', 'false') == 'true':
            show_base = 'true'

        return render_to_response(
            "triboo_analytics/course.html",
            {
                'show_base':show_base,
                'courses': courses_list,
                'course_id': course_id,
                'course_name': courses.get(course_id),
                'last_update': last_update,
                'course_report': course_report,
                'unique_visitors_csv_data': unique_visitors_csv_data,
                'query_dict': query_dict,
                'query_triples': query_triples,
                'learner_course_table': summary_table,
                'learner_course_progress_table': progress_table,
                'learner_course_time_spent_table': time_spent_table,
                'time_period_form': time_period_form,
                'filter_form': filter_form,
                'user_properties_form': user_properties_form,
                'row_count': row_count,
                'filters_data': get_filters_data(),
                'list_table_downloads_url': reverse('list_table_downloads', kwargs={'report': 'course'}),
            }
        )
    else:
        return render_to_response(
            "triboo_analytics/course.html",
            {'error_message': _("Invalid Course ID")}
        )


@transaction.non_atomic_requests
@analytics_on
@analytics_member_required
@ensure_csrf_cookie
@cache_control(no_cache=True, no_store=True, must_revalidate=True)
def course_export_table(request):
    report = request.GET.get('report', "summary")
    if report not in ['summary', 'progress', 'time_spent']:
        report = "summary"
    orgs = configuration_helpers.get_current_site_orgs()
    if not orgs:
        return HttpResponseNotFound()
    try:
        course_key = CourseKey.from_string(request.GET.get('course_id', None))
    except InvalidKeyError:
        return JsonResponseBadRequest({"message": _("Invalid course id.")})
    last_reportlog = ReportLog.get_latest()
    if last_reportlog:
        last_update = last_reportlog.created

        if report == "summary":
            unused_filter_form, unused_prop_form, time_period_form, filter_kwargs, exclude, query_dict = get_course_summary_table_filters(
                                                                                                            request,
                                                                                                            course_key,
                                                                                                            last_update,
                                                                                                            as_string=True)
            report_args = {
                'report_cls': LearnerCourseDailyReport.__name__,
                'filter_kwargs': filter_kwargs,
                'table_cls': CourseTable.__name__,
                'exclude': list(exclude)
            }
            return _export_table(request, course_key, 'summary_report', report_args)

        else:
            unused_filter_form, unused_prop_form, unused_period_form, filter_kwargs, exclude, query_dict = get_filter_kwargs_with_table_exclude(
                                                                                        request)
            report_args = {
                'filter_kwargs': filter_kwargs,
                'exclude': list(exclude)
            }
            if report == "progress":
                return _export_table(request, course_key, 'progress_report', report_args)
            elif report == "time_spent":
                return _export_table(request, course_key, 'time_spent_report', report_args)
    return None


@analytics_on
@login_required
@analytics_member_required
@ensure_csrf_cookie
def microsite_view(request):
    orgs = configuration_helpers.get_current_site_orgs()
    if not orgs:
        return HttpResponseNotFound()

    microsite_report_org = orgs[0]
    if len(orgs) > 1:
        microsite_report_org = get_combined_org(orgs)

    last_reportlog = ReportLog.get_latest()
    last_update = ""
    if last_reportlog:
        last_update = last_reportlog.created
        microsite_report = MicrositeDailyReport.get_by_day(date_time=last_update, org=microsite_report_org)

        from_date = request.GET.get('from_day')
        from_date = datetime.strptime(from_date, "%Y-%m-%d").date() if from_date else None
        to_date = request.GET.get('to_day')
        to_date = datetime.strptime(to_date, "%Y-%m-%d").date() if to_date else None
        print "LAETITIA -- %s - %s" % (from_date, to_date)
        unique_visitors_csv_data = MicrositeDailyReport.get_unique_visitors_csv_data(microsite_report_org,
                                                                                     from_date,
                                                                                     to_date)
        print "LAETITIA -- %s" % unique_visitors_csv_data
        users_by_country_csv_data = ""
        country_reports = CountryDailyReport.filter_by_day(date_time=last_update, org=microsite_report_org)
        for report in country_reports:
            country_code = report.country.numeric
            if country_code:
                if (country_code / 100) == 0:
                    if (country_code / 10) == 0:
                        country_code = "00%d" % country_code
                    else:
                        country_code = "0%d" % country_code
                else:
                    country_code = "%d" % country_code
                users_by_country_csv_data += "%s,%s,%d\\n" % (country_code, report.country.name, report.nb_users)

        return render_to_response(
                "triboo_analytics/microsite.html",
                {
                    'last_update': dt2str(last_update),
                    'microsite_report': microsite_report,
                    'time_period_form': TimePeriodForm(request.GET.copy()),
                    'unique_visitors_csv_data': unique_visitors_csv_data,
                    'users_by_country_csv_data': users_by_country_csv_data,
                    'list_table_downloads_url': reverse('list_table_downloads', kwargs={'report': 'global'}),
                }
            )

    return render_to_response(
        "triboo_analytics/microsite.html",
        {
            'last_update': "",
            'microsite_report': None,
            'time_period_form': TimePeriodForm(),
            'unique_visitors_csv_data': "",
            'users_by_country_csv_data': "",
            'list_table_downloads_url': reverse('list_table_downloads', kwargs={'report': 'global'}),
        }
    )


def get_ilt_report_table(orgs, filter_kwargs):
    ilt_reports = IltSession.objects.none()
    time_range = None
    if filter_kwargs.has_key('start__range'):
        time_range = filter_kwargs.pop('start__range')

    for org in orgs:
        org_ilt_reports = IltSession.objects.filter(org=org) if not time_range \
                    else IltSession.objects.filter(org=org, start__range=time_range)
        ilt_reports = ilt_reports | org_ilt_reports
    row_count = ilt_reports.count()
    ilt_report_table = IltTable(ilt_reports)
    return ilt_report_table, row_count


def get_ilt_learner_report_table(orgs, filter_kwargs, exclude):
    if filter_kwargs.pop('invalid', False):
        return IltLearnerTable([]), 0

    ilt_reports = IltSession.objects.none()
    time_range = None
    if filter_kwargs.has_key('start__range'):
        time_range = filter_kwargs.pop('start__range')

    for org in orgs:
        org_ilt_reports = IltSession.objects.filter(org=org)
        ilt_reports = ilt_reports | org_ilt_reports

    module_ids = ilt_reports.values_list('ilt_module_id', flat=True)
    ilt_learner_reports = IltLearnerReport.objects.filter(ilt_module_id__in=module_ids, **filter_kwargs).prefetch_related('user__profile')
    if time_range:
        ilt_learner_reports_in_range = IltLearnerReport.objects.filter(ilt_session__start__range=time_range).prefetch_related('user__profile')
        ilt_learner_reports = ilt_learner_reports & ilt_learner_reports_in_range
    row_count = ilt_learner_reports.count()
    ilt_learner_report_table = IltLearnerTable(ilt_learner_reports, exclude=exclude)
    return ilt_learner_report_table, row_count


def get_filters_data(db=True):
    analytics_user_properties = configuration_helpers.get_value('ANALYTICS_USER_PROPERTIES',
                                                                settings.FEATURES.get('ANALYTICS_USER_PROPERTIES', {}))
    user_properties_helper = UserPropertiesHelper(analytics_user_properties)
    filters_data = user_properties_helper.get_possible_choices(db)
    return filters_data


@analytics_on
@login_required
@analytics_member_required
@ensure_csrf_cookie
def ilt_view(request):
    report = request.GET.get('report', "global")
    if report not in ['global', 'learner']:
        report = "global"

    orgs = configuration_helpers.get_current_site_orgs()
    if not orgs:
        return HttpResponseNotFound()

    ilt_report_table = False
    ilt_learner_report_table = False
    filter_form = None
    user_properties_form = None
    row_count = 0

    show_base = 'false'
    if request.GET and request.GET.get('show_base', 'false') == 'true':
        show_base = 'true'

    if report == "global":
        filter_form, user_properties_form, time_period_form, filter_kwargs, exclude, query_dict = get_ilt_table_filters(request)
        ilt_report_table, row_count = get_ilt_report_table(orgs, filter_kwargs)
        config_tables(request, ilt_report_table)

        return render_to_response(
            "triboo_analytics/ilt.html",
            {
                'show_base': show_base,
                'ilt_report_table': ilt_report_table,
                'time_period_form': time_period_form,
                'filter_form': filter_form,
                'user_properties_form': user_properties_form,
                'row_count': row_count,
                'list_table_downloads_url': reverse('list_table_downloads', kwargs={'report': 'ilt'}),
            }
        )

    elif report == "learner":
        filter_form, user_properties_form, time_period_form, filter_kwargs, exclude, query_dict = get_ilt_table_filters(request)
        ilt_learner_report_table, row_count = get_ilt_learner_report_table(orgs, filter_kwargs, exclude)
        config_tables(request, ilt_learner_report_table)
        query_triples = get_query_triples(query_dict)

        return render_to_response(
            "triboo_analytics/ilt.html",
            {
                'show_base': show_base,
                'ilt_learner_report_table': ilt_learner_report_table,
                'time_period_form': time_period_form,
                'filter_form': filter_form,
                'filters_data': get_filters_data(),
                'query_dict': query_dict,
                'query_triples': query_triples,
                'user_properties_form': user_properties_form,
                'row_count': row_count,
                'list_table_downloads_url': reverse('list_table_downloads', kwargs={'report': 'ilt'}),
            }
        )


@transaction.non_atomic_requests
@analytics_on
@analytics_member_required
@ensure_csrf_cookie
@cache_control(no_cache=True, no_store=True, must_revalidate=True)
def ilt_export_table(request):
    report = request.GET.get('report', "global")
    if report not in ['global', 'learner']:
        report = "global"

    orgs = configuration_helpers.get_current_site_orgs()
    if not orgs:
        return HttpResponseNotFound()

    if report == "global":
        unused_filter_form, unused_prop_form, unused_period_form, filter_kwargs, exclude, query_dict = get_ilt_table_filters(request, as_string=True)
        report_args = {
            'orgs': orgs,
            'filter_kwargs': filter_kwargs
        }
        return _export_table(request, CourseKeyField.Empty, 'ilt_global_report', report_args)

    # report == "learner"
    unused_filter_form, unused_prop_form, unused_period_form, filter_kwargs, exclude, query_dict = get_ilt_table_filters(request, as_string=True)
    report_args = {
        'orgs': orgs,
        'filter_kwargs': filter_kwargs,
        'exclude': list(exclude)
    }
    return _export_table(request, CourseKeyField.Empty, 'ilt_learner_report', report_args)


@login_required
@analytics_on
@analytics_full_member_required
@ensure_csrf_cookie
def customized_view(request):

    orgs = configuration_helpers.get_current_site_orgs()
    if not orgs:
        return HttpResponseNotFound()

    report_type = request.GET.get('report_type', None)
    courses_selected = request.GET.get('courses_selected', None)
    report_types = [
        ('course_summary', 'Course Summary', 'multiple'),
        ('course_progress', 'Course Progress', 'single'),
        ('course_time_spent', 'Course Time Spent', 'single'),
        ('learner', 'Learner', ''),
        ('ilt_global', 'ILT Global', ''),
        ('ilt_learner', 'ILT Learner', ''),
    ]
    export_formats = ['csv', 'xls', 'json']
    courses, courses_list = get_all_courses(request, orgs)
    last_reportlog = ReportLog.get_latest()
    last_update = last_reportlog.created
    course_triples = get_course_triples(courses_list, last_update)

    analytics_user_properties = configuration_helpers.get_value('ANALYTICS_USER_PROPERTIES',
                                                                settings.FEATURES.get('ANALYTICS_USER_PROPERTIES', {}))
    user_properties_helper = UserPropertiesHelper(analytics_user_properties)

    request_copy = request.GET.copy()
    request_copy = new_request_copy(request_copy)
    filter_form = TableFilterForm(request_copy, user_properties_helper.get_possible_choices())
    user_properties_form = UserPropertiesForm(request_copy,
                                              user_properties_helper.get_possible_choices(False),
                                              user_properties_helper.get_initial_choices())

    return render_to_response(
        "triboo_analytics/customized.html",
        {
            'report_types': report_types,
            'report_type': report_type,
            'courses': course_triples,
            'courses_selected': courses_selected,
            'filter_form': filter_form,
            'user_properties_form': user_properties_form,
            'export_formats': export_formats,
            'list_table_downloads_url': reverse('list_table_downloads', kwargs={'report': 'course'}),
        }
    )


@transaction.non_atomic_requests
@analytics_on
@analytics_member_required
@ensure_csrf_cookie
@cache_control(no_cache=True, no_store=True, must_revalidate=True)
def customized_export_table(request):

    orgs = configuration_helpers.get_current_site_orgs()
    if not orgs:
        return HttpResponseNotFound()

    report_type = request.POST.get('report_type', None)
    courses_selected = request.POST.get('courses_selected', None)

    if report_type == 'course_summary':
        last_reportlog = ReportLog.get_latest()
        if last_reportlog:
            last_update = last_reportlog.created
            date_time = day2str(last_update)
            filter_form, user_properties_form, time_period_form, filter_kwargs, exclude, query_dict = get_filter_kwargs_with_table_exclude(request)
            report_args = {
                'report_cls': LearnerCourseDailyReport.__name__,
                'filter_kwargs': filter_kwargs,
                'courses_selected': courses_selected,
                'date_time': date_time,
                'table_cls': CustomizedCourseTable.__name__,
                'exclude': list(exclude)
            }
            return _export_table(request, CourseKeyField.Empty, 'summary_report', report_args)

    elif report_type in ['course_progress', 'course_time_spent']:
        try:
            course_key = CourseKey.from_string(courses_selected)
        except InvalidKeyError:
            return JsonResponseBadRequest({"message": _("Invalid course id.")})
        unused_filter_form, unused_prop_form, unused_period_form, filter_kwargs, exclude, query_dict = get_filter_kwargs_with_table_exclude(request)
        report_args = {
            'filter_kwargs': filter_kwargs,
            'exclude': list(exclude)
        }
        if report_type == "course_progress":
            return _export_table(request, course_key, 'progress_report', report_args)
        elif report_type == "course_time_spent":
            return _export_table(request, course_key, 'time_spent_report', report_args)

    elif report_type == 'learner':
        unused_filter_form, unused_prop_form, filter_kwargs, exclude, unused_update, query_dict = get_learner_table_filters(
                                                                                                    request,
                                                                                                    orgs,
                                                                                                    as_string=True)
        report_args = {
            'report_cls': LearnerDailyReport.__name__,
            'filter_kwargs': filter_kwargs,
            'table_cls': LearnerDailyTable.__name__,
            'exclude': list(exclude)
        }
        return _export_table(request, CourseKeyField.Empty, 'learner_report', report_args)

    elif report_type in ['ilt_global', 'ilt_learner']:
        if report_type == "ilt_global":
            unused_filter_form, unused_prop_form, unused_period_form, filter_kwargs, exclude, query_dict = get_ilt_table_filters(request, as_string=True)
            report_args = {
                'orgs': orgs,
                'filter_kwargs': filter_kwargs
            }
            return _export_table(request, CourseKeyField.Empty, 'ilt_global_report', report_args)

        # report_type == "ilt_learner"
        unused_filter_form, unused_prop_form, unused_period_form, filter_kwargs, exclude, query_dict = get_ilt_table_filters(request, as_string=True)
        report_args = {
            'orgs': orgs,
            'filter_kwargs': filter_kwargs,
            'exclude': list(exclude)
        }
        return _export_table(request, CourseKeyField.Empty, 'ilt_learner_report', report_args)


def to_db_tuples(tuples):
    query_tuples = []
    for string, field in tuples:
        prop = field.split('_', 1)[1]
        db_prefix = "user__"
        if prop not in ['email', 'username', 'date_joined']:
            db_prefix += "profile__"
        db_tuple = (string, db_prefix + prop)
        query_tuples.append(db_tuple)
    return query_tuples


def get_filter_kwargs_with_table_exclude_for_json_table(data, selected_props):
    kwargs = {}
    analytics_user_properties = configuration_helpers.get_value('ANALYTICS_USER_PROPERTIES',
                                                                settings.FEATURES.get('ANALYTICS_USER_PROPERTIES', {}))
    user_properties_helper = UserPropertiesHelper(analytics_user_properties)

    tuples = data.get('query_tuples')
    query_tuples = to_db_tuples(tuples)
    for query_string, queried_field in query_tuples:
        if query_string:
            if queried_field == "user__profile__country":
                queried_country = query_string.lower()
                country_code_by_name = {name.lower(): code for code, name in list(countries)}
                country_codes = []
                for country_name in country_code_by_name.keys():
                    if queried_country in country_name:
                        country_codes.append(country_code_by_name[country_name])
                if country_codes:
                    kwargs['user__profile__country__in'] = country_codes
                else:
                    kwargs['invalid'] = True
            elif queried_field == "user__profile__lt_gdpr":
                queried_str = query_string.lower()
                if queried_str == "true":
                    kwargs[queried_field] = True
                elif queried_str == "false":
                    kwargs[queried_field] = False
                else:
                    kwargs['invalid'] = True
            else:
                kwargs[queried_field + '__icontains'] = query_string

    from_day = data.get('from_day', None)
    to_day = data.get('to_day', None)
    if from_day and to_day:
        from_date = utc.localize(datetime.strptime(from_day, '%Y-%m-%d'))
        to_date = utc.localize(datetime.strptime(to_day, '%Y-%m-%d')) + timedelta(days=1)
        kwargs['start__range'] = (from_date, to_date)

    all_properties = ["user_%s" % prop for prop in AVAILABLE_CHOICES.keys()]
    if selected_props:
        selected_props += ['user_name']
    else:
        selected_props = ['user_name']
        for prop in AVAILABLE_CHOICES.keys():
            if prop in analytics_user_properties.keys() and analytics_user_properties[prop] == "default":
                selected_props.append("user_%s" % prop)
    # user_properties_form = UserPropertiesForm(data, user_properties_helper.get_possible_choices(False), initial_choices)
    # exclude = []
    # if user_properties_form.is_valid():
    #     data = user_properties_form.cleaned_data
    #     if 'user_name' in data['excluded_properties']:
    #         new_excluded_properties = list(set(data['excluded_properties']) - {'user_name'})
    #         exclude = new_excluded_properties
    #     else:
    #         exclude = data['excluded_properties']
    exclude = set(all_properties) - set(selected_props)

    return kwargs, exclude


@transaction.non_atomic_requests
@analytics_on
@analytics_member_required
@ensure_csrf_cookie
@cache_control(no_cache=True, no_store=True, must_revalidate=True)
def export_tables(request):
    """
    :param data:
        Filter condition to get query for table.
        Example:
            "{
                'report_type': 'course_summary',
                'courses_selected': 'course-v1:edX+DemoX+Demo_Course',
                'query_tuples': [['Yu', 'user_name'], ['China', 'user_country']],
                'from_day': '',
                'to_day': '',
                'selected_properties': ['user_lt_address', 'user_country'],
                'format': 'csv',
                'csrfmiddlewaretoken': 'nDou5pR169v76UwtX4XOpbQsSTLu6SexeWyd0ykjGR2ahYMV0OY7nddkYQqnT6ze',
                'page': '',
            }"
    :return:
        Serialized table data
    """

    orgs = configuration_helpers.get_current_site_orgs()
    if not orgs:
        return JsonResponseBadRequest({"message": _("Response Not Found.")})

    body_data = request.body.decode('utf-8')
    data = json.loads(body_data)

    report_type = data.get('report_type', None)
    courses_selected = data.get('courses_selected', None)
    selected_properties = data.get('selected_properties', None)

    if report_type == 'course_summary':
        last_reportlog = ReportLog.get_latest()
        if last_reportlog:
            last_update = last_reportlog.created
            date_time = day2str(last_update)
            filter_kwargs, exclude = get_filter_kwargs_with_table_exclude_for_json_table(data, selected_properties)
            report_args = {
                'report_cls': LearnerCourseDailyReport.__name__,
                'filter_kwargs': filter_kwargs,
                'courses_selected': courses_selected,
                'date_time': date_time,
                'table_cls': CustomizedCourseTable.__name__,
                'exclude': list(exclude)
            }
            return _export_table(request, CourseKeyField.Empty, 'summary_report', report_args)

    elif report_type in ['course_progress', 'course_time_spent']:
        try:
            course_key = CourseKey.from_string(courses_selected)
        except InvalidKeyError:
            return JsonResponseBadRequest({"message": _("Invalid course id.")})
        filter_kwargs, exclude = get_filter_kwargs_with_table_exclude_for_json_table(data, selected_properties)
        report_args = {
            'filter_kwargs': filter_kwargs,
            'exclude': list(exclude)
        }
        if report_type == "course_progress":
            return _export_table(request, course_key, 'progress_report', report_args)
        elif report_type == "course_time_spent":
            return _export_table(request, course_key, 'time_spent_report', report_args)

    elif report_type == 'learner':
        learner_report_org = orgs[0]
        if len(orgs) > 1:
            learner_report_org = get_combined_org(orgs)

        last_reportlog = ReportLog.get_latest()
        if last_reportlog:
            last_update = last_reportlog.created
            filter_kwargs, exclude = get_filter_kwargs_with_table_exclude_for_json_table(data, selected_properties)
            filter_kwargs.update({
                'org': learner_report_org,
                'date_time': day2str(last_update)
            })
            report_args = {
                'report_cls': LearnerDailyReport.__name__,
                'filter_kwargs': filter_kwargs,
                'table_cls': LearnerDailyTable.__name__,
                'exclude': list(exclude)
            }
            return _export_table(request, CourseKeyField.Empty, 'learner_report', report_args)

    elif report_type in ['ilt_global', 'ilt_learner']:
        if report_type == "ilt_global":
            filter_kwargs, exclude = get_filter_kwargs_with_table_exclude_for_json_table(data, selected_properties)
            report_args = {
                'orgs': orgs,
                'filter_kwargs': filter_kwargs
            }
            return _export_table(request, CourseKeyField.Empty, 'ilt_global_report', report_args)

        # report_type == "ilt_learner"
        else:
            filter_kwargs, exclude = get_filter_kwargs_with_table_exclude_for_json_table(data, selected_properties)
            report_args = {
                'orgs': orgs,
                'filter_kwargs': filter_kwargs,
                'exclude': list(exclude)
            }
            return _export_table(request, CourseKeyField.Empty, 'ilt_learner_report', report_args)


@transaction.non_atomic_requests
@analytics_on
@analytics_member_required
@ensure_csrf_cookie
@cache_control(no_cache=True, no_store=True, must_revalidate=True)
def course_view_data(request):
    body_data = request.body.decode('utf-8')
    data = json.loads(body_data)
    report = data.get('report_type', 'course_summary')
    selected_properties = data['selected_properties']

    orgs = configuration_helpers.get_current_site_orgs()
    if not orgs:
        return JsonResponseBadRequest({"message": _("Response Not Found.")})
    try:
        course_key = CourseKey.from_string(data.get('course_id', None))
        # course_key = CourseKey.from_string('course-v1:edX+DemoX+Demo_Course')
    except InvalidKeyError:
        return JsonResponseBadRequest({"message": _("Invalid course id.")})

    last_reportlog = ReportLog.get_latest()
    if last_reportlog:
        last_update = last_reportlog.created

        if report == "course_summary":
            filter_kwargs, exclude = get_filter_kwargs_with_table_exclude_for_json_table(data, selected_properties)
            filter_kwargs.update({
                'date_time': day2str(last_update),
                'course_id': "%s" % course_key
            })
            report_args = {
                'report_cls': LearnerCourseDailyReport.__name__,
                'filter_kwargs': filter_kwargs,
                'table_cls': CourseTable.__name__,
                'exclude': list(exclude),
                'page': data['page'],
            }
            task_input = {
                'report_name': "summary_report",
                'report_args': report_args
            }
            return table_view_data(course_key, task_input)

        else:
            filter_kwargs, exclude = get_filter_kwargs_with_table_exclude_for_json_table(data, selected_properties)
            report_args = {
                'filter_kwargs': filter_kwargs,
                'exclude': list(exclude),
                'page': data['page'],
            }
            report_name = "progress_report" if report == "course_progress" else "time_spent_report"
            task_input = {
                'report_name': report_name,
                'report_args': report_args
            }
            return table_view_data(course_key, task_input)
    return None


@transaction.non_atomic_requests
@analytics_on
@analytics_full_member_required
@ensure_csrf_cookie
@cache_control(no_cache=True, no_store=True, must_revalidate=True)
def learner_view_data(request):
    orgs = configuration_helpers.get_current_site_orgs()
    if not orgs:
        return JsonResponseBadRequest({"message": _("Response Not Found.")})

    learner_report_org = orgs[0]
    if len(orgs) > 1:
        learner_report_org = get_combined_org(orgs)

    body_data = request.body.decode('utf-8')
    data = json.loads(body_data)

    selected_properties = data['selected_properties']
    last_reportlog = ReportLog.get_latest()
    if last_reportlog:
        last_update = last_reportlog.created
        filter_kwargs, exclude = get_filter_kwargs_with_table_exclude_for_json_table(data, selected_properties)
        filter_kwargs.update({
            'org': learner_report_org,
            'date_time': day2str(last_update)
        })
        report_args = {
            'report_cls': LearnerDailyReport.__name__,
            'filter_kwargs': filter_kwargs,
            'table_cls': LearnerDailyTable.__name__,
            'exclude': list(exclude),
            'page': data['page'],
        }
        task_input = {
            'report_name': "learner_report",
            'report_args': report_args
        }
        return table_view_data(CourseKeyField.Empty, task_input)


@transaction.non_atomic_requests
@analytics_on
@analytics_full_member_required
@ensure_csrf_cookie
@cache_control(no_cache=True, no_store=True, must_revalidate=True)
def ilt_view_data(request):
    orgs = configuration_helpers.get_current_site_orgs()
    if not orgs:
        return JsonResponseBadRequest({"message": _("Response Not Found.")})

    body_data = request.body.decode('utf-8')
    data = json.loads(body_data)
    report = data.get('report_type', 'ilt_global')
    selected_properties = data['selected_properties']

    last_reportlog = ReportLog.get_latest()
    if last_reportlog:
        last_update = last_reportlog.created
        filter_kwargs, exclude = get_filter_kwargs_with_table_exclude_for_json_table(data, selected_properties)
        if 'start__range' in filter_kwargs:
            from_date = filter_kwargs['start__range'][0]
            to_date = filter_kwargs['start__range'][1]
            filter_kwargs['start__range'] = json.dumps((dt2str(from_date), dt2str(to_date)))
        report_args = {
            'filter_kwargs': filter_kwargs,
            'orgs': orgs,
            'exclude': list(exclude),
            'page': data['page'],
        }
        report_name = 'ilt_global_report' if report == 'ilt_global' else 'ilt_learner_report'
        task_input = {
            'report_name': report_name,
            'report_args': report_args
        }
        return table_view_data(CourseKeyField.Empty, task_input)


def table_view_data(course_id, _task_input):
    try:
        if _task_input['report_name'] == "transcript":
            table, _ = get_transcript_table(_task_input['report_args']['orgs'],
                                            _task_input['report_args']['user_id'],
                                            datetime.strptime(_task_input['report_args']['last_update'], "%Y-%m-%d"))
        elif _task_input['report_name'] == "ilt_global_report":
            kwargs = _task_input['report_args']['filter_kwargs']
            table, _ = get_ilt_report_table(_task_input['report_args']['orgs'],
                                            kwargs)
        elif _task_input['report_name'] == "ilt_learner_report":
            kwargs = _task_input['report_args']['filter_kwargs']
            table, _ = get_ilt_learner_report_table(_task_input['report_args']['orgs'],
                                                    kwargs,
                                                    _task_input['report_args']['exclude'])
        else:
            kwargs = _task_input['report_args']['filter_kwargs']
            exclude = _task_input['report_args']['exclude']
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
            else:
                if _task_input['report_name'] == "progress_report":
                    enrollments = CourseEnrollment.objects.filter(is_active=True,
                                                                  course_id=course_id,
                                                                  user__is_active=True,
                                                                  **kwargs).prefetch_related('user')
                    table, _ = get_course_progress_table(course_id, enrollments, kwargs, exclude)
                elif _task_input['report_name'] == "time_spent_report":
                    table, _ = get_course_time_spent_table(course_id, kwargs, exclude)
                else:
                    report_cls = getattr(models, _task_input['report_args']['report_cls'])
                    table_cls = getattr(tables, _task_input['report_args']['table_cls'])
                    if 'date_time' in kwargs.keys():
                        kwargs['date_time'] = datetime.strptime(kwargs['date_time'], "%Y-%m-%d")
                    if 'course_id' in kwargs.keys():
                        kwargs['course_id'] = CourseKey.from_string(kwargs['course_id'])
                    table, _ = get_table(report_cls, kwargs, table_cls, exclude)

        report_name = _task_input['report_name']
        exporter = TableExport('json', table)
        content = exporter.export()
        content = json.loads(content)
        reversed_filter_dict = reverse_filter_dict(get_filters_data(False))
        response_data = format_headers(content, reversed_filter_dict)
        total_dict = get_total_dict(response_data, report_name)

        page = _task_input['report_args']['page']
        page_start = (page['no'] - 1) * page['size']
        page_end = page['no'] * page['size']
        response_data = response_data[page_start:page_end]
        response_dict = dict(
            list=response_data,
            total=total_dict,

            pagination=dict(
                rowsCount=len(content)
            )
        )
        return JsonResponse(response_dict)
    except Exception as e:
        return JsonResponseBadRequest({"message": "Unable to fetch data."})


def get_total_dict(data, report):
    total_dict = collections.OrderedDict()
    summary_columns = []
    if report == "summary_report":
        summary_columns = ['Progress', 'CurrentScore', 'Badges', 'Posts', 'TotalTimeSpent']
    elif report == "learner_report":
        summary_columns = ['Enrollments', 'Successful', 'Unsuccessful', 'NotStarted', 'AverageFinalScore', 'Badges', 'Posts', 'TotalTimeSpent', 'InProgress']
    for col in summary_columns:
        if col == 'Badges':
            values = []
            for row in data:
                if row[col]:
                    split_str = '(/' if '(' in row[col] else '/'
                    values.append(int(row[col].split(split_str)[0].strip()))
            total_dict[col] = sum(values)
        elif col == 'TotalTimeSpent':
            values = [str2sec(row[col]) for row in data if row[col]]
            total_dict[col] = sec2str(sum(values))
        elif col in ['Progress', 'CurrentScore', 'AverageFinalScore']:
            values = [int(row[col].split('%')[0].strip()) for row in data if row[col]]
            total_dict[col] = str(sum(values) // len(values)) + '%' if values else '0%'
        else:
            values = [row[col] for row in data if row[col] and row[col] != '-']
            total_dict[col] = sum(values)
    return total_dict


def format_headers(data, formats):
    response_data = []
    index = 1
    for row in data:
        new_row = collections.OrderedDict(
            ID=index
        )
        for k, v in row.items():
            if k in formats.keys():
                key = formats[k]
            else:
                key = k.replace(' ', '')
            new_row[key] = v
        response_data.append(new_row)
        index += 1
    return response_data


def reverse_filter_dict(filter_tuples):
    f = collections.OrderedDict()
    for t in filter_tuples:
        f[t[1]] = t[0]
    return f


def str2sec(t):
    h, m, s = t.strip().split(':')
    return int(h) * 3600 + int(m) * 60 + int(s)


def sec2str(sec):
    m, s = divmod(sec, 60)
    h, m = divmod(m, 60)
    t = "%d:%02d:%02d" % (h, m, s)
    return t


@analytics_on
def get_properties(request):
    analytics_user_properties = configuration_helpers.get_value('ANALYTICS_USER_PROPERTIES',
                                                                settings.FEATURES.get('ANALYTICS_USER_PROPERTIES', {}))
    user_properties_helper = UserPropertiesHelper(analytics_user_properties)
    filters_data = user_properties_helper.get_possible_choices2(False)
    json_string = """
    {
        "status":1,
        "message":"",
        "list": []
    }
    """
    jsonData = json.loads(json_string)
    for item in filters_data:
        jsonData['list'].append({
            'text': item[1],
            'value': item[0],
            'type': item[2]
        })
    return JsonResponse(jsonData)

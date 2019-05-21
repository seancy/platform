# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from six import text_type
import logging
import json

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.core.urlresolvers import reverse
from django.db import transaction
from django.http import HttpResponseNotFound, Http404, JsonResponse
from django.shortcuts import redirect
from django.utils.translation import ugettext as _
from django.views.decorators.cache import cache_control
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_GET, require_POST

from lms.djangoapps.courseware.courses import get_course_by_id
from lms.djangoapps.courseware.module_render import toc_for_course
from lms.djangoapps.grades.constants import ScoreDatabaseTableEnum
from lms.djangoapps.grades.course_data import CourseData
from lms.djangoapps.grades.course_grade_factory import CourseGradeFactory
from lms.djangoapps.grades.events import SUBSECTION_GRADE_CALCULATED, subsection_grade_calculated
from lms.djangoapps.grades.models import (
    PersistentCourseGrade,
    PersistentSubsectionGrade,
    PersistentSubsectionGradeOverride,
    PersistentSubsectionGradeOverrideHistory,
)
from lms.djangoapps.grades.subsection_grade import CreateSubsectionGrade
from lms.djangoapps.grades.tasks import recalculate_subsection_grade_v3
from lms.djangoapps.instructor.enrollment import get_user_email_language, send_mail_to_student
from lms.djangoapps.instructor.views.api import require_level
from edxmako.shortcuts import render_to_response
from student.models import CourseEnrollment, WaiverRequest, PendingRequestExitsError, RequestAlreadyApprovedError
from student.roles import CourseInstructorRole, CourseStaffRole
from track.event_transaction_utils import (
    create_new_event_transaction_id,
    get_event_transaction_id,
    get_event_transaction_type,
    set_event_transaction_type
)
from opaque_keys import InvalidKeyError
from opaque_keys.edx.keys import CourseKey, UsageKey
from openedx.core.djangoapps.site_configuration import helpers as configuration_helpers
from util.date_utils import to_timestamp
from xmodule.modulestore.django import modulestore
from .tasks import send_waiver_request_email


log = logging.getLogger('triboo_analytics')


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


def _transcript_view(user, request, template, report_type):

    course_contents = {}
    courses = []
    # we didn't create triboo_analytics models yet, so this queryset
    # is temporary way to get course_id.
    queryset = CourseEnrollment.objects.filter(
        user=user,
        is_active=True
    )
    for enrollment in queryset:
        content = toc_for_course(
            user, request, modulestore().get_course(enrollment.course_id), None, None, None
        )
        for chapter in content['chapters']:
            chapter['disabled'] = True
            for section in chapter['sections']:
                if section['graded']:
                    chapter['disabled'] = False
                    break
        course_contents[unicode(enrollment.course_id)] = content
        overview = enrollment.course_overview
        courses.append({'id': overview.id, 'display_name': overview.display_name_with_default})

    course_contents = json.dumps(course_contents)

    return render_to_response(template, {'course_contents': course_contents, 'courses': courses})


@analytics_on
@login_required
@ensure_csrf_cookie
def my_transcript_view(request):
    return _transcript_view(request.user, request, "triboo_analytics/my_transcript.html", "my_transcript")


@analytics_on
@login_required
@ensure_csrf_cookie
def transcript_view(request, user_id):
    return HttpResponseNotFound()


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
        return JsonResponse(status=409, data={"message": message})
    except RequestAlreadyApprovedError:
        message = _("The request is already approved by the instructor!")
        return JsonResponse(status=409, data={"message": message})
    except Exception:
        message = _("Unknown error. Please contact the support!")
        return JsonResponse(status=400, data={"message": message})

    return JsonResponse(status=201, data={"message": _("Request sent successfully!")})


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
                    log.info("GradeOverride for User: {} has failed, Reason: {}".format(
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
                    log.info("GradeOverride succeeded for User: {}, Usage_id: {}, Instrucotr: {}".format(
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
    return render_to_response('triboo_analytics/process_waiver_request.html', {
        'message': message,
        'grade_page_url': grade_page_url
    })


def create_subsection_grade(user, course, subsection):
    course_data = CourseData(user, course=course)
    subsection_grade = CreateSubsectionGrade(subsection, course_data.structure, {}, {})
    return subsection_grade.update_or_create_model(user, force_update_subsections=True)


def create_override(request_user, subsection_grade_model, **override_data):
    """
    Helper method to create a `PersistentSubsectionGradeOverride` object
    and send a `SUBSECTION_OVERRIDE_CHANGED` signal.
    """
    override = PersistentSubsectionGradeOverride.update_or_create_override(
        requesting_user=request_user,
        subsection_grade_model=subsection_grade_model,
        feature=PersistentSubsectionGradeOverrideHistory.GRADEBOOK,
        **override_data
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
    return HttpResponseNotFound()


@transaction.non_atomic_requests
@analytics_on
@analytics_full_member_required
@ensure_csrf_cookie
@cache_control(no_cache=True, no_store=True, must_revalidate=True)
def my_transcript_export_table(request):
    return HttpResponseNotFound()


@transaction.non_atomic_requests
@analytics_on
@analytics_full_member_required
@ensure_csrf_cookie
@cache_control(no_cache=True, no_store=True, must_revalidate=True)
def transcript_export_table(request, user_id):
    return HttpResponseNotFound()


@login_required
@analytics_on
@analytics_full_member_required
@ensure_csrf_cookie
def learner_view(request):
    return HttpResponseNotFound()


@transaction.non_atomic_requests
@analytics_on
@analytics_full_member_required
@ensure_csrf_cookie
@cache_control(no_cache=True, no_store=True, must_revalidate=True)
def learner_export_table(request):
    return HttpResponseNotFound()


@login_required
@analytics_on
@analytics_member_required
@ensure_csrf_cookie
def course_view(request):
    return HttpResponseNotFound()


@transaction.non_atomic_requests
@analytics_on
@analytics_member_required
@ensure_csrf_cookie
@cache_control(no_cache=True, no_store=True, must_revalidate=True)
def course_export_table(request):
    return HttpResponseNotFound()


@analytics_on
@login_required
@analytics_member_required
@ensure_csrf_cookie
def microsite_view(request):
    return HttpResponseNotFound()


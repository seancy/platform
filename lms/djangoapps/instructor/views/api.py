"""
Instructor Dashboard API views

JSON views which the instructor dashboard requests.

Many of these GETs may become PUTs in the future.
"""
import csv
from datetime import datetime
import decimal
import json
import logging
import random
import re
import string
import StringIO
import time
import unicodecsv
import urllib
from django_countries import countries
from django.conf import settings
from django.contrib.auth.models import User
from django.core.exceptions import (
    MultipleObjectsReturned,
    ObjectDoesNotExist,
    PermissionDenied,
    ValidationError
)
from django.core.mail.message import EmailMessage
from django.urls import reverse
from django.core.validators import validate_email
from django.db import IntegrityError, transaction
from django.http import HttpResponse, HttpResponseBadRequest, HttpResponseForbidden, HttpResponseNotFound
from django.shortcuts import redirect
from django.utils.encoding import DjangoUnicodeDecodeError
from django.utils.html import strip_tags
from django.utils.translation import ugettext as _
from django.utils.translation import pgettext
from django.views.decorators.cache import cache_control
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_http_methods, require_POST
from opaque_keys import InvalidKeyError
from opaque_keys.edx.keys import CourseKey, UsageKey
from six import text_type

import instructor_analytics.basic
import instructor_analytics.csvs
import instructor_analytics.distributions
import lms.djangoapps.instructor.enrollment as enrollment
import lms.djangoapps.instructor_task.api
from bulk_email.models import BulkEmailFlag, CourseEmail
from lms.djangoapps.certificates import api as certs_api
from lms.djangoapps.certificates.models import (
    CertificateInvalidation, CertificateStatuses, CertificateWhitelist, GeneratedCertificate
)
from lms.djangoapps.certificates.queue import XQueueCertInterface
from courseware.access import has_access
from courseware.courses import get_course_by_id, get_course_with_access
from courseware.models import StudentModule
from django_comment_client.utils import (
    has_forum_access,
    get_course_discussion_settings,
    get_group_name,
    get_group_id_for_user
)
from django_comment_common.models import (
    Role,
    FORUM_ROLE_ADMINISTRATOR,
    FORUM_ROLE_MODERATOR,
    FORUM_ROLE_GROUP_MODERATOR,
    FORUM_ROLE_COMMUNITY_TA,
)
from edxmako.shortcuts import render_to_string
from lms.djangoapps.instructor.access import ROLES, allow_access, list_with_level, revoke_access, update_forum_role
from lms.djangoapps.instructor.enrollment import (
    enroll_email,
    enroll_user,
    get_email_params,
    get_user_email_language,
    send_beta_role_email,
    send_mail_to_student,
    unenroll_email,
    unenroll_user
)
from lms.djangoapps.instructor.views import INVOICE_KEY
from lms.djangoapps.instructor.views.instructor_task_helpers import extract_email_features, extract_task_features
from lms.djangoapps.instructor_task.api import submit_override_score
from lms.djangoapps.instructor_task.api_helper import AlreadyRunningError, QueueConnectionError
from lms.djangoapps.instructor_task.models import ReportStore, InstructorTask
from openedx.core.djangoapps.content.course_overviews.models import CourseOverview
from openedx.core.djangoapps.course_groups.cohorts import is_course_cohorted
from openedx.core.djangoapps.site_configuration import helpers as configuration_helpers
from openedx.core.djangoapps.user_api.accounts import (
    USERNAME_MIN_LENGTH,
    USERNAME_MAX_LENGTH,
    USERNAME_BAD_LENGTH_MSG
)
from openedx.core.djangoapps.user_api.accounts.image_helpers import get_profile_image_urls_for_user
from openedx.core.djangoapps.user_api.preferences.api import get_user_preference, set_user_preference
from openedx.core.djangolib.markup import HTML, Text
from shoppingcart.models import (
    Coupon,
    CourseMode,
    CourseRegistrationCode,
    CourseRegistrationCodeInvoiceItem,
    Invoice,
    RegistrationCodeRedemption
)
from student import auth
from student.forms import validate_username
from student.models import (
    ALLOWEDTOENROLL_TO_ENROLLED,
    ALLOWEDTOENROLL_TO_UNENROLLED,
    DEFAULT_TRANSITION_STATE,
    ENROLLED_TO_ENROLLED,
    ENROLLED_TO_UNENROLLED,
    UNENROLLED_TO_ALLOWEDTOENROLL,
    UNENROLLED_TO_ENROLLED,
    UNENROLLED_TO_UNENROLLED,
    CourseEnrollment,
    EntranceExamConfiguration,
    ManualEnrollmentAudit,
    Registration,
    UserProfile,
    anonymous_id_for_user,
    get_user_by_username_or_email,
    unique_id_for_user,
    is_email_retired,
    is_username_retired
)
from student.roles import CourseFinanceAdminRole, CourseSalesAdminRole
from submissions import api as sub_api  # installed from the edx-submissions repository
from util.file import (
    FileValidationException,
    UniversalNewlineIterator,
    course_and_time_based_filename_generator,
    store_uploaded_file
)
from util.json_request import JsonResponse, JsonResponseBadRequest
from util.views import require_global_staff
from xmodule.modulestore.django import modulestore

from .tools import (
    dump_module_extensions,
    dump_student_extensions,
    find_unit,
    get_student_from_identifier,
    handle_dashboard_error,
    parse_datetime,
    require_student_from_identifier,
    set_due_date_extension,
    strip_if_string
)

from student.forms import PasswordCreateResetFormNoActive

log = logging.getLogger(__name__)

TASK_SUBMISSION_OK = 'created'

SUCCESS_MESSAGE_TEMPLATE = _("The {report_type} report is being created. "
                             "To view the status of the report, see Pending Tasks below.")


def common_exceptions_400(func):
    """
    Catches common exceptions and renders matching 400 errors.
    (decorator without arguments)
    """

    def wrapped(request, *args, **kwargs):  # pylint: disable=missing-docstring
        use_json = (request.is_ajax() or
                    request.META.get("HTTP_ACCEPT", "").startswith("application/json"))
        try:
            return func(request, *args, **kwargs)
        except User.DoesNotExist:
            message = _('User does not exist.')
        except MultipleObjectsReturned:
            message = _('Found a conflict with given identifier. Please try an alternative identifier')
        except (AlreadyRunningError, QueueConnectionError) as err:
            message = unicode(err)

        if use_json:
            return JsonResponseBadRequest(message)
        else:
            return HttpResponseBadRequest(message)

    return wrapped


def require_post_params(*args, **kwargs):
    """
    Checks for required parameters or renders a 400 error.
    (decorator with arguments)

    `args` is a *list of required POST parameter names.
    `kwargs` is a **dict of required POST parameter names
        to string explanations of the parameter
    """
    required_params = []
    required_params += [(arg, None) for arg in args]
    required_params += [(key, kwargs[key]) for key in kwargs]
    # required_params = e.g. [('action', 'enroll or unenroll'), ['emails', None]]

    def decorator(func):  # pylint: disable=missing-docstring
        def wrapped(*args, **kwargs):  # pylint: disable=missing-docstring
            request = args[0]

            error_response_data = {
                'error': 'Missing required query parameter(s)',
                'parameters': [],
                'info': {},
            }

            for (param, extra) in required_params:
                default = object()
                if request.POST.get(param, default) == default:
                    error_response_data['parameters'].append(param)
                    error_response_data['info'][param] = extra

            if len(error_response_data['parameters']) > 0:
                return JsonResponse(error_response_data, status=400)
            else:
                return func(*args, **kwargs)
        return wrapped
    return decorator


def require_level(level):
    """
    Decorator with argument that requires an access level of the requesting
    user. If the requirement is not satisfied, returns an
    HttpResponseForbidden (403).

    Assumes that request is in args[0].
    Assumes that course_id is in kwargs['course_id'].

    `level` is in ['instructor', 'staff']
    if `level` is 'staff', instructors will also be allowed, even
        if they are not in the staff group.
    """
    if level not in ['instructor', 'staff']:
        raise ValueError("unrecognized level '{}'".format(level))

    def decorator(func):  # pylint: disable=missing-docstring
        def wrapped(*args, **kwargs):  # pylint: disable=missing-docstring
            request = args[0]
            course = get_course_by_id(CourseKey.from_string(kwargs['course_id']))

            if has_access(request.user, level, course):
                return func(*args, **kwargs)
            else:
                return HttpResponseForbidden()
        return wrapped
    return decorator


def require_sales_admin(func):
    """
    Decorator for checking sales administrator access before executing an HTTP endpoint. This decorator
    is designed to be used for a request based action on a course. It assumes that there will be a
    request object as well as a course_id attribute to leverage to check course level privileges.

    If the user does not have privileges for this operation, this will return HttpResponseForbidden (403).
    """
    def wrapped(request, course_id):  # pylint: disable=missing-docstring

        try:
            course_key = CourseKey.from_string(course_id)
        except InvalidKeyError:
            log.error(u"Unable to find course with course key %s", course_id)
            return HttpResponseNotFound()

        access = auth.user_has_role(request.user, CourseSalesAdminRole(course_key))

        if access:
            return func(request, course_id)
        else:
            return HttpResponseForbidden()
    return wrapped


def require_finance_admin(func):
    """
    Decorator for checking finance administrator access before executing an HTTP endpoint. This decorator
    is designed to be used for a request based action on a course. It assumes that there will be a
    request object as well as a course_id attribute to leverage to check course level privileges.

    If the user does not have privileges for this operation, this will return HttpResponseForbidden (403).
    """
    def wrapped(request, course_id):  # pylint: disable=missing-docstring

        try:
            course_key = CourseKey.from_string(course_id)
        except InvalidKeyError:
            log.error(u"Unable to find course with course key %s", course_id)
            return HttpResponseNotFound()

        access = auth.user_has_role(request.user, CourseFinanceAdminRole(course_key))

        if access:
            return func(request, course_id)
        else:
            return HttpResponseForbidden()
    return wrapped


LT_CSV = {
    'old_username': 0,
    'old_email': 1,
    'first_name': 0,
    'last_name': 1,
    'username': 2,
    'email': 3,
    'password': 4,
    'gender': 5,
    'year_of_birth': 6,
    'language': 7,
    'country': 8,
    'city': 9,
    'location': 10,
    'company': 11,
    'employee_id': 12,
    'hire_date': 13,
    'job_code': 14,
    'department': 15,
    'supervisor': 16,
    'learning_group': 17,
    'comments': 18,
}

def csv_student_fields_validation(first_name, last_name, username, email, password, gender,
                                  year_of_birth, language, country, company, hire_date, row_num):
    row_errors = []

    if len(first_name) == 0:
        row_errors.append({'response': _('Row #{row_num}: A first name is required.').format(row_num=row_num)})

    if len(last_name) == 0:
        row_errors.append({'response': _('Row #{row_num}: A last name is required.').format(row_num=row_num)})

    valid_username = False
    username_length = len(username)
    if username_length > 0:
        try:
            validate_username(username)  # Raises ValidationError if invalid
        except ValidationError:
            row_errors.append({'response': _('Row #{row_num}: Invalid username.').format(row_num=row_num)})
        else:
            if (username_length < USERNAME_MIN_LENGTH
                or username_length > USERNAME_MAX_LENGTH):
                row_errors.append({'response': _(
                    'Row #{row_num}: {error_msg}').format(row_num=row_num, error_msg=USERNAME_BAD_LENGTH_MSG)})
            else:
                valid_username = True
    else:
        row_errors.append({'response': _('Row #{row_num}: A username is required.').format(row_num=row_num)})

    valid_email = False
    if len(email) > 0:
        try:
            validate_email(email)  # Raises ValidationError if invalid
        except ValidationError:
            row_errors.append({'response': _('Row #{row_num}: Invalid email address.').format(row_num=row_num)})
        else:
            valid_email = True
    else:
        row_errors.append({'response': _('Row #{row_num}: An email address is required.').format(row_num=row_num)})

    if len(password) == 0:
        row_errors.append({'response': _('Row #{row_num}: A password is required.').format(row_num=row_num)})

    if gender.lower() not in {'m', 'f', 'o'}:
        row_errors.append({'response': _('Row #{row_num}: Genders must be \'m\', \'f\' or \'o\'.').format(row_num=row_num)})

    if len(year_of_birth) > 0:
        try:
            yob = int(year_of_birth)
            if yob < 1900 or yob > datetime.now().year:
                raise ValueError
        except ValueError:
            row_errors.append({'response': _('Row #{row_num}: Invalid year of birth (expected format: YYYY).').format(row_num=row_num)})

    if len(language) == 0:
        row_errors.append({
            'response': _('Row #{row_num}: Missing language, a language code is expected (e.g. en, fr, zh, pt).')
                .format(row_num=row_num)
        })
    else:
        if language not in dict(settings.ALL_LANGUAGES):
            row_errors.append({
                'response': _('Row #{row_num}: Invalid language, a language code is expected (e.g. en, fr, zh, pt).')
                    .format(row_num=row_num)
            })

    if len(country) == 0:
        row_errors.append({
            'response': _('Row #{row_num}: Missing country, a 2-character country code is expected (e.g. FR, CN, US, BR).')
                .format(row_num=row_num)
        })
    else:
        if country not in dict(countries).keys():
            row_errors.append({
                'response': _('Row #{row_num}: Invalid country, a 2-character country code is expected (e.g. FR, CN, US, BR).')
                    .format(row_num=row_num)
            })

    if len(company) == 0:
        row_errors.append({'response': _('Row #{row_num}: A company is required.').format(row_num=row_num)})

    if len(hire_date) > 0:
        try:
            time.strptime(hire_date, "%Y-%m-%d")
        except ValueError:
            row_errors.append({'response': _('Row #{row_num}: Invalid hire date (expected format: YYYY-MM-DD).').format(row_num=row_num)})

    return row_errors, valid_username, valid_email

@cache_control(no_cache=True, no_store=True, must_revalidate=True)
@require_level('staff')
def register_and_enroll_students_precheck(request, course_id):
    """
    Check a CSV file that contains a list of students to warn the user of errors
    that would rise if the file was passed to register_and_enroll_students.
    Requires staff access.

    Mandatory fields are: firstname, lastname, username, email, password,
                          gender, language, country, company.

    The email address and username must be unique in the file.
    There should not be an existing user with the same username but a different email address,
    or with the same email address but a different username.

    The following fields must have the correct format:
    username, email, gender, year of birth, language, country, hire date

    """

    if not configuration_helpers.get_value(
            'ALLOW_AUTOMATED_SIGNUPS',
            settings.FEATURES.get('ALLOW_AUTOMATED_SIGNUPS', False),):
        return HttpResponseForbidden()

    general_errors = []
    row_errors = []

    if 'students_list' in request.FILES:
        students = []

        try:
            upload_file = request.FILES.get('students_list')
            if upload_file.name.endswith('csv'):
                students = [row for row in csv.reader(upload_file.read().splitlines())]
            else:
                general_errors.append({'response': _('Make sure that the file you upload is in CSV format.')})

        except Exception as ex: #pylint: disable=broad-except
            general_errors.append({'response': _('Could not read uploaded file.')})
        finally:
            upload_file.close()

        row_num = 0
        for student in students:
            row_num = row_num + 1

            expected_length = len(LT_CSV) - 2
            if len(student) != expected_length:
                if len(student) > 0:
                    row_errors.append({
                        'response': _('Row #{row_num}: Data must have exactly {expected_length} columns ('
                            'first name, last name, username, email, password, gender, year of birth, '
                            'language, country, city, location, company, employee id, hire date, job code, '
                            'department, supervisor, learning group, comments).')
                            .format(row_num=row_num, expected_length=expected_length)
                    })
                continue

            first_name = student[LT_CSV['first_name']].strip()
            last_name = student[LT_CSV['last_name']].strip()
            username = student[LT_CSV['username']].strip()
            email = student[LT_CSV['email']].strip()
            password = student[LT_CSV['password']].strip()
            gender = student[LT_CSV['gender']].strip()
            year_of_birth = student[LT_CSV['year_of_birth']].strip()
            language = student[LT_CSV['language']].strip().lower()
            country = student[LT_CSV['country']].strip().upper()
            company = student[LT_CSV['company']].strip()
            hire_date = student[LT_CSV['hire_date']].strip()

            try:
                validation_errors, valid_username, valid_email = csv_student_fields_validation(first_name, last_name,
                                                                    username, email, password, gender, year_of_birth,
                                                                    language, country, company, hire_date, row_num)

                row_errors += validation_errors

                if valid_username and valid_email:
                    if User.objects.filter(username=username).exists() and not User.objects.filter(email=email, username=username).exists():
                        row_errors.append({
                            'response': _('Row #{row_num}: An account with username {username} exists but the provided email {email} '
                                'is different.').format(row_num=row_num)
                        })

                    if User.objects.filter(email=email).exists() and not User.objects.filter(email=email, username=username).exists():
                        row_errors.append({
                            'response': _('Row #{row_num}: An account with email {email} exists but the provided username {username} '
                                'is different.').format(row_num=row_num, email=email, username=username)
                        })
            except DjangoUnicodeDecodeError:
                row_errors.append({
                    'response': _('Row #{row_num}: Invalid utf-8 characters').format(row_num=row_num)
                })

    else:
        general_errors.append({'response': _('File is not attached.')})

    results = {
        'general_errors': general_errors,
        'row_errors': row_errors,
    }
    return JsonResponse(results)


@require_POST
@ensure_csrf_cookie
@cache_control(no_cache=True, no_store=True, must_revalidate=True)
@require_level('staff')
def register_and_enroll_students(request, course_id):  # pylint: disable=too-many-statements
    """
    Create new account and Enroll students in this course.
    Passing a csv file that contains a list of students.
    Requires staff access.

    -If the email address and username don't exist, create the new account and enroll the user in the course

    -If the email address and username already exists and the user is not enrolled in the course,
    enroll the user in the course

    -If the email address and username already exists and the user is already enrolled in the course,
    do nothing

    -If the email address already exists, but the username is different, assume there is an error and fail.
    The failure will be messaged in a response in the browser.

    -If the username already exists but the email is different, assume it is a different user and fail.
    The failure will be messaged in a response in the browser.

    The errors and the number of users created / enrolled is logged in the browser response.
    """

    if not configuration_helpers.get_value(
            'ALLOW_AUTOMATED_SIGNUPS',
            settings.FEATURES.get('ALLOW_AUTOMATED_SIGNUPS', False),
    ):
        return HttpResponseForbidden()

    course_id = CourseKey.from_string(course_id)
    general_errors = []
    row_errors = []
    created_and_enrolled = []
    only_enrolled = []
    untouched = []

    # for white labels we use 'shopping cart' which uses CourseMode.DEFAULT_SHOPPINGCART_MODE_SLUG as
    # course mode for creating course enrollments.
    if CourseMode.is_white_label(course_id):
        course_mode = CourseMode.DEFAULT_SHOPPINGCART_MODE_SLUG
    else:
        course_mode = None

    if 'students_list' in request.FILES:
        students = []

        try:
            upload_file = request.FILES.get('students_list')
            if upload_file.name.endswith('.csv'):
                students = [row for row in csv.reader(upload_file.read().splitlines())]
                course = get_course_by_id(course_id)
            else:
                general_errors.append({'response': _(
                    'Make sure that the file you upload is in CSV format with no extraneous characters or rows.')})

        except Exception:  # pylint: disable=broad-except
            general_errors.append({'response': _('Could not read uploaded file.')})
        finally:
            upload_file.close()

        row_num = 0
        for student in students:
            row_num = row_num + 1

            # verify that we have the right number of columns in every row but allow for blank lines
            expected_length = len(LT_CSV) - 2
            if len(student) != expected_length:
                if len(student) > 0:
                    row_errors.append({
                        'response': _('Row #{row_num}: Data must have exactly {expected_length} columns ('
                            'first name, last name, username, email, password, gender, year of birth, '
                            'language, country, city, location, company, employee id, hire date, job code, '
                            'department, supervisor, learning group, comments).')
                            .format(row_num=row_num, expected_length=expected_length)
                    })
                continue

            first_name = student[LT_CSV['first_name']].strip()
            last_name = student[LT_CSV['last_name']].strip()
            username = student[LT_CSV['username']].strip()
            email = student[LT_CSV['email']].strip()
            password = student[LT_CSV['password']].strip()
            gender = student[LT_CSV['gender']].strip()
            year_of_birth = student[LT_CSV['year_of_birth']].strip()
            language = student[LT_CSV['language']].strip().lower()
            country = student[LT_CSV['country']].strip().upper()
            company = student[LT_CSV['company']].strip()
            hire_date = student[LT_CSV['hire_date']].strip()

            try:
                validation_errors, valid_username, valid_email = csv_student_fields_validation(
                                            first_name, last_name, username, email, password,
                                            gender, year_of_birth, language, country, company, hire_date, row_num)

                row_errors += validation_errors

                if len(validation_errors) == 0:
                    try:
                        if User.objects.filter(email=email).exists():
                            # Email address already exists.
                            # see if it is an exact match with email and username
                            # if it's not an exact match then just display an error message
                            if not User.objects.filter(email=email, username=username).exists():
                                row_errors.append({
                                    'response': _('Row #{row_num}: An account with email {email} exists but the provided username {username} '
                                        'is different.').format(row_num=row_num, email=email, username=username)
                                })
                            else:
                                # user (username, email) already exists
                                # enroll the user if not already enrolled
                                user = User.objects.get(email=email, username= username)
                                if not CourseEnrollment.is_enrolled(user, course_id):
                                    # Enroll user to the course and add manual enrollment audit trail
                                    create_manual_course_enrollment(user=user, course_id=course_id,
                                        mode=course_mode, enrolled_by=request.user, reason='Enrolling via csv upload',
                                        state_transition=UNENROLLED_TO_ENROLLED,)
                                    only_enrolled.append({
                                        'response': _('Row #{row_num}: User with username {username} is now enrolled in this course.')
                                            .format(row_num=row_num, username=username)
                                    })
                                else:
                                    log.info(u'user %s already enrolled in the course %s', username, course.id,)
                                    untouched.append({
                                        'response': _('Row #{row_num}: User with username {username} was already enrolled '\
                                            'in this course so nothing has changed.').format(row_num=row_num, username=username)
                                    })

                        elif is_email_retired(email):
                            # We are either attempting to enroll a retired user or create a new user with
                            # an email or a username which is already associated with a retired account.
                            # Simply block these attempts.
                            row_errors.append({
                                'username': username,
                                'email': email,
                                'response': _('Row #{row_num}: Invalid email address.').format(row_num=row_num),
                            })
                            log.warning(u'Email address %s or username %s is associated with a retired user, ' +
                                        u'so course enrollment was blocked.', email, username)
                        else:
                            # This email does not yet exist, so we need to create a new account
                            # If username already exists in the database, then it will raise an IntegrityError exception.
                            hire_date = hire_date if len(hire_date) > 0 else None
                            if User.objects.filter(username=username).exists():
                                row_errors.append({
                                    'response': _('Row #{row_num}: An account with username {username} exists but the provided email {email} '
                                        'is different.').format(row_num=row_num, username=username, email=email)
                                })
                            elif is_username_retired(username):
                                row_errors.append({
                                    'username': username,
                                    'email': email,
                                    'response': _('Row #{row_num}: Invalid username.').format(row_num=row_num),
                                })
                                log.warning(u'Email address %s or username %s is associated with a retired user, ' +
                                            u'so course enrollment was blocked.', email, username)
                            else:
                                year_of_birth = int(year_of_birth) if len(year_of_birth) > 0 else None
                                user = lt_create_user_and_user_profile(
                                        email, username, first_name, last_name, password,
                                        gender, year_of_birth, language, country,
                                        student[LT_CSV['city']].strip(),
                                        student[LT_CSV['location']].strip(),
                                        student[LT_CSV['company']].strip(),
                                        student[LT_CSV['employee_id']].strip(),
                                        hire_date,
                                        student[LT_CSV['job_code']].strip(),
                                        student[LT_CSV['department']].strip(),
                                        student[LT_CSV['supervisor']].strip(),
                                        student[LT_CSV['learning_group']].strip(),
                                        student[LT_CSV['comments']].strip())
                                create_manual_course_enrollment(user=user, course_id=course_id,
                                    mode=course_mode, enrolled_by=request.user, reason='Enrolling via csv upload',
                                    state_transition=UNENROLLED_TO_ENROLLED,)

                                log.info(u'user %s created and enrolled in this course', username)
                                created_and_enrolled.append({
                                    'response': _('Row #{row_num}: {username} / {email}')
                                        .format(row_num=row_num, username=username, email=email)
                                })
                    except Exception as ex:
                        log.exception(type(ex).__name__)
                        row_errors.append({'response': _('Row #{row_num}: {ex}').format(row_num=row_num, ex=type(ex).__name__)})
            except DjangoUnicodeDecodeError:
                row_errors.append({
                    'response': _('Row #{row_num}: Invalid utf-8 characters').format(row_num=row_num)
                })

    else:
        general_errors.append({'response': _('File is not attached.')})

    results = {
        'general_errors': general_errors,
        'row_errors': row_errors,
        'created_and_enrolled': created_and_enrolled,
        'only_enrolled': only_enrolled,
        'untouched': untouched
    }
    return JsonResponse(results)

@require_POST
@cache_control(no_cache=True, no_store=True, must_revalidate=True)
@require_level('staff')
def batch_update_student(request, course_id):
    """
    This method allows the staff user to update user accounts and profiles by batch from a CSV file.
    The purpose of this is to be able to update wrong data after a batch register and enroll.

    Passing a CSV file that contains a list of students.
    Requires staff access.
    """
    if not configuration_helpers.get_value(
            'ALLOW_AUTOMATED_SIGNUPS',
            settings.FEATURES.get('ALLOW_AUTOMATED_SIGNUPS', False),):
        return HttpResponseForbidden()

    general_errors = []
    row_errors = []
    updated = []

    if 'students_list' in request.FILES:
        students = []

        try:
            upload_file = request.FILES.get('students_list')
            if upload_file.name.endswith('.csv'):
                students = [row for row in csv.reader(upload_file.read().splitlines())]
            else:
                general_errors.append({'response': _('Make sure that the file you upload is in CSV format.')})

        except Exception as ex:  # pylint: disable=broad-except
            general_errors.append({'response': _('Could not read uploaded file.')})
        finally:
            upload_file.close()

        row_num = 0
        for student in students:
            row_num = row_num + 1

            expected_length = len(LT_CSV)
            if len(student) != expected_length:
                if len(student) > 0:
                    row_errors.append({
                        'response': _('Row #{row_num}: Data must have exactly {expected_length} columns ('
                            'old username, old email, first name, last name, username, email, password, gender, '
                            'year of birth, language, country, city, location, company, employee id, hire date, '
                            'job code, department, supervisor, learning group, comments).')
                            .format(row_num=row_num, expected_length=expected_length)
                    })
                continue

            old_username = student[LT_CSV['old_username']].strip()
            old_email = student[LT_CSV['old_email']].strip()
            first_name = student[LT_CSV['first_name'] + 2].strip()
            last_name = student[LT_CSV['last_name'] + 2].strip()
            new_username = student[LT_CSV['username'] + 2].strip()
            new_email = student[LT_CSV['email'] + 2].strip()
            password = student[LT_CSV['password']].strip()
            gender = student[LT_CSV['gender'] + 2].strip()
            year_of_birth = student[LT_CSV['year_of_birth'] + 2].strip()
            language = student[LT_CSV['language'] + 2].strip().lower()
            country = student[LT_CSV['country'] + 2].strip().upper()
            company = student[LT_CSV['company'] + 2].strip()
            hire_date = student[LT_CSV['hire_date'] + 2].strip()

            if len(old_username) < 2:
                row_errors.append({'response': _('Row #{row_num}: An old username is required.').format(row_num=row_num)})
                continue

            if len(old_email) == 0:
                row_errors.append({'response': _('Row #{row_num}: An old email address is required.').format(row_num=row_num)})
                continue

            if is_email_retired(old_email):
                row_errors.append({
                    'response': _('Row #{row_num}: Invalid old email address.').format(row_num=row_num),
                })
                continue

            if is_username_retired(old_username):
                row_errors.append({
                    'response': _('Row #{row_num}: Invalid old username.').format(row_num=row_num),
                })
                continue

            username_needs_update = False
            username_to_check = old_username
            if len(new_username) >= 2 and new_username != old_username:
                username_needs_update = True
                username_to_check = new_username

            email_needs_update = False
            email_to_check = old_email
            if len(new_email) > 0 and new_email != old_email:
                email_needs_update = True
                email_to_check = new_email

            try:
                validation_errors, valid_username, valid_email = csv_student_fields_validation(
                                            first_name, last_name, username_to_check, email_to_check,
                                            password, gender, year_of_birth, language, country, company, hire_date, row_num)

                row_errors += validation_errors

                if len(validation_errors) == 0:
                    if User.objects.filter(email=old_email).exists():
                        # Email address already exists.
                        # see if it is an exact match with email and username
                        # if it's not an exact match then just display an error message
                        if not User.objects.filter(email=old_email, username=old_username).exists():
                            row_errors.append({
                                'response': _(
                                    'Row #{row_num}: An account with email {email} exists but the provided username {username} '
                                    'is different.').format(row_num=row_num, email=old_email, username=old_username)
                            })
                        else:
                            if email_needs_update:
                                if User.objects.filter(email=new_email).exists():
                                    row_errors.append({
                                        'response': _('Row #{row_num}: An other account with email {email} already exists.')
                                            .format(row_num=row_num, email=new_email)
                                    })
                                elif is_email_retired(new_email):
                                    row_errors.append({
                                        'response': _('Row #{row_num}: Invalid new email address.').format(row_num=row_num),
                                    })
                            if username_needs_update:
                                if User.objects.filter(username=new_username).exists():
                                    row_errors.append({
                                        'response': _('Row #{row_num}: An other account with username {username} already exists.')
                                            .format(row_num=row_num, username=new_username)
                                    })
                                elif is_username_retired(new_username):
                                    row_errors.append({
                                        'response': _('Row #{row_num}: Invalid new username.').format(row_num=row_num),
                                    })
                            if len(row_errors) == 0:
                                user = User.objects.get(email=old_email, username= old_username)

                                try:
                                    with transaction.atomic():
                                        if username_needs_update:
                                            user.username = new_username
                                        if email_needs_update:
                                            user.email = new_email
                                        user.first_name = first_name
                                        user.last_name = last_name
                                        user.set_password(password)
                                        user.save()

                                        year_of_birth = int(year_of_birth) if len(year_of_birth) > 0 else None
                                        lt_update_profile(
                                            user.profile, first_name, last_name,
                                            gender, year_of_birth, language, country,
                                            student[LT_CSV['city'] + 2].strip(),
                                            student[LT_CSV['location'] + 2].strip(),
                                            student[LT_CSV['company'] + 2].strip(),
                                            student[LT_CSV['employee_id'] + 2].strip(),
                                            hire_date,
                                            student[LT_CSV['job_code'] + 2].strip(),
                                            student[LT_CSV['department'] + 2].strip(),
                                            student[LT_CSV['supervisor'] + 2].strip(),
                                            student[LT_CSV['learning_group'] + 2].strip(),
                                            student[LT_CSV['comments'] + 2].strip())

                                except Exception as ex:
                                    log.exception(type(ex).__name__)
                                    row_errors.append({'response': _('Row #{row_num}: {ex}').format(row_num=row_num, ex=type(ex).__name__)})
                                else:
                                    # Successful update
                                    log.info(u'user profile updated for %s (now: %s)', old_username, new_username)
                                    if username_needs_update:
                                        updated.append({
                                            'response': _('Row #{row_num}: user {old} (now: {new}) successfully updated.')
                                                .format(row_num=row_num, old=old_username, new=new_username)
                                        })
                                    else:
                                        updated.append({
                                            'response': _('Row #{row_num}: user {old} successfully updated.')
                                                .format(row_num=row_num, old=old_username)
                                        })
                    else:
                        # This email does not exist, so raise an error
                        if User.objects.filter(username=old_username).exists():
                            row_errors.append({
                                'response': _('Row #{row_num}: An account with username {username} exits but the provided email {email} '
                                    'is different.').format(row_num=row_num, username=old_username, email=old_email)
                            })
                        else:
                            row_errors.append({
                                'response': _('Row #{row_num}: No account was found with the provided username and email.')
                                    .format(row_num=row_num)
                            })
            except DjangoUnicodeDecodeError:
                row_errors.append({
                    'response': _('Row #{row_num}: Invalid utf-8 characters').format(row_num=row_num)
                })

    else:
        general_errors.append({'response': _('File is not attached.')})

    results = {
        'general_errors': general_errors,
        'row_errors': row_errors,
        'updated': updated
    }
    return JsonResponse(results)


@require_POST
@ensure_csrf_cookie
@cache_control(no_cache=True, no_store=True, must_revalidate=True)
@require_level('staff')
def send_welcoming_email(request, course_id):
    """
    Send a welcoming email to students with a link to create (reset) password.
    It is intended to be used after a batch register and enroll.
    Passing a list of email addresses.
    Requires staff access.
    """

    # emails_raw = request.POST.get('emails')
    emails_raw = request.POST.get('emails')
    emails = emails_raw.splitlines()
    emails = [s.strip() for s in emails]
    emails = [s for s in emails if s != '']

    row_errors = []
    row_successes = []
    course_key = CourseKey.from_string(course_id)
    course_name = ""

    try:
        course = CourseOverview.get_from_id(course_key)
        course_name = course.display_name
    except CourseOverview.DoesNotExist:
        pass

    for email in emails:
        form = PasswordCreateResetFormNoActive({'email': email}, course_name)
        if form.is_valid():
            form.save(use_https=request.is_secure(),
                      domain_override=request.get_host(),
                      request=request)
            row_successes.append(email)

        else:
            # No user with the provided email address exists.
            row_errors.append(email)

    results = {
        'row_errors': row_errors,
        'row_successes': row_successes

    }
    return JsonResponse(results)


def generate_random_string(length):
    """
    Create a string of random characters of specified length
    """
    chars = [
        char for char in string.ascii_uppercase + string.digits + string.ascii_lowercase
        if char not in 'aAeEiIoOuU1l'
    ]

    return string.join((random.choice(chars) for __ in range(length)), '')


def generate_unique_password(generated_passwords, password_length=12):
    """
    generate a unique password for each student.
    """

    password = generate_random_string(password_length)
    while password in generated_passwords:
        password = generate_random_string(password_length)

    generated_passwords.append(password)

    return password


def create_user_and_user_profile(email, username, name, country, password):
    """
    Create a new user, add a new Registration instance for letting user verify its identity and create a user profile.

    :param email: user's email address
    :param username: user's username
    :param name: user's name
    :param country: user's country
    :param password: user's password

    :return: User instance of the new user.
    """
    user = User.objects.create_user(username, email, password)
    reg = Registration()
    reg.register(user)

    profile = UserProfile(user=user)
    profile.name = name
    profile.country = country
    profile.save()

    return user

def lt_create_user_and_user_profile(email, username, first_name, last_name,
    password, gender, year_of_birth, language, country, city, location,
    lt_company, lt_employee_id, lt_hire_date, lt_job_code, lt_department,
    lt_supervisor, lt_learning_group, lt_comments):
    user = User.objects.create_user(username, email, password)
    reg = Registration()
    reg.register(user)

    user.first_name = first_name
    user.last_name = last_name
    user.is_active = True
    user.save()

    lt_update_profile(UserProfile(user=user), first_name, last_name,
        gender, year_of_birth, language, country, city, location,
        lt_company, lt_employee_id, lt_hire_date, lt_job_code, lt_department,
        lt_supervisor, lt_learning_group, lt_comments)

    return user


def lt_update_profile(profile, first_name, last_name,
    gender, year_of_birth, language, country, city, location,
    lt_company, lt_employee_id, lt_hire_date, lt_job_code, lt_department,
    lt_supervisor, lt_learning_group, lt_comments):
    name = last_name + ' ' + first_name
    profile.name = name
    profile.gender = gender
    profile.year_of_birth = year_of_birth
    profile.language = language
    profile.country = country
    profile.city = city
    profile.location = location
    profile.lt_company = lt_company
    profile.lt_employee_id = lt_employee_id
    if lt_hire_date != '':
        profile.lt_hire_date = lt_hire_date
    profile.lt_job_code = lt_job_code
    profile.lt_department = lt_department
    profile.lt_supervisor = lt_supervisor
    profile.lt_learning_group = lt_learning_group
    profile.lt_comments = lt_comments
    client_service_id = configuration_helpers.get_value('CLIENT_SERVICE_ID', None)
    if client_service_id:
        profile.service_id = client_service_id
    profile.save()


def create_manual_course_enrollment(user, course_id, mode, enrolled_by, reason, state_transition):
    """
    Create course enrollment for the given student and create manual enrollment audit trail.

    :param user: User who is to enroll in course
    :param course_id: course identifier of the course in which to enroll the user.
    :param mode: mode for user enrollment, e.g. 'honor', 'audit' etc.
    :param enrolled_by: User who made the manual enrollment entry (usually instructor or support)
    :param reason: Reason behind manual enrollment
    :param state_transition: state transition denoting whether student enrolled from un-enrolled,
            un-enrolled from enrolled etc.
    :return CourseEnrollment instance.
    """
    enrollment_obj = CourseEnrollment.enroll(user, course_id, mode=mode)
    ManualEnrollmentAudit.create_manual_enrollment_audit(
        enrolled_by, user.email, state_transition, reason, enrollment_obj
    )

    log.info(u'user %s enrolled in the course %s', user.username, course_id)
    return enrollment_obj


def create_and_enroll_user(email, username, name, country, password, course_id, course_mode, enrolled_by, email_params):
    """
    Create a new user and enroll him/her to the given course, return list of errors in the following format
        Error format:
            each error is key-value pait dict with following key-value pairs.
            1. username: username of the user to enroll
            1. email: email of the user to enroll
            1. response: readable error message

    :param email: user's email address
    :param username: user's username
    :param name: user's name
    :param country: user's country
    :param password: user's password
    :param course_id: course identifier of the course in which to enroll the user.
    :param course_mode: mode for user enrollment, e.g. 'honor', 'audit' etc.
    :param enrolled_by: User who made the manual enrollment entry (usually instructor or support)
    :param email_params: information to send to the user via email

    :return: list of errors
    """
    errors = list()
    try:
        with transaction.atomic():
            # Create a new user
            user = create_user_and_user_profile(email, username, name, country, password)

            # Enroll user to the course and add manual enrollment audit trail
            create_manual_course_enrollment(
                user=user,
                course_id=course_id,
                mode=course_mode,
                enrolled_by=enrolled_by,
                reason='Enrolling via csv upload',
                state_transition=UNENROLLED_TO_ENROLLED,
            )
    except IntegrityError:
        errors.append({
            'username': username, 'email': email, 'response': _('Username {user} already exists.').format(user=username)
        })
    except Exception as ex:  # pylint: disable=broad-except
        log.exception(type(ex).__name__)
        errors.append({
            'username': username, 'email': email, 'response': type(ex).__name__,
        })
    else:
        try:
            # It's a new user, an email will be sent to each newly created user.
            email_params.update({
                'message': 'account_creation_and_enrollment',
                'email_address': email,
                'password': password,
                'platform_name': configuration_helpers.get_value('PLATFORM_NAME', settings.PLATFORM_NAME),
            })
            send_mail_to_student(email, email_params)
        except Exception as ex:  # pylint: disable=broad-except
            log.exception(
                "Exception '{exception}' raised while sending email to new user.".format(exception=type(ex).__name__)
            )
            errors.append({
                'username': username,
                'email': email,
                'response':
                    _("Error '{error}' while sending email to new user (user email={email}). "
                      "Without the email learner would not be able to login. "
                      "Please contact support for further information.").format(error=type(ex).__name__, email=email),
            })
        else:
            log.info(u'email sent to new created user at %s', email)

    return errors


@require_POST
@ensure_csrf_cookie
@cache_control(no_cache=True, no_store=True, must_revalidate=True)
@require_level('staff')
@require_post_params(action="enroll or unenroll", identifiers="stringified list of emails and/or usernames")
def students_update_enrollment(request, course_id):
    """
    Enroll or unenroll students by email.
    Requires staff access.

    Query Parameters:
    - action in ['enroll', 'unenroll']
    - identifiers is string containing a list of emails and/or usernames separated by anything split_input_list can handle.
    - auto_enroll is a boolean (defaults to false)
        If auto_enroll is false, students will be allowed to enroll.
        If auto_enroll is true, students will be enrolled as soon as they register.
    - email_students is a boolean (defaults to false)
        If email_students is true, students will be sent email notification
        If email_students is false, students will not be sent email notification

    Returns an analog to this JSON structure: {
        "action": "enroll",
        "auto_enroll": false,
        "results": [
            {
                "email": "testemail@test.org",
                "before": {
                    "enrollment": false,
                    "auto_enroll": false,
                    "user": true,
                    "allowed": false
                },
                "after": {
                    "enrollment": true,
                    "auto_enroll": false,
                    "user": true,
                    "allowed": false
                }
            }
        ]
    }
    """
    course_id = CourseKey.from_string(course_id)
    action = request.POST.get('action')
    identifiers_raw = request.POST.get('identifiers')
    identifiers = _split_input_list(identifiers_raw)
    auto_enroll = _get_boolean_param(request, 'auto_enroll')
    email_students = _get_boolean_param(request, 'email_students')
    reason = request.POST.get('reason')
    role = request.POST.get('role')

    allowed_role_choices = configuration_helpers.get_value(
        'MANUAL_ENROLLMENT_ROLE_CHOICES',
        settings.MANUAL_ENROLLMENT_ROLE_CHOICES)
    if role and role not in allowed_role_choices:
        return JsonResponse(
            {
                'action': action,
                'results': [{'error': True, 'message': 'Not a valid role choice'}],
                'auto_enroll': auto_enroll,
            }, status=400)

    enrollment_obj = None
    state_transition = DEFAULT_TRANSITION_STATE

    email_params = {}
    if email_students:
        course = get_course_by_id(course_id)
        email_params = get_email_params(course, auto_enroll, secure=request.is_secure())

    results = []
    for identifier in identifiers:
        # First try to get a user object from the identifer
        user = None
        email = None
        language = None
        try:
            user = get_student_from_identifier(identifier)
        except User.DoesNotExist:
            email = identifier
        else:
            email = user.email
            language = get_user_email_language(user)

        try:
            # Use django.core.validators.validate_email to check email address
            # validity (obviously, cannot check if email actually /exists/,
            # simply that it is plausibly valid)
            validate_email(email)  # Raises ValidationError if invalid
            no_email_address = getattr(settings, 'LEARNER_NO_EMAIL')
            if action == 'enroll':
                if (no_email_address and email.endswith(no_email_address)
                    and auto_enroll and not email_students):
                    before, after, enrollment_obj = enroll_user(course_id, user)
                    results.append({
                        'identifier': identifier,
                        'before': {
                            'user': True,
                            'enrollment': before,
                            'allowed': False,
                            'auto_enroll': False,
                        },
                        'after': {
                            'user': True,
                            'enrollment': after,
                            'allowed': False,
                            'auto_enroll': False,
                        }
                    })
                else:
                    before, after, enrollment_obj = enroll_email(
                        course_id, email, auto_enroll, email_students, email_params, language=language
                    )
                    before_enrollment = before.to_dict()['enrollment']
                    before_user_registered = before.to_dict()['user']
                    before_allowed = before.to_dict()['allowed']
                    after_enrollment = after.to_dict()['enrollment']
                    after_allowed = after.to_dict()['allowed']

                    if before_user_registered:
                        if after_enrollment:
                            if before_enrollment:
                                state_transition = ENROLLED_TO_ENROLLED
                            else:
                                if before_allowed:
                                    state_transition = ALLOWEDTOENROLL_TO_ENROLLED
                                else:
                                    state_transition = UNENROLLED_TO_ENROLLED
                    else:
                        if after_allowed:
                            state_transition = UNENROLLED_TO_ALLOWEDTOENROLL

            elif action == 'unenroll':
                if (no_email_address and email.endswith(no_email_address)
                    and not email_students):
                    before, after = unenroll_user(course_id, user)
                    results.append({
                        'identifier': identifier,
                        'before': {
                            'user': True,
                            'enrollment': before,
                            'allowed': False,
                            'auto_enroll': False,
                        },
                        'after': {
                            'user': True,
                            'enrollment': after,
                            'allowed': False,
                            'auto_enroll': False,
                        }
                    })
                else:
                    before, after = unenroll_email(
                        course_id, email, email_students, email_params, language=language
                    )
                    before_enrollment = before.to_dict()['enrollment']
                    before_allowed = before.to_dict()['allowed']
                    enrollment_obj = CourseEnrollment.get_enrollment(user, course_id) if user else None

                    if before_enrollment:
                        state_transition = ENROLLED_TO_UNENROLLED
                    else:
                        if before_allowed:
                            state_transition = ALLOWEDTOENROLL_TO_UNENROLLED
                        else:
                            state_transition = UNENROLLED_TO_UNENROLLED

            else:
                return HttpResponseBadRequest(strip_tags(
                    "Unrecognized action '{}'".format(action)
                ))

        except ValidationError:
            # Flag this email as an error if invalid, but continue checking
            # the remaining in the list
            results.append({
                'identifier': identifier,
                'invalidIdentifier': True,
            })

        except Exception as exc:  # pylint: disable=broad-except
            # catch and log any exceptions
            # so that one error doesn't cause a 500.
            log.exception(u"Error while #{}ing student")
            log.exception(exc)
            results.append({
                'identifier': identifier,
                'error': True,
            })

        else:
            if (no_email_address and not email.endswith(no_email_address)) or \
                    (no_email_address is None and email is not None):
                ManualEnrollmentAudit.create_manual_enrollment_audit(
                    request.user, email, state_transition, reason, enrollment_obj, role
                )
                results.append({
                    'identifier': identifier,
                    'before': before.to_dict(),
                    'after': after.to_dict(),
                })

    response_payload = {
        'action': action,
        'results': results,
        'auto_enroll': auto_enroll,
    }
    return JsonResponse(response_payload)


@require_POST
@ensure_csrf_cookie
@cache_control(no_cache=True, no_store=True, must_revalidate=True)
@require_level('instructor')
@common_exceptions_400
@require_post_params(
    identifiers="stringified list of emails and/or usernames",
    action="add or remove",
)
def bulk_beta_modify_access(request, course_id):
    """
    Enroll or unenroll users in beta testing program.

    Query parameters:
    - identifiers is string containing a list of emails and/or usernames separated by
      anything split_input_list can handle.
    - action is one of ['add', 'remove']
    """
    course_id = CourseKey.from_string(course_id)
    action = request.POST.get('action')
    identifiers_raw = request.POST.get('identifiers')
    identifiers = _split_input_list(identifiers_raw)
    email_students = _get_boolean_param(request, 'email_students')
    auto_enroll = _get_boolean_param(request, 'auto_enroll')
    results = []
    rolename = 'beta'
    course = get_course_by_id(course_id)

    email_params = {}
    if email_students:
        secure = request.is_secure()
        email_params = get_email_params(course, auto_enroll=auto_enroll, secure=secure)

    for identifier in identifiers:
        try:
            error = False
            user_does_not_exist = False
            user = get_student_from_identifier(identifier)
            user_active = user.is_active

            if action == 'add':
                allow_access(course, user, rolename)
            elif action == 'remove':
                revoke_access(course, user, rolename)
            else:
                return HttpResponseBadRequest(strip_tags(
                    "Unrecognized action '{}'".format(action)
                ))
        except User.DoesNotExist:
            error = True
            user_does_not_exist = True
            user_active = None
        # catch and log any unexpected exceptions
        # so that one error doesn't cause a 500.
        except Exception as exc:  # pylint: disable=broad-except
            log.exception(u"Error while #{}ing student")
            log.exception(exc)
            error = True
        else:
            # If no exception thrown, see if we should send an email
            if email_students:
                send_beta_role_email(action, user, email_params)
            # See if we should autoenroll the student
            if auto_enroll:
                # Check if student is already enrolled
                if not CourseEnrollment.is_enrolled(user, course_id):
                    CourseEnrollment.enroll(user, course_id)

        finally:
            # Tabulate the action result of this email address
            results.append({
                'identifier': identifier,
                'error': error,
                'userDoesNotExist': user_does_not_exist,
                'is_active': user_active
            })

    response_payload = {
        'action': action,
        'results': results,
    }
    return JsonResponse(response_payload)


@require_POST
@ensure_csrf_cookie
@cache_control(no_cache=True, no_store=True, must_revalidate=True)
@require_level('instructor')
@require_post_params(
    unique_student_identifier="email or username of user to change access",
    rolename="'instructor', 'staff', 'beta', or 'ccx_coach'",
    action="'allow' or 'revoke'"
)
@common_exceptions_400
def modify_access(request, course_id):
    """
    Modify staff/instructor access of other user.
    Requires instructor access.

    NOTE: instructors cannot remove their own instructor access.

    Query parameters:
    unique_student_identifer is the target user's username or email
    rolename is one of ['instructor', 'staff', 'beta', 'ccx_coach']
    action is one of ['allow', 'revoke']
    """
    course_id = CourseKey.from_string(course_id)
    course = get_course_with_access(
        request.user, 'instructor', course_id, depth=None
    )
    try:
        user = get_student_from_identifier(request.POST.get('unique_student_identifier'))
    except User.DoesNotExist:
        response_payload = {
            'unique_student_identifier': request.POST.get('unique_student_identifier'),
            'userDoesNotExist': True,
        }
        return JsonResponse(response_payload)

    # Check that user is active, because add_users
    # in common/djangoapps/student/roles.py fails
    # silently when we try to add an inactive user.
    if not user.is_active:
        response_payload = {
            'unique_student_identifier': user.username,
            'inactiveUser': True,
        }
        return JsonResponse(response_payload)

    rolename = request.POST.get('rolename')
    action = request.POST.get('action')

    if rolename not in ROLES:
        error = strip_tags("unknown rolename '{}'".format(rolename))
        log.error(error)
        return HttpResponseBadRequest(error)

    # disallow instructors from removing their own instructor access.
    if rolename == 'instructor' and user == request.user and action != 'allow':
        response_payload = {
            'unique_student_identifier': user.username,
            'rolename': rolename,
            'action': action,
            'removingSelfAsInstructor': True,
        }
        return JsonResponse(response_payload)

    if action == 'allow':
        allow_access(course, user, rolename)
    elif action == 'revoke':
        revoke_access(course, user, rolename)
    else:
        return HttpResponseBadRequest(strip_tags(
            "unrecognized action '{}'".format(action)
        ))

    response_payload = {
        'unique_student_identifier': user.username,
        'rolename': rolename,
        'action': action,
        'success': 'yes',
    }
    return JsonResponse(response_payload)


@require_POST
@ensure_csrf_cookie
@cache_control(no_cache=True, no_store=True, must_revalidate=True)
@require_level('instructor')
@require_post_params(rolename="'instructor', 'staff', or 'beta'")
def list_course_role_members(request, course_id):
    """
    List instructors and staff.
    Requires instructor access.

    rolename is one of ['instructor', 'staff', 'beta', 'ccx_coach']

    Returns JSON of the form {
        "course_id": "some/course/id",
        "staff": [
            {
                "username": "staff1",
                "email": "staff1@example.org",
                "first_name": "Joe",
                "last_name": "Shmoe",
            }
        ]
    }
    """
    course_id = CourseKey.from_string(course_id)
    course = get_course_with_access(
        request.user, 'instructor', course_id, depth=None
    )

    rolename = request.POST.get('rolename')

    if rolename not in ROLES:
        return HttpResponseBadRequest()

    def extract_user_info(user):
        """ convert user into dicts for json view """

        return {
            'username': user.username,
            'email': user.email,
            'first_name': user.first_name,
            'last_name': user.last_name,
            'name': user.profile.name,
            'profile_image_url': get_profile_image_urls_for_user(user)['medium']
        }

    response_payload = {
        'course_id': text_type(course_id),
        rolename: map(extract_user_info, list_with_level(
            course, rolename
        )),
    }
    return JsonResponse(response_payload)


@transaction.non_atomic_requests
@require_POST
@ensure_csrf_cookie
@cache_control(no_cache=True, no_store=True, must_revalidate=True)
@require_level('staff')
@common_exceptions_400
def get_problem_responses(request, course_id):
    """
    Initiate generation of a CSV file containing all student answers
    to a given problem.

    Responds with JSON
        {"status": "... status message ...", "task_id": created_task_UUID}

    if initiation is successful (or generation task is already running).

    Responds with BadRequest if problem location is faulty.
    """
    course_key = CourseKey.from_string(course_id)
    problem_location = request.POST.get('problem_location', '')
    report_type = _('problem responses')

    try:
        problem_key = UsageKey.from_string(problem_location)
        # Are we dealing with an "old-style" problem location?
        run = problem_key.run
        if not run:
            problem_key = UsageKey.from_string(problem_location).map_into_course(course_key)
        if problem_key.course_key != course_key:
            raise InvalidKeyError(type(problem_key), problem_key)
    except InvalidKeyError:
        return JsonResponseBadRequest(_("Could not find problem with this location."))

    task = lms.djangoapps.instructor_task.api.submit_calculate_problem_responses_csv(
        request, course_key, problem_location
    )
    success_status = SUCCESS_MESSAGE_TEMPLATE.format(report_type=report_type)

    return JsonResponse({"status": success_status, "task_id": task.task_id})


@require_POST
@ensure_csrf_cookie
@cache_control(no_cache=True, no_store=True, must_revalidate=True)
@require_level('staff')
def get_grading_config(request, course_id):
    """
    Respond with json which contains a html formatted grade summary.
    """
    course_id = CourseKey.from_string(course_id)
    course = get_course_with_access(
        request.user, 'staff', course_id, depth=None
    )
    grading_config_summary = instructor_analytics.basic.dump_grading_context(course)

    response_payload = {
        'course_id': text_type(course_id),
        'grading_config_summary': grading_config_summary,
    }
    return JsonResponse(response_payload)


@ensure_csrf_cookie
@cache_control(no_cache=True, no_store=True, must_revalidate=True)
@require_level('staff')
def get_sale_records(request, course_id, csv=False):  # pylint: disable=unused-argument, redefined-outer-name
    """
    return the summary of all sales records for a particular course
    """
    course_id = CourseKey.from_string(course_id)
    query_features = [
        'company_name', 'company_contact_name', 'company_contact_email', 'total_codes', 'total_used_codes',
        'total_amount', 'created', 'customer_reference_number', 'recipient_name', 'recipient_email', 'created_by',
        'internal_reference', 'invoice_number', 'codes', 'course_id'
    ]

    sale_data = instructor_analytics.basic.sale_record_features(course_id, query_features)

    if not csv:
        for item in sale_data:
            item['created_by'] = item['created_by'].username

        response_payload = {
            'course_id': text_type(course_id),
            'sale': sale_data,
            'queried_features': query_features
        }
        return JsonResponse(response_payload)
    else:
        header, datarows = instructor_analytics.csvs.format_dictlist(sale_data, query_features)
        return instructor_analytics.csvs.create_csv_response("e-commerce_sale_invoice_records.csv", header, datarows)


@ensure_csrf_cookie
@cache_control(no_cache=True, no_store=True, must_revalidate=True)
@require_level('staff')
def get_sale_order_records(request, course_id):  # pylint: disable=unused-argument
    """
    return the summary of all sales records for a particular course
    """
    course_id = CourseKey.from_string(course_id)
    query_features = [
        ('id', 'Order Id'),
        ('company_name', 'Company Name'),
        ('company_contact_name', 'Company Contact Name'),
        ('company_contact_email', 'Company Contact Email'),
        ('logged_in_username', 'Login Username'),
        ('logged_in_email', 'Login User Email'),
        ('purchase_time', 'Date of Sale'),
        ('customer_reference_number', 'Customer Reference Number'),
        ('recipient_name', 'Recipient Name'),
        ('recipient_email', 'Recipient Email'),
        ('bill_to_street1', 'Street 1'),
        ('bill_to_street2', 'Street 2'),
        ('bill_to_city', 'City'),
        ('bill_to_state', 'State'),
        ('bill_to_postalcode', 'Postal Code'),
        ('bill_to_country', 'Country'),
        ('order_type', 'Order Type'),
        ('status', 'Order Item Status'),
        ('coupon_code', 'Coupon Code'),
        ('list_price', 'List Price'),
        ('unit_cost', 'Unit Price'),
        ('quantity', 'Quantity'),
        ('total_discount', 'Total Discount'),
        ('total_amount', 'Total Amount Paid'),
    ]

    db_columns = [x[0] for x in query_features]
    csv_columns = [x[1] for x in query_features]
    sale_data = instructor_analytics.basic.sale_order_record_features(course_id, db_columns)
    __, datarows = instructor_analytics.csvs.format_dictlist(sale_data, db_columns)
    return instructor_analytics.csvs.create_csv_response("e-commerce_sale_order_records.csv", csv_columns, datarows)


@require_level('staff')
@require_POST
def sale_validation(request, course_id):
    """
    This method either invalidate or re validate the sale against the invoice number depending upon the event type
    """
    try:
        invoice_number = request.POST["invoice_number"]
    except KeyError:
        return HttpResponseBadRequest("Missing required invoice_number parameter")
    try:
        invoice_number = int(invoice_number)
    except ValueError:
        return HttpResponseBadRequest(
            "invoice_number must be an integer, {value} provided".format(
                value=invoice_number
            )
        )
    try:
        event_type = request.POST["event_type"]
    except KeyError:
        return HttpResponseBadRequest("Missing required event_type parameter")

    course_id = CourseKey.from_string(course_id)
    try:
        obj_invoice = CourseRegistrationCodeInvoiceItem.objects.select_related('invoice').get(
            invoice_id=invoice_number,
            course_id=course_id
        )
        obj_invoice = obj_invoice.invoice
    except CourseRegistrationCodeInvoiceItem.DoesNotExist:  # Check for old type invoices
        return HttpResponseNotFound(_("Invoice number '{num}' does not exist.").format(num=invoice_number))

    if event_type == "invalidate":
        return invalidate_invoice(obj_invoice)
    else:
        return re_validate_invoice(obj_invoice)


def invalidate_invoice(obj_invoice):
    """
    This method invalidate the sale against the invoice number
    """
    if not obj_invoice.is_valid:
        return HttpResponseBadRequest(_("The sale associated with this invoice has already been invalidated."))
    obj_invoice.is_valid = False
    obj_invoice.save()
    message = _('Invoice number {0} has been invalidated.').format(obj_invoice.id)
    return JsonResponse({'message': message})


def re_validate_invoice(obj_invoice):
    """
    This method re-validate the sale against the invoice number
    """
    if obj_invoice.is_valid:
        return HttpResponseBadRequest(_("This invoice is already active."))

    obj_invoice.is_valid = True
    obj_invoice.save()
    message = _('The registration codes for invoice {0} have been re-activated.').format(obj_invoice.id)
    return JsonResponse({'message': message})


@transaction.non_atomic_requests
@ensure_csrf_cookie
@cache_control(no_cache=True, no_store=True, must_revalidate=True)
@require_level('staff')
def get_issued_certificates(request, course_id):
    """
    Responds with JSON if CSV is not required. contains a list of issued certificates.
    Arguments:
        course_id
    Returns:
        {"certificates": [{course_id: xyz, mode: 'honor'}, ...]}

    """
    course_key = CourseKey.from_string(course_id)
    csv_required = request.GET.get('csv', 'false')

    query_features = ['course_id', 'mode', 'total_issued_certificate', 'report_run_date']
    query_features_names = [
        ('course_id', _('CourseID')),
        ('mode', _('Certificate Type')),
        ('total_issued_certificate', _('Total Certificates Issued')),
        ('report_run_date', _('Date Report Run'))
    ]
    certificates_data = instructor_analytics.basic.issued_certificates(course_key, query_features)
    if csv_required.lower() == 'true':
        __, data_rows = instructor_analytics.csvs.format_dictlist(certificates_data, query_features)
        return instructor_analytics.csvs.create_csv_response(
            'issued_certificates.csv',
            [col_header for __, col_header in query_features_names],
            data_rows
        )
    else:
        response_payload = {
            'certificates': certificates_data,
            'queried_features': query_features,
            'feature_names': dict(query_features_names)
        }
        return JsonResponse(response_payload)


@transaction.non_atomic_requests
@require_POST
@ensure_csrf_cookie
@cache_control(no_cache=True, no_store=True, must_revalidate=True)
@require_level('staff')
@common_exceptions_400
def get_students_features(request, course_id, csv=False):  # pylint: disable=redefined-outer-name
    """
    Respond with json which contains a summary of all enrolled students profile information.

    Responds with JSON
        {"students": [{-student-info-}, ...]}

    TO DO accept requests for different attribute sets.
    """
    course_key = CourseKey.from_string(course_id)
    course = get_course_by_id(course_key)
    report_type = _('enrolled learner profile')
    available_features = instructor_analytics.basic.AVAILABLE_FEATURES

    # Allow for sites to be able to define additional columns.
    # Note that adding additional columns has the potential to break
    # the student profile report due to a character limit on the
    # asynchronous job input which in this case is a JSON string
    # containing the list of columns to include in the report.
    # TODO: Refactor the student profile report code to remove the list of columns
    # that should be included in the report from the asynchronous job input.
    # We need to clone the list because we modify it below
    query_features = list(configuration_helpers.get_value('student_profile_download_fields', []))

    if not query_features:
        query_features = [
            'id', 'username', 'name', 'email', 'language', 'location',
            'year_of_birth', 'gender', 'level_of_education', 'mailing_address',
            'goals', 'enrollment_mode', 'verification_status',
        ]

    # Provide human-friendly and translatable names for these features. These names
    # will be displayed in the table generated in data_download.js. It is not (yet)
    # used as the header row in the CSV, but could be in the future.
    query_features_names = {
        'id': _('User ID'),
        'username': _('Username'),
        'name': _('Name'),
        'email': _('Email'),
        'language': _('Language'),
        'location': pgettext('user.profile', 'Location'),
        'year_of_birth': _('Birth Year'),
        'gender': _('Gender'),
        'level_of_education': _('Level of Education'),
        'mailing_address': _('Mailing Address'),
        'goals': _('Goals'),
        'enrollment_mode': _('Enrollment Mode'),
        'verification_status': _('Verification Status'),
    }

    if is_course_cohorted(course.id):
        # Translators: 'Cohort' refers to a group of students within a course.
        query_features.append('cohort')
        query_features_names['cohort'] = _('Cohort')

    if course.teams_enabled:
        query_features.append('team')
        query_features_names['team'] = _('Team')

    # For compatibility reasons, city and country should always appear last.
    query_features.append('city')
    query_features_names['city'] = _('City')
    query_features.append('country')
    query_features_names['country'] = _('Country')

    if not csv:
        student_data = instructor_analytics.basic.enrolled_students_features(course_key, query_features)
        response_payload = {
            'course_id': unicode(course_key),
            'students': student_data,
            'students_count': len(student_data),
            'queried_features': query_features,
            'feature_names': query_features_names,
            'available_features': available_features,
        }
        return JsonResponse(response_payload)

    else:
        lms.djangoapps.instructor_task.api.submit_calculate_students_features_csv(
            request,
            course_key,
            query_features
        )
        success_status = SUCCESS_MESSAGE_TEMPLATE.format(report_type=report_type)

        return JsonResponse({"status": success_status})


@transaction.non_atomic_requests
@require_POST
@ensure_csrf_cookie
@cache_control(no_cache=True, no_store=True, must_revalidate=True)
@require_level('staff')
@common_exceptions_400
def get_students_who_may_enroll(request, course_id):
    """
    Initiate generation of a CSV file containing information about
    students who may enroll in a course.

    Responds with JSON
        {"status": "... status message ..."}

    """
    course_key = CourseKey.from_string(course_id)
    query_features = ['email']
    report_type = _('enrollment')
    lms.djangoapps.instructor_task.api.submit_calculate_may_enroll_csv(request, course_key, query_features)
    success_status = SUCCESS_MESSAGE_TEMPLATE.format(report_type=report_type)

    return JsonResponse({"status": success_status})


@transaction.non_atomic_requests
@ensure_csrf_cookie
@cache_control(no_cache=True, no_store=True, must_revalidate=True)
@require_POST
@require_level('staff')
@common_exceptions_400
def add_users_to_cohorts(request, course_id):
    """
    View method that accepts an uploaded file (using key "uploaded-file")
    containing cohort assignments for users. This method spawns a celery task
    to do the assignments, and a CSV file with results is provided via data downloads.
    """
    course_key = CourseKey.from_string(course_id)

    try:
        def validator(file_storage, file_to_validate):
            """
            Verifies that the expected columns are present.
            """
            with file_storage.open(file_to_validate) as f:
                reader = unicodecsv.reader(UniversalNewlineIterator(f), encoding='utf-8')
                try:
                    fieldnames = next(reader)
                except StopIteration:
                    fieldnames = []
                msg = None
                if "cohort" not in fieldnames:
                    msg = _("The file must contain a 'cohort' column containing cohort names.")
                elif "email" not in fieldnames and "username" not in fieldnames:
                    msg = _("The file must contain a 'username' column, an 'email' column, or both.")
                if msg:
                    raise FileValidationException(msg)

        __, filename = store_uploaded_file(
            request, 'uploaded-file', ['.csv'],
            course_and_time_based_filename_generator(course_key, "cohorts"),
            max_file_size=2000000,  # limit to 2 MB
            validator=validator
        )
        # The task will assume the default file storage.
        lms.djangoapps.instructor_task.api.submit_cohort_students(request, course_key, filename)
    except (FileValidationException, PermissionDenied) as err:
        return JsonResponse({"error": unicode(err)}, status=400)

    return JsonResponse()


@ensure_csrf_cookie
@cache_control(no_cache=True, no_store=True, must_revalidate=True)
@require_level('staff')
def get_coupon_codes(request, course_id):  # pylint: disable=unused-argument
    """
    Respond with csv which contains a summary of all Active Coupons.
    """
    course_id = CourseKey.from_string(course_id)
    coupons = Coupon.objects.filter(course_id=course_id)

    query_features = [
        ('code', _('Coupon Code')),
        ('course_id', _('Course Id')),
        ('percentage_discount', _('% Discount')),
        ('description', _('Description')),
        ('expiration_date', _('Expiration Date')),
        ('is_active', _('Is Active')),
        ('code_redeemed_count', _('Code Redeemed Count')),
        ('total_discounted_seats', _('Total Discounted Seats')),
        ('total_discounted_amount', _('Total Discounted Amount')),
    ]
    db_columns = [x[0] for x in query_features]
    csv_columns = [x[1] for x in query_features]

    coupons_list = instructor_analytics.basic.coupon_codes_features(db_columns, coupons, course_id)
    __, data_rows = instructor_analytics.csvs.format_dictlist(coupons_list, db_columns)
    return instructor_analytics.csvs.create_csv_response('Coupons.csv', csv_columns, data_rows)


@transaction.non_atomic_requests
@require_POST
@ensure_csrf_cookie
@cache_control(no_cache=True, no_store=True, must_revalidate=True)
@require_level('staff')
@require_finance_admin
@common_exceptions_400
def get_enrollment_report(request, course_id):
    """
    get the enrollment report for the particular course.
    """
    course_key = CourseKey.from_string(course_id)
    report_type = _('detailed enrollment')
    lms.djangoapps.instructor_task.api.submit_detailed_enrollment_features_csv(request, course_key)
    success_status = SUCCESS_MESSAGE_TEMPLATE.format(report_type=report_type)

    return JsonResponse({"status": success_status})


@transaction.non_atomic_requests
@require_POST
@ensure_csrf_cookie
@cache_control(no_cache=True, no_store=True, must_revalidate=True)
@require_level('staff')
@require_finance_admin
@common_exceptions_400
def get_exec_summary_report(request, course_id):
    """
    get the executive summary report for the particular course.
    """
    course_key = CourseKey.from_string(course_id)
    report_type = _('executive summary')
    lms.djangoapps.instructor_task.api.submit_executive_summary_report(request, course_key)
    success_status = SUCCESS_MESSAGE_TEMPLATE.format(report_type=report_type)

    return JsonResponse({"status": success_status})


@transaction.non_atomic_requests
@require_POST
@ensure_csrf_cookie
@cache_control(no_cache=True, no_store=True, must_revalidate=True)
@require_level('staff')
@common_exceptions_400
def get_course_survey_results(request, course_id):
    """
    get the survey results report for the particular course.
    """
    course_key = CourseKey.from_string(course_id)
    report_type = _('survey')
    lms.djangoapps.instructor_task.api.submit_course_survey_report(request, course_key)
    success_status = SUCCESS_MESSAGE_TEMPLATE.format(report_type=report_type)

    return JsonResponse({"status": success_status})


@transaction.non_atomic_requests
@require_POST
@ensure_csrf_cookie
@cache_control(no_cache=True, no_store=True, must_revalidate=True)
@require_level('staff')
@common_exceptions_400
def get_proctored_exam_results(request, course_id):
    """
    get the proctored exam resultsreport for the particular course.
    """
    course_key = CourseKey.from_string(course_id)
    report_type = _('proctored exam results')
    lms.djangoapps.instructor_task.api.submit_proctored_exam_results_report(request, course_key)
    success_status = SUCCESS_MESSAGE_TEMPLATE.format(report_type=report_type)

    return JsonResponse({"status": success_status})


def save_registration_code(user, course_id, mode_slug, invoice=None, order=None, invoice_item=None):
    """
    recursive function that generate a new code every time and saves in the Course Registration Table
    if validation check passes

    Args:
        user (User): The user creating the course registration codes.
        course_id (str): The string representation of the course ID.
        mode_slug (str): The Course Mode Slug associated with any enrollment made by these codes.
        invoice (Invoice): (Optional) The associated invoice for this code.
        order (Order): (Optional) The associated order for this code.
        invoice_item (CourseRegistrationCodeInvoiceItem) : (Optional) The associated CourseRegistrationCodeInvoiceItem

    Returns:
        The newly created CourseRegistrationCode.

    """
    code = random_code_generator()

    # check if the generated code is in the Coupon Table
    matching_coupons = Coupon.objects.filter(code=code, is_active=True)
    if matching_coupons:
        return save_registration_code(
            user, course_id, mode_slug, invoice=invoice, order=order, invoice_item=invoice_item
        )

    course_registration = CourseRegistrationCode(
        code=code,
        course_id=unicode(course_id),
        created_by=user,
        invoice=invoice,
        order=order,
        mode_slug=mode_slug,
        invoice_item=invoice_item
    )
    try:
        with transaction.atomic():
            course_registration.save()
        return course_registration
    except IntegrityError:
        return save_registration_code(
            user, course_id, mode_slug, invoice=invoice, order=order, invoice_item=invoice_item
        )


def registration_codes_csv(file_name, codes_list, csv_type=None):
    """
    Respond with the csv headers and data rows
    given a dict of codes list
    :param file_name:
    :param codes_list:
    :param csv_type:
    """
    # csv headers
    query_features = [
        'code', 'redeem_code_url', 'course_id', 'company_name', 'created_by',
        'redeemed_by', 'invoice_id', 'purchaser', 'customer_reference_number', 'internal_reference', 'is_valid'
    ]

    registration_codes = instructor_analytics.basic.course_registration_features(query_features, codes_list, csv_type)
    header, data_rows = instructor_analytics.csvs.format_dictlist(registration_codes, query_features)
    return instructor_analytics.csvs.create_csv_response(file_name, header, data_rows)


def random_code_generator():
    """
    generate a random alphanumeric code of length defined in
    REGISTRATION_CODE_LENGTH settings
    """
    code_length = getattr(settings, 'REGISTRATION_CODE_LENGTH', 8)
    return generate_random_string(code_length)


@ensure_csrf_cookie
@cache_control(no_cache=True, no_store=True, must_revalidate=True)
@require_level('staff')
@require_POST
def get_registration_codes(request, course_id):
    """
    Respond with csv which contains a summary of all Registration Codes.
    """
    course_id = CourseKey.from_string(course_id)

    #filter all the  course registration codes
    registration_codes = CourseRegistrationCode.objects.filter(
        course_id=course_id
    ).order_by('invoice_item__invoice__company_name')

    company_name = request.POST['download_company_name']
    if company_name:
        registration_codes = registration_codes.filter(invoice_item__invoice__company_name=company_name)

    csv_type = 'download'
    return registration_codes_csv("Registration_Codes.csv", registration_codes, csv_type)


@ensure_csrf_cookie
@cache_control(no_cache=True, no_store=True, must_revalidate=True)
@require_sales_admin
@require_POST
def generate_registration_codes(request, course_id):
    """
    Respond with csv which contains a summary of all Generated Codes.
    """
    course_id = CourseKey.from_string(course_id)
    invoice_copy = False

    # covert the course registration code number into integer
    try:
        course_code_number = int(request.POST['total_registration_codes'])
    except ValueError:
        course_code_number = int(float(request.POST['total_registration_codes']))

    company_name = request.POST['company_name']
    company_contact_name = request.POST['company_contact_name']
    company_contact_email = request.POST['company_contact_email']
    unit_price = request.POST['unit_price']

    try:
        unit_price = (
            decimal.Decimal(unit_price)
        ).quantize(
            decimal.Decimal('.01'),
            rounding=decimal.ROUND_DOWN
        )
    except decimal.InvalidOperation:
        return HttpResponse(
            status=400,
            content=_(u"Could not parse amount as a decimal")
        )

    recipient_name = request.POST['recipient_name']
    recipient_email = request.POST['recipient_email']
    address_line_1 = request.POST['address_line_1']
    address_line_2 = request.POST['address_line_2']
    address_line_3 = request.POST['address_line_3']
    city = request.POST['city']
    state = request.POST['state']
    zip_code = request.POST['zip']
    country = request.POST['country']
    internal_reference = request.POST['internal_reference']
    customer_reference_number = request.POST['customer_reference_number']
    recipient_list = [recipient_email]
    if request.POST.get('invoice', False):
        recipient_list.append(request.user.email)
        invoice_copy = True

    sale_price = unit_price * course_code_number
    set_user_preference(request.user, INVOICE_KEY, invoice_copy)
    sale_invoice = Invoice.objects.create(
        total_amount=sale_price,
        company_name=company_name,
        company_contact_email=company_contact_email,
        company_contact_name=company_contact_name,
        course_id=course_id,
        recipient_name=recipient_name,
        recipient_email=recipient_email,
        address_line_1=address_line_1,
        address_line_2=address_line_2,
        address_line_3=address_line_3,
        city=city,
        state=state,
        zip=zip_code,
        country=country,
        internal_reference=internal_reference,
        customer_reference_number=customer_reference_number
    )

    invoice_item = CourseRegistrationCodeInvoiceItem.objects.create(
        invoice=sale_invoice,
        qty=course_code_number,
        unit_price=unit_price,
        course_id=course_id
    )

    course = get_course_by_id(course_id, depth=0)
    paid_modes = CourseMode.paid_modes_for_course(course_id)

    if len(paid_modes) != 1:
        msg = (
            u"Generating Code Redeem Codes for Course '{course_id}', which must have a single paid course mode. "
            u"This is a configuration issue. Current course modes with payment options: {paid_modes}"
        ).format(course_id=course_id, paid_modes=paid_modes)
        log.error(msg)
        return HttpResponse(
            status=500,
            content=_(u"Unable to generate redeem codes because of course misconfiguration.")
        )

    course_mode = paid_modes[0]
    course_price = course_mode.min_price

    registration_codes = []
    for __ in range(course_code_number):
        generated_registration_code = save_registration_code(
            request.user, course_id, course_mode.slug, invoice=sale_invoice, order=None, invoice_item=invoice_item
        )
        registration_codes.append(generated_registration_code)

    site_name = configuration_helpers.get_value('SITE_NAME', 'localhost')
    quantity = course_code_number
    discount = (float(quantity * course_price) - float(sale_price))
    course_url = '{base_url}{course_about}'.format(
        base_url=configuration_helpers.get_value('SITE_NAME', settings.SITE_NAME),
        course_about=reverse('about_course', kwargs={'course_id': text_type(course_id)})
    )
    dashboard_url = '{base_url}{dashboard}'.format(
        base_url=configuration_helpers.get_value('SITE_NAME', settings.SITE_NAME),
        dashboard=reverse('dashboard')
    )

    try:
        pdf_file = sale_invoice.generate_pdf_invoice(course, course_price, int(quantity), float(sale_price))
    except Exception:  # pylint: disable=broad-except
        log.exception('Exception at creating pdf file.')
        pdf_file = None

    from_address = configuration_helpers.get_value('email_from_address', settings.DEFAULT_FROM_EMAIL)
    context = {
        'invoice': sale_invoice,
        'site_name': site_name,
        'course': course,
        'course_price': course_price,
        'sub_total': course_price * quantity,
        'discount': discount,
        'sale_price': sale_price,
        'quantity': quantity,
        'registration_codes': registration_codes,
        'currency_symbol': settings.PAID_COURSE_REGISTRATION_CURRENCY[1],
        'course_url': course_url,
        'platform_name': configuration_helpers.get_value('PLATFORM_NAME', settings.PLATFORM_NAME),
        'dashboard_url': dashboard_url,
        'contact_email': from_address,
        'corp_address': configuration_helpers.get_value('invoice_corp_address', settings.INVOICE_CORP_ADDRESS),
        'payment_instructions': configuration_helpers.get_value(
            'invoice_payment_instructions',
            settings. INVOICE_PAYMENT_INSTRUCTIONS,
        ),
        'date': time.strftime("%m/%d/%Y")
    }
    # composes registration codes invoice email
    subject = u'Confirmation and Invoice for {course_name}'.format(course_name=course.display_name)
    message = render_to_string('emails/registration_codes_sale_email.txt', context)

    invoice_attachment = render_to_string('emails/registration_codes_sale_invoice_attachment.txt', context)

    #send_mail(subject, message, from_address, recipient_list, fail_silently=False)
    csv_file = StringIO.StringIO()
    csv_writer = csv.writer(csv_file)
    for registration_code in registration_codes:
        full_redeem_code_url = 'http://{base_url}{redeem_code_url}'.format(
            base_url=configuration_helpers.get_value('SITE_NAME', settings.SITE_NAME),
            redeem_code_url=reverse('register_code_redemption', kwargs={'registration_code': registration_code.code})
        )
        csv_writer.writerow([registration_code.code, full_redeem_code_url])
    finance_email = configuration_helpers.get_value('finance_email', settings.FINANCE_EMAIL)
    if finance_email:
        # append the finance email into the recipient_list
        recipient_list.append(finance_email)

    # send a unique email for each recipient, don't put all email addresses in a single email
    for recipient in recipient_list:
        email = EmailMessage()
        email.subject = subject
        email.body = message
        email.from_email = from_address
        email.to = [recipient]
        email.attach(u'RegistrationCodes.csv', csv_file.getvalue(), 'text/csv')
        email.attach(u'Invoice.txt', invoice_attachment, 'text/plain')
        if pdf_file is not None:
            email.attach(u'Invoice.pdf', pdf_file.getvalue(), 'application/pdf')
        else:
            file_buffer = StringIO.StringIO(_('pdf download unavailable right now, please contact support.'))
            email.attach(u'pdf_unavailable.txt', file_buffer.getvalue(), 'text/plain')
        email.send()

    return registration_codes_csv("Registration_Codes.csv", registration_codes)


@ensure_csrf_cookie
@cache_control(no_cache=True, no_store=True, must_revalidate=True)
@require_level('staff')
@require_POST
def active_registration_codes(request, course_id):
    """
    Respond with csv which contains a summary of all Active Registration Codes.
    """
    course_id = CourseKey.from_string(course_id)

    # find all the registration codes in this course
    registration_codes_list = CourseRegistrationCode.objects.filter(
        course_id=course_id
    ).order_by('invoice_item__invoice__company_name')

    company_name = request.POST['active_company_name']
    if company_name:
        registration_codes_list = registration_codes_list.filter(invoice_item__invoice__company_name=company_name)
    # find the redeemed registration codes if any exist in the db
    code_redemption_set = RegistrationCodeRedemption.objects.select_related(
        'registration_code', 'registration_code__invoice_item__invoice'
    ).filter(registration_code__course_id=course_id)
    if code_redemption_set.exists():
        redeemed_registration_codes = [code.registration_code.code for code in code_redemption_set]
        # exclude the redeemed registration codes from the registration codes list and you will get
        # all the registration codes that are active
        registration_codes_list = registration_codes_list.exclude(code__in=redeemed_registration_codes)

    return registration_codes_csv("Active_Registration_Codes.csv", registration_codes_list)


@ensure_csrf_cookie
@cache_control(no_cache=True, no_store=True, must_revalidate=True)
@require_level('staff')
@require_POST
def spent_registration_codes(request, course_id):
    """
    Respond with csv which contains a summary of all Spent(used) Registration Codes.
    """
    course_id = CourseKey.from_string(course_id)

    # find the redeemed registration codes if any exist in the db
    code_redemption_set = RegistrationCodeRedemption.objects.select_related('registration_code').filter(
        registration_code__course_id=course_id
    )
    spent_codes_list = []
    if code_redemption_set.exists():
        redeemed_registration_codes = [code.registration_code.code for code in code_redemption_set]
        # filter the Registration Codes by course id and the redeemed codes and
        # you will get a list of all the spent(Redeemed) Registration Codes
        spent_codes_list = CourseRegistrationCode.objects.filter(
            course_id=course_id, code__in=redeemed_registration_codes
        ).order_by('invoice_item__invoice__company_name').select_related('invoice_item__invoice')

        company_name = request.POST['spent_company_name']
        if company_name:
            spent_codes_list = spent_codes_list.filter(invoice_item__invoice__company_name=company_name)  # pylint: disable=maybe-no-member

    csv_type = 'spent'
    return registration_codes_csv("Spent_Registration_Codes.csv", spent_codes_list, csv_type)


@ensure_csrf_cookie
@cache_control(no_cache=True, no_store=True, must_revalidate=True)
@require_level('staff')
def get_anon_ids(request, course_id):  # pylint: disable=unused-argument
    """
    Respond with 2-column CSV output of user-id, anonymized-user-id
    """
    # TODO: the User.objects query and CSV generation here could be
    # centralized into instructor_analytics. Currently instructor_analytics
    # has similar functionality but not quite what's needed.
    course_id = CourseKey.from_string(course_id)

    def csv_response(filename, header, rows):
        """Returns a CSV http response for the given header and rows (excel/utf-8)."""
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename={0}'.format(text_type(filename).encode('utf-8'))
        writer = csv.writer(response, dialect='excel', quotechar='"', quoting=csv.QUOTE_ALL)
        # In practice, there should not be non-ascii data in this query,
        # but trying to do the right thing anyway.
        encoded = [text_type(s).encode('utf-8') for s in header]
        writer.writerow(encoded)
        for row in rows:
            encoded = [text_type(s).encode('utf-8') for s in row]
            writer.writerow(encoded)
        return response

    students = User.objects.filter(
        courseenrollment__course_id=course_id,
    ).order_by('id')
    header = ['User ID', 'Anonymized User ID', 'Course Specific Anonymized User ID']
    rows = [[s.id, unique_id_for_user(s, save=False), anonymous_id_for_user(s, course_id, save=False)] for s in students]
    return csv_response(text_type(course_id).replace('/', '-') + '-anon-ids.csv', header, rows)


@require_POST
@ensure_csrf_cookie
@cache_control(no_cache=True, no_store=True, must_revalidate=True)
@require_level('staff')
@require_post_params(
    unique_student_identifier="email or username of student for whom to get progress url"
)
@common_exceptions_400
def get_student_progress_url(request, course_id):
    """
    Get the progress url of a student.
    Limited to staff access.

    Takes query parameter unique_student_identifier and if the student exists
    returns e.g. {
        'progress_url': '/../...'
    }
    """
    course_id = CourseKey.from_string(course_id)
    user = get_student_from_identifier(request.POST.get('unique_student_identifier'))

    progress_url = reverse('student_progress', kwargs={'course_id': text_type(course_id), 'student_id': user.id})

    response_payload = {
        'course_id': text_type(course_id),
        'progress_url': progress_url,
    }
    return JsonResponse(response_payload)


@transaction.non_atomic_requests
@require_POST
@ensure_csrf_cookie
@cache_control(no_cache=True, no_store=True, must_revalidate=True)
@require_level('staff')
@require_post_params(
    problem_to_reset="problem urlname to reset"
)
@common_exceptions_400
def reset_student_attempts(request, course_id):
    """

    Resets a students attempts counter or starts a task to reset all students
    attempts counters. Optionally deletes student state for a problem. Limited
    to staff access. Some sub-methods limited to instructor access.

    Takes some of the following query paremeters
        - problem_to_reset is a urlname of a problem
        - unique_student_identifier is an email or username
        - all_students is a boolean
            requires instructor access
            mutually exclusive with delete_module
            mutually exclusive with delete_module
        - delete_module is a boolean
            requires instructor access
            mutually exclusive with all_students
    """
    course_id = CourseKey.from_string(course_id)
    course = get_course_with_access(
        request.user, 'staff', course_id, depth=None
    )
    all_students = _get_boolean_param(request, 'all_students')

    if all_students and not has_access(request.user, 'instructor', course):
        return HttpResponseForbidden("Requires instructor access.")

    problem_to_reset = strip_if_string(request.POST.get('problem_to_reset'))
    student_identifier = request.POST.get('unique_student_identifier', None)
    student = None
    if student_identifier is not None:
        student = get_student_from_identifier(student_identifier)
    delete_module = _get_boolean_param(request, 'delete_module')

    # parameter combinations
    if all_students and student:
        return HttpResponseBadRequest(
            "all_students and unique_student_identifier are mutually exclusive."
        )
    if all_students and delete_module:
        return HttpResponseBadRequest(
            "all_students and delete_module are mutually exclusive."
        )

    try:
        module_state_key = UsageKey.from_string(problem_to_reset).map_into_course(course_id)
    except InvalidKeyError:
        return HttpResponseBadRequest()

    response_payload = {}
    response_payload['problem_to_reset'] = problem_to_reset

    if student:
        try:
            enrollment.reset_student_attempts(
                course_id,
                student,
                module_state_key,
                requesting_user=request.user,
                delete_module=delete_module
            )
        except StudentModule.DoesNotExist:
            return HttpResponseBadRequest(_("Module does not exist."))
        except sub_api.SubmissionError:
            # Trust the submissions API to log the error
            error_msg = _("An error occurred while deleting the score.")
            return HttpResponse(error_msg, status=500)
        response_payload['student'] = student_identifier
    elif all_students:
        lms.djangoapps.instructor_task.api.submit_reset_problem_attempts_for_all_students(request, module_state_key)
        response_payload['task'] = TASK_SUBMISSION_OK
        response_payload['student'] = 'All Students'
    else:
        return HttpResponseBadRequest()

    return JsonResponse(response_payload)


@transaction.non_atomic_requests
@require_POST
@ensure_csrf_cookie
@cache_control(no_cache=True, no_store=True, must_revalidate=True)
@require_level('staff')
@common_exceptions_400
def reset_student_attempts_for_entrance_exam(request, course_id):  # pylint: disable=invalid-name
    """

    Resets a students attempts counter or starts a task to reset all students
    attempts counters for entrance exam. Optionally deletes student state for
    entrance exam. Limited to staff access. Some sub-methods limited to instructor access.

    Following are possible query parameters
        - unique_student_identifier is an email or username
        - all_students is a boolean
            requires instructor access
            mutually exclusive with delete_module
        - delete_module is a boolean
            requires instructor access
            mutually exclusive with all_students
    """
    course_id = CourseKey.from_string(course_id)
    course = get_course_with_access(
        request.user, 'staff', course_id, depth=None
    )

    if not course.entrance_exam_id:
        return HttpResponseBadRequest(
            _("Course has no entrance exam section.")
        )

    student_identifier = request.POST.get('unique_student_identifier', None)
    student = None
    if student_identifier is not None:
        student = get_student_from_identifier(student_identifier)
    all_students = _get_boolean_param(request, 'all_students')
    delete_module = _get_boolean_param(request, 'delete_module')

    # parameter combinations
    if all_students and student:
        return HttpResponseBadRequest(
            _("all_students and unique_student_identifier are mutually exclusive.")
        )
    if all_students and delete_module:
        return HttpResponseBadRequest(
            _("all_students and delete_module are mutually exclusive.")
        )

    # instructor authorization
    if all_students or delete_module:
        if not has_access(request.user, 'instructor', course):
            return HttpResponseForbidden(_("Requires instructor access."))

    try:
        entrance_exam_key = UsageKey.from_string(course.entrance_exam_id).map_into_course(course_id)
        if delete_module:
            lms.djangoapps.instructor_task.api.submit_delete_entrance_exam_state_for_student(
                request,
                entrance_exam_key,
                student
            )
        else:
            lms.djangoapps.instructor_task.api.submit_reset_problem_attempts_in_entrance_exam(
                request,
                entrance_exam_key,
                student
            )
    except InvalidKeyError:
        return HttpResponseBadRequest(_("Course has no valid entrance exam section."))

    response_payload = {'student': student_identifier or _('All Learners'), 'task': TASK_SUBMISSION_OK}
    return JsonResponse(response_payload)


@transaction.non_atomic_requests
@require_POST
@ensure_csrf_cookie
@cache_control(no_cache=True, no_store=True, must_revalidate=True)
@require_level('staff')
@require_post_params(problem_to_reset="problem urlname to reset")
@common_exceptions_400
def rescore_problem(request, course_id):
    """
    Starts a background process a students attempts counter. Optionally deletes student state for a problem.
    Rescore for all students is limited to instructor access.

    Takes either of the following query paremeters
        - problem_to_reset is a urlname of a problem
        - unique_student_identifier is an email or username
        - all_students is a boolean

    all_students and unique_student_identifier cannot both be present.
    """
    course_id = CourseKey.from_string(course_id)
    course = get_course_with_access(request.user, 'staff', course_id)
    all_students = _get_boolean_param(request, 'all_students')

    if all_students and not has_access(request.user, 'instructor', course):
        return HttpResponseForbidden("Requires instructor access.")

    only_if_higher = _get_boolean_param(request, 'only_if_higher')
    problem_to_reset = strip_if_string(request.POST.get('problem_to_reset'))
    student_identifier = request.POST.get('unique_student_identifier', None)
    student = None
    if student_identifier is not None:
        student = get_student_from_identifier(student_identifier)

    if not (problem_to_reset and (all_students or student)):
        return HttpResponseBadRequest("Missing query parameters.")

    if all_students and student:
        return HttpResponseBadRequest(
            "Cannot rescore with all_students and unique_student_identifier."
        )

    try:
        module_state_key = UsageKey.from_string(problem_to_reset).map_into_course(course_id)
    except InvalidKeyError:
        return HttpResponseBadRequest("Unable to parse problem id")

    response_payload = {'problem_to_reset': problem_to_reset}

    if student:
        response_payload['student'] = student_identifier
        try:
            lms.djangoapps.instructor_task.api.submit_rescore_problem_for_student(
                request,
                module_state_key,
                student,
                only_if_higher,
            )
        except NotImplementedError as exc:
            return HttpResponseBadRequest(text_type(exc))

    elif all_students:
        try:
            lms.djangoapps.instructor_task.api.submit_rescore_problem_for_all_students(
                request,
                module_state_key,
                only_if_higher,
            )
        except NotImplementedError as exc:
            return HttpResponseBadRequest(text_type(exc))
    else:
        return HttpResponseBadRequest()

    response_payload['task'] = TASK_SUBMISSION_OK
    return JsonResponse(response_payload)


@transaction.non_atomic_requests
@require_POST
@ensure_csrf_cookie
@cache_control(no_cache=True, no_store=True, must_revalidate=True)
@require_level('staff')
@require_post_params(problem_to_reset="problem urlname to reset", score='overriding score')
@common_exceptions_400
def override_problem_score(request, course_id):
    course_key = CourseKey.from_string(course_id)
    score = strip_if_string(request.POST.get('score'))
    problem_to_reset = strip_if_string(request.POST.get('problem_to_reset'))
    student_identifier = request.POST.get('unique_student_identifier', None)

    if not problem_to_reset:
        return HttpResponseBadRequest("Missing query parameter problem_to_reset.")

    if not student_identifier:
        return HttpResponseBadRequest("Missing query parameter student_identifier.")

    if student_identifier is not None:
        student = get_student_from_identifier(student_identifier)
    else:
        return _create_error_response(request, "Invalid student ID {}.".format(student_identifier))

    try:
        usage_key = UsageKey.from_string(problem_to_reset).map_into_course(course_key)
    except InvalidKeyError:
        return _create_error_response(request, "Unable to parse problem id {}.".format(problem_to_reset))

    # check the user's access to this specific problem
    if not has_access(request.user, "staff", modulestore().get_item(usage_key)):
        _create_error_response(request, "User {} does not have permission to override scores for problem {}.".format(
            request.user.id,
            problem_to_reset
        ))

    response_payload = {
        'problem_to_reset': problem_to_reset,
        'student': student_identifier
    }
    try:
        submit_override_score(
            request,
            usage_key,
            student,
            score,
        )
    except NotImplementedError as exc:  # if we try to override the score of a non-scorable block, catch it here
        return _create_error_response(request, text_type(exc))

    except ValueError as exc:
        return _create_error_response(request, text_type(exc))

    response_payload['task'] = TASK_SUBMISSION_OK
    return JsonResponse(response_payload)


@transaction.non_atomic_requests
@require_POST
@ensure_csrf_cookie
@cache_control(no_cache=True, no_store=True, must_revalidate=True)
@require_level('instructor')
@common_exceptions_400
def rescore_entrance_exam(request, course_id):
    """
    Starts a background process a students attempts counter for entrance exam.
    Optionally deletes student state for a problem. Limited to instructor access.

    Takes either of the following query parameters
        - unique_student_identifier is an email or username
        - all_students is a boolean

    all_students and unique_student_identifier cannot both be present.
    """
    course_id = CourseKey.from_string(course_id)
    course = get_course_with_access(
        request.user, 'staff', course_id, depth=None
    )

    student_identifier = request.POST.get('unique_student_identifier', None)
    only_if_higher = request.POST.get('only_if_higher', None)
    student = None
    if student_identifier is not None:
        student = get_student_from_identifier(student_identifier)

    all_students = _get_boolean_param(request, 'all_students')

    if not course.entrance_exam_id:
        return HttpResponseBadRequest(
            _("Course has no entrance exam section.")
        )

    if all_students and student:
        return HttpResponseBadRequest(
            _("Cannot rescore with all_students and unique_student_identifier.")
        )

    try:
        entrance_exam_key = UsageKey.from_string(course.entrance_exam_id).map_into_course(course_id)
    except InvalidKeyError:
        return HttpResponseBadRequest(_("Course has no valid entrance exam section."))

    response_payload = {}
    if student:
        response_payload['student'] = student_identifier
    else:
        response_payload['student'] = _("All Learners")

    lms.djangoapps.instructor_task.api.submit_rescore_entrance_exam_for_student(
        request, entrance_exam_key, student, only_if_higher,
    )
    response_payload['task'] = TASK_SUBMISSION_OK
    return JsonResponse(response_payload)


@require_POST
@ensure_csrf_cookie
@cache_control(no_cache=True, no_store=True, must_revalidate=True)
@require_level('staff')
def list_background_email_tasks(request, course_id):  # pylint: disable=unused-argument
    """
    List background email tasks.
    """
    course_id = CourseKey.from_string(course_id)
    task_type = 'bulk_course_email'
    # Specifying for the history of a single task type
    tasks = lms.djangoapps.instructor_task.api.get_instructor_task_history(
        course_id,
        task_type=task_type
    )

    response_payload = {
        'tasks': map(extract_task_features, tasks),
    }
    return JsonResponse(response_payload)


@require_POST
@ensure_csrf_cookie
@cache_control(no_cache=True, no_store=True, must_revalidate=True)
@require_level('staff')
def list_email_content(request, course_id):  # pylint: disable=unused-argument
    """
    List the content of bulk emails sent
    """
    course_id = CourseKey.from_string(course_id)
    task_type = 'bulk_course_email'
    # First get tasks list of bulk emails sent
    emails = lms.djangoapps.instructor_task.api.get_instructor_task_history(course_id, task_type=task_type)

    response_payload = {
        'emails': map(extract_email_features, emails),
    }
    return JsonResponse(response_payload)


@require_POST
@ensure_csrf_cookie
@cache_control(no_cache=True, no_store=True, must_revalidate=True)
@require_level('staff')
def list_instructor_tasks(request, course_id):
    """
    List instructor tasks.

    Takes optional query paremeters.
        - With no arguments, lists running tasks.
        - `problem_location_str` lists task history for problem
        - `problem_location_str` and `unique_student_identifier` lists task
            history for problem AND student (intersection)
    """
    course_id = CourseKey.from_string(course_id)
    problem_location_str = strip_if_string(request.POST.get('problem_location_str', False))
    student = request.POST.get('unique_student_identifier', None)
    if student is not None:
        student = get_student_from_identifier(student)

    if student and not problem_location_str:
        return HttpResponseBadRequest(
            "unique_student_identifier must accompany problem_location_str"
        )

    if problem_location_str:
        try:
            module_state_key = UsageKey.from_string(problem_location_str).map_into_course(course_id)
        except InvalidKeyError:
            return HttpResponseBadRequest()
        if student:
            # Specifying for a single student's history on this problem
            tasks = lms.djangoapps.instructor_task.api.get_instructor_task_history(course_id, module_state_key, student)
        else:
            # Specifying for single problem's history
            tasks = lms.djangoapps.instructor_task.api.get_instructor_task_history(course_id, module_state_key)
    else:
        # If no problem or student, just get currently running tasks
        tasks = lms.djangoapps.instructor_task.api.get_running_instructor_tasks(course_id)

    response_payload = {
        'tasks': map(extract_task_features, tasks),
    }
    return JsonResponse(response_payload)


@require_POST
@ensure_csrf_cookie
@cache_control(no_cache=True, no_store=True, must_revalidate=True)
@require_level('staff')
def list_entrance_exam_instructor_tasks(request, course_id):  # pylint: disable=invalid-name
    """
    List entrance exam related instructor tasks.

    Takes either of the following query parameters
        - unique_student_identifier is an email or username
        - all_students is a boolean
    """
    course_id = CourseKey.from_string(course_id)
    course = get_course_by_id(course_id)
    student = request.POST.get('unique_student_identifier', None)
    if student is not None:
        student = get_student_from_identifier(student)

    try:
        entrance_exam_key = UsageKey.from_string(course.entrance_exam_id).map_into_course(course_id)
    except InvalidKeyError:
        return HttpResponseBadRequest(_("Course has no valid entrance exam section."))
    if student:
        # Specifying for a single student's entrance exam history
        tasks = lms.djangoapps.instructor_task.api.get_entrance_exam_instructor_task_history(
            course_id,
            entrance_exam_key,
            student
        )
    else:
        # Specifying for all student's entrance exam history
        tasks = lms.djangoapps.instructor_task.api.get_entrance_exam_instructor_task_history(
            course_id,
            entrance_exam_key
        )

    response_payload = {
        'tasks': map(extract_task_features, tasks),
    }
    return JsonResponse(response_payload)


@require_POST
@ensure_csrf_cookie
@cache_control(no_cache=True, no_store=True, must_revalidate=True)
@require_level('staff')
def list_report_downloads(request, course_id):
    """
    List grade CSV files that are available for download for this course.

    Takes the following query parameters:
    - (optional) report_name - name of the report
    """
    course_id = CourseKey.from_string(course_id)
    report_store = ReportStore.from_config(config_name='GRADES_DOWNLOAD')
    report_name = request.POST.get("report_name", None)

    response_payload = {
        'downloads': [
            dict(name=name, url=url, link=HTML('<a href="{}">{}</a>').format(HTML(url), Text(name)))
            for name, url in report_store.links_for(course_id) if report_name is None or name == report_name
        ]
    }
    return JsonResponse(response_payload)


@require_POST
@ensure_csrf_cookie
@cache_control(no_cache=True, no_store=True, must_revalidate=True)
@require_level('staff')
@require_finance_admin
def list_financial_report_downloads(_request, course_id):
    """
    List grade CSV files that are available for download for this course.
    """
    course_id = CourseKey.from_string(course_id)
    report_store = ReportStore.from_config(config_name='FINANCIAL_REPORTS')

    response_payload = {
        'downloads': [
            dict(name=name, url=url, link=HTML('<a href="{}">{}</a>').format(HTML(url), Text(name)))
            for name, url in report_store.links_for(course_id)
        ]
    }
    return JsonResponse(response_payload)


@transaction.non_atomic_requests
@require_POST
@ensure_csrf_cookie
@cache_control(no_cache=True, no_store=True, must_revalidate=True)
@require_level('staff')
@common_exceptions_400
def export_ora2_data(request, course_id):
    """
    Pushes a Celery task which will aggregate ora2 responses for a course into a .csv
    """
    course_key = CourseKey.from_string(course_id)
    report_type = _('ORA data')
    lms.djangoapps.instructor_task.api.submit_export_ora2_data(request, course_key)
    success_status = SUCCESS_MESSAGE_TEMPLATE.format(report_type=report_type)

    return JsonResponse({"status": success_status})


@transaction.non_atomic_requests
@require_POST
@ensure_csrf_cookie
@cache_control(no_cache=True, no_store=True, must_revalidate=True)
@require_level('staff')
@common_exceptions_400
def calculate_grades_csv(request, course_id):
    """
    AlreadyRunningError is raised if the course's grades are already being updated.
    """
    report_type = _('grade')
    course_key = CourseKey.from_string(course_id)
    lms.djangoapps.instructor_task.api.submit_calculate_grades_csv(request, course_key)
    success_status = SUCCESS_MESSAGE_TEMPLATE.format(report_type=report_type)

    return JsonResponse({"status": success_status})


@transaction.non_atomic_requests
@require_POST
@ensure_csrf_cookie
@cache_control(no_cache=True, no_store=True, must_revalidate=True)
@require_level('staff')
@common_exceptions_400
def problem_grade_report(request, course_id):
    """
    Request a CSV showing students' grades for all problems in the
    course.

    AlreadyRunningError is raised if the course's grades are already being
    updated.
    """
    course_key = CourseKey.from_string(course_id)
    report_type = _('problem grade')
    lms.djangoapps.instructor_task.api.submit_problem_grade_report(request, course_key)
    success_status = SUCCESS_MESSAGE_TEMPLATE.format(report_type=report_type)

    return JsonResponse({"status": success_status})


@require_POST
@ensure_csrf_cookie
@cache_control(no_cache=True, no_store=True, must_revalidate=True)
@require_level('staff')
@require_post_params('rolename')
def list_forum_members(request, course_id):
    """
    Lists forum members of a certain rolename.
    Limited to staff access.

    The requesting user must be at least staff.
    Staff forum admins can access all roles EXCEPT for FORUM_ROLE_ADMINISTRATOR
        which is limited to instructors.

    Takes query parameter `rolename`.
    """
    course_id = CourseKey.from_string(course_id)
    course = get_course_by_id(course_id)
    has_instructor_access = has_access(request.user, 'instructor', course)
    has_forum_admin = has_forum_access(
        request.user, course_id, FORUM_ROLE_ADMINISTRATOR
    )

    rolename = request.POST.get('rolename')

    # default roles require either (staff & forum admin) or (instructor)
    if not (has_forum_admin or has_instructor_access):
        return HttpResponseBadRequest(
            "Operation requires staff & forum admin or instructor access"
        )

    # EXCEPT FORUM_ROLE_ADMINISTRATOR requires (instructor)
    if rolename == FORUM_ROLE_ADMINISTRATOR and not has_instructor_access:
        return HttpResponseBadRequest("Operation requires instructor access.")

    # filter out unsupported for roles
    if rolename not in [FORUM_ROLE_ADMINISTRATOR, FORUM_ROLE_MODERATOR, FORUM_ROLE_GROUP_MODERATOR,
                        FORUM_ROLE_COMMUNITY_TA]:
        return HttpResponseBadRequest(strip_tags(
            "Unrecognized rolename '{}'.".format(rolename)
        ))

    try:
        role = Role.objects.get(name=rolename, course_id=course_id)
        users = role.users.all().order_by('username')
    except Role.DoesNotExist:
        users = []

    course_discussion_settings = get_course_discussion_settings(course_id)

    def extract_user_info(user):
        """ Convert user to dict for json rendering. """
        group_id = get_group_id_for_user(user, course_discussion_settings)
        group_name = get_group_name(group_id, course_discussion_settings)

        return {
            'username': user.username,
            'email': user.email,
            'first_name': user.first_name,
            'last_name': user.last_name,
            'group_name': group_name,
        }

    response_payload = {
        'course_id': text_type(course_id),
        rolename: map(extract_user_info, users),
        'division_scheme': course_discussion_settings.division_scheme,
    }
    return JsonResponse(response_payload)


@transaction.non_atomic_requests
@require_POST
@ensure_csrf_cookie
@cache_control(no_cache=True, no_store=True, must_revalidate=True)
@require_level('staff')
@require_post_params(send_to="sending to whom", subject="subject line", message="message text")
@common_exceptions_400
def send_email(request, course_id):
    """
    Send an email to self, staff, cohorts, or everyone involved in a course.
    Query Parameters:
    - 'send_to' specifies what group the email should be sent to
       Options are defined by the CourseEmail model in
       lms/djangoapps/bulk_email/models.py
    - 'subject' specifies email's subject
    - 'message' specifies email's content
    """
    course_id = CourseKey.from_string(course_id)

    if not BulkEmailFlag.feature_enabled(course_id):
        log.warning(u'Email is not enabled for course %s', course_id)
        return HttpResponseForbidden("Email is not enabled for this course.")

    targets = json.loads(request.POST.get("send_to"))
    subject = request.POST.get("subject")
    message = request.POST.get("message")

    # allow two branding points to come from Site Configuration: which CourseEmailTemplate should be used
    # and what the 'from' field in the email should be
    #
    # If these are None (there is no site configuration enabled for the current site) than
    # the system will use normal system defaults
    course_overview = CourseOverview.get_from_id(course_id)
    from_addr = configuration_helpers.get_value('course_email_from_addr')
    if isinstance(from_addr, dict):
        # If course_email_from_addr is a dict, we are customizing
        # the email template for each organization that has courses
        # on the site. The dict maps from addresses by org allowing
        # us to find the correct from address to use here.
        from_addr = from_addr.get(course_overview.display_org_with_default)

    template_name = configuration_helpers.get_value('course_email_template_name', 'default.template')
    if isinstance(template_name, dict):
        # If course_email_template_name is a dict, we are customizing
        # the email template for each organization that has courses
        # on the site. The dict maps template names by org allowing
        # us to find the correct template to use here.
        template_name = template_name.get(course_overview.display_org_with_default)

    # Create the CourseEmail object.  This is saved immediately, so that
    # any transaction that has been pending up to this point will also be
    # committed.
    try:
        email = CourseEmail.create(
            course_id,
            request.user,
            targets,
            subject, message,
            template_name=template_name,
            from_addr=from_addr
        )
    except ValueError as err:
        log.exception(u'Cannot create course email for course %s requested by user %s for targets %s',
                      course_id, request.user, targets)
        return HttpResponseBadRequest(repr(err))

    # Submit the task, so that the correct InstructorTask object gets created (for monitoring purposes)
    lms.djangoapps.instructor_task.api.submit_bulk_course_email(request, course_id, email.id)

    response_payload = {
        'course_id': text_type(course_id),
        'success': True,
    }

    return JsonResponse(response_payload)


@require_POST
@ensure_csrf_cookie
@cache_control(no_cache=True, no_store=True, must_revalidate=True)
@require_level('staff')
@require_post_params(
    unique_student_identifier="email or username of user to change access",
    rolename="the forum role",
    action="'allow' or 'revoke'",
)
@common_exceptions_400
def update_forum_role_membership(request, course_id):
    """
    Modify user's forum role.

    The requesting user must be at least staff.
    Staff forum admins can access all roles EXCEPT for FORUM_ROLE_ADMINISTRATOR
        which is limited to instructors.
    No one can revoke an instructors FORUM_ROLE_ADMINISTRATOR status.

    Query parameters:
    - `email` is the target users email
    - `rolename` is one of [FORUM_ROLE_ADMINISTRATOR, FORUM_ROLE_GROUP_MODERATOR,
        FORUM_ROLE_MODERATOR, FORUM_ROLE_COMMUNITY_TA]
    - `action` is one of ['allow', 'revoke']
    """
    course_id = CourseKey.from_string(course_id)
    course = get_course_by_id(course_id)
    has_instructor_access = has_access(request.user, 'instructor', course)
    has_forum_admin = has_forum_access(
        request.user, course_id, FORUM_ROLE_ADMINISTRATOR
    )

    unique_student_identifier = request.POST.get('unique_student_identifier')
    rolename = request.POST.get('rolename')
    action = request.POST.get('action')

    # default roles require either (staff & forum admin) or (instructor)
    if not (has_forum_admin or has_instructor_access):
        return HttpResponseBadRequest(
            "Operation requires staff & forum admin or instructor access"
        )

    # EXCEPT FORUM_ROLE_ADMINISTRATOR requires (instructor)
    if rolename == FORUM_ROLE_ADMINISTRATOR and not has_instructor_access:
        return HttpResponseBadRequest("Operation requires instructor access.")

    if rolename not in [FORUM_ROLE_ADMINISTRATOR, FORUM_ROLE_MODERATOR, FORUM_ROLE_GROUP_MODERATOR,
                        FORUM_ROLE_COMMUNITY_TA]:
        return HttpResponseBadRequest(strip_tags(
            "Unrecognized rolename '{}'.".format(rolename)
        ))

    user = get_student_from_identifier(unique_student_identifier)

    try:
        update_forum_role(course_id, user, rolename, action)
    except Role.DoesNotExist:
        return HttpResponseBadRequest("Role does not exist.")

    response_payload = {
        'course_id': text_type(course_id),
        'action': action,
    }
    return JsonResponse(response_payload)


@require_POST
def get_user_invoice_preference(request, course_id):  # pylint: disable=unused-argument
    """
    Gets invoice copy user's preferences.
    """
    invoice_copy_preference = True
    invoice_preference_value = get_user_preference(request.user, INVOICE_KEY)
    if invoice_preference_value is not None:
        invoice_copy_preference = invoice_preference_value == 'True'

    return JsonResponse({
        'invoice_copy': invoice_copy_preference
    })


def _display_unit(unit):
    """
    Gets string for displaying unit to user.
    """
    name = getattr(unit, 'display_name', None)
    if name:
        return u'{0} ({1})'.format(name, text_type(unit.location))
    else:
        return text_type(unit.location)


@handle_dashboard_error
@require_POST
@ensure_csrf_cookie
@cache_control(no_cache=True, no_store=True, must_revalidate=True)
@require_level('staff')
@require_post_params('student', 'url', 'due_datetime')
def change_due_date(request, course_id):
    """
    Grants a due date extension to a student for a particular unit.
    """
    course = get_course_by_id(CourseKey.from_string(course_id))
    student = require_student_from_identifier(request.POST.get('student'))
    unit = find_unit(course, request.POST.get('url'))
    due_date = parse_datetime(request.POST.get('due_datetime'))
    set_due_date_extension(course, unit, student, due_date)

    return JsonResponse(_(
        'Successfully changed due date for learner {0} for {1} '
        'to {2}').format(student.profile.name, _display_unit(unit),
                         due_date.strftime('%Y-%m-%d %H:%M')))


@handle_dashboard_error
@require_POST
@ensure_csrf_cookie
@cache_control(no_cache=True, no_store=True, must_revalidate=True)
@require_level('staff')
@require_post_params('student', 'url')
def reset_due_date(request, course_id):
    """
    Rescinds a due date extension for a student on a particular unit.
    """
    course = get_course_by_id(CourseKey.from_string(course_id))
    student = require_student_from_identifier(request.POST.get('student'))
    unit = find_unit(course, request.POST.get('url'))
    set_due_date_extension(course, unit, student, None)
    if not getattr(unit, "due", None):
        # It's possible the normal due date was deleted after an extension was granted:
        return JsonResponse(
            _("Successfully removed invalid due date extension (unit has no due date).")
        )

    original_due_date_str = unit.due.strftime('%Y-%m-%d %H:%M')
    return JsonResponse(_(
        'Successfully reset due date for learner {0} for {1} '
        'to {2}').format(student.profile.name, _display_unit(unit),
                         original_due_date_str))


@handle_dashboard_error
@require_POST
@ensure_csrf_cookie
@cache_control(no_cache=True, no_store=True, must_revalidate=True)
@require_level('staff')
@require_post_params('url')
def show_unit_extensions(request, course_id):
    """
    Shows all of the students which have due date extensions for the given unit.
    """
    course = get_course_by_id(CourseKey.from_string(course_id))
    unit = find_unit(course, request.POST.get('url'))
    return JsonResponse(dump_module_extensions(course, unit))


@handle_dashboard_error
@require_POST
@ensure_csrf_cookie
@cache_control(no_cache=True, no_store=True, must_revalidate=True)
@require_level('staff')
@require_post_params('student')
def show_student_extensions(request, course_id):
    """
    Shows all of the due date extensions granted to a particular student in a
    particular course.
    """
    student = require_student_from_identifier(request.POST.get('student'))
    course = get_course_by_id(CourseKey.from_string(course_id))
    return JsonResponse(dump_student_extensions(course, student))


def _split_input_list(str_list):
    """
    Separate out individual student email from the comma, or space separated string.

    e.g.
    in: "Lorem@ipsum.dolor, sit@amet.consectetur\nadipiscing@elit.Aenean\r convallis@at.lacus\r, ut@lacinia.Sed"
    out: ['Lorem@ipsum.dolor', 'sit@amet.consectetur', 'adipiscing@elit.Aenean', 'convallis@at.lacus', 'ut@lacinia.Sed']

    `str_list` is a string coming from an input text area
    returns a list of separated values
    """

    new_list = re.split(r'[\n\r\s,]', str_list)
    new_list = [s.strip() for s in new_list]
    new_list = [s for s in new_list if s != '']

    return new_list


def _instructor_dash_url(course_key, section=None):
    """Return the URL for a section in the instructor dashboard.

    Arguments:
        course_key (CourseKey)

    Keyword Arguments:
        section (str): The name of the section to load.

    Returns:
        unicode: The URL of a section in the instructor dashboard.

    """
    url = reverse('instructor_dashboard', kwargs={'course_id': unicode(course_key)})
    if section is not None:
        url += u'#view-{section}'.format(section=section)
    return url


@require_global_staff
@require_POST
def generate_example_certificates(request, course_id=None):  # pylint: disable=unused-argument
    """Start generating a set of example certificates.

    Example certificates are used to verify that certificates have
    been configured correctly for the course.

    Redirects back to the intructor dashboard once certificate
    generation has begun.

    """
    course_key = CourseKey.from_string(course_id)
    # insecure = True
    # if request.is_secure():
    #     insecure = False
    certs_api.generate_example_certificates(
        course_key,
        request_user=request.user,
        site=request.site
    )
    return redirect(_instructor_dash_url(course_key, section='certificates'))


@require_global_staff
@require_POST
def generate_intermediate_certificates(request, course_id=None):  # pylint: disable=unused-argument
    """Start generating a set of intermediate certificates.

    Intermediate certificates are used to verify that certificates have
    been configured correctly for the course.

    """
    from six import text_type
    from edxmako.shortcuts import render_to_response
    cert_url_list = []
    cert_url = '{base_url}{cert}'.format(
        base_url=configuration_helpers.get_value('SITE_NAME', settings.SITE_NAME),
        cert=reverse('intermediate_certificate_display',
                             kwargs={
                                 'course_id': text_type(course_id),
                                 'user_id': '2',
                                 'badge_type': 'Homework',
                             })
    )
    cert_url_list.append(cert_url)
    context = dict(
        cert_urls=cert_url_list,
    )
    # '{}{}'.format(settings.LMS_ROOT_URL, reverse('account_settings'))
    return render_to_response('instructor/instructor_dashboard_2/intermediate-certificates.html', context)


@require_global_staff
@require_POST
def enable_certificate_generation(request, course_id=None):
    """Enable/disable self-generated certificates for a course.

    Once self-generated certificates have been enabled, students
    who have passed the course will be able to generate certificates.

    Redirects back to the intructor dashboard once the
    setting has been updated.

    """
    course_key = CourseKey.from_string(course_id)
    is_enabled = (request.POST.get('certificates-enabled', 'false') == 'true')
    certs_api.set_cert_generation_enabled(course_key, is_enabled)
    return redirect(_instructor_dash_url(course_key, section='certificates'))


@ensure_csrf_cookie
@cache_control(no_cache=True, no_store=True, must_revalidate=True)
@require_level('staff')
@require_POST
def mark_student_can_skip_entrance_exam(request, course_id):  # pylint: disable=invalid-name
    """
    Mark a student to skip entrance exam.
    Takes `unique_student_identifier` as required POST parameter.
    """
    course_id = CourseKey.from_string(course_id)
    student_identifier = request.POST.get('unique_student_identifier')
    student = get_student_from_identifier(student_identifier)

    __, created = EntranceExamConfiguration.objects.get_or_create(user=student, course_id=course_id)
    if created:
        message = _('This learner (%s) will skip the entrance exam.') % student_identifier
    else:
        message = _('This learner (%s) is already allowed to skip the entrance exam.') % student_identifier
    response_payload = {
        'message': message,
    }
    return JsonResponse(response_payload)


@transaction.non_atomic_requests
@ensure_csrf_cookie
@cache_control(no_cache=True, no_store=True, must_revalidate=True)
@require_global_staff
@require_POST
@common_exceptions_400
def start_certificate_generation(request, course_id):
    """
    Start generating certificates for all students enrolled in given course.
    """
    course_key = CourseKey.from_string(course_id)
    task = lms.djangoapps.instructor_task.api.generate_certificates_for_students(request, course_key)
    message = _('Certificate generation task for all learners of this course has been started. '
                'You can view the status of the generation task in the "Pending Tasks" section.')
    response_payload = {
        'message': message,
        'task_id': task.task_id
    }

    return JsonResponse(response_payload)


@transaction.non_atomic_requests
@ensure_csrf_cookie
@cache_control(no_cache=True, no_store=True, must_revalidate=True)
@require_global_staff
@require_POST
@common_exceptions_400
def start_certificate_regeneration(request, course_id):
    """
    Start regenerating certificates for students whose certificate statuses lie with in 'certificate_statuses'
    entry in POST data.
    """
    course_key = CourseKey.from_string(course_id)
    certificates_statuses = request.POST.getlist('certificate_statuses', [])
    if CertificateStatuses.notpassing in certificates_statuses:
        certificates_statuses.append(CertificateStatuses.not_completed)
    if not certificates_statuses:
        return JsonResponse(
            {'message': _('Please select one or more certificate statuses that require certificate regeneration.')},
            status=400
        )

    # Check if the selected statuses are allowed
    allowed_statuses = [
        CertificateStatuses.downloadable,
        CertificateStatuses.error,
        CertificateStatuses.notpassing,
        CertificateStatuses.audit_passing,
        CertificateStatuses.audit_notpassing,
        CertificateStatuses.not_completed
    ]
    if not set(certificates_statuses).issubset(allowed_statuses):
        return JsonResponse(
            {'message': _('Please select certificate statuses from the list only.')},
            status=400
        )

    lms.djangoapps.instructor_task.api.regenerate_certificates(request, course_key, certificates_statuses)
    response_payload = {
        'message': _('Certificate regeneration task has been started. '
                     'You can view the status of the generation task in the "Pending Tasks" section.'),
        'success': True
    }
    return JsonResponse(response_payload)


@transaction.non_atomic_requests
@ensure_csrf_cookie
@cache_control(no_cache=True, no_store=True, must_revalidate=True)
@require_global_staff
@require_http_methods(['POST', 'DELETE'])
def certificate_exception_view(request, course_id):
    """
    Add/Remove students to/from certificate white list.

    :param request: HttpRequest object
    :param course_id: course identifier of the course for whom to add/remove certificates exception.
    :return: JsonResponse object with success/error message or certificate exception data.
    """
    course_key = CourseKey.from_string(course_id)
    # Validate request data and return error response in case of invalid data
    try:
        certificate_exception, student = parse_request_data_and_get_user(request, course_key)
    except ValueError as error:
        return JsonResponse({'success': False, 'message': text_type(error)}, status=400)

    # Add new Certificate Exception for the student passed in request data
    if request.method == 'POST':
        try:
            exception = add_certificate_exception(course_key, student, certificate_exception)
        except ValueError as error:
            return JsonResponse({'success': False, 'message': text_type(error)}, status=400)
        return JsonResponse(exception)

    # Remove Certificate Exception for the student passed in request data
    elif request.method == 'DELETE':
        try:
            remove_certificate_exception(course_key, student)
        except ValueError as error:
            return JsonResponse({'success': False, 'message': text_type(error)}, status=400)

        return JsonResponse({}, status=204)


def add_certificate_exception(course_key, student, certificate_exception):
    """
    Add a certificate exception to CertificateWhitelist table.
    Raises ValueError in case Student is already white listed.

    :param course_key: identifier of the course whose certificate exception will be added.
    :param student: User object whose certificate exception will be added.
    :param certificate_exception: A dict object containing certificate exception info.
    :return: CertificateWhitelist item in dict format containing certificate exception info.
    """
    if len(CertificateWhitelist.get_certificate_white_list(course_key, student)) > 0:
        raise ValueError(
            _("Learner (username/email={user}) already in certificate exception list.").format(user=student.username)
        )

    certificate_white_list, __ = CertificateWhitelist.objects.get_or_create(
        user=student,
        course_id=course_key,
        defaults={
            'whitelist': True,
            'notes': certificate_exception.get('notes', '')
        }
    )
    log.info(u'%s has been added to the whitelist in course %s', student.username, course_key)

    generated_certificate = GeneratedCertificate.eligible_certificates.filter(
        user=student,
        course_id=course_key,
        status=CertificateStatuses.downloadable,
    ).first()

    exception = dict({
        'id': certificate_white_list.id,
        'user_email': student.email,
        'user_name': student.username,
        'user_id': student.id,
        'certificate_generated': generated_certificate and generated_certificate.created_date.strftime("%B %d, %Y"),
        'created': certificate_white_list.created.strftime("%A, %B %d, %Y"),
    })

    return exception


def remove_certificate_exception(course_key, student):
    """
    Remove certificate exception for given course and student from CertificateWhitelist table and
    invalidate its GeneratedCertificate if present.
    Raises ValueError in case no exception exists for the student in the given course.

    :param course_key: identifier of the course whose certificate exception needs to be removed.
    :param student: User object whose certificate exception needs to be removed.
    :return:
    """
    try:
        certificate_exception = CertificateWhitelist.objects.get(user=student, course_id=course_key)
    except ObjectDoesNotExist:
        raise ValueError(
            _('Certificate exception (user={user}) does not exist in certificate white list. '
              'Please refresh the page and try again.').format(user=student.username)
        )

    try:
        generated_certificate = GeneratedCertificate.objects.get(  # pylint: disable=no-member
            user=student,
            course_id=course_key
        )
        generated_certificate.invalidate()
        log.info(
            u'Certificate invalidated for %s in course %s when removed from certificate exception list',
            student.username,
            course_key
        )
    except ObjectDoesNotExist:
        # Certificate has not been generated yet, so just remove the certificate exception from white list
        pass
    log.info(u'%s has been removed from the whitelist in course %s', student.username, course_key)
    certificate_exception.delete()


def parse_request_data_and_get_user(request, course_key):
    """
        Parse request data into Certificate Exception and User object.
        Certificate Exception is the dict object containing information about certificate exception.

    :param request:
    :param course_key: Course Identifier of the course for whom to process certificate exception
    :return: key-value pairs containing certificate exception data and User object
    """
    certificate_exception = parse_request_data(request)

    user = certificate_exception.get('user_name', '') or certificate_exception.get('user_email', '')
    if not user:
        raise ValueError(_('Learner username/email field is required and can not be empty. '
                           'Kindly fill in username/email and then press "Add to Exception List" button.'))
    db_user = get_student(user, course_key)

    return certificate_exception, db_user


def parse_request_data(request):
    """
    Parse and return request data, raise ValueError in case of invalid JSON data.

    :param request: HttpRequest request object.
    :return: dict object containing parsed json data.
    """
    try:
        data = json.loads(request.body or '{}')
    except ValueError:
        raise ValueError(_('The record is not in the correct format. Please add a valid username or email address.'))

    return data


def get_student(username_or_email, course_key):
    """
    Retrieve and return User object from db, raise ValueError
    if user is does not exists or is not enrolled in the given course.

    :param username_or_email: String containing either user name or email of the student.
    :param course_key: CourseKey object identifying the current course.
    :return: User object
    """
    try:
        student = get_user_by_username_or_email(username_or_email)
    except ObjectDoesNotExist:
        raise ValueError(_("{user} does not exist in the LMS. Please check your spelling and retry.").format(
            user=username_or_email
        ))

    # Make Sure the given student is enrolled in the course
    if not CourseEnrollment.is_enrolled(student, course_key):
        raise ValueError(_("{user} is not enrolled in this course. Please check your spelling and retry.")
                         .format(user=username_or_email))
    return student


@transaction.non_atomic_requests
@ensure_csrf_cookie
@cache_control(no_cache=True, no_store=True, must_revalidate=True)
@require_global_staff
@require_POST
@common_exceptions_400
def generate_certificate_exceptions(request, course_id, generate_for=None):
    """
    Generate Certificate for students in the Certificate White List.

    :param request: HttpRequest object,
    :param course_id: course identifier of the course for whom to generate certificates
    :param generate_for: string to identify whether to generate certificates for 'all' or 'new'
            additions to the certificate white-list
    :return: JsonResponse object containing success/failure message and certificate exception data
    """
    course_key = CourseKey.from_string(course_id)

    if generate_for == 'all':
        # Generate Certificates for all white listed students
        students = 'all_whitelisted'

    elif generate_for == 'new':
        students = 'whitelisted_not_generated'

    else:
        # Invalid data, generate_for must be present for all certificate exceptions
        return JsonResponse(
            {
                'success': False,
                'message': _('Invalid data, generate_for must be "new" or "all".'),
            },
            status=400
        )

    lms.djangoapps.instructor_task.api.generate_certificates_for_students(request, course_key, student_set=students)
    response_payload = {
        'success': True,
        'message': _('Certificate generation started for white listed learners.'),
    }

    return JsonResponse(response_payload)


@cache_control(no_cache=True, no_store=True, must_revalidate=True)
@require_global_staff
@require_POST
def generate_bulk_certificate_exceptions(request, course_id):  # pylint: disable=invalid-name
    """
    Add Students to certificate white list from the uploaded csv file.
    :return response in dict format.
    {
        general_errors: [errors related to csv file e.g. csv uploading, csv attachment, content reading etc. ],
        row_errors: {
            data_format_error:              [users/data in csv file that are not well formatted],
            user_not_exist:                 [csv with none exiting users in LMS system],
            user_already_white_listed:      [users that are already white listed],
            user_not_enrolled:              [rows with not enrolled users in the given course]
        },
        success: [list of successfully added users to the certificate white list model]
    }
    """
    user_index = 0
    notes_index = 1
    row_errors_key = ['data_format_error', 'user_not_exist', 'user_already_white_listed', 'user_not_enrolled']
    course_key = CourseKey.from_string(course_id)
    students, general_errors, success = [], [], []
    row_errors = {key: [] for key in row_errors_key}

    def build_row_errors(key, _user, row_count):
        """
        inner method to build dict of csv data as row errors.
        """
        row_errors[key].append(_('user "{user}" in row# {row}').format(user=_user, row=row_count))

    if 'students_list' in request.FILES:
        try:
            upload_file = request.FILES.get('students_list')
            if upload_file.name.endswith('.csv'):
                students = [row for row in csv.reader(upload_file.read().splitlines())]
            else:
                general_errors.append(_('Make sure that the file you upload is in CSV format with no '
                                        'extraneous characters or rows.'))

        except Exception:  # pylint: disable=broad-except
            general_errors.append(_('Could not read uploaded file.'))
        finally:
            upload_file.close()

        row_num = 0
        for student in students:
            row_num += 1
            # verify that we have exactly two column in every row either email or username and notes but allow for
            # blank lines
            if len(student) != 2:
                if len(student) > 0:
                    build_row_errors('data_format_error', student[user_index], row_num)
                    log.info(u'invalid data/format in csv row# %s', row_num)
                continue

            user = student[user_index]
            try:
                user = get_user_by_username_or_email(user)
            except ObjectDoesNotExist:
                build_row_errors('user_not_exist', user, row_num)
                log.info(u'student %s does not exist', user)
            else:
                if len(CertificateWhitelist.get_certificate_white_list(course_key, user)) > 0:
                    build_row_errors('user_already_white_listed', user, row_num)
                    log.warning(u'student %s already exist.', user.username)

                # make sure user is enrolled in course
                elif not CourseEnrollment.is_enrolled(user, course_key):
                    build_row_errors('user_not_enrolled', user, row_num)
                    log.warning(u'student %s is not enrolled in course.', user.username)

                else:
                    CertificateWhitelist.objects.create(
                        user=user,
                        course_id=course_key,
                        whitelist=True,
                        notes=student[notes_index]
                    )
                    success.append(_('user "{username}" in row# {row}').format(username=user.username, row=row_num))

    else:
        general_errors.append(_('File is not attached.'))

    results = {
        'general_errors': general_errors,
        'row_errors': row_errors,
        'success': success
    }

    return JsonResponse(results)


@transaction.non_atomic_requests
@ensure_csrf_cookie
@cache_control(no_cache=True, no_store=True, must_revalidate=True)
@require_global_staff
@require_http_methods(['POST', 'DELETE'])
def certificate_invalidation_view(request, course_id):
    """
    Invalidate/Re-Validate students to/from certificate.

    :param request: HttpRequest object
    :param course_id: course identifier of the course for whom to add/remove certificates exception.
    :return: JsonResponse object with success/error message or certificate invalidation data.
    """
    course_key = CourseKey.from_string(course_id)
    # Validate request data and return error response in case of invalid data
    try:
        certificate_invalidation_data = parse_request_data(request)
        certificate = validate_request_data_and_get_certificate(certificate_invalidation_data, course_key)
    except ValueError as error:
        return JsonResponse({'message': text_type(error)}, status=400)

    # Invalidate certificate of the given student for the course course
    if request.method == 'POST':
        try:
            certificate_invalidation = invalidate_certificate(request, certificate, certificate_invalidation_data)
        except ValueError as error:
            return JsonResponse({'message': text_type(error)}, status=400)
        return JsonResponse(certificate_invalidation)

    # Re-Validate student certificate for the course course
    elif request.method == 'DELETE':
        try:
            re_validate_certificate(request, course_key, certificate)
        except ValueError as error:
            return JsonResponse({'message': text_type(error)}, status=400)

        return JsonResponse({}, status=204)


def invalidate_certificate(request, generated_certificate, certificate_invalidation_data):
    """
    Invalidate given GeneratedCertificate and add CertificateInvalidation record for future reference or re-validation.

    :param request: HttpRequest object
    :param generated_certificate: GeneratedCertificate object, the certificate we want to invalidate
    :param certificate_invalidation_data: dict object containing data for CertificateInvalidation.
    :return: dict object containing updated certificate invalidation data.
    """
    if len(CertificateInvalidation.get_certificate_invalidations(
            generated_certificate.course_id,
            generated_certificate.user,
    )) > 0:
        raise ValueError(
            _("Certificate of {user} has already been invalidated. Please check your spelling and retry.").format(
                user=generated_certificate.user.username,
            )
        )

    # Verify that certificate user wants to invalidate is a valid one.
    if not generated_certificate.is_valid():
        raise ValueError(
            _("Certificate for learner {user} is already invalid, kindly verify that certificate was generated "
              "for this learner and then proceed.").format(user=generated_certificate.user.username)
        )

    # Add CertificateInvalidation record for future reference or re-validation
    certificate_invalidation, __ = CertificateInvalidation.objects.update_or_create(
        generated_certificate=generated_certificate,
        defaults={
            'invalidated_by': request.user,
            'notes': certificate_invalidation_data.get("notes", ""),
            'active': True,
        }
    )

    # Invalidate GeneratedCertificate
    generated_certificate.invalidate()
    return {
        'id': certificate_invalidation.id,
        'user': certificate_invalidation.generated_certificate.user.username,
        'invalidated_by': certificate_invalidation.invalidated_by.username,
        'created': certificate_invalidation.created.strftime("%B %d, %Y"),
        'notes': certificate_invalidation.notes,
    }


@common_exceptions_400
def re_validate_certificate(request, course_key, generated_certificate):
    """
    Remove certificate invalidation from db and start certificate generation task for this student.
    Raises ValueError if certificate invalidation is present.

    :param request: HttpRequest object
    :param course_key: CourseKey object identifying the current course.
    :param generated_certificate: GeneratedCertificate object of the student for the given course
    """
    try:
        # Fetch CertificateInvalidation object
        certificate_invalidation = CertificateInvalidation.objects.get(generated_certificate=generated_certificate)
    except ObjectDoesNotExist:
        raise ValueError(_("Certificate Invalidation does not exist, Please refresh the page and try again."))
    else:
        # Deactivate certificate invalidation if it was fetched successfully.
        certificate_invalidation.deactivate()

    # We need to generate certificate only for a single student here
    student = certificate_invalidation.generated_certificate.user

    lms.djangoapps.instructor_task.api.generate_certificates_for_students(
        request, course_key, student_set="specific_student", specific_student_id=student.id
    )


def validate_request_data_and_get_certificate(certificate_invalidation, course_key):
    """
    Fetch and return GeneratedCertificate of the student passed in request data for the given course.

    Raises ValueError in case of missing student username/email or
    if student does not have certificate for the given course.

    :param certificate_invalidation: dict containing certificate invalidation data
    :param course_key: CourseKey object identifying the current course.
    :return: GeneratedCertificate object of the student for the given course
    """
    user = certificate_invalidation.get("user")

    if not user:
        raise ValueError(
            _('Learner username/email field is required and can not be empty. '
              'Kindly fill in username/email and then press "Invalidate Certificate" button.')
        )

    student = get_student(user, course_key)

    certificate = GeneratedCertificate.certificate_for_student(student, course_key)
    if not certificate:
        raise ValueError(_(
            "The learner {student} does not have certificate for the course {course}. Kindly verify learner "
            "username/email and the selected course are correct and try again."
        ).format(student=student.username, course=course_key.course))
    return certificate


@transaction.non_atomic_requests
@require_POST
@ensure_csrf_cookie
@cache_control(no_cache=True, no_store=True, must_revalidate=True)
@require_level('staff')
@require_post_params(identifiers="stringified list of emails and/or usernames")
def certificates_export(request, course_id):
    """
    This is the api for generating certificates zip file.
    In the front end, we input list of users name/email,
    it will imediately return list of users that don't get
    the certificates, and also the reason.
    Meanwhile, it creates a background task to generate the
    zip file.
    """
    xqueue = XQueueCertInterface()
    #if request.is_secure():
    #    xqueue.use_https = True
    #else:
    #    xqueue.use_https = False
    course_key = CourseKey.from_string(course_id)
    identifiers_raw = request.POST.get('identifiers')
    identifiers = _split_input_list(identifiers_raw)
    context = {"fail": [], "success": []}
    certs = []
    for identifier in identifiers:
        try:
            user = get_student_from_identifier(identifier)
            cert = xqueue.add_cert(user, course_key, site=request.site)
            if not (cert.status == 'generating' or cert.status == 'downloadable'):
                context["fail"].append(u'<li>{identifier}: {result}</li>'.format(
                    identifier=identifier,
                    result=cert.status
                ))
            else:
                certs.append(cert.id)
        except User.DoesNotExist:
            context["fail"].append(u'<li>{identifier}: {result}</li>'.format(
                    identifier=identifier,
                    result='User does not exist'
                ))

    # if there are valid certificates, we submit a background task to generate zip file
    if certs:
        lms.djangoapps.instructor_task.api.submit_cert_zip_gen_task(request, course_key, certs)
    return JsonResponse(context)


@transaction.non_atomic_requests
@require_POST
@ensure_csrf_cookie
@cache_control(no_cache=True, no_store=True, must_revalidate=True)
@require_level('staff')
# @require_post_params(identifiers="stringified list of emails and/or usernames")
def intermediate_certificates_export(request, course_id):
    """
    This is the api for generating certificates zip file.
    In the front end, we input list of users name/email,
    it will imediately return list of users that don't get
    the certificates, and also the reason.
    Meanwhile, it creates a background task to generate the
    zip file.
    """
    xqueue = XQueueCertInterface()
    #if request.is_secure():
    #    xqueue.use_https = True
    #else:
    #    xqueue.use_https = False
    course_key = CourseKey.from_string(course_id)
    identifiers_raw = request.POST.get('identifiers')
    identifiers = _split_input_list(identifiers_raw)
    context = {"fail": [], "success": []}
    certs = []
    for identifier in identifiers:
        try:
            user = get_student_from_identifier(identifier)
            cert = xqueue.add_cert(user, course_key, site=request.site)
            if not (cert.status == 'generating' or cert.status == 'downloadable'):
                context["fail"].append(u'<li>{identifier}: {result}</li>'.format(
                    identifier=identifier,
                    result=cert.status
                ))
            else:
                certs.append(cert.id)
        except User.DoesNotExist:
            context["fail"].append(u'<li>{identifier}: {result}</li>'.format(
                    identifier=identifier,
                    result='User does not exist'
                ))

    # if there are valid certificates, we submit a background task to generate zip file
    if certs:
        lms.djangoapps.instructor_task.api.submit_cert_zip_gen_task(request, course_key, certs)
    return JsonResponse(context)


@ensure_csrf_cookie
@cache_control(no_cache=True, no_store=True, must_revalidate=True)
@require_level('staff')
def list_cert_zip_gen_tasks(request, course_id):
    """
    This is the api to get the list of intermediate certificates.

    In the front end we call this api
    """
    task_type = 'generate_certificates_zip_file'
    course_key = CourseKey.from_string(course_id)
    tasks = InstructorTask.objects.filter(
        course_id=course_key,
        task_type=task_type,
        task_state='SUCCESS'
    ).order_by('-id')
    links = ['<li><a href="{href}">{file}</a></li>'.format(
        href=json.loads(task.task_output).get('download_url', "#"),
        file=urllib.unquote(json.loads(task.task_output).get('download_url').split('certs-zip/')[-1])
    )
        for task in tasks if task.task_output != 'null' and json.loads(task.task_output).has_key('download_url')]
    context = {"links": links}
    return JsonResponse(context)


@ensure_csrf_cookie
@cache_control(no_cache=True, no_store=True, must_revalidate=True)
@require_level('staff')
def list_ic_certs(request, course_id):
    """
    This is the api to get the list of intermediate certificates.
    """
    users_raw = request.POST.get('users')
    users = users_raw.split(', ')
    links = ['<li><a href="intermediate_certificate/2/Homework">{user_name}: Homework</a></li>'.format(
        href=user,
        user_name=user
    )
        for user in users]
    context = {"links": links}
    return JsonResponse(context)


def _get_boolean_param(request, param_name):
    """
    Returns the value of the boolean parameter with the given
    name in the POST request. Handles translation from string
    values to boolean values.
    """
    return request.POST.get(param_name, False) in ['true', 'True', True]


def _create_error_response(request, msg):
    """
    Creates the appropriate error response for the current request,
    in JSON form.
    """
    return JsonResponse({"error": _(msg)}, 400)

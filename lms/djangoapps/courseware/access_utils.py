"""
Simple utility functions for computing access.
It allows us to share code between access.py and block transformers.
"""

from datetime import datetime, timedelta
from logging import getLogger

from django.conf import settings
from pytz import UTC

from courseware.access_response import AccessResponse, StartDateError
from courseware.masquerade import is_masquerading_as_student
from openedx.features.course_experience import COURSE_PRE_START_ACCESS_FLAG
from student.roles import CourseBetaTesterRole
from xmodule.util.django import get_current_request_hostname
from openedx.core.djangoapps.site_configuration import helpers as configuration_helpers

DEBUG_ACCESS = False
log = getLogger(__name__)

ACCESS_GRANTED = AccessResponse(True)
ACCESS_DENIED = AccessResponse(False)


def debug(*args, **kwargs):
    """
    Helper function for local debugging.
    """
    # to avoid overly verbose output, this is off by default
    if DEBUG_ACCESS:
        log.debug(*args, **kwargs)


def adjust_start_date(user, days_early_for_beta, start, course_key):
    """
    If user is in a beta test group, adjust the start date by the appropriate number of
    days.

    Returns:
        A datetime.  Either the same as start, or earlier for beta testers.
    """
    if days_early_for_beta is None:
        # bail early if no beta testing is set up
        return start

    if CourseBetaTesterRole(course_key).has_user(user):
        debug("Adjust start time: user in beta role for %s", course_key)
        delta = timedelta(days_early_for_beta)
        effective = start - delta
        return effective

    return start


def check_start_date(user, days_early_for_beta, start, course_key):
    """
    Verifies whether the given user is allowed access given the
    start date and the Beta offset for the given course.

    Returns:
        AccessResponse: Either ACCESS_GRANTED or StartDateError.
    """
    start_dates_disabled = settings.FEATURES['DISABLE_START_DATES']
    if start_dates_disabled and not is_masquerading_as_student(user, course_key):
        return ACCESS_GRANTED
    else:
        now = datetime.now(UTC)
        if start is None or in_preview_mode():
            return ACCESS_GRANTED

        effective_start = adjust_start_date(user, days_early_for_beta, start, course_key)
        if now > effective_start:
            return ACCESS_GRANTED

        return StartDateError(start)


def in_preview_mode():
    """
    Returns whether the user is in preview mode or not.
    """
    hostname = get_current_request_hostname()
    preview_lms_base = configuration_helpers.get_value('SITE_PREVIEW_LMS_DOMAIN_NAME', settings.FEATURES.get('PREVIEW_LMS_BASE', None))
    return bool(preview_lms_base and hostname and hostname.split(':')[0] == preview_lms_base.split(':')[0])


def check_course_open_for_learner(user, course):
    """
    Check if the course is open for learners based on the start date.

    Returns:
        AccessResponse: Either ACCESS_GRANTED or StartDateError.
    """
    if COURSE_PRE_START_ACCESS_FLAG.is_enabled(course.id):
        return ACCESS_GRANTED
    return check_start_date(user, course.days_early_for_beta, course.start, course.id)

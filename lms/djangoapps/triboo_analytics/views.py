# -*- coding: utf-8 -*-


from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.http import HttpResponseNotFound
from django.views.decorators.cache import cache_control
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_GET, require_POST
from instructor.views.api import require_level
from openedx.core.djangoapps.site_configuration import helpers as configuration_helpers


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

@analytics_on
@login_required
@ensure_csrf_cookie
def my_transcript_view(request):
    return HttpResponseNotFound()


@analytics_on
@login_required
@ensure_csrf_cookie
def transcript_view(request, user_id):
    return HttpResponseNotFound()


@require_POST
@login_required
@ensure_csrf_cookie
def waiver_request_view(request):
    return HttpResponseNotFound()


@require_GET
@login_required
@require_level('staff')
def process_waiver_request(request, course_id, waiver_id):
    return HttpResponseNotFound()


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


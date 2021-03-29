from collections import Iterable
import logging

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import AnonymousUser
from django.core.paginator import EmptyPage, PageNotAnInteger, Paginator
from django.db import DatabaseError
from django.db.models import Count
from django.http import Http404, HttpResponseNotAllowed, HttpResponseBadRequest
from django.shortcuts import redirect
from django.views.decorators.csrf import ensure_csrf_cookie
from edxmako.shortcuts import render_to_response
from isodate import parse_duration
from util.json_request import JsonResponse, expect_json

from lms.djangoapps.external_catalog.models import EdflexCategory, EdflexResource
from openedx.core.djangoapps.site_configuration import helpers as configuration_helpers
from openedx.core.djangoapps.user_api.models import UserPreference
from ..utils import get_edflex_configuration
from lms.djangoapps.external_catalog.utils import get_crehana_configuration
from student.triboo_groups import EDFLEX_DENIED_GROUP
from student.triboo_groups import CREHANA_DENIED_GROUP
from util.cache import cache_if_anonymous


log = logging.getLogger(__name__)

FILTERS = [
    'type',
    'categories',
    'language'
]

OUTPUT_COURSE_ATTRS = [
    'title',
    'type',
    'language',
    'url',
    'duration',
    'publication_date',
    'image_url',
    'rating'
]


def _format_output(query_set):
    """Used for customizing output for response.
    """
    output = query_set.values(*OUTPUT_COURSE_ATTRS)
    for item in output:
        item['duration'] = parse_duration(item['duration']).seconds if item['duration'] else None
    return output


def get_categories_by_language(queryset, configured_languages, platform_language):
    category_res = set()  # the final list for the dropdown
    category_by_id = {}
    categories = EdflexCategory.objects.filter(resources__in=queryset)
    for category in categories:
        if not category_by_id.get(category.category_id, None):
            category_by_id[category.category_id] = {}
        category_by_id[category.category_id][category.language] = category.name
    for category_id, names in category_by_id.iteritems():
        # if we have a translation in the platform_language we use it in priority
        if platform_language in names.keys():
            category_res.add(names[platform_language])
        else:
            # we don't have a translation in the platform_language
            # so we'll use the first translation we can find for configured_languages
            # configured_languages is ordered: language with most priority comes first
            name = None
            nb_lang = len(configured_languages)
            i = 0
            while not name and i < nb_lang:
                if configured_languages[i] in names.keys():
                    name = names[configured_languages[i]]
                i += 1
            if name:
                category_res.add(name)
    return sorted(category_res)


def _get_facet(filters, platform_language, configured_languages, course_queryset=None):
    """Get filter data as facet search group.
    """
    if course_queryset is None:
        course_queryset = EdflexResource.objects.all()
    facet_content = dict()
    status = 'success'
    message = ''
    try:
        for filter_type in filters:
            group_values = list()
            if filter_type == 'categories':
                categories = get_categories_by_language(course_queryset, configured_languages, platform_language)
                for cat in categories:
                    group_values.append({'text': cat, 'value': cat})
                facet_content.update({filter_type: group_values})
            else:
                annotate_values = course_queryset.values(filter_type).annotate(
                    count=Count(filter_type)).order_by()
                for item in annotate_values:
                    group_values.append({'text': item[filter_type], 'value': item[filter_type], 'count': item['count']})
                facet_content.update({filter_type: group_values})
    except DatabaseError:
        status, message = 'fail', 'Database error for transaction'
        log.exception(message)

    return {"facet_content": facet_content, 'status': status, 'message': message}


def _get_courses(request):
    """
    Return the json response according to user's search/filter data.
    """
    edflex_configuration = get_edflex_configuration()
    configured_languages = edflex_configuration['locale']
    if not request.user.is_authenticated:
        platform_language = configured_languages[0]
    else:
        platform_language = UserPreference.get_value(request.user, 'pref-lang', default='en').split('_')[0]

    status = 'success'
    message = ''
    queryset = EdflexResource.objects.all()
    default_queryset = queryset
    default_category = configuration_helpers.get_value('DEFAULT_EXTERNAL_CATEGORY', settings.FEATURES.get(
            'DEFAULT_EXTERNAL_CATEGORY', ''))
    if default_category:
        try:
            default_category_ids = EdflexCategory.objects.filter(name=default_category).values('category_id').distinct()
            queryset = queryset.filter(categories=default_category_ids)
            default_queryset = queryset
        except EdflexCategory.DoesNotExist:
            pass
    try:
        for k, v in request.json['filter_content'].items():
            if isinstance(v, Iterable) and 'all' in v:
                continue

            if k == 'categories':
                category_ids = EdflexCategory.objects.filter(name=v).values('category_id').distinct()
                queryset = queryset.filter(categories__category_id__in=category_ids)
            else:
                search_type = k + '__in'
                queryset = queryset.filter(**{search_type: v})

        if request.json['search_content']:
            queryset = queryset.filter(title__icontains=request.json['search_content'])
    except DatabaseError:
        status, message = 'fail', 'Database error for transaction'
        log.exception(message)

    course_count = len(queryset)
    # If no search results, set queryset as the default queryset
    if len(queryset) == 0:
        queryset = default_queryset
    paginator = Paginator(_format_output(queryset), request.json['page_size'])
    try:
        courses = paginator.page(request.json['page_no'])
    except PageNotAnInteger:
        courses = paginator.page(1)
    except EmptyPage:
        courses = paginator.page(paginator.num_pages)

    return {'course_list': courses.object_list,
            'status': status,
            'message': message,
            'course_count': course_count,
            'search_content': request.json['search_content'],
            'facet_content': _get_facet(FILTERS, platform_language, configured_languages, queryset)['facet_content']}


@ensure_csrf_cookie
@expect_json
def edflex_courses_handler(request):
    """
        External catalog courses
        POST
            json: get the search result
    """
    if not configuration_helpers.get_value('ENABLE_EXTERNAL_CATALOG', settings.FEATURES.get(
            'ENABLE_EXTERNAL_CATALOG', False)):
        raise Http404

    if request.META.get('CONTENT_TYPE', '') == 'application/json':
        return JsonResponse(_get_courses(request))

    return HttpResponseBadRequest()


@ensure_csrf_cookie
def edflex_catalog_handler(request):
    """
        External catalog facet filter.
        GET
            html: get the page structure
            json: get the initial data for facet filter component.
    """
    is_external_catalog_button = configuration_helpers.get_value('ENABLE_EXTERNAL_CATALOG', settings.FEATURES.get(
            'ENABLE_EXTERNAL_CATALOG', False))
    # edflex_enabled = configuration_helpers.get_value('ENABLE_EDFLEX_CATALOG',
    #                                                 settings.FEATURES.get('ENABLE_EDFLEX_CATALOG', False))
    edflex_configuration_available = True
    edflex_configuration = get_edflex_configuration()
    for conf, val in edflex_configuration.items():
        if not val:
            edflex_configuration_available = False
            break
    user_groups = {group.name for group in request.user.groups.all()}
    external_catalog_and_edflex_enabled = is_external_catalog_button and edflex_configuration_available \
            and EDFLEX_DENIED_GROUP not in user_groups
    if not external_catalog_and_edflex_enabled:
        raise Http404

    if 'text/html' in request.META.get('HTTP_ACCEPT', '') and request.method == 'GET':
        need_show_3_tabs = all(
            (
                all(get_crehana_configuration().values()),
                request.user.is_authenticated,
                CREHANA_DENIED_GROUP not in user_groups
            )
        )
        return render_to_response(
            'external_catalog/external_catalog.html',
            {
                'need_show_3_tabs': need_show_3_tabs
            }
        )

    elif request.META.get('CONTENT_TYPE', '') == 'application/json':
        configured_languages = edflex_configuration['locale']
        if isinstance(request.user, AnonymousUser):
            platform_language = configured_languages[0]
        else:
            platform_language = UserPreference.get_value(request.user, 'pref-lang', default='en').split('_')[0]
        return JsonResponse(_get_facet(FILTERS, platform_language, configured_languages))
    return HttpResponseNotAllowed(['GET'])


@ensure_csrf_cookie
@login_required
@cache_if_anonymous()
def edflex_catalog(request):
    """
    If the "ENABLE_EDFLEX_CATALOG" feature is true
       and the EDFLEX url link is provided in django admin
       and the user is not part of the EDFLEX_DENIED_GROUP
    then render the page containing an iframe loading the url.
    Otherwise return 404
    """
    enable_edflex = configuration_helpers.get_value('ENABLE_EDFLEX_CATALOG',
                                                    settings.FEATURES.get('ENABLE_EDFLEX_CATALOG', False))
    edflex_url = configuration_helpers.get_value('EDFLEX_URL', None)
    if (enable_edflex and edflex_url
            and EDFLEX_DENIED_GROUP not in [group.name for group in request.user.groups.all()]):
        context = {'edflex_url': edflex_url}
        # By default redirect
        redirect_edflex = configuration_helpers.get_value('ENABLE_EDFLEX_REDIRECTION', True)
        if redirect_edflex:
            return redirect(edflex_url)
        return render_to_response('external_catalog/edflex_catalog.html', context)
    else:
        raise Http404

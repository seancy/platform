from isodate import parse_duration
import logging

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.http import Http404
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import ensure_csrf_cookie

from edxmako.shortcuts import render_to_response
from .languages_mapping import languages_mapping
from lms.djangoapps.external_catalog.models import CrehanaResource, AndersPinkArticle
from lms.djangoapps.external_catalog.models import EdflexResource
from openedx.core.djangoapps.site_configuration import helpers as configuration_helpers
from student.triboo_groups import EDFLEX_DENIED_GROUP
from student.triboo_groups import CREHANA_DENIED_GROUP
from student.triboo_groups import ANDERSPINK_DENIED_GROUP
from ...utils import get_crehana_configuration,get_anderspink_configuration
from lms.djangoapps.external_catalog.utils import get_edflex_configuration
from util.json_request import JsonResponse


log = logging.getLogger(__name__)


class OverviewPage(View):
    """Overview Page interface for CREHANA"""
    TEMPLATE_PATH = r'external_catalog/external_catalog_overview.html'

    @method_decorator(login_required)
    @method_decorator(ensure_csrf_cookie)
    def get(self, request):
        """
            Showing overview page if `edflex enabled` + `crehana enable` + `user authenticated`
        """
        enable_external_catalog_button = configuration_helpers.get_value(
            'ENABLE_EXTERNAL_CATALOG', settings.FEATURES.get('ENABLE_EXTERNAL_CATALOG', False)
        )
        if not enable_external_catalog_button:
            raise Http404

        user_groups = {group.name for group in request.user.groups.all()}
        
        external_catalogs = []
        edflex_courses = ""
        crehana_courses = ""
        anderspink_courses = ""

        if all(
            (all(get_edflex_configuration().values()), EDFLEX_DENIED_GROUP not in user_groups)
        ):
          external_catalogs.append({"name": "EDFLEX", "to" : "/edflex_catalog"})
          edflex_courses = [
            {
                'image': course.image_url,
                'duration': parse_duration(course.duration).seconds if course.duration else None,
                'rating': course.rating,
                'title': course.title,
                'language': course.language,
                'publication_date': course.publication_date,
                'url': course.url,
                'type': course.type
            }
            for course in EdflexResource.objects.all()[:8]
          ]
        
        if all(
            (all(get_crehana_configuration().values()), CREHANA_DENIED_GROUP not in user_groups)
        ):
          external_catalogs.append({"name": "CREHANA", "to" : "/crehana_catalog"})
          crehana_courses = [
            {
                'image': course.image,
                'duration': course.duration,
                'rating': course.rating,
                'title': course.title,
                'url': course.url,
                'languages': [
                    languages_mapping.get_lang_name_by_id(int(lang_id))
                    for lang_id in course.languages.split(',')
                ]
            }
            for course in CrehanaResource.objects.all()[:8]
          ]

        
        if all(
            (all(get_anderspink_configuration().values()), ANDERSPINK_DENIED_GROUP not in user_groups)
        ):
          external_catalogs.append({"name": "ANDERSPINK", "to" : "/anderspink_catalog"})
          anderspink_courses = [
            {
                'title': article.title,
                'image': article.image,
                'date_published': article.date_published,
                'url': article.url,
                'author': article.author,
                'reading_time': article.reading_time,
                'language': article.language
            }
            for article in AndersPinkArticle.objects.all()[:8]
            ]

        if len(external_catalogs) < 2:
           raise Http404  
           
    
    
        return render_to_response(
            self.TEMPLATE_PATH,
            {
                'edflex_courses': edflex_courses,
                'crehana_courses':crehana_courses,
                'anderspink_courses':anderspink_courses,
                'external_catalogs': external_catalogs
            }
        )

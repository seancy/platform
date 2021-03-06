# pylint: disable=missing-docstring
from django.core.exceptions import PermissionDenied
from django.views.decorators.csrf import ensure_csrf_cookie
from opaque_keys.edx.keys import CourseKey
from xmodule.modulestore.django import modulestore

from edxmako.shortcuts import render_to_response
from student.auth import has_course_author_access
from student.roles import studio_login_required

__all__ = ['checklists_handler']


@studio_login_required
@ensure_csrf_cookie
def checklists_handler(request, course_key_string=None):
    '''
    The restful handler for course checklists.
    It allows retrieval of the checklists (as an HTML page).

    GET
        html: return an html page which will show course checklists. Note that only the checklists container
            is returned and that the actual data is determined with a client-side request.
    '''
    course_key = CourseKey.from_string(course_key_string)
    if not has_course_author_access(request.user, course_key):
        raise PermissionDenied()

    course_module = modulestore().get_course(course_key)
    return render_to_response('checklists.html', {
        'language_code': request.LANGUAGE_CODE,
        'context_course': course_module,
    })

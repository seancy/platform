"""
This file contains implementation override of SearchInitializer which will allow
    * To set initial set of masquerades and other parameters
"""

from opaque_keys.edx.keys import CourseKey
from search.initializer import SearchInitializer

from courseware.access import has_access
from courseware.masquerade import setup_masquerade


class CmsSearchInitializer(SearchInitializer):
    """ SearchInitializer for LMS Search """
    def initialize(self, **kwargs):
        if 'request' in kwargs and kwargs['request'] and kwargs['course_id']:
            request = kwargs['request']
            course_key = CourseKey.from_string(kwargs['course_id'])
            staff_access = bool(has_access(request.user, 'staff', course_key))
            setup_masquerade(request, course_key, staff_access)

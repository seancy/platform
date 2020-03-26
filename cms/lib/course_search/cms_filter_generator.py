"""
This file contains implementation override of SearchFilterGenerator which will allow
    * Filter by all courses in which the user is enrolled in
"""

from search.filter_generator import SearchFilterGenerator

from openedx.core.djangoapps.course_groups.partition_scheme import CohortPartitionScheme
from openedx.core.djangoapps.site_configuration import helpers as configuration_helpers
from openedx.core.djangoapps.user_api.partition_schemes import RandomUserPartitionScheme
from student.roles import (
    CourseInstructorRole,
    CourseStaffRole,
    GlobalStaff,
    UserBasedRole,
)

INCLUDE_SCHEMES = [CohortPartitionScheme, RandomUserPartitionScheme, ]
SCHEME_SUPPORTS_ASSIGNMENT = [RandomUserPartitionScheme, ]


def _courses_with_user(user):
    """Get all courses that user can access.
    """
    instructor_courses = UserBasedRole(user, CourseInstructorRole.ROLE).courses_with_role()
    staff_courses = UserBasedRole(user, CourseStaffRole.ROLE).courses_with_role()
    all_courses = instructor_courses | staff_courses
    return [course.course_id for course in all_courses if course.course_id]


class CmsSearchFilterGenerator(SearchFilterGenerator):
    """ SearchFilterGenerator for CMS Search """

    _user_access_courses = {}

    def _course_access_for_user(self, user):
        """ Return the specified user's course enrollments """
        if user not in self._user_access_courses:
            self._user_access_courses[user] = _courses_with_user(user)
        return self._user_access_courses[user]

    def field_dictionary(self, **kwargs):
        """ add course if provided otherwise add courses in which the user is enrolled in """
        field_dictionary = super(CmsSearchFilterGenerator, self).field_dictionary(**kwargs)
        if not kwargs.get('user'):
            field_dictionary['course'] = []
        elif not kwargs.get('course_id'):
            user_access_courses = self._course_access_for_user(kwargs['user'])
            field_dictionary['course'] = [unicode(course) for course in user_access_courses]

        # if we have an org filter, only include results for these orgs
        course_org_filter = configuration_helpers.get_current_site_orgs()
        if course_org_filter:
            field_dictionary['org'] = course_org_filter

        return field_dictionary

    def exclude_dictionary(self, **kwargs):
        """
            Exclude any courses defined outside the current org.
        """
        exclude_dictionary = super(CmsSearchFilterGenerator, self).exclude_dictionary(**kwargs)
        course_org_filter = configuration_helpers.get_current_site_orgs()
        # If we have a course filter we are ensuring that we only get those courses above
        if not course_org_filter:
            org_filter_out_set = configuration_helpers.get_all_orgs()
            if org_filter_out_set:
                exclude_dictionary['org'] = list(org_filter_out_set)

        return exclude_dictionary

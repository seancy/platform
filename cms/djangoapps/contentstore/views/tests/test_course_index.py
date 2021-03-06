"""
Unit tests for getting the list of courses and the course outline.
"""
import datetime
import json

import ddt
import lxml
import mock
import pytz
from django.conf import settings
from django.core.exceptions import PermissionDenied
from django.test.utils import override_settings
from django.utils.translation import ugettext as _
from opaque_keys.edx.locator import CourseLocator
from search.api import perform_search

from contentstore.courseware_index import CoursewareSearchIndexer, SearchIndexingError
from contentstore.tests.utils import CourseTestCase
from contentstore.utils import add_instructor, reverse_course_url, reverse_usage_url
from contentstore.views.course import (
    _deprecated_blocks_info,
    course_outline_initial_state,
    reindex_course_and_check_access
)
from contentstore.views.course import WAFFLE_NAMESPACE as COURSE_WAFFLE_NAMESPACE
from contentstore.views.item import VisibilityState, create_xblock_info
from course_action_state.managers import CourseRerunUIStateManager
from course_action_state.models import CourseRerunState
from openedx.core.djangoapps.waffle_utils import WaffleSwitchNamespace
from student.auth import has_course_author_access
from student.roles import STUDIO_ADMIN_ACCESS_GROUP, CourseStaffRole, GlobalStaff, LibraryUserRole
from student.tests.factories import UserFactory, GroupFactory
from util.date_utils import get_default_time_display
from xmodule.modulestore import ModuleStoreEnum
from xmodule.modulestore.django import modulestore
from xmodule.modulestore.exceptions import ItemNotFoundError
from xmodule.modulestore.tests.factories import CourseFactory, ItemFactory, LibraryFactory, check_mongo_calls


class TestCourseIndex(CourseTestCase):
    """
    Unit tests for getting the list of courses and the course outline.
    """
    shard = 1

    def setUp(self):
        """
        Add a course with odd characters in the fields
        """
        super(TestCourseIndex, self).setUp()
        # had a problem where index showed course but has_access failed to retrieve it for non-staff
        self.odd_course = CourseFactory.create(
            org='test.org_1-2',
            number='test-2.3_course',
            display_name='dotted.course.name-2',
        )

    def check_courses_on_index(self, authed_client):
        """
        Test that the course listing is present.
        """
        index_url = '/home/'
        index_response = authed_client.get(index_url, {}, HTTP_ACCEPT='text/html')
        parsed_html = lxml.html.fromstring(index_response.content)
        courses_tab = parsed_html.find_class('course-listing')
        self.assertEqual(len(courses_tab), 1)

    def test_libraries_on_index(self):
        """
        Test that the library tab is present.
        """
        def _assert_library_tab_present(response):
            """
            Asserts there's a library tab.
            """
            parsed_html = lxml.html.fromstring(response.content)
            library_tab = parsed_html.find_class('react-library-listing')
            self.assertEqual(len(library_tab), 1)

        # Add a library:
        lib1 = LibraryFactory.create()

        index_url = '/home/'
        index_response = self.client.get(index_url, {}, HTTP_ACCEPT='text/html')
        _assert_library_tab_present(index_response)

        # Make sure libraries are visible to non-staff users too
        self.client.logout()
        non_staff_user, non_staff_userpassword = self.create_non_staff_user()
        non_staff_user.groups.add(GroupFactory(name=STUDIO_ADMIN_ACCESS_GROUP))
        lib2 = LibraryFactory.create(user_id=non_staff_user.id)
        LibraryUserRole(lib2.location.library_key).add_users(non_staff_user)
        self.client.login(username=non_staff_user.username, password=non_staff_userpassword)
        index_response = self.client.get(index_url, {}, HTTP_ACCEPT='text/html')
        _assert_library_tab_present(index_response)

    def test_is_staff_access(self):
        """
        Test that people with is_staff see the courses and can navigate into them
        """
        self.check_courses_on_index(self.client)

    def test_negative_conditions(self):
        """
        Test the error conditions for the access
        """
        outline_url = reverse_course_url('course_handler', self.course.id)
        # register a non-staff member and try to delete the course branch
        non_staff_client, _ = self.create_non_staff_authed_user_client()
        response = non_staff_client.delete(outline_url, {}, HTTP_ACCEPT='application/json')
        self.assertEqual(response.status_code, 403)

    def test_course_staff_access(self):
        """
        Make and register course_staff and ensure they can access the courses
        """
        course_staff_client, course_staff = self.create_non_staff_authed_user_client()
        course_staff.groups.add(GroupFactory(name=STUDIO_ADMIN_ACCESS_GROUP))
        for course in [self.course, self.odd_course]:
            permission_url = reverse_course_url('course_team_handler', course.id, kwargs={'email': course_staff.email})

            self.client.post(
                permission_url,
                data=json.dumps({"role": "staff"}),
                content_type="application/json",
                HTTP_ACCEPT="application/json",
            )

        # test access
        self.check_courses_on_index(course_staff_client)

    def test_json_responses(self):
        outline_url = reverse_course_url('course_handler', self.course.id)
        chapter = ItemFactory.create(parent_location=self.course.location, category='chapter', display_name="Week 1")
        lesson = ItemFactory.create(parent_location=chapter.location, category='sequential', display_name="Lesson 1")
        subsection = ItemFactory.create(
            parent_location=lesson.location,
            category='vertical',
            display_name='Subsection 1'
        )
        ItemFactory.create(parent_location=subsection.location, category="video", display_name="My Video")

        resp = self.client.get(outline_url, HTTP_ACCEPT='application/json')
        json_response = json.loads(resp.content)

        # First spot check some values in the root response
        self.assertEqual(json_response['category'], 'course')
        self.assertEqual(json_response['id'], unicode(self.course.location))
        self.assertEqual(json_response['display_name'], self.course.display_name)
        self.assertTrue(json_response['published'])
        self.assertIsNone(json_response['visibility_state'])

        # Now verify the first child
        children = json_response['child_info']['children']
        self.assertGreater(len(children), 0)
        first_child_response = children[0]
        self.assertEqual(first_child_response['category'], 'chapter')
        self.assertEqual(first_child_response['id'], unicode(chapter.location))
        self.assertEqual(first_child_response['display_name'], 'Week 1')
        self.assertTrue(json_response['published'])
        self.assertEqual(first_child_response['visibility_state'], VisibilityState.unscheduled)
        self.assertGreater(len(first_child_response['child_info']['children']), 0)

        # Finally, validate the entire response for consistency
        self.assert_correct_json_response(json_response)

    def test_notifications_handler_get(self):
        state = CourseRerunUIStateManager.State.FAILED
        action = CourseRerunUIStateManager.ACTION
        should_display = True

        # try when no notification exists
        notification_url = reverse_course_url('course_notifications_handler', self.course.id, kwargs={
            'action_state_id': 1,
        })

        resp = self.client.get(notification_url, HTTP_ACCEPT='application/json')

        # verify that we get an empty dict out
        self.assertEquals(resp.status_code, 400)

        # create a test notification
        rerun_state = CourseRerunState.objects.update_state(
            course_key=self.course.id,
            new_state=state,
            allow_not_found=True
        )
        CourseRerunState.objects.update_should_display(
            entry_id=rerun_state.id,
            user=UserFactory(),
            should_display=should_display
        )

        # try to get information on this notification
        notification_url = reverse_course_url('course_notifications_handler', self.course.id, kwargs={
            'action_state_id': rerun_state.id,
        })
        resp = self.client.get(notification_url, HTTP_ACCEPT='application/json')

        json_response = json.loads(resp.content)

        self.assertEquals(json_response['state'], state)
        self.assertEquals(json_response['action'], action)
        self.assertEquals(json_response['should_display'], should_display)

    def test_notifications_handler_dismiss(self):
        state = CourseRerunUIStateManager.State.FAILED
        should_display = True
        rerun_course_key = CourseLocator(org='testx', course='test_course', run='test_run')

        # add an instructor to this course
        user2 = UserFactory()
        add_instructor(rerun_course_key, self.user, user2)

        # create a test notification
        rerun_state = CourseRerunState.objects.update_state(
            course_key=rerun_course_key,
            new_state=state,
            allow_not_found=True
        )
        CourseRerunState.objects.update_should_display(
            entry_id=rerun_state.id,
            user=user2,
            should_display=should_display
        )

        # try to get information on this notification
        notification_dismiss_url = reverse_course_url('course_notifications_handler', self.course.id, kwargs={
            'action_state_id': rerun_state.id,
        })
        resp = self.client.delete(notification_dismiss_url)
        self.assertEquals(resp.status_code, 200)

        with self.assertRaises(CourseRerunState.DoesNotExist):
            # delete nofications that are dismissed
            CourseRerunState.objects.get(id=rerun_state.id)

        self.assertFalse(has_course_author_access(user2, rerun_course_key))

    def assert_correct_json_response(self, json_response):
        """
        Asserts that the JSON response is syntactically consistent
        """
        self.assertIsNotNone(json_response['display_name'])
        self.assertIsNotNone(json_response['id'])
        self.assertIsNotNone(json_response['category'])
        self.assertTrue(json_response['published'])
        if json_response.get('child_info', None):
            for child_response in json_response['child_info']['children']:
                self.assert_correct_json_response(child_response)

    def test_course_updates_invalid_url(self):
        """
        Tests the error conditions for the invalid course updates URL.
        """
        # Testing the response code by passing slash separated course id whose format is valid but no course
        # having this id exists.
        invalid_course_key = '{}_blah_blah_blah'.format(self.course.id)
        course_updates_url = reverse_course_url('course_info_handler', invalid_course_key)
        response = self.client.get(course_updates_url)
        self.assertEqual(response.status_code, 404)

        # Testing the response code by passing split course id whose format is valid but no course
        # having this id exists.
        split_course_key = CourseLocator(org='orgASD', course='course_01213', run='Run_0_hhh_hhh_hhh')
        course_updates_url_split = reverse_course_url('course_info_handler', split_course_key)
        response = self.client.get(course_updates_url_split)
        self.assertEqual(response.status_code, 404)

        # Testing the response by passing split course id whose format is invalid.
        invalid_course_id = 'invalid.course.key/{}'.format(split_course_key)
        course_updates_url_split = reverse_course_url('course_info_handler', invalid_course_id)
        response = self.client.get(course_updates_url_split)
        self.assertEqual(response.status_code, 404)

    def test_course_index_invalid_url(self):
        """
        Tests the error conditions for the invalid course index URL.
        """
        # Testing the response code by passing slash separated course key, no course
        # having this key exists.
        invalid_course_key = '{}_some_invalid_run'.format(self.course.id)
        course_outline_url = reverse_course_url('course_handler', invalid_course_key)
        response = self.client.get_html(course_outline_url)
        self.assertEqual(response.status_code, 404)

        # Testing the response code by passing split course key, no course
        # having this key exists.
        split_course_key = CourseLocator(org='invalid_org', course='course_01111', run='Run_0_invalid')
        course_outline_url_split = reverse_course_url('course_handler', split_course_key)
        response = self.client.get_html(course_outline_url_split)
        self.assertEqual(response.status_code, 404)

    def test_course_outline_with_display_course_number_as_none(self):
        """
        Tests course outline when 'display_coursenumber' field is none.
        """
        # Change 'display_coursenumber' field to None and update the course.
        self.course.display_coursenumber = None
        updated_course = self.update_course(self.course, self.user.id)

        # Assert that 'display_coursenumber' field has been changed successfully.
        self.assertEqual(updated_course.display_coursenumber, None)

        # Perform GET request on course outline url with the course id.
        course_outline_url = reverse_course_url('course_handler', updated_course.id)
        response = self.client.get_html(course_outline_url)

        # Assert that response code is 200.
        self.assertEqual(response.status_code, 200)

        # Assert that 'display_course_number' is being set to "" (as display_coursenumber was None).
        self.assertIn('display_course_number: ""', response.content)


@ddt.ddt
class TestCourseOutline(CourseTestCase):
    """
    Unit tests for the course outline.
    """
    shard = 1
    ENABLED_SIGNALS = ['course_published']

    def setUp(self):
        """
        Set up the for the course outline tests.
        """
        super(TestCourseOutline, self).setUp()

        self.chapter = ItemFactory.create(
            parent_location=self.course.location, category='chapter', display_name="Week 1"
        )
        self.sequential = ItemFactory.create(
            parent_location=self.chapter.location, category='sequential', display_name="Lesson 1"
        )
        self.vertical = ItemFactory.create(
            parent_location=self.sequential.location, category='vertical', display_name='Subsection 1'
        )
        self.video = ItemFactory.create(
            parent_location=self.vertical.location, category="video", display_name="My Video"
        )

    @ddt.data(True, False)
    def test_json_responses(self, is_concise):
        """
        Verify the JSON responses returned for the course.

        Arguments:
            is_concise (Boolean) : If True, fetch concise version of course outline.
        """
        outline_url = reverse_course_url('course_handler', self.course.id)
        outline_url = outline_url + '?format=concise' if is_concise else outline_url
        resp = self.client.get(outline_url, HTTP_ACCEPT='application/json')
        json_response = json.loads(resp.content)

        # First spot check some values in the root response
        self.assertEqual(json_response['category'], 'course')
        self.assertEqual(json_response['id'], unicode(self.course.location))
        self.assertEqual(json_response['display_name'], self.course.display_name)
        self.assertNotEqual(json_response.get('published', False), is_concise)
        self.assertIsNone(json_response.get('visibility_state'))

        # Now verify the first child
        children = json_response['child_info']['children']
        self.assertGreater(len(children), 0)
        first_child_response = children[0]
        self.assertEqual(first_child_response['category'], 'chapter')
        self.assertEqual(first_child_response['id'], unicode(self.chapter.location))
        self.assertEqual(first_child_response['display_name'], 'Week 1')
        self.assertNotEqual(json_response.get('published', False), is_concise)
        if not is_concise:
            self.assertEqual(first_child_response['visibility_state'], VisibilityState.unscheduled)
        self.assertGreater(len(first_child_response['child_info']['children']), 0)

        # Finally, validate the entire response for consistency
        self.assert_correct_json_response(json_response, is_concise)

    def assert_correct_json_response(self, json_response, is_concise=False):
        """
        Asserts that the JSON response is syntactically consistent
        """
        self.assertIsNotNone(json_response['display_name'])
        self.assertIsNotNone(json_response['id'])
        self.assertIsNotNone(json_response['category'])
        self.assertNotEqual(json_response.get('published', False), is_concise)
        if json_response.get('child_info', None):
            for child_response in json_response['child_info']['children']:
                self.assert_correct_json_response(child_response, is_concise)

    def test_course_outline_initial_state(self):
        course_module = modulestore().get_item(self.course.location)
        course_structure = create_xblock_info(
            course_module,
            include_child_info=True,
            include_children_predicate=lambda xblock: not xblock.category == 'vertical'
        )

        # Verify that None is returned for a non-existent locator
        self.assertIsNone(course_outline_initial_state('no-such-locator', course_structure))

        # Verify that the correct initial state is returned for the test chapter
        chapter_locator = unicode(self.chapter.location)
        initial_state = course_outline_initial_state(chapter_locator, course_structure)
        self.assertEqual(initial_state['locator_to_show'], chapter_locator)
        expanded_locators = initial_state['expanded_locators']
        self.assertIn(unicode(self.sequential.location), expanded_locators)
        self.assertIn(unicode(self.vertical.location), expanded_locators)

    def test_start_date_on_page(self):
        """
        Verify that the course start date is included on the course outline page.
        """
        def _get_release_date(response):
            """Return the release date from the course page"""
            parsed_html = lxml.html.fromstring(response.content)
            return parsed_html.find_class('course-status')[0].find_class('status-release-value')[0].text_content()

        def _assert_settings_link_present(response):
            """
            Asserts there's a course settings link on the course page by the course release date.
            """
            parsed_html = lxml.html.fromstring(response.content)
            settings_link = parsed_html.find_class('course-status')[0].find_class('action-edit')[0].find('a')
            self.assertIsNotNone(settings_link)
            self.assertEqual(settings_link.get('href'), reverse_course_url('settings_handler', self.course.id))

        outline_url = reverse_course_url('course_handler', self.course.id)
        response = self.client.get(outline_url, {}, HTTP_ACCEPT='text/html')

        # A course with the default release date should display as "Unscheduled"
        self.assertEqual(_get_release_date(response), 'Unscheduled')
        _assert_settings_link_present(response)

        self.course.start = datetime.datetime(2014, 1, 1, tzinfo=pytz.utc)
        modulestore().update_item(self.course, ModuleStoreEnum.UserID.test)
        response = self.client.get(outline_url, {}, HTTP_ACCEPT='text/html')

        self.assertEqual(_get_release_date(response), get_default_time_display(self.course.start))
        _assert_settings_link_present(response)

    def _create_test_data(self, course_module, create_blocks=False, publish=True, block_types=None):
        """
        Create data for test.
        """
        if create_blocks:
            for block_type in block_types:
                ItemFactory.create(
                    parent_location=self.vertical.location,
                    category=block_type,
                    display_name='{} Problem'.format(block_type)
                )

            if not publish:
                self.store.unpublish(self.vertical.location, self.user.id)

        course_module.advanced_modules.extend(block_types)

    def _verify_deprecated_info(self, course_id, advanced_modules, info, deprecated_block_types):
        """
        Verify deprecated info.
        """
        expected_blocks = []
        for block_type in deprecated_block_types:
            expected_blocks.append(
                [
                    reverse_usage_url('container_handler', self.vertical.location),
                    '{} Problem'.format(block_type)
                ]
            )

        self.assertEqual(
            info['deprecated_enabled_block_types'],
            [component for component in advanced_modules if component in deprecated_block_types]
        )

        self.assertItemsEqual(info['blocks'], expected_blocks)
        self.assertEqual(
            info['advance_settings_url'],
            reverse_course_url('advanced_settings_handler', course_id)
        )

    @ddt.data(
        [{'publish': True}, ['notes']],
        [{'publish': False}, ['notes']],
        [{'publish': True}, ['notes', 'lti']]
    )
    @ddt.unpack
    def test_verify_deprecated_warning_message(self, publish, block_types):
        """
        Verify deprecated warning info.
        """
        course_module = modulestore().get_item(self.course.location)
        self._create_test_data(course_module, create_blocks=True, block_types=block_types, publish=publish)
        info = _deprecated_blocks_info(course_module, block_types)
        self._verify_deprecated_info(
            course_module.id,
            course_module.advanced_modules,
            info,
            block_types
        )

    @ddt.data(
        (["a", "b", "c"], ["a", "b", "c"]),
        (["a", "b", "c"], ["a", "b", "d"]),
        (["a", "b", "c"], ["a", "d", "e"]),
        (["a", "b", "c"], ["d", "e", "f"])
    )
    @ddt.unpack
    def test_verify_warn_only_on_enabled_modules(self, enabled_block_types, deprecated_block_types):
        """
        Verify that we only warn about block_types that are both deprecated and enabled.
        """
        expected_block_types = list(set(enabled_block_types) & set(deprecated_block_types))
        course_module = modulestore().get_item(self.course.location)
        self._create_test_data(course_module, create_blocks=True, block_types=enabled_block_types)
        info = _deprecated_blocks_info(course_module, deprecated_block_types)
        self._verify_deprecated_info(
            course_module.id,
            course_module.advanced_modules,
            info,
            expected_block_types
        )


class TestCourseReIndex(CourseTestCase):
    """
    Unit tests for the course outline.
    """
    shard = 1
    SUCCESSFUL_RESPONSE = _("Course has been successfully reindexed.")

    ENABLED_SIGNALS = ['course_published']

    def setUp(self):
        """
        Set up the for the course outline tests.
        """

        super(TestCourseReIndex, self).setUp()

        self.course.start = datetime.datetime(2014, 1, 1, tzinfo=pytz.utc)
        modulestore().update_item(self.course, self.user.id)

        self.chapter = ItemFactory.create(
            parent_location=self.course.location, category='chapter', display_name="Week 1"
        )
        self.sequential = ItemFactory.create(
            parent_location=self.chapter.location, category='sequential', display_name="Lesson 1"
        )
        self.vertical = ItemFactory.create(
            parent_location=self.sequential.location, category='vertical', display_name='Subsection 1'
        )
        self.video = ItemFactory.create(
            parent_location=self.vertical.location, category="video", display_name="My Video"
        )

        self.html = ItemFactory.create(
            parent_location=self.vertical.location, category="html", display_name="My HTML",
            data="<div>This is my unique HTML content</div>",

        )

    def test_reindex_course(self):
        """
        Verify that course gets reindexed.
        """
        index_url = reverse_course_url('course_search_index_handler', self.course.id)
        response = self.client.get(index_url, {}, HTTP_ACCEPT='application/json')

        # A course with the default release date should display as "Unscheduled"
        self.assertIn(self.SUCCESSFUL_RESPONSE, response.content)
        self.assertEqual(response.status_code, 200)

        response = self.client.post(index_url, {}, HTTP_ACCEPT='application/json')
        self.assertEqual(response.content, '')
        self.assertEqual(response.status_code, 405)

        self.client.logout()
        response = self.client.get(index_url, {}, HTTP_ACCEPT='application/json')
        self.assertEqual(response.status_code, 302)

    def test_negative_conditions(self):
        """
        Test the error conditions for the access
        """
        index_url = reverse_course_url('course_search_index_handler', self.course.id)
        # register a non-staff member and try to delete the course branch
        non_staff_client, _ = self.create_non_staff_authed_user_client()
        response = non_staff_client.get(index_url, {}, HTTP_ACCEPT='application/json')
        self.assertEqual(response.status_code, 403)

    def test_empty_content_type(self):
        """
        Test json content type is set if '' is selected
        """
        index_url = reverse_course_url('course_search_index_handler', self.course.id)
        response = self.client.get(index_url, {}, CONTENT_TYPE='')

        # A course with the default release date should display as "Unscheduled"
        self.assertIn(self.SUCCESSFUL_RESPONSE, response.content)
        self.assertEqual(response.status_code, 200)

    @mock.patch('xmodule.html_module.HtmlDescriptor.index_dictionary')
    def test_reindex_course_search_index_error(self, mock_index_dictionary):
        """
        Test json response with mocked error data for html
        """

        # set mocked exception response
        err = SearchIndexingError
        mock_index_dictionary.return_value = err

        index_url = reverse_course_url('course_search_index_handler', self.course.id)

        # Start manual reindex and check error in response
        response = self.client.get(index_url, {}, HTTP_ACCEPT='application/json')
        self.assertEqual(response.status_code, 500)

    def test_reindex_json_responses(self):
        """
        Test json response with real data
        """
        # results are indexed because they are published from ItemFactory
        response = perform_search(
            "unique",
            user=self.user,
            size=10,
            from_=0,
            course_id=unicode(self.course.id))
        self.assertEqual(response['total'], 1)

        # Start manual reindex
        reindex_course_and_check_access(self.course.id, self.user)

        # Check results remain the same
        response = perform_search(
            "unique",
            user=self.user,
            size=10,
            from_=0,
            course_id=unicode(self.course.id))
        self.assertEqual(response['total'], 1)

    @mock.patch('xmodule.video_module.VideoDescriptor.index_dictionary')
    def test_reindex_video_error_json_responses(self, mock_index_dictionary):
        """
        Test json response with mocked error data for video
        """
        # results are indexed because they are published from ItemFactory
        response = perform_search(
            "unique",
            user=self.user,
            size=10,
            from_=0,
            course_id=unicode(self.course.id))
        self.assertEqual(response['total'], 1)

        # set mocked exception response
        err = SearchIndexingError
        mock_index_dictionary.return_value = err

        # Start manual reindex and check error in response
        with self.assertRaises(SearchIndexingError):
            reindex_course_and_check_access(self.course.id, self.user)

    @mock.patch('xmodule.html_module.HtmlDescriptor.index_dictionary')
    def test_reindex_html_error_json_responses(self, mock_index_dictionary):
        """
        Test json response with mocked error data for html
        """
        # results are indexed because they are published from ItemFactory
        response = perform_search(
            "unique",
            user=self.user,
            size=10,
            from_=0,
            course_id=unicode(self.course.id))
        self.assertEqual(response['total'], 1)

        # set mocked exception response
        err = SearchIndexingError
        mock_index_dictionary.return_value = err

        # Start manual reindex and check error in response
        with self.assertRaises(SearchIndexingError):
            reindex_course_and_check_access(self.course.id, self.user)

    @mock.patch('xmodule.seq_module.SequenceDescriptor.index_dictionary')
    def test_reindex_seq_error_json_responses(self, mock_index_dictionary):
        """
        Test json response with mocked error data for sequence
        """
        # results are indexed because they are published from ItemFactory
        response = perform_search(
            "unique",
            user=self.user,
            size=10,
            from_=0,
            course_id=unicode(self.course.id))
        self.assertEqual(response['total'], 1)

        # set mocked exception response
        err = Exception
        mock_index_dictionary.return_value = err

        # Start manual reindex and check error in response
        with self.assertRaises(SearchIndexingError):
            reindex_course_and_check_access(self.course.id, self.user)

    @mock.patch('xmodule.modulestore.mongo.base.MongoModuleStore.get_course')
    def test_reindex_no_item(self, mock_get_course):
        """
        Test system logs an error if no item found.
        """
        # set mocked exception response
        err = ItemNotFoundError
        mock_get_course.return_value = err

        # Start manual reindex and check error in response
        with self.assertRaises(SearchIndexingError):
            reindex_course_and_check_access(self.course.id, self.user)

    def test_reindex_no_permissions(self):
        # register a non-staff member and try to delete the course branch
        user2 = UserFactory()
        with self.assertRaises(PermissionDenied):
            reindex_course_and_check_access(self.course.id, user2)

    def test_indexing_responses(self):
        """
        Test do_course_reindex response with real data
        """
        # results are indexed because they are published from ItemFactory
        response = perform_search(
            "unique",
            user=self.user,
            size=10,
            from_=0,
            course_id=unicode(self.course.id))
        self.assertEqual(response['total'], 1)

        # Start manual reindex
        CoursewareSearchIndexer.do_course_reindex(modulestore(), self.course.id)

        # Check results are the same following reindex
        response = perform_search(
            "unique",
            user=self.user,
            size=10,
            from_=0,
            course_id=unicode(self.course.id))
        self.assertEqual(response['total'], 1)

    @mock.patch('xmodule.video_module.VideoDescriptor.index_dictionary')
    def test_indexing_video_error_responses(self, mock_index_dictionary):
        """
        Test do_course_reindex response with mocked error data for video
        """
        # results are indexed because they are published from ItemFactory
        response = perform_search(
            "unique",
            user=self.user,
            size=10,
            from_=0,
            course_id=unicode(self.course.id))
        self.assertEqual(response['total'], 1)

        # set mocked exception response
        err = Exception
        mock_index_dictionary.return_value = err

        # Start manual reindex and check error in response
        with self.assertRaises(SearchIndexingError):
            CoursewareSearchIndexer.do_course_reindex(modulestore(), self.course.id)

    @mock.patch('xmodule.html_module.HtmlDescriptor.index_dictionary')
    def test_indexing_html_error_responses(self, mock_index_dictionary):
        """
        Test do_course_reindex response with mocked error data for html
        """
        # results are indexed because they are published from ItemFactory
        response = perform_search(
            "unique",
            user=self.user,
            size=10,
            from_=0,
            course_id=unicode(self.course.id))
        self.assertEqual(response['total'], 1)

        # set mocked exception response
        err = Exception
        mock_index_dictionary.return_value = err

        # Start manual reindex and check error in response
        with self.assertRaises(SearchIndexingError):
            CoursewareSearchIndexer.do_course_reindex(modulestore(), self.course.id)

    @mock.patch('xmodule.seq_module.SequenceDescriptor.index_dictionary')
    def test_indexing_seq_error_responses(self, mock_index_dictionary):
        """
        Test do_course_reindex response with mocked error data for sequence
        """
        # results are indexed because they are published from ItemFactory
        response = perform_search(
            "unique",
            user=self.user,
            size=10,
            from_=0,
            course_id=unicode(self.course.id))
        self.assertEqual(response['total'], 1)

        # set mocked exception response
        err = Exception
        mock_index_dictionary.return_value = err

        # Start manual reindex and check error in response
        with self.assertRaises(SearchIndexingError):
            CoursewareSearchIndexer.do_course_reindex(modulestore(), self.course.id)

    @mock.patch('xmodule.modulestore.mongo.base.MongoModuleStore.get_course')
    def test_indexing_no_item(self, mock_get_course):
        """
        Test system logs an error if no item found.
        """
        # set mocked exception response
        err = ItemNotFoundError
        mock_get_course.return_value = err

        # Start manual reindex and check error in response
        with self.assertRaises(SearchIndexingError):
            CoursewareSearchIndexer.do_course_reindex(modulestore(), self.course.id)

"""
Tests for the plugin API
"""

from django.test import TestCase
from nose.plugins.attrib import attr

from openedx.core.lib.plugins import PluginError
from openedx.core.lib.course_tabs import CourseTabPluginManager


@attr(shard=2)
class TestCourseTabApi(TestCase):
    """
    Unit tests for the course tab plugin API
    """

    def test_get_plugin(self):
        """
        Verify that get_plugin works as expected.
        """
        tab_type = CourseTabPluginManager.get_plugin("progress")
        self.assertEqual(tab_type.title, "Progress")

        with self.assertRaises(PluginError):
            CourseTabPluginManager.get_plugin("no_such_type")

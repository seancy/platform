"""
Tests for site configuration's django models.
"""
from mock import patch

from django.test import TestCase
from django.db import IntegrityError, transaction
from django.contrib.sites.models import Site

from openedx.core.djangoapps.site_configuration.models import SiteConfigurationHistory, SiteConfiguration
from openedx.core.djangoapps.site_configuration.tests.factories import SiteConfigurationFactory


class SiteConfigurationTests(TestCase):
    """
    Tests for SiteConfiguration and its signals/receivers.
    """
    domain = 'site_configuration_post_save_receiver_example.com'
    name = 'site_configuration_post_save_receiver_example'

    test_config1 = {
        "university": "Test University",
        "PLATFORM_NAME": "Test Education Program",
        "SITE_NAME": "test.localhost",
        "course_org_filter": "TestX",
        "css_overrides_file": "test/css/site.css",
        "ENABLE_MKTG_SITE": False,
        "ENABLE_THIRD_PARTY_AUTH": False,
        "course_about_show_social_links": False,
        "favicon_path": "/static/test.ico",
    }

    test_config2 = {
        "university": "Test Another University",
        "PLATFORM_NAME": "Test Another Education Program",
        "SITE_NAME": "test-another.localhost",
        "course_org_filter": "TestAnotherX",
        "css_overrides_file": "test-another/css/site.css",
        "ENABLE_MKTG_SITE": True,
        "ENABLE_THIRD_PARTY_AUTH": True,
        "course_about_show_social_links": False,
        "favicon_path": "/static/test-another.ico",
    }

    @classmethod
    def setUpClass(cls):
        super(SiteConfigurationTests, cls).setUpClass()
        cls.site, _ = Site.objects.get_or_create(domain=cls.domain, name=cls.domain)
        cls.site2, _ = Site.objects.get_or_create(
            domain=cls.test_config2['SITE_NAME'],
            name=cls.test_config2['SITE_NAME'],
        )

    def test_site_configuration_post_save_receiver(self):
        """
        Test that and entry is added to SiteConfigurationHistory model each time a new
        SiteConfiguration is added.
        """
        # add SiteConfiguration to database
        site_configuration = SiteConfigurationFactory.create(
            site=self.site,
        )

        # Verify an entry to SiteConfigurationHistory was added.
        site_configuration_history = SiteConfigurationHistory.objects.filter(
            site=site_configuration.site,
        ).all()

        # Make sure an entry (and only one entry) is saved for SiteConfiguration
        self.assertEqual(len(site_configuration_history), 1)

    def test_site_configuration_post_update_receiver(self):
        """
        Test that and entry is added to SiteConfigurationHistory each time a
        SiteConfiguration is updated.
        """
        # add SiteConfiguration to database
        site_configuration = SiteConfigurationFactory.create(
            site=self.site,
        )

        site_configuration.values = {'test': 'test'}
        site_configuration.save()

        # Verify an entry to SiteConfigurationHistory was added.
        site_configuration_history = SiteConfigurationHistory.objects.filter(
            site=site_configuration.site,
        ).all()

        # Make sure two entries (one for save and one for update) are saved for SiteConfiguration
        self.assertEqual(len(site_configuration_history), 2)

    def test_no_entry_is_saved_for_errors(self):
        """
        Test that and entry is not added to SiteConfigurationHistory if there is an error while
        saving SiteConfiguration.
        """
        # add SiteConfiguration to database
        site_configuration = SiteConfigurationFactory.create(
            site=self.site,
        )

        # Verify an entry to SiteConfigurationHistory was added.
        site_configuration_history = SiteConfigurationHistory.objects.filter(
            site=site_configuration.site,
        ).all()

        # Make sure entry is saved if there is no error
        self.assertEqual(len(site_configuration_history), 1)

        with transaction.atomic():
            with self.assertRaises(IntegrityError):
                # try to add a duplicate entry
                site_configuration = SiteConfigurationFactory.create(
                    site=self.site,
                )
        site_configuration_history = SiteConfigurationHistory.objects.filter(
            site=site_configuration.site,
        ).all()

        # Make sure no entry is saved if there an error
        self.assertEqual(len(site_configuration_history), 1)

    def test_get_value(self):
        """
        Test that get_value returns correct value for any given key.
        """
        # add SiteConfiguration to database
        site_configuration = SiteConfigurationFactory.create(
            site=self.site,
            values=self.test_config1,
        )

        # Make sure entry is saved and retrieved correctly
        self.assertEqual(site_configuration.get_value("university"), self.test_config1['university'])
        self.assertEqual(site_configuration.get_value("PLATFORM_NAME"), self.test_config1['PLATFORM_NAME'])
        self.assertEqual(site_configuration.get_value("SITE_NAME"), self.test_config1['SITE_NAME'])
        self.assertEqual(site_configuration.get_value("course_org_filter"), self.test_config1['course_org_filter'])
        self.assertEqual(site_configuration.get_value("css_overrides_file"), self.test_config1['css_overrides_file'])
        self.assertEqual(site_configuration.get_value("ENABLE_MKTG_SITE"), self.test_config1['ENABLE_MKTG_SITE'])
        self.assertEqual(site_configuration.get_value("favicon_path"), self.test_config1['favicon_path'])
        self.assertEqual(
            site_configuration.get_value("ENABLE_THIRD_PARTY_AUTH"),
            self.test_config1['ENABLE_THIRD_PARTY_AUTH'],
        )
        self.assertEqual(
            site_configuration.get_value("course_about_show_social_links"),
            self.test_config1['course_about_show_social_links'],
        )

        # Test that the default value is returned if the value for the given key is not found in the configuration
        self.assertEqual(
            site_configuration.get_value("non_existent_name", "dummy-default-value"),
            "dummy-default-value",
        )

        # Test that the default value is returned if Site configuration is not enabled
        site_configuration.enabled = False
        site_configuration.save()

        self.assertEqual(site_configuration.get_value("university"), None)
        self.assertEqual(
            site_configuration.get_value("PLATFORM_NAME", "Default Platform Name"),
            "Default Platform Name",
        )
        self.assertEqual(site_configuration.get_value("SITE_NAME", "Default Site Name"), "Default Site Name")

    def test_invalid_data_error_on_get_value(self):
        """
        Test that get_value logs an error if json data is not valid.
        """
        # import logger, for patching
        from openedx.core.djangoapps.site_configuration.models import logger
        invalid_data = [self.test_config1]

        # add SiteConfiguration to database
        site_configuration = SiteConfigurationFactory.create(
            site=self.site,
            values=invalid_data,
        )

        # make sure get_value logs an error for invalid json data
        with patch.object(logger, "exception") as mock_logger:
            self.assertEqual(site_configuration.get_value("university"), None)
            self.assertTrue(mock_logger.called)

        # make sure get_value returns default_value for invalid json data
        with patch.object(logger, "exception") as mock_logger:
            value = site_configuration.get_value("PLATFORM_NAME", "Default Platform Name")
            self.assertTrue(mock_logger.called)
            self.assertEqual(value, "Default Platform Name")

    def test_get_value_for_org(self):
        """
        Test that get_value_for_org returns correct value for any given key.
        """
        # add SiteConfiguration to database
        SiteConfigurationFactory.create(
            site=self.site,
            values=self.test_config1,
        )
        SiteConfigurationFactory.create(
            site=self.site2,
            values=self.test_config2,
        )

        # Make sure entry is saved and retrieved correctly
        self.assertEqual(
            SiteConfiguration.get_value_for_org(self.test_config1['course_org_filter'], "university"),
            self.test_config1['university'],
        )
        self.assertEqual(
            SiteConfiguration.get_value_for_org(self.test_config1['course_org_filter'], "PLATFORM_NAME"),
            self.test_config1['PLATFORM_NAME'],
        )
        self.assertEqual(
            SiteConfiguration.get_value_for_org(self.test_config1['course_org_filter'], "SITE_NAME"),
            self.test_config1['SITE_NAME'],
        )
        self.assertEqual(
            SiteConfiguration.get_value_for_org(self.test_config1['course_org_filter'], "css_overrides_file"),
            self.test_config1['css_overrides_file'],
        )
        self.assertEqual(
            SiteConfiguration.get_value_for_org(self.test_config1['course_org_filter'], "ENABLE_MKTG_SITE"),
            self.test_config1['ENABLE_MKTG_SITE'],
        )

        # Make sure entry is saved and retrieved correctly
        self.assertEqual(
            SiteConfiguration.get_value_for_org(self.test_config2['course_org_filter'], "university"),
            self.test_config2['university'],
        )
        self.assertEqual(
            SiteConfiguration.get_value_for_org(self.test_config2['course_org_filter'], "PLATFORM_NAME"),
            self.test_config2['PLATFORM_NAME'],
        )
        self.assertEqual(
            SiteConfiguration.get_value_for_org(self.test_config2['course_org_filter'], "SITE_NAME"),
            self.test_config2['SITE_NAME'],
        )
        self.assertEqual(
            SiteConfiguration.get_value_for_org(self.test_config2['course_org_filter'], "css_overrides_file"),
            self.test_config2['css_overrides_file'],
        )
        self.assertEqual(
            SiteConfiguration.get_value_for_org(self.test_config2['course_org_filter'], "ENABLE_MKTG_SITE"),
            self.test_config2['ENABLE_MKTG_SITE'],
        )

        # Test that the default value is returned if the value for the given key is not found in the configuration
        self.assertEqual(
            SiteConfiguration.get_value_for_org(
                self.test_config1['course_org_filter'],
                "non-existent",
                "dummy-default-value"),
            "dummy-default-value",
        )

        # Test that the default value is returned if the value for the given key is not found in the configuration
        self.assertEqual(
            SiteConfiguration.get_value_for_org(
                self.test_config2['course_org_filter'],
                "non-existent",
                "dummy-default-value"),
            "dummy-default-value",
        )

        # Test that the default value is returned if org is not found in the configuration
        self.assertEqual(
            SiteConfiguration.get_value_for_org(
                "non-existent-org",
                "PLATFORM_NAME",
                "dummy-default-value"),
            "dummy-default-value",
        )

    def test_get_all_orgs(self):
        """
        Test that get_all_orgs returns all orgs from site configuration.
        """
        expected_orgs = [self.test_config1['course_org_filter'], self.test_config2['course_org_filter']]
        # add SiteConfiguration to database
        SiteConfigurationFactory.create(
            site=self.site,
            values=self.test_config1,
        )
        SiteConfigurationFactory.create(
            site=self.site2,
            values=self.test_config2,
        )

        # Test that the default value is returned if the value for the given key is not found in the configuration
        self.assertListEqual(
            list(SiteConfiguration.get_all_orgs()),
            expected_orgs,
        )

    def test_get_all_orgs_returns_only_enabled(self):
        """
        Test that get_all_orgs returns only those orgs whose configurations are enabled.
        """
        expected_orgs = [self.test_config2['course_org_filter']]
        # add SiteConfiguration to database
        SiteConfigurationFactory.create(
            site=self.site,
            values=self.test_config1,
            enabled=False,
        )
        SiteConfigurationFactory.create(
            site=self.site2,
            values=self.test_config2,
        )

        # Test that the default value is returned if the value for the given key is not found in the configuration
        self.assertListEqual(
            list(SiteConfiguration.get_all_orgs()),
            expected_orgs,
        )

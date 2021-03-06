""" Overrides for Docker-based devstack. """

from .devstack import *  # pylint: disable=wildcard-import, unused-wildcard-import

# Docker does not support the syslog socket at /dev/log. Rely on the console.
LOGGING['handlers']['local'] = LOGGING['handlers']['tracking'] = {
    'class': 'logging.NullHandler',
}

LOGGING['loggers']['tracking']['handlers'] = ['console']

LMS_BASE = 'edx.devstack.lms:18000'
CMS_BASE = 'edx.devstack.studio:18010'
SITE_NAME = LMS_BASE
LMS_ROOT_URL = 'http://{}'.format(LMS_BASE)
LMS_INTERNAL_ROOT_URL = LMS_ROOT_URL

ECOMMERCE_PUBLIC_URL_ROOT = 'http://localhost:18130'
ECOMMERCE_API_URL = 'http://edx.devstack.ecommerce:18130/api/v2'

COMMENTS_SERVICE_URL = 'http://edx.devstack.forum:4567'

ENTERPRISE_API_URL = '{}/enterprise/api/v1/'.format(LMS_INTERNAL_ROOT_URL)

CREDENTIALS_INTERNAL_SERVICE_URL = 'http://edx.devstack.credentials:18150'
CREDENTIALS_PUBLIC_SERVICE_URL = 'http://localhost:18150'

OAUTH_OIDC_ISSUER = '{}/oauth2'.format(LMS_ROOT_URL)

DEFAULT_JWT_ISSUER = {
    'ISSUER': OAUTH_OIDC_ISSUER,
    'SECRET_KEY': 'lms-secret',
    'AUDIENCE': 'lms-key',
}
JWT_AUTH.update({
    'JWT_ISSUER': DEFAULT_JWT_ISSUER['ISSUER'],
    'JWT_AUDIENCE': DEFAULT_JWT_ISSUER['AUDIENCE'],
    'JWT_ISSUERS': [
        DEFAULT_JWT_ISSUER,
        RESTRICTED_APPLICATION_JWT_ISSUER,
    ],
})

FEATURES.update({
    'ALLOW_AUTOMATED_SIGNUPS': True,
    'AUTOMATIC_AUTH_FOR_TESTING': True,
    'BATCH_ENROLLMENT_NOTIFY_USERS_DEFAULT': False,
    'COURSES_ARE_BROWSABLE': True,
    'ENABLE_COMBINED_LOGIN_REGISTRATION': True,
    'ENABLE_COURSEWARE_SEARCH': True,
    'ENABLE_COURSE_DISCOVERY': True,
    'ENABLE_COURSEWARE_INDEX': True,
    'ENABLE_DASHBOARD_SEARCH': False,
    'ENABLE_DISCUSSION_SERVICE': True,
    'ENABLE_LAST_ACTIVITY': True,
    'ENABLE_OAUTH2_PROVIDER': True,
    'ENABLE_THIRD_PARTY_AUTH': True,
    'ENFORCE_PASSWORD_POLICY': True,
    'SHOW_HEADER_LANGUAGE_SELECTOR': True,
    'SHOW_FOOTER_LANGUAGE_SELECTOR': True,
    'ENABLE_ENTERPRISE_INTEGRATION': False,
    'ENABLE_UNENROLLMENT_TRACKING': True,
    'ENABLE_EXTERNAL_CATALOG': True
})

ENABLE_MKTG_SITE = os.environ.get('ENABLE_MARKETING_SITE', False)
MARKETING_SITE_ROOT = os.environ.get('MARKETING_SITE_ROOT', 'http://localhost:8080')

MKTG_URLS = {
    'ABOUT': '/about',
    'ACCESSIBILITY': '/accessibility',
    'AFFILIATES': '/affiliate-program',
    'BLOG': '/blog',
    'CAREERS': '/careers',
    'CONTACT': '/support/contact_us',
    'COURSES': '/course',
    'DONATE': '/donate',
    'ENTERPRISE': '/enterprise',
    'FAQ': '/student-faq',
    'HONOR': '/edx-terms-service',
    'HOW_IT_WORKS': '/how-it-works',
    'MEDIA_KIT': '/media-kit',
    'NEWS': '/news-announcements',
    'PRESS': '/press',
    'PRIVACY': '/edx-privacy-policy',
    'ROOT': MARKETING_SITE_ROOT,
    'SCHOOLS': '/schools-partners',
    'SITE_MAP': '/sitemap',
    'TRADEMARKS': '/trademarks',
    'TOS': '/edx-terms-service',
    'TOS_AND_HONOR': '/edx-terms-service',
    'WHAT_IS_VERIFIED_CERT': '/verified-certificate',
}

CREDENTIALS_SERVICE_USERNAME = 'credentials_worker'

COURSE_CATALOG_API_URL = 'http://edx.devstack.discovery:18381/api/v1/'

COURSE_ABOUT_VISIBILITY_PERMISSION = "see_private_about_page"

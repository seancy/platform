from django.conf import settings

# default settings
EDFLEX_CLIENT_ID = settings.XBLOCK_SETTINGS.get('EdflexXBlock', {}).get('EDFLEX_CLIENT_ID')
EDFLEX_CLIENT_SECRET = settings.XBLOCK_SETTINGS.get('EdflexXBlock', {}).get('EDFLEX_CLIENT_SECRET')
EDFLEX_LOCALE = settings.XBLOCK_SETTINGS.get('EdflexXBlock', {}).get('EDFLEX_LOCALE', ['en'])
EDFLEX_BASE_API_URL = settings.XBLOCK_SETTINGS.get('EdflexXBlock', {}).get('EDFLEX_BASE_API_URL')


def get_edflex_configuration():
    return {
        'client_id': EDFLEX_CLIENT_ID,
        'client_secret': EDFLEX_CLIENT_SECRET,
        'locale': EDFLEX_LOCALE,
        'base_api_url': EDFLEX_BASE_API_URL
    }

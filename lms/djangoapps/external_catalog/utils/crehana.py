from django.conf import settings

# default settings
CREHANA_CLIENT_KEY = settings.AUTH_TOKENS.get('CREHANA_API', {}).get('CREHANA_CLIENT_KEY')
CREHANA_CLIENT_SECRET = settings.AUTH_TOKENS.get('CREHANA_API', {}).get('CREHANA_CLIENT_SECRET')
CREHANA_CLIENT_SLUG = settings.AUTH_TOKENS.get('CREHANA_API', {}).get('CREHANA_CLIENT_SLUG')
CREHANA_BASE_API_URL = settings.AUTH_TOKENS.get('CREHANA_API', {}).get('CREHANA_BASE_API_URL')


def get_crehana_configuration():
    return {
        'client_key': CREHANA_CLIENT_KEY,
        'client_secret': CREHANA_CLIENT_SECRET,
        'client_slug': CREHANA_CLIENT_SLUG,
        'base_api_url': CREHANA_BASE_API_URL,
    }

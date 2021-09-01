from django.conf import settings

# default settings
ANDERSPINK_CLIENT_KEY = settings.AUTH_TOKENS.get('ANDERSPINK_API', {}).get('ANDERSPINK_CLIENT_KEY')
ANDERSPINK_CLIENT_TIME = settings.AUTH_TOKENS.get('ANDERSPINK_API', {}).get('ANDERSPINK_CLIENT_TIME', '3-days')
ANDERSPINK_BASE_API_URL = settings.AUTH_TOKENS.get('ANDERSPINK_API', {}).get('ANDERSPINK_BASE_API_URL', 'https://anderspink.com/api/v3/')
IS_BOARD_ENABLED = settings.AUTH_TOKENS.get('ANDERSPINK_API', {}).get('IS_BOARD_ENABLED',False)


def get_anderspink_configuration():
    return {
        'api_key': ANDERSPINK_CLIENT_KEY,
        'base_url': ANDERSPINK_BASE_API_URL,
        'api_time': ANDERSPINK_CLIENT_TIME,
        'is_board_enabled': IS_BOARD_ENABLED
    }

from django.core.management.base import BaseCommand
from datetime import datetime
from traceback import format_exc

from ...api import AnderspinkResourcesSynchronizer
from django.core.exceptions import ImproperlyConfigured
from lms.djangoapps.external_catalog.utils import ExternalCatalogLogger
from ...tasks import log
from ...utils import get_anderspink_configuration


# logger = ExternalCatalogLogger(r'anderspink_external_catalog_update.log').logger


class Command(BaseCommand):
    help = 'Sync. briefing from anderspink briefing provider into mysql.'

    def _sync_briefing(self):
        anderspink_configuration = get_anderspink_configuration()
        if not all(
                list(anderspink_configuration.values())
        ):
            raise ImproperlyConfigured(
                'In order to use API for Anderspink of the followings must be configured: '
                'ANDERSPINK_CLIENT_KEY, ANDERSPINK_BASE_API_URL'
            )

        AnderspinkResourcesSynchronizer(
            api_key=anderspink_configuration['api_key'],
            base_api_url=anderspink_configuration['base_url'],
            api_time=anderspink_configuration['api_time']
        ).run()

    def handle(self, *args, **options):
        try:
            log.info(r'Starting requesting the anderspink briefing data...')

            start_time = datetime.now()
            self._sync_briefing()

            log.info(r'Finished all requests after {}'.format(datetime.now() - start_time))
        except Exception:
            log.error('Unknow exception occured in script, Traceback ===> {}'.format(format_exc()))


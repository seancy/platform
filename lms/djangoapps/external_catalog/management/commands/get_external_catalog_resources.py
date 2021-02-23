from django.core.management.base import BaseCommand

import logging
from datetime import datetime
import time
from lms.djangoapps.external_catalog.tasks import get_resources


logger = logging.getLogger("external_catalog")
log_handler = logging.handlers.TimedRotatingFileHandler('/edx/var/log/lms/edflex_external_catalog_update.log',
                                                         when='D',
                                                         interval=10,
                                                         backupCount=4,
                                                         encoding='utf-8')
log_formatter = logging.Formatter(u'%(asctime)s [%(name)s] [%(filename)s:%(lineno)d] %(levelname)s  - %(message)s')
log_formatter.converter = time.gmtime
log_handler.setFormatter(log_formatter)
log_handler.setLevel(logging.INFO)
logger.addHandler(log_handler)

class Command(BaseCommand):
    help = 'Get resources from external provider'

    def handle(self, *args, **options):
        logger.info(u"Starting requesting the catalog data...")
        start_time = datetime.now()

        get_resources()

        logger.info(u"Finished all requests after {}".format(datetime.now() - start_time))

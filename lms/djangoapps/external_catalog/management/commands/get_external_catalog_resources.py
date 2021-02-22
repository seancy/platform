from django.core.management.base import BaseCommand

import logging
from datetime import datetime
from lms.djangoapps.external_catalog.tasks import get_resources


logger = logging.getLogger("external_catalog")


class Command(BaseCommand):
    help = 'Get resources from external provider'

    def handle(self, *args, **options):
        logger.info(u"Starting requesting the catalog data...")
        start_time = datetime.now()

        get_resources()

        logger.info(u"Finished all requests after {}".format(datetime.now() - start_time))

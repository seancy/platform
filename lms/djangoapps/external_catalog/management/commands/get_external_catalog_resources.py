from django.core.management.base import BaseCommand

from lms.djangoapps.external_catalog.tasks import get_resources

class Command(BaseCommand):
    help = 'Get resources from external provider'

    def handle(self, *args, **options):
        get_resources()

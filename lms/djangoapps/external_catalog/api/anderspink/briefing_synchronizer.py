from django.db import transaction
from dateutil.parser import parse
from django.db import IntegrityError
from lms.djangoapps.external_catalog.utils import ExternalCatalogLogger
from ...models import AndersPinkArticle
from ...models import AndersPinkBriefing
from .briefing_downloader import AndersPinkDataCache
from ..utils import print_error_arguments


log = ExternalCatalogLogger.getLoggerByName()


class BriefingSynchronizer(object):
    """Download & Save resources from crehana server into mysql"""
    def __init__(self, api_key, base_api_url, api_time):
        self.__data_cache = AndersPinkDataCache(
            api_key,
            base_api_url,
            api_time
        )

        self.__time_of_first_inserting = None


    @print_error_arguments
    def _save_article(self, articles):
        """Write into table `briefing` & `article`"""
        for article in articles['data'].get('articles', ()):

            try:
                model_article, _ = AndersPinkArticle.objects.update_or_create(
                    title_id=article['id'],
                    defaults={
                        'title': article['title'],
                        'image': article['image'],
                        'date_published': article['date_published'],
                        'url': article['url'],
                        'author': article['author'] if article.get('author', None) else None,
                        'language': article['language'],
                        'reading_time': article['reading_time'] if article.get('reading_time', None) else None,
                    },
                )
                briefing = AndersPinkBriefing.objects.get(briefing_id=int(articles['data']['id']))
                model_article.briefing_id = briefing
                model_article.save()
                log.info(u"Updated: Article ({id})".format(id=article['id']))
            except KeyError as e:
                log.error(u"%s doesn't exist for article: %s" % (e, article['id']))
                continue
            except IntegrityError as e:
                log.error(u"Database IntegrityError: %s" % str(e))
                continue


    @print_error_arguments
    def _save_briefing(self, briefings):
        for briefing in briefings:
            model_briefing, _ = AndersPinkBriefing.objects.update_or_create(
                briefing_id=briefing['id'],
                defaults={
                    'name': briefing['name'],
                }
            )
            log.info(u"Updated: Briefing ({id})".format(id=briefing['id']))


    def run(self):
        """Download data from server & store the data into mysql."""
        log.info('Anderspink briefing synchronizer is running...')
        self.__data_cache.download()

        with transaction.atomic():
            log.info('Saving Anderspink Briefings..........')
            self._save_briefing(self.__data_cache.briefings)
            log.info('Anderspink Briefings Saved!!!!!!!!!!!!!!')

        with transaction.atomic():
            log.info('Saving Anderspink Articles..........')
            for article in self.__data_cache.articles:
                self._save_article(article)
            log.info('Anderspink Articles Saved!!!!!!!!!!!!!!')

        log.info('Anderspink briefing synchronizer quit.')

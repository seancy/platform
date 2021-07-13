"""A wrapper of Anderspink B2B Api : `AnderspinkClient`
"""
from requests import get as _http_get
from urlparse import urljoin

from lms.djangoapps.external_catalog.utils import ExternalCatalogLogger
from .basic_accessor import BasicBriefingAccessor as _BasicBriefingAccessor
from ..utils import exception_retry

log = ExternalCatalogLogger.getLoggerByName()


class AndersPinkDownloader(_BasicBriefingAccessor):
    """
    Client to consume Anderspink service API.
    """

    def __init__(self, api_key, base_api_url, api_time):
        super(AndersPinkDownloader, self).__init__(api_key, base_api_url, api_time)
        self.base_api_url = base_api_url
        self.api_time = api_time

        

    @exception_retry(retry_times=3)
    def get_briefings(self):
        response = _http_get(
            url=urljoin(
                self.base_api_url,
                'briefings'
            ), headers=self._headers
        )
        return self._validate_and_return(response)

    @exception_retry(retry_times=3)
    def get_articles(self, limit, offset, time, briefing):
        """Create a anders pink user with parameters & Return User Info."""
        # article_list = []

        url = urljoin(
            self.base_api_url,
            'briefings/{id}?limit={limit}&offset={offset}&time={time}'.format(id=briefing["id"], limit=limit,
                                                                              offset=offset, time=time),
        )
        response = _http_get(url, headers=self._headers)
        # response =
        # article_list.append(response)

        return self._validate_and_return(response)


class AndersPinkDataCache(AndersPinkDownloader):
    """A cache of AndersPink `briefings/articles`"""
    FETCH_BATCH_SIZE = 50

    def __init__(self, api_key, base_api_url, api_time):
        super(AndersPinkDataCache, self).__init__(
            api_key, base_api_url, api_time
        )
        self._briefing_cache = []
        self._article_cache = []
        self.TIME = api_time


    def download(self):
        """
            Downloading resources from anderspink server

            *** Throw exception if still get error while downloading after retry ***
        """
        log.info('Anderspink briefing is downloading...')
        # Caching for `briefing`
        # self._briefing_cache = self.fetch_all_briefings()

        # Caching for `article`
        briefings = self.get_briefings()
        log.info(
            'Downloaded, briefing count = {}'.format(
                len(briefings)
            )
        )
        self._briefing_cache.append(briefings)

        for briefing in self._briefing_cache[0]['data'].get("owned_briefings", ()):
            for i in range(0, 0xffff, self.FETCH_BATCH_SIZE):
                try:
                    articles = self.get_articles(
                    self.FETCH_BATCH_SIZE, i, self.TIME, briefing)
                    if not articles['data'].get('articles', ()):
                        break

                    self._article_cache.append(articles)
                except Exception as e:
                    log.info(str(e))

        #         log.info('Articles = {}'.format(self._article_cache))
        # log.info(
        #     'Downloaded, briefing count = {}, article count = {}'.format(
        #         len(self._briefing_cache), len(self._article_cache)
        #     )
        # )

    @property
    def briefings(self):
        """briefings cache"""
        return self._briefing_cache

    @property
    def articles(self):
        """articles cache"""
        return self._article_cache

from .edflex import (
    edflex_catalog,
    edflex_catalog_handler,
    edflex_courses_handler
)
from .crehana.courses import (
    Data as CrehanaCoursesData,
    SearchPage as CrehanaCoursesSearchPage
)
from .crehana.overview import OverviewPage as CoursesOverviewPage
from .crehana.third_party import ThirdPartyRedirectionPage as CrehanaSSORedirectionPage

from .anderspink.articles import (
    Data as AndersPinkData,
    SearchPage as AndersPinkSearchPage
)

define([
    'edx-ui-toolkit/js/utils/date-utils'
], function(DateUtils) {
    function formatDate(date, userLanguage, userTimezone) {
        var context;
        context = {
            datetime: date,
            language: userLanguage,
            timezone: userTimezone,
            format: DateUtils.dateFormatEnum.shortDate
        };
        return DateUtils.localize(context);
    }

    return { DateUtils, formatDate };

});


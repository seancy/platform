(function(define) {
    'use strict';
    define([
        'jquery',
        'underscore',
        'backbone',
        'gettext',
        'edx-ui-toolkit/js/utils/date-utils'
    ], function($, _, Backbone, gettext, DateUtils) {
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

        return Backbone.View.extend({

            tagName: 'li',
            templateId: '#course_card-tpl',
            className: 'courses-listing-item',

            initialize: function() {
                this.tpl = _.template($(this.templateId).html());
            },

            render: function() {
                var data = _.clone(this.model.attributes);
                var userLanguage = '',
                    userTimezone = '';
                if (this.model.userPreferences !== undefined) {
                    userLanguage = this.model.userPreferences.userLanguage;
                    userTimezone = this.model.userPreferences.userTimezone;
                }
                if (data.advertised_start !== undefined) {
                    data.start = data.advertised_start;
                } else {
                    data.start = formatDate(
                        new Date(data.start),
                        userLanguage,
                        userTimezone
                    );
                }
                data.end = formatDate(
                    new Date(data.end),
                    userLanguage,
                    userTimezone
                );
                data.enrollment_start = formatDate(
                    new Date(data.enrollment_start),
                    userLanguage,
                    userTimezone
                );
                if (data.course_category) {
                    data.course_category = window.COURSE_CATEGORIES[data.course_category];
                }
                if (data.content.duration) {
                    var duration = data.content.duration.trim().split(' ');
                    var fmt = '';
                    if (duration.length > 1 && !_.isNaN(duration[0])) {
                        if (duration[1].startsWith('minute')) {
                            fmt = ngettext('%(num)s minute', '%(num)s minutes', duration[0]);
                            data.display_duration = interpolate(fmt, {num: duration[0]}, true);
                        } else if (duration[1].startsWith('hour')) {
                            fmt = ngettext('%(num)s hour', '%(num)s hours', duration[0]);
                            data.display_duration = interpolate(fmt, {num: duration[0]}, true);
                        }
                    }
                }
                this.$el.html(this.tpl(data));
                return this;
            }
        });
    });
}(define || RequireJS.define));

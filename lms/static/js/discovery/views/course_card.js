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

        function formatLanguage (language, userPreferences) {
            if (!window.Intl || !window.Intl.DisplayNames) return language

            const capitalize = s => s.charAt(0).toUpperCase() + s.slice(1);

            const displayLanguage = (userPreferences || {})['pref-lang'] || (document.querySelector('#footer-language-select option[selected]') || {}).value

            const languageNames = new Intl.DisplayNames([displayLanguage || 'en'], {type: 'language'})
            return capitalize(languageNames.of((language || 'en').split(/[-_]/)[0]))
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
                    if (duration.length > 1 && !_.isEmpty(duration[0])) {
                        if (duration[1].startsWith('minute')) {
                            fmt = gettext('%(min)s min', duration[0]);
                            data.display_duration = interpolate(fmt, {min: duration[0]}, true);
                        } else if (duration[1].startsWith('hour')) {
                            fmt = gettext('%(h)s h', duration[0]);
                            data.display_duration = interpolate(fmt, {h: duration[0]}, true);
                        } else if (duration[1].startsWith('day')) {
                            fmt = gettext('%(d)s d', duration[0]);
                            data.display_duration = interpolate(fmt, {d: duration[0]}, true);
                        }
                    }
                }
                data.formatLanguageString = language => formatLanguage(language, this.model.userPreferences),
                this.$el.html(this.tpl(data));
                return this;
            }
        });
    });
}(define || RequireJS.define));

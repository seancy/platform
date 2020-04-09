(function(define) {
    'use strict';
    define([
        'jquery',
        'underscore',
        'backbone',
        'gettext',
        'js/discovery/views/course_card'
    ], function($, _, Backbone, gettext, CourseCardView) {
        return Backbone.View.extend({

            el: 'div.courses',
            $window: $(window),
            $document: $(document),

            initialize: function() {
                this.$list = this.$el.find('.courses-listing');
                this.attachScrollHandler();
                this.loadSkeletons()
            },

            render: function() {
                this.$list.empty();
                this.renderItems();
                return this;
            },

            renderNext: function() {
                this.renderItems();
                this.isLoading = false;
            },

            loadSkeletons(){
                var items = [0, 1,2,3,4,5,6].map(function(index) {
                    var m0 = {attributes:{duration:'', badges:'', org:'', course_category:'', course_mandatory_enabled:'', language:'', image_url:'', course:'',content:{}}}
                    var item = new CourseCardView({model: m0})
                    var el = item.render().el;
                    $(el).find('.course').addClass('skeleton')
                    return el;
                }, this);
                this.$list.append(items);
            },

            renderItems: function() {
                /* eslint no-param-reassign: [2, { "props": true }] */
                var latest = this.model.latest();
                var items = latest.map(function(result) {
                    result.userPreferences = this.model.userPreferences;
                    var item = new CourseCardView({model: result});
                    return item.render().el;
                }, this);
                this.$list.append(items);
                /* eslint no-param-reassign: [2, { "props": false }] */
            },

            attachScrollHandler: function() {
                this.$window.on('scroll', _.throttle(this.scrollHandler.bind(this), 400));
            },

            scrollHandler: function() {
                if (this.isNearBottom() && !this.isLoading) {
                    this.trigger('next');
                    this.isLoading = true;
                }
            },

            isNearBottom: function() {
                var scrollBottom = this.$window.scrollTop() + this.$window.height();
                var threshold = this.$document.height() - 200;
                return scrollBottom >= threshold;
            }

        });
    });
}(define || RequireJS.define));

(function(define) {
    'use strict';
    define([
        'underscore',
        'backbone',
        'js/discovery/models/course_item',
        'js/discovery/models/facet_option'
    ], function(_, Backbone, CourseItem, FacetOption) {
        return Backbone.Model.extend({
            url: '/course_search/',
            jqhxr: null,

            defaults: {
                totalCount: 0,
                latestCount: 0
            },

            initialize: function() {
                this.courseItems = new Backbone.Collection([], {model: CourseItem});
                this.courseItems.comparator = function(item) {
                    return item.get('content').display_name.toLowerCase();
                };
                this.facetOptions = new Backbone.Collection([], {model: FacetOption});
            },

            parse: function(response) {
                var courses = response.results || [];
                var facets = response.facets || {};
                var options = this.facetOptions;
                this.courseItems.add(_.pluck(courses, 'data'));

                this.set({
                    totalCount: response.total,
                    latestCount: courses.length
                });

                _(facets).each(function(obj, key) {
                    _(obj.terms).each(function(count, term) {
                        if (count > 0) {
                            options.add({
                                facet: key,
                                term: term,
                                count: count
                            }, {merge: true});
                        }
                    });
                });
            },

            reset: function() {
                this.set({
                    totalCount: 0,
                    latestCount: 0
                });
                this.courseItems.reset();
                this.facetOptions.reset();
            },

            latest: function() {
                return this.courseItems.last(this.get('latestCount'));
            }

        });
    });
}(define || RequireJS.define));

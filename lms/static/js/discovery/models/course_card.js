(function(define) {
    define(['backbone'], function(Backbone) {
        'use strict';

        return Backbone.Model.extend({
            defaults: {
                modes: [],
                course: '',
                enrollment_start: '',
                number: '',
                content: {
                    overview: '',
                    display_name: '',
                    number: ''
                },
                start: '',
                end: '',
                image_url: '',
                org: '',
                id: '',
                course_category: '',
                course_mandatory_enabled: '',
                vendor: '',
                language: '',
                duration: ''
            }
        });
    });
}(define || RequireJS.define));

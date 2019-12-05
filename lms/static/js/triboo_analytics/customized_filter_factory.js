(function(define) {
    'use strict';

    define(['backbone', 'js/triboo_analytics/collections/filters',
        'js/triboo_analytics/views/search_form', 'js/triboo_analytics/views/filter_bar'],
        function(Backbone, Filters, SearchForm, FilterBar) {
            return function(searchQuery) {
                var dispatcher = _.extend({}, Backbone.Events);
                var filters = new Filters();
                var form = new SearchForm();
                var filterBar = new FilterBar({collection: filters});

                dispatcher.listenTo(form, 'filter', function(type, query, name) {
                    log('query', query)
                    var targetQuery = {
                        type: type,
                        query: query,
                        name: name + ': ' + query
                    }
                    if (query) {
                        filters.remove(targetQuery);
                        filters.add(targetQuery);
                        form.clearFilter();
                    } else {
                        filters.remove(targetQuery);
                        form.clearFilter();
                    }

                    var fs = $('.active-filters button')
                    var hidden_queries = $('#hidden-queries')
                    hidden_queries.empty()
                    var html = ''
                    for (var i = 0; i < fs.length; i++) {
                        html += '<input type="hidden", name="queried_field_' + (i + 1) + '", value=' + fs[i].dataset.type + '>'
                        html += '<input type="hidden", name="query_string_' + (i + 1) + '", value=' + fs[i].dataset.value + '>'
                    }
                    hidden_queries.append(html)
                });

                dispatcher.listenTo(filterBar, 'clearFilter', function(type) {
                    filters.remove(type);
                });

                dispatcher.listenTo(form, 'clearAll', function() {
                    filterBar.resetFilters();
                    form.clearFilter();
                });
            };
        });
}(define || RequireJS.define));

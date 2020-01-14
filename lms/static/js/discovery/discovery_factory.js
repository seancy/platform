(function(define) {
    'use strict';
    define(['backbone', 'underscore', 'js/discovery/models/search_state', 'js/discovery/collections/filters',
        'js/discovery/views/search_form', 'js/discovery/views/courses_listing',
        'js/discovery/views/filter_bar', 'js/discovery/views/refine_sidebar'],
        function(Backbone, _, SearchState, Filters, SearchForm, CoursesListing, FilterBar, RefineSidebar) {
            return function(meanings, titleMeanings, preFacetFilters, searchQuery, userLanguage, userTimezone) {
                var dispatcher = _.extend({}, Backbone.Events);
                var search = new SearchState();
                var filters = new Filters();
                var form = new SearchForm();
                var filterBar = new FilterBar({collection: filters});
                var refineSidebar = new RefineSidebar({
                    collection: search.discovery.facetOptions,
                    meanings: meanings,
                    titleMeanings: titleMeanings
                });
                var listing;
                var courseListingModel = search.discovery;
                courseListingModel.userPreferences = {
                    userLanguage: userLanguage,
                    userTimezone: userTimezone
                };
                listing = new CoursesListing({model: courseListingModel});

                function removeFilter(filter) {
                    form.showLoadingIndicator();
                    filters.remove(filter);
                    if (filter.startsWith('search_query')) {
                        form.doSearch('');
                    } else {
                        search.refineSearch(filters.getTerms());
                    }
                }

                function quote(string) {
                    return '"' + string + '"';
                }

                function performPreFilterSearch(preFilters) {
                    form.showLoadingIndicator();
                    filters.reset();
                    _.each(preFilters, function(queries, type) {
                        _.each(queries, function(query) {
                            filters.add({
                                id: type + '-' + query,
                                type: type,
                                query: query,
                                name: query
                            });
                        });
                    });
                    search.refineSearch(preFilters);
                }

                dispatcher.listenTo(form, 'search', function(query) {
                    filters.reset();
                    form.showLoadingIndicator();
                    search.performSearch(query, filters.getTerms());
                });

                dispatcher.listenTo(refineSidebar, 'selectOption', function(type, query, name) {
                    form.showLoadingIndicator();
                    if (filters.get(type + '-' + query)) {
                        removeFilter(type + '-' + query);
                    } else {
                        filters.add({id: type + '-' + query, type: type, query: query, name: name});
                        search.refineSearch(filters.getTerms());
                    }
                });

                dispatcher.listenTo(filterBar, 'clearFilter', removeFilter);

                dispatcher.listenTo(refineSidebar, 'clearAll', function() {
                    form.doSearch('');
                });

                dispatcher.listenTo(listing, 'next', function() {
                    search.loadNextPage();
                });

                dispatcher.listenTo(search, 'next', function() {
                    listing.renderNext();
                });

                dispatcher.listenTo(search, 'search', function(query, total) {
                    if (total > 0) {
                        form.showFoundMessage(total);
                        if (query) {
                            filters.add(
                                {id: 'search_query-' + query, type: 'search_query', query: query, name: quote(query)},
                                {merge: true}
                            );
                        }
                    } else {
                        form.showNotFoundMessage(query);
                        filters.reset();
                    }
                    form.hideLoadingIndicator();
                    listing.render();
                    refineSidebar.render();
                });

                dispatcher.listenTo(search, 'error', function() {
                    form.showErrorMessage(search.errorMessage);
                    form.hideLoadingIndicator();
                });

                // kick off search on page refresh
                if (preFacetFilters) {
                    performPreFilterSearch(preFacetFilters);
                } else {
                    form.doSearch(searchQuery);
                }
            };
        });
}(define || RequireJS.define));

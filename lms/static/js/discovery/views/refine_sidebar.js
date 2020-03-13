(function (define) {
    'use strict';
    define([
        'jquery',
        'underscore',
        'backbone',
        'edx-ui-toolkit/js/utils/html-utils'
    ], function ($, _, Backbone, HtmlUtils) {
        return Backbone.View.extend({

            el: '.search-facets',
            events: {
                'click li button': 'selectOption',
                'click .show-less': 'collapse',
                'click .show-more': 'expand',
                'click .header-facet': 'togglePanel',
                'click #clear-all-filters': 'clearAll'
            },

            initialize: function (options) {
                this.meanings = options.meanings || {};
                this.titleMeanings = options.titleMeanings || {};
                this.$container = this.$el.find('.search-facets-lists');
                this.facetTpl = HtmlUtils.template($('#facet-tpl').html());
                this.facetOptionTpl = HtmlUtils.template($('#facet_option-tpl').html());
                $('body').on('click', this.resetPanel.bind(this))
            },

            clearAll: function(event) {
                this.trigger('clearAll');
            },

            resetPanel: function (e) {
                this.$container.find('.fact-wrapper').each(function (i, item) {
                    $(item).addClass('hidden-panel')
                })

            },

            togglePanel: function (e) {
                setTimeout(function () {
                    const $wrapper = $(e.currentTarget).parent();
                    if ($wrapper.hasClass('hidden-panel')) {
                        $wrapper.removeClass('hidden-panel')
                    } else {
                        $wrapper.addClass('hidden-panel')
                    }
                }, 50)

            },

            facetName: function (key) {
                return this.meanings[key] && this.meanings[key].name || key;
            },

            title:function(key){
                return this.titleMeanings[key];
            },

            termName: function (option) {
                return this.meanings[option.attributes.facet] &&
                    this.meanings[option.attributes.facet].terms &&
                    this.meanings[option.attributes.facet].terms[option.attributes.term] || option.attributes.term;
            },

            renderOptions: function (options) {
                var sortedOptions = _.sortBy(options, this.termName, this);
                return HtmlUtils.joinHtml.apply(this, _.map(sortedOptions, function (option) {
                    var data = _.clone(option.attributes);
                    data.name = this.termName(option);
                    return this.facetOptionTpl(data);
                }, this));
            },

            renderFacet: function (facetKey, options) {
                var displayName = this.facetName(facetKey);
                return this.facetTpl({
                    name: facetKey,
                    displayName: displayName,
                    title: this.title(displayName),
                    optionsHtml: this.renderOptions(options)
                });
            },

            render: function () {
                var grouped = this.collection.groupBy('facet');
                var htmlSnippet = HtmlUtils.joinHtml.apply(
                    this, _.map(grouped, function (options, facetKey) {
                        if (options.length > 0) {
                            return this.renderFacet(facetKey, options);
                        }
                    }, this)
                );
                HtmlUtils.setHtml(this.$container, htmlSnippet);
                return this;
            },

            collapse: function (event) {
                var $el = $(event.currentTarget),
                    $more = $el.siblings('.show-more'),
                    $ul = $el.parent().siblings('ul');

                $ul.addClass('collapse');
                $el.addClass('hidden');
                $more.removeClass('hidden');
            },

            expand: function (event) {
                var $el = $(event.currentTarget),
                    $ul = $el.parent('div').siblings('ul');

                $el.addClass('hidden');
                $ul.removeClass('collapse');
                $el.siblings('.show-less').removeClass('hidden');
            },

            selectOption: function (event) {
                var $target = $(event.currentTarget);
                this.trigger(
                    'selectOption',
                    $target.data('facet'),
                    $target.data('value'),
                    $target.data('text')
                );
            }

        });
    });
}(define || RequireJS.define));

/* globals Discussion */
(function(define) {
    'use strict';

    define([
        'underscore',
        'backbone',
        'edx-ui-toolkit/js/utils/html-utils',
        'edx-ui-toolkit/js/utils/constants',
        'common/js/discussion/utils',
        'common/js/discussion/views/discussion_thread_list_view',
        'discussion/js/views/discussion_search_view',
        'text!discussion/templates/discussion-home.underscore'
    ],
    function(_, Backbone, HtmlUtils, Constants, DiscussionUtil,
        DiscussionThreadListView, DiscussionSearchView, discussionHomeTemplate) {
        var DiscussionBoardView = Backbone.View.extend({
            events: {
                'click .forum-nav-browse-title': 'selectTopicHandler',
                'click .all-topics': 'toggleBrowseMenu',
                'keypress .forum-nav-browse-filter-input': function(event) {
                    return DiscussionUtil.ignoreEnterKey(event);
                },
                'keyup .forum-nav-browse-filter-input': 'filterTopics',
                'keydown .forum-nav-browse-filter-input': 'keyboardBinding',
                'click .forum-nav-browse-menu-wrapper': 'ignoreClick',
                'keydown .search-input': 'performSearch',
                'click .search-button': 'performSearch',
                'topic:selected': 'clearSearch',
                'click .new-post-btn':'showNewPost',
                'click .back-thread-list':'backThreadList',
                'click .fa-times': 'clearAndShowThreads'
            },

            initialize: function(options) {
                this.courseSettings = options.courseSettings;
                this.sidebar_padding = 10;
                this.current_search = '';
                this.mode = 'all';
                this.discussion = options.discussion;
                this.newPostView = options.newPostView;
                this.filterInputReset();
                this.selectedTopic = $('.forum-nav-browse-menu-item:visible .forum-nav-browse-title.is-focused');
                this.listenTo(this.model, 'change', this.render);

            },

            showNewPost: function(e) {
                this.searchView.$el.hide();
                this.newPostView.$el.show();
                this.discussionThreadListView.$el.hide();
                const $btn = $(e.currentTarget);
                $btn.hide().siblings().show();
            },

            backThreadList: function(e) {
                this.searchView.$el.show();
                this.newPostView.$el.hide();
                this.discussionThreadListView.$el.show();
                const $btn = $(e.currentTarget);
                $btn.hide().siblings().show();

                this.trigger('back-thread-list');
            },

            render: function() {
                this.discussionThreadListView = new DiscussionThreadListView({
                    collection: this.discussion,
                    el: this.$('.discussion-thread-list-container'),
                    courseSettings: this.courseSettings,
                    supportsActiveThread: true,
                    mode: this.mode
                }).render();
                this.searchView = new DiscussionSearchView({
                    el: this.$('.forum-search')
                }).render();
                this.showBrowseMenu(true);
                return this;
            },

            isBrowseMenuVisible: function() {
                return this.$('.forum-nav-browse-menu-wrapper').is(':visible');
            },

            showBrowseMenu: function(initialLoad) {
            },

            hideBrowseMenu: function() {
            },

            toggleBrowseMenu: function(event) {
                var inputText = this.$('.forum-nav-browse-filter-input').val();
                event.preventDefault();
                event.stopPropagation();
                if (this.isBrowseMenuVisible()) {
                    this.hideBrowseMenu();
                } else {
                    if (inputText !== '') {
                        this.filterTopics(inputText);
                    }
                    this.showBrowseMenu();
                }
                this.clearSearch();
            },

            performSearch: function(event) {
                this.$('.fa-times').show();
                if (event.which === Constants.keyCodes.enter || event.type === 'click') {
                    event.preventDefault();
                    this.hideBrowseMenu();
                    this.discussionThreadListView.performSearch($('.search-input', this.$el));
                }
            },

            clearSearch: function() {
                this.$('.search-input').val('');
                this.discussionThreadListView.clearSearchAlerts();
            },

            clearAndShowThreads: function() {
                this.$('.search-input').val('');
                this.$('.fa-times').hide();
                this.hideBrowseMenu();
                this.discussionThreadListView.performSearch($('.search-input', this.$el));
            },

            goHome: function() {
                var url = DiscussionUtil.urlFor('notifications_status', window.user.get('id'));
                HtmlUtils.append(this.$('.forum-content').empty(), HtmlUtils.template(discussionHomeTemplate)({}));
                this.$('.forum-nav-thread-list a').removeClass('is-active').find('.sr')
                    .remove();
                this.$('input.email-setting').bind('click', this.discussionThreadListView.updateEmailNotifications);
                DiscussionUtil.safeAjax({
                    url: url,
                    type: 'GET',
                    success: function(response) {
                        $('input.email-setting').prop('checked', response.status);
                    }
                });
            },

            filterInputReset: function() {
                this.filterEnabled = true;
                this.selectedTopicIndex = -1;
                this.selectedTopicId = null;
            },

            selectOption: function(element) {
                var activeDescendantId, activeDescendantText;
                if (this.selectedTopic.length > 0) {
                    this.selectedTopic.removeClass('is-focused');
                }
                if (element) {
                    element.addClass('is-focused');
                    activeDescendantId = element.parent().attr('id');
                    activeDescendantText = element.text();
                    this.selectedTopic = element;
                    this.selectedTopicId = activeDescendantId;
                    this.$('.forum-nav-browse-filter-input')
                        .attr('aria-activedescendant', activeDescendantId)
                        .val(activeDescendantText);
                }
            },

            keyboardBinding: function(event) {
                var key = event.which,
                    $inputText = $('.forum-nav-browse-filter-input'),
                    $filteredMenuItems = $('.forum-nav-browse-menu-item:visible'),
                    filteredMenuItemsLen = $filteredMenuItems.length,
                    $curOption = $filteredMenuItems.eq(0).find('.forum-nav-browse-title').eq(0),
                    $activeOption, $prev, $next;

                switch (key) {
                case Constants.keyCodes.enter:
                    $activeOption = $filteredMenuItems.find('.forum-nav-browse-title.is-focused');
                    if ($inputText.val() !== '') {
                        $activeOption.trigger('click');
                        this.filterInputReset();
                    }
                    break;

                case Constants.keyCodes.esc:
                    this.toggleBrowseMenu(event);
                    this.$('.forum-nav-browse-filter-input').val('');
                    this.filterInputReset();
                    $('.all-topics').trigger('click');
                    break;

                case Constants.keyCodes.up:
                    if (this.selectedTopicIndex > 0) {
                        this.selectedTopicIndex -= 1;
                        if (this.isBrowseMenuVisible()) {
                            $prev = $('.forum-nav-browse-menu-item:visible')
                            .eq(this.selectedTopicIndex).find('.forum-nav-browse-title')
                            .eq(0);
                            this.filterEnabled = false;
                            $curOption.removeClass('is-focused');
                            $prev.addClass('is-focused');
                        }
                        this.selectOption($prev);
                    }
                    break;

                case Constants.keyCodes.down:
                    if (this.selectedTopicIndex < filteredMenuItemsLen - 1) {
                        this.selectedTopicIndex += 1;
                        if (this.isBrowseMenuVisible()) {
                            $next = $('.forum-nav-browse-menu-item:visible')
                                .eq(this.selectedTopicIndex).find('.forum-nav-browse-title')
                                .eq(0);
                            this.filterEnabled = false;
                            $curOption.removeClass('is-focused');
                            $next.addClass('is-focused');
                        }
                        this.selectOption($next);
                    }
                    break;

                default:
                }
            },

            filterTopics: function() {
                var $items, query, filteredItems,
                    self = this;
                query = this.$('.forum-nav-browse-filter-input').val();
                $items = this.$('.forum-nav-browse-menu-item');
                if (query.length === 0) {
                    $items.find('.forum-nav-browse-title.is-focused').removeClass('is-focused');
                    return $items.show();
                } else {
                    if (self.filterEnabled) {
                        $items.hide();
                        filteredItems = $items.each(function(i, item) {
                            var path, pathText,
                                $item = $(item);
                            if (!$item.is(':visible')) {
                                pathText = self.getPathText($item).toLowerCase();
                                if (query.split(' ').every(function(term) {
                                    return pathText.search(term.toLowerCase()) !== -1;
                                })) {
                                    path = $item.parents('.forum-nav-browse-menu-item').andSelf();
                                    path.add($item.find('.forum-nav-browse-menu-item')).show();
                                }
                            }
                        });
                    }
                    return filteredItems;
                }
            },

            getPathText: function(item) {
                var path, pathTitles;
                path = item.parents('.forum-nav-browse-menu-item').andSelf();
                pathTitles = path.children('.forum-nav-browse-title').map(function(i, elem) {
                    return $(elem).text();
                }).get();
                return pathTitles.join(' / ');
            },

            selectTopicHandler: function(event) {
                var $item = $(event.target).closest('.forum-nav-browse-menu-item');
                event.preventDefault();
                this.hideBrowseMenu();
                this.trigger('topic:selected', this.getBreadcrumbText($item));
                return this.discussionThreadListView.selectTopic($(event.target));
            },

            getBreadcrumbText: function($item) {
                var $parentSubMenus = $item.parents('.forum-nav-browse-submenu'),
                    crumbs = [],
                    subTopic = $('.forum-nav-browse-title', $item)
                        .first()
                        .contents()
                        .last()
                        .text()
                        .trim();

                $parentSubMenus.each(function(i, el) {
                    crumbs.push(
                        $(el).siblings('.forum-nav-browse-title')
                        .first()
                        .contents()
                        .last()
                        .text()
                        .trim()
                    );
                });

                if (subTopic !== 'All Discussions') {
                    crumbs.push(subTopic);
                }

                return crumbs;
            }

        });

        return DiscussionBoardView;
    });
}).call(this, define || RequireJS.define);

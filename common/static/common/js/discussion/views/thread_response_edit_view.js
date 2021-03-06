/* globals DiscussionUtil */
(function() {
    'use strict';
    var __hasProp = {}.hasOwnProperty,
        __extends = function(child, parent) {
            for (var key in parent) {
                if (__hasProp.call(parent, key)) {
                    child[key] = parent[key];
                }
            }
            function ctor() {
                this.constructor = child;
            }

            ctor.prototype = parent.prototype;
            child.prototype = new ctor();
            child.__super__ = parent.prototype;
            return child;
        };

    if (typeof Backbone !== 'undefined' && Backbone !== null) {
        this.ThreadResponseEditView = (function(_super) {
            __extends(ThreadResponseEditView, _super);

            function ThreadResponseEditView() {
                return ThreadResponseEditView.__super__.constructor.apply(this, arguments);
            }

            ThreadResponseEditView.prototype.events = {
                'click .post-update': 'update',
                'click .post-cancel': 'cancel_edit'
            };

            ThreadResponseEditView.prototype.$ = function(selector) {
                return this.$el.find(selector);
            };

            ThreadResponseEditView.prototype.initialize = function(options) {
                this.options = options;
                return ThreadResponseEditView.__super__.initialize.call(this);
            };

            ThreadResponseEditView.prototype.render = function() {
                var body_length = this.model.attributes.body.length;
                var country_tag = this.model.attributes.body.substr(body_length - 4, 4);
                if (country_tag.startsWith(" #")) {
                    this.model.attributes.body = this.model.attributes.body.substr(0, body_length - 4);
                    this.model.attributes.country_tag = country_tag;
                }

                var context = $.extend({mode: this.options.mode, startHeader: this.options.startHeader},
                    this.model.attributes);

                this.template = _.template($('#thread-response-edit-template').html());
                this.$el.html(this.template(context));
                this.delegateEvents();
                DiscussionUtil.makeWmdEditor(this.$el, $.proxy(this.$, this), 'edit-post-body');
                return this;
            };

            ThreadResponseEditView.prototype.update = function(event) {
                return this.trigger('response:update', event);
            };

            ThreadResponseEditView.prototype.cancel_edit = function(event) {
                var country_tag = this.model.attributes.country_tag ? this.model.attributes.country_tag : '';
                this.model.attributes.body = this.model.attributes.body + country_tag;
                return this.trigger('response:cancel_edit', event);
            };

            return ThreadResponseEditView;
        }(Backbone.View));
    }
}).call(window);


var edx = edx || {};

(function($, _, Backbone, gettext) {
    'use strict';

    edx.dialog = edx.dialog || {};
    edx.confirmation= edx.confirmation || {};

    window.LearningTribes = window.LearningTribes || {};
    window.LearningTribes.dialog = edx.dialog;
    window.LearningTribes.confirmation = edx.confirmation;

    var $dialogContainer = $('#dialog-container');

    var initialize = function () {
        this.$bg = $('<div class="message-dialog-transparent-background"></div>').addClass('hide');
        this.$el = $('<div></div>').addClass('message-dialog hide').html($('#dialog-template').html());
        $dialogContainer.append(this.$el);
        $dialogContainer.append(this.$bg);
        this.$el.find('i').on('click', $.proxy(function () {
            this.hide();
        }, this))
    }

    initialize.prototype.show = function (content) {
        this.$el.find('.dialog-content').html(content);
        this.$bg.removeClass('hide')
        this.$el.removeClass('hide');
    }

    initialize.prototype.hide = function(){
        this.$bg.addClass('hide');
        this.$el.addClass('hide');
    }

    // confirmation dialog
    var Confirmation = function (message, confirmationCallback, cancelCallback, commonCallback) {
        this.$bg = $('<div class="confirmation-dialog-transparent-background"></div>').addClass('hide');
        this.$el = $('<div></div>').addClass('confirmation-dialog hide').html($('#confirmation-template').html());
        $dialogContainer.append(this.$el);
        $dialogContainer.append(this.$bg);

        var cancel = $.proxy(function () {
            this.destroy();
            cancelCallback && cancelCallback();
            commonCallback && commonCallback();
        }, this)
        var confirm = $.proxy(function () {
            this.destroy();
            confirmationCallback && confirmationCallback();
            commonCallback && commonCallback();
        }, this)
        this.$el.find('i').on('click', cancel)
        this.$el.find('.btn-secondary').on('click', cancel)
        this.$el.find('.btn-primary').on('click', confirm)

        this.$el.find('.dialog-content').html(message);
    }

    Confirmation.prototype.destroy = function(){
        this.$el.remove();
        this.$bg.remove();
    }

    edx.dialog = LearningTribes.dialog = new initialize();
    edx.confirmation = LearningTribes.confirmation = {
        _confirmation:null,
        show:function (message, confirmationCallback, cancelCallback) {
            if (this._confirmation == null){
                this._confirmation = new Confirmation (message, confirmationCallback, cancelCallback, $.proxy(function () {
                    this._confirmation = null;
                }, this))
            }
        }
    }

}(jQuery, _, Backbone, gettext));



odoo.define('fal_invoice_milestone.Invpolicywidget', function (require) {
"use strict";

var core = require('web.core');
var QWeb = core.qweb;

var Widget = require('web.Widget');
var Context = require('web.Context');
var data_manager = require('web.data_manager');
var widget_registry = require('web.widget_registry');
var config = require('web.config');

var _t = core._t;
var time = require('web.time');

var Invpolicywidget = Widget.extend({
    template: 'fal_invoice_milestone.inv_policy',
    events: _.extend({}, Widget.prototype.events, {
        'click .fa-info-circle': '_onClickButton',
    }),

    init: function (parent, params) {
        this.data = params.data;
        this._super(parent);
    },

    start: function () {
        var self = this;
        return this._super.apply(this, arguments).then(function () {
            self._setPopOver();
        });
    },

    updateState: function (state) {
        this.$el.popover('dispose');
        var candidate = state.data[this.getParent().currentRow];
        if (candidate) {
            this.data = candidate.data;
            this.renderElement();
            this._setPopOver();
        }
    },


    _setPopOver: function () {
        var self = this;
        if (this.data.state !== 'sale') {
            return;
        }
        this.data.debug = config.isDebug();

        self._rpc({
            model: 'sale.order.line',
            method: 'get_components',
            args: [[self.data.id]]
        }).then(function (res) {
            var $content = $(QWeb.render('fal_invoice_milestone.InvPopOver', {
                data: res,
            }));
            var $forecastButton = $content.find('.action_open_milestone');
            $forecastButton.on('click', function(ev) {
                self.do_action({
                    name: _t('Invoice Rule Line'),
                    views: [[false, 'list'], [false, 'form']],
                    view_mode: "list",
                    res_model: 'fal.invoice.term.line',
                    type: 'ir.actions.act_window',
                    target: 'current',
                    domain: [['id', 'in', res.rule_lines]],
                 });
            });
            var options = {
                content: $content,
                html: true,
                placement: 'right',
                title: _t('Invoice Rule Info'),
                trigger: 'focus',
                delay: {'show': 0, 'hide': 100 },
            };
            self.$el.popover(options);
        });
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------
    _onClickButton: function () {
        this.$el.find('.fa-info-circle').prop('special_click', true);
    },
});

widget_registry.add('invoice_policy', Invpolicywidget);

return Invpolicywidget;
});

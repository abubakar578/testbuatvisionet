# -*- coding: utf-8 -*-
from odoo import models, fields, api


class MailMessage(models.Model):
    _inherit = 'mail.message'

    tracking_message = fields.Html(string="Tracking Message", compute="_get_tracking_message", store=True)
    tracking_count = fields.Integer(compute="_get_tracking_message", store=True)

    @api.depends('tracking_value_ids')
    def _get_tracking_message(self):
        for message in self:
            message.tracking_message = "<br>".join("%s: %s → %s" % (tracking.field_desc, tracking.get_old_display_value()[0], tracking.get_new_display_value()[0]) for tracking in message.tracking_value_ids)
            message.tracking_count = message.tracking_value_ids and len(message.tracking_value_ids) or 0

# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, tools, api


class ActivityReport(models.Model):
    """ CRM Lead Analysis """

    _inherit = "crm.activity.report"

    tracking_message = fields.Html('Tracking Message', readonly=True)
    presales = fields.Many2one('res.users', 'Presales', readonly=True)

    def _select(self):
        res = super(ActivityReport, self)._select()
        res += ', m.tracking_message, l.presales'
        return res

    def _where(self):
        disccusion_subtype = self.env.ref('mail.mt_comment')
        return """
            WHERE
                m.model = 'crm.lead' AND (m.mail_activity_type_id IS NOT NULL OR m.subtype_id = %s OR m.tracking_count > 0)
        """ % (disccusion_subtype.id,)

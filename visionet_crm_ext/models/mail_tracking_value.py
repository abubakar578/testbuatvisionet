import logging
from odoo import models, api, fields, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class MailTracking(models.Model):
    _inherit = 'mail.tracking.value'

    model_id = fields.Many2one('ir.model', string="Model", compute='_tracking_model', store=True)
    crm_id = fields.Many2one('crm.lead', string="Record", compute='_get_record', store=True)

    @api.depends('field')
    def _tracking_model(self):
        for rec in self:
            rec['model_id'] = rec.field.model_id

    @api.depends('mail_message_id')
    def _get_record(self):
        for record in self:
            if record.mail_message_id.model != 'crm.lead':
                record.crm_id = False
            else:
                record['crm_id'] = self.env['crm.lead'].browse(record.mail_message_id.res_id).id

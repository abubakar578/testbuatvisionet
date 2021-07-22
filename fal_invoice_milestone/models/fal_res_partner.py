from odoo import fields, models, api


class FalResPartner(models.Model):
    _inherit = 'res.partner'

    fal_partner_invoice_term = fields.Many2one('fal.invoice.term', 'Invoice Rule', domain=[('is_template', '=', True)])

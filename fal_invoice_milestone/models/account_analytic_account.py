from odoo import fields, models


class account_analytic_account(models.Model):
    _inherit = 'account.analytic.account'

    ###################################################################
    # Field Definition
    # Usually You will Connect 1 Terms to Analytic Account, so we have this field as default
    fal_invoice_term_id = fields.Many2one('fal.invoice.term', 'Invoice Rule', domain=[('is_template', '=', False)])

from odoo import api, fields, models, _


class MilestoneWizzard(models.TransientModel):
    _name = "invoice.milestone.wizard"
    _description = "Invoice Milestone"

    fal_template_id = fields.Many2one('fal.invoice.term', required=True, string="Template", domain=[('is_template', '=', True)])
    fal_sale_order = fields.Many2one('sale.order', string="Sale Order")

    def create_invoices_rule(self):
        rule = self.fal_template_id.take_template()
        fal_template_id = self.id
        self.fal_sale_order.fal_invoice_term_id = rule.get('res_id')
        return rule.get('res_id')

    def create_invoices_rule_view(self):
        rule = self.create_invoices_rule()
        view = self.env.ref('fal_invoice_milestone.view_fal_invoice_term_form_fal_ordeinmile')
        return {
            'type': 'ir.actions.act_window',
            'name': _('Invoice Terms'),
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'fal.invoice.term',
            'views': [(view.id, 'form')],
            'view_id': view.id,
            'res_id': rule,
            'target': 'current',
        }

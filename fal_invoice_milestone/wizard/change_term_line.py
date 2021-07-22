from odoo import api, fields, models, _


class ChangeTermLine(models.TransientModel):
    _name = "change.term.line.wizard"
    _description = "Change Term Line"

    date = fields.Date('Invoice Date')
    invoice_forecast_date = fields.Date(
        "Invoice Forecast Date")
    fal_invoice_term_line_ids = fields.Many2many(
        'fal.invoice.term.line', string="Term Line")
    term_line = fields.Many2one('fal.invoice.term.line')

    def change_term_line(self):
        for wiz in self:
            wiz.term_line.date = self.date
            wiz.term_line.invoice_forecast_date = self.invoice_forecast_date
            for term in wiz.fal_invoice_term_line_ids:
                term_so = term.search([
                    ('parent_id', '=', term.parent_id.id),
                    ('fal_order_id', '=', term.fal_sale_order_line_id.order_id.id)
                ])
                #term line on sale.order.line
                term.date = self.date
                term.invoice_forecast_date = self.invoice_forecast_date

                # term line on sale.odrer
                term_so.date = self.date
                term_so.invoice_forecast_date = self.invoice_forecast_date

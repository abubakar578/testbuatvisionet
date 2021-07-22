import time
from odoo import api, fields, models, _
from odoo.exceptions import UserError
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
from datetime import datetime
from dateutil.relativedelta import relativedelta


class SaleAdvancePaymentInv(models.TransientModel):
    _inherit = "sale.advance.payment.inv"
    # see in /odoo/addons/sale/wizard/sale_make_invoice_advance.py

    def _get_advance_details(self, order):
        amount, name = super(SaleAdvancePaymentInv, self)._get_advance_details(order)
        ctx = dict(self._context)
        original_so_line = ctx.get('so_line')
        if original_so_line and self.advance_payment_method == 'percentage':
            amount = original_so_line.price_subtotal * self.amount / 100
        return amount, name

    def _create_invoice(self, order, so_line, amount):
        invoice = super(SaleAdvancePaymentInv, self)._create_invoice(order, so_line, amount)
        ctx = dict(self._context)
        original_term_line = ctx.get('term_line')
        original_so_line = ctx.get('so_line')
        if original_so_line:
            new_name = ''
            for invoice_line in invoice.invoice_line_ids:
                for sale_order_line in invoice_line.sale_line_ids:
                    if sale_order_line.product_id == self.product_id:
                        new_name = original_so_line.product_id.display_name or "" + " - "
                        new_name += sale_order_line.name
                        # If there is description on term line
                        if original_term_line and original_term_line.description:
                            new_name += " - " + original_term_line.description
                        sale_order_line.name = new_name
                # change invoice name
                invoice_line.name = new_name
        if original_term_line:
            original_term_line.invoice_id = invoice.id
        return invoice
# end of FalInvoiceMilestoneLine()

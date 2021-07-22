from odoo import fields, models, api


class AccountMove(models.Model):
    _inherit = 'account.move'

    fal_sale_id = fields.Many2one(
        'sale.order',
        compute='_fal_get_so_line',
        string='Sales Source',
        readonly=True,
    )

    @api.depends(
        'invoice_line_ids',
        'invoice_line_ids.sale_line_ids',
        'invoice_line_ids.sale_line_ids.order_id'
    )
    def _fal_get_so_line(self):
        order = False
        for line in self:
            for order_line in line.invoice_line_ids:
                for sale_order_line in order_line.sale_line_ids:
                    if sale_order_line.order_id:
                        order = sale_order_line.order_id
            line.fal_sale_id = order

    def _get_total_ordered_amount(self):
        for invoice in self:
            total = 0
            sale_ids = []
            for invoice_line in invoice.invoice_line_ids:
                if invoice.move_type in ['out_invoice', 'out_refund']:
                    for sale_line in invoice_line.sale_line_ids:
                        if sale_line.order_id not in sale_ids:
                            sale_ids.append(sale_line.order_id)
                            for sale in sale_ids:
                                total += sale.amount_untaxed
                else:
                    super(AccountMove, self)._get_total_ordered_amount()
            invoice.fal_total_ordered_amount = total

    def _get_total_invoiced_amount(self):
        for invoice in self:
            total = 0
            invoice_list = []
            for invoice_line in invoice.invoice_line_ids:
                if invoice.move_type in ['out_invoice', 'out_refund']:
                    for sale_line in invoice_line.sale_line_ids:
                        for inv in sale_line.order_id.invoice_ids:
                            if inv not in invoice_list and inv.state != 'cancel':
                                invoice_list.append(inv)
                else:
                    super(AccountMove, self)._get_total_invoiced_amount()
            for item in invoice_list:
                total += item.amount_untaxed if item.move_type in ['out_invoice'] else -item.amount_untaxed
            invoice.fal_total_amount_already_invoced = total

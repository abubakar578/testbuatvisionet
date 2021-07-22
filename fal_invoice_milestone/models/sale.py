from odoo import api, fields, models, _
from datetime import timedelta, datetime
from dateutil.relativedelta import relativedelta
from odoo.exceptions import UserError, AccessError
from odoo.tools import float_is_zero, float_compare
from itertools import groupby


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    ####################################################################################################
    # Fields Definition
    # Invoice Term Management
    def _get_auto_run_milestone(self):
        ICPSudo = self.env['ir.config_parameter'].sudo()
        return ICPSudo.get_param('fal_invoice_milestone.fal_active_milestone_cron')

    fal_invoice_term_id = fields.Many2one('fal.invoice.term', 'Invoice Rule', domain=[('is_template', '=', False)], readonly=True, copy=False, states={'draft': [('readonly', False)]})
    fal_milestone_by_cron = fields.Boolean("Auto Run Invoice Milestone", default=_get_auto_run_milestone)

    ####################################################################################################
    # Override Odoo Method
    # Make sure to check that in every sales order line, the total milestone percentage is 100
    def action_confirm(self):
        res = super(SaleOrder, self).action_confirm()
        for order in self:
            order.compute_fal_invoice_term_id()
            for order_line in order.order_line.filtered(lambda r: r.fal_invoice_term_id and r.fal_invoice_term_id.fal_invoice_rules == 'milestone'):
                temp = 0.0
                for invoice_milestone_line in order_line.fal_invoice_milestone_line_date_ids:
                    temp += invoice_milestone_line.percentage
                if temp > 100:
                    raise UserError(_(
                        "Total Percentage %s cannot be greater than 100"
                    ) % (order_line.product_id.display_name))
                if temp < 100:
                    raise UserError(_(
                        "Total Percentage %s cannot be lower than 100"
                    ) % (order_line.product_id.display_name))
        return res

    ###################################################################################################
    # Function Definition
    def compute_fal_invoice_term_id(self):
        # We Remove Existing Milestone on Lines First
        if self.fal_invoice_term_id:
            temp = []
            val_order_date = self.date_order.date()
            # If Invoice Type is milestone, we just need to copy the line of invoice term to the sale order line
            if self.fal_invoice_term_id.fal_invoice_rules == 'milestone':
                for line in self.fal_invoice_term_id.fal_invoice_term_line_ids:
                    temp.append((0, 0, {
                        'parent_id': line.id,
                        'company_id': self.company_id.id,
                        'fal_invoice_rules': self.fal_invoice_term_id.fal_invoice_rules,
                        'fal_invoice_rules_type': self.fal_invoice_term_id.fal_invoice_rules_type,
                        'percentage': line.percentage,
                        'amount': line.amount,
                        'date': line.date,
                        'invoice_forecast_date': line.invoice_forecast_date,
                        'sequence': line.sequence,
                        'product_id': line.product_id.id,
                        'name': line.name,
                        'description': line.description,
                    }))
            # If Invoice Type is subscription, we see if subscription has starting date
            # If not means that we need to put the date based on order date
            else:
                if self.fal_invoice_term_id.date_start:
                    for line in self.fal_invoice_term_id.fal_invoice_term_line_ids:
                        temp.append((0, 0, {
                            'parent_id': line.id,
                            'company_id': self.company_id.id,
                            'fal_invoice_rules': self.fal_invoice_term_id.fal_invoice_rules,
                            'fal_invoice_rules_type': self.fal_invoice_term_id.fal_invoice_rules_type,
                            'percentage': line.percentage,
                            'amount': line.amount,
                            'date': line.date,
                            'invoice_forecast_date': line.invoice_forecast_date,
                            'sequence': line.sequence,
                            'product_id': line.product_id.id,
                            'name': line.name,
                            'description': line.description,
                        }))
                else:
                    int_days = self.fal_invoice_term_id.recurring_interval
                    var_date = val_order_date
                    for line in self.fal_invoice_term_id.fal_invoice_term_line_ids:
                        temp.append((0, 0, {
                            'parent_id': line.id,
                            'company_id': self.company_id.id,
                            'fal_invoice_rules': self.fal_invoice_term_id.fal_invoice_rules,
                            'fal_invoice_rules_type': self.fal_invoice_term_id.fal_invoice_rules_type,
                            'percentage': line.percentage,
                            'amount': line.amount,
                            'date': var_date,
                            'invoice_forecast_date': line.invoice_forecast_date,
                            'sequence': line.sequence,
                            'product_id': line.product_id.id,
                            'name': line.name,
                            'description': line.description,
                        }))
                        if self.fal_invoice_term_id.recurring_rule_type == 'daily':
                            var_date = var_date + relativedelta(days=int_days)
                        elif self.fal_invoice_term_id.recurring_rule_type == 'weekly':
                            var_date = var_date + relativedelta(weeks=int_days)
                        elif self.fal_invoice_term_id.recurring_rule_type == 'monthly':
                            var_date = var_date + relativedelta(months=int_days)
                        elif self.fal_invoice_term_id.recurring_rule_type == 'yearly':
                            var_date = var_date + relativedelta(years=int_days)
            # Apply the temp to all line
            for order_line in self.order_line:
                order_line.fal_invoice_milestone_line_date_ids = False
                order_line.update({'fal_invoice_milestone_line_date_ids': temp, 'fal_invoice_term_id': self.fal_invoice_term_id})

    # Force Call of CRON Method
    def create_invoice_milestone_btn(self):
        self.ensure_one()
        temp_count = self.invoice_count
        FalInvoiceTermLine = self.env['fal.invoice.term.line']
        current_date = datetime.now()
        term_line_ids = FalInvoiceTermLine.search([
            ('date', '<=', current_date),
            ('fal_sale_order_id', 'in', self.ids),
            ('invoice_id', '=', False),
        ])
        term_line_ids._generate_invoice_order_line_by_planning_date()
        if self.invoice_count > temp_count:
            # new invoice is created
            return self.action_view_invoice()
        return True

    # CLuedoo Override
    def _get_invoiceable_lines(self, final=False):
        """Return the invoiceable lines for order `self`."""
        down_payment_line_ids = []
        invoiceable_line_ids = []
        pending_section = None
        precision = self.env['decimal.precision'].precision_get('Product Unit of Measure')
        original_term_line = self._context.get("term_line", False)

        if original_term_line:
            order_line = [self._context.get('so_line')]
            for item in self._context.get('so_line').fal_invoice_milestone_line_date_ids.filtered(lambda a: not a.is_final):
                for invoice in item.invoice_id.invoice_line_ids:
                    order_line.append(invoice.sale_line_ids)

            for line in order_line:
                if line.display_type == 'line_section':
                    # Only invoice the section if one of its lines is invoiceable
                    pending_section = line
                    continue
                if line.display_type != 'line_note' and float_is_zero(line.qty_to_invoice, precision_digits=precision):
                    continue
                if line.qty_to_invoice > 0 or (line.qty_to_invoice < 0 and final) or line.display_type == 'line_note':
                    if line.is_downpayment:
                        # Keep down payment lines separately, to put them together
                        # at the end of the invoice, in a specific dedicated section.
                        down_payment_line_ids.append(line.id)
                        continue
                    if pending_section:
                        invoiceable_line_ids.append(pending_section.id)
                        pending_section = None
                    invoiceable_line_ids.append(line.id)

            return self.env['sale.order.line'].browse(invoiceable_line_ids + down_payment_line_ids)
        else:
            return super(SaleOrder, self)._get_invoiceable_lines(final)

    # CLuedoo Override
    def _create_invoices(self, grouped=False, final=False, date=None):
        original_term_line = self._context.get("term_line", False)
        """
        Create the invoice associated to the SO.
        :param grouped: if True, invoices are grouped by SO id. If False, invoices are grouped by
                        (partner_invoice_id, currency)
        :param final: if True, refunds will be generated if necessary
        :returns: list of created invoices
        """
        if not self.env['account.move'].check_access_rights('create', False):
            try:
                self.check_access_rights('write')
                self.check_access_rule('write')
            except AccessError:
                return self.env['account.move']

        # 1) Create invoices.
        invoice_vals_list = []
        invoice_item_sequence = 0 # Incremental sequencing to keep the lines order on the invoice.
        for order in self:
            order = order.with_company(order.company_id)
            current_section_vals = None
            down_payments = order.env['sale.order.line']

            invoice_vals = order._prepare_invoice()
            invoiceable_lines = order._get_invoiceable_lines(final)

            if not any(not line.display_type for line in invoiceable_lines):
                raise self._nothing_to_invoice_error()

            invoice_line_vals = []
            down_payment_section_added = False
            for line in invoiceable_lines:
                if not down_payment_section_added and line.is_downpayment:
                    # Create a dedicated section for the down payments
                    # (put at the end of the invoiceable_lines)
                    # CLuedoo Change Here
                    if not original_term_line:
                        invoice_line_vals.append(
                            (0, 0, order._prepare_down_payment_section_line(
                                sequence=invoice_item_sequence,
                            )),
                        )
                        dp_section = True
                        invoice_item_sequence += 1
                    # End Here
                invoice_line_vals.append(
                    (0, 0, line._prepare_invoice_line(
                        sequence=invoice_item_sequence,
                    )),
                )
                invoice_item_sequence += 1

            invoice_vals['invoice_line_ids'] = invoice_line_vals
            invoice_vals_list.append(invoice_vals)

        if not invoice_vals_list:
            raise self._nothing_to_invoice_error()

        # 2) Manage 'grouped' parameter: group by (partner_id, currency_id).
        if not grouped:
            new_invoice_vals_list = []
            invoice_grouping_keys = self._get_invoice_grouping_keys()
            for grouping_keys, invoices in groupby(invoice_vals_list, key=lambda x: [x.get(grouping_key) for grouping_key in invoice_grouping_keys]):
                origins = set()
                payment_refs = set()
                refs = set()
                ref_invoice_vals = None
                for invoice_vals in invoices:
                    if not ref_invoice_vals:
                        ref_invoice_vals = invoice_vals
                    else:
                        ref_invoice_vals['invoice_line_ids'] += invoice_vals['invoice_line_ids']
                    origins.add(invoice_vals['invoice_origin'])
                    payment_refs.add(invoice_vals['payment_reference'])
                    refs.add(invoice_vals['ref'])
                ref_invoice_vals.update({
                    'ref': ', '.join(refs)[:2000],
                    'invoice_origin': ', '.join(origins),
                    'payment_reference': len(payment_refs) == 1 and payment_refs.pop() or False,
                })
                new_invoice_vals_list.append(ref_invoice_vals)
            invoice_vals_list = new_invoice_vals_list

        # 3) Create invoices.

        # As part of the invoice creation, we make sure the sequence of multiple SO do not interfere
        # in a single invoice. Example:
        # SO 1:
        # - Section A (sequence: 10)
        # - Product A (sequence: 11)
        # SO 2:
        # - Section B (sequence: 10)
        # - Product B (sequence: 11)
        #
        # If SO 1 & 2 are grouped in the same invoice, the result will be:
        # - Section A (sequence: 10)
        # - Section B (sequence: 10)
        # - Product A (sequence: 11)
        # - Product B (sequence: 11)
        #
        # Resequencing should be safe, however we resequence only if there are less invoices than
        # orders, meaning a grouping might have been done. This could also mean that only a part
        # of the selected SO are invoiceable, but resequencing in this case shouldn't be an issue.
        if len(invoice_vals_list) < len(self):
            SaleOrderLine = self.env['sale.order.line']
            for invoice in invoice_vals_list:
                sequence = 1
                for line in invoice['invoice_line_ids']:
                    line[2]['sequence'] = SaleOrderLine._get_invoice_line_sequence(new=sequence, old=line[2]['sequence'])
                    sequence += 1

        # Manage the creation of invoices in sudo because a salesperson must be able to generate an invoice from a
        # sale order without "billing" access rights. However, he should not be able to create an invoice from scratch.
        moves = self.env['account.move'].sudo().with_context(default_move_type='out_invoice').create(invoice_vals_list)

        # 4) Some moves might actually be refunds: convert them if the total amount is negative
        # We do this after the moves have been created since we need taxes, etc. to know if the total
        # is actually negative or not
        if final:
            moves.sudo().filtered(lambda m: m.amount_total < 0).action_switch_invoice_into_refund_credit_note()
        for move in moves:
            move.message_post_with_view('mail.message_origin_link',
                values={'self': move, 'origin': move.line_ids.mapped('sale_line_ids.order_id')},
                subtype_id=self.env.ref('mail.mt_note').id
            )
            if original_term_line and move.id:
                original_term_line.invoice_id = move.id
        return moves

    #############################################################################################
    # Onchange
    # Set Invoice Term based on analytic account id
    @api.onchange('analytic_account_id')
    def onchange_analytic_account_id(self):
        if self.analytic_account_id:
            self.fal_invoice_term_id = self.analytic_account_id.fal_invoice_term_id

    def view_wizzard_invoi(self):
        view = self.env.ref('fal_invoice_milestone.calendar_event_warning_wizard_form')
        wiz = self.env['invoice.milestone.wizard']
        return {
            'name': _('Invoice Milestone'),
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'invoice.milestone.wizard',
            'views': [(view.id, 'form')],
            'view_id': view.id,
            'target': 'new',
            'res_id': wiz.id,
            'context': {'default_fal_template_id': self.partner_id.fal_partner_invoice_term.id, 'default_fal_sale_order': self.id}
        }


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    ###############################################################
    # Fields Definition
    # 1. To be able to manage invoice term per sales order line, but only intended for advanced user and need studio to open
    # 2. Invoice Term / Rule Management
    fal_invoice_term_id = fields.Many2one('fal.invoice.term', 'Invoice Rule', domain=[('is_template', '=', False)], copy=False)
    fal_invoice_rules = fields.Selection([
        ('milestone', 'Invoice Milestone'),
        ('subscription', 'Subscription'),
    ], string='Rules', related='fal_invoice_term_id.fal_invoice_rules', store=True)
    fal_invoice_rules_type = fields.Selection([
        ('percentage', 'By percentage'),
        ('amount', 'By Exact Amount'),
    ], string="Rules Type", related='fal_invoice_term_id.fal_invoice_rules_type', store=True)
    fal_invoice_term_type = fields.Selection(
        'Invoice Term Type', related='fal_invoice_term_id.type')
    # 3. Invoice Term Line
    fal_invoice_milestone_line_date_ids = fields.One2many(
        "fal.invoice.term.line", "fal_sale_order_line_id",
        string="Term Lines", copy=False)

    def get_components(self):
        rule_line = self.fal_invoice_milestone_line_date_ids.filtered(lambda self: not self.invoice_id and self.invoice_id.state != 'cancel')
        policy = dict(self.product_id._fields['invoice_policy']._description_selection(self.env)).get(self.product_id.invoice_policy)
        service_policy = self.env['ir.model.fields'].search([('name', '=', 'service_policy')])
        if service_policy and self.product_id.type == 'service':
            policy = dict(self.product_id._fields['service_policy']._description_selection(self.env)).get(self.product_id.service_policy)

        vals = {
            'invoiced': True,
            'invoice_policy': policy,
            'rule_lines': self.fal_invoice_milestone_line_date_ids.ids,
            'term_id': self.order_id.fal_invoice_term_id.id or False,
        }

        if rule_line:
            number = 0
            for item in self.fal_invoice_milestone_line_date_ids:
                number += 1
                if item == rule_line[0]:
                    break
            vals.update({
                'number_of_invoice': "%s of %s" % (number, len(self.fal_invoice_milestone_line_date_ids)),
                'percentage': rule_line[0].percentage,
                'date': rule_line[0].date or "",
                'invoiced': False,
            })

        return vals

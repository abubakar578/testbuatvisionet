from odoo import api, fields, models, _
from odoo.exceptions import UserError
from datetime import datetime
import math
from itertools import groupby
from operator import itemgetter
from datetime import timedelta
from dateutil.relativedelta import relativedelta


class FalInvoiceTerm(models.Model):
    _name = 'fal.invoice.term'
    _description = 'Invoice Rule'
    _inherit = ['mail.thread']
    ############################################################################################
    # Invoice Term Object
    # The Idea is to have 1 parent object to help managing your invoice term line.
    # But the full control should be on the invoice term line

    ############################################################################################
    # Fields Definition
    # 0. Standard Info
    active = fields.Boolean('Active', default=1)
    name = fields.Char('Name', size=64, required=1)
    sequence = fields.Integer('Sequence', default=10)
    product_id = fields.Many2one('product.product', string='Product')
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company)
    # 1. Templating, so It's easy to create a new invoice term
    is_template = fields.Boolean(string="Is template")
    fal_template_id = fields.Many2one('fal.invoice.term', string="Template", domain=[('is_template', '=', True)])
    # 2. We have 2 kinds of Invoice term rules
    #    By Milestone / Subscription
    #    The main difference is that by milestone, we will take the number / amount of the sales
    #    By subsription, we will use the quantity of the product sold
    fal_invoice_rules = fields.Selection([
        ('milestone', 'Invoice Milestone'),
        ('subscription', 'Subscription'),
    ], string='Rules', required=True, default='milestone')
    # 3. We can define The rules type, so we can choose to downpayment based on percentage / amount
    fal_invoice_rules_type = fields.Selection([
        ('percentage', 'By percentage'),
        ('amount', 'By Exact Amount'),
    ], string="Rules Type", required=True, default='percentage')
    # 4. Manage the Subscription Type Interval / Date
    date_start = fields.Date(string='Start Date', default=fields.Date.today)
    recurring_rule_type = fields.Selection([
        ('daily', 'Day(s)'), ('weekly', 'Week(s)'),
        ('monthly', 'Month(s)'), ('yearly', 'Year(s)'), ],
        string='Recurrence', required=True, help="Invoice automatically repeat at specified interval", default='monthly')
    recurring_interval = fields.Integer(string="Repeat Every", help="Repeat every (Days/Week/Month/Year)", required=True, default=1, tracking=True)
    recurring_rule_boundary = fields.Selection([
        ('unlimited', 'Forever'),
        ('limited', 'Fixed')
    ], string='Duration', default='unlimited')
    recurring_rule_count = fields.Integer(string="End After", default=1, required=True)
    # 4. Invoice Terms Line Management
    fal_invoice_term_line_ids = fields.One2many('fal.invoice.term.line', 'fal_invoice_term_id', tracking=True)
    # 5. Computed Info Fields
    total_amount = fields.Float(compute="_compute_total_amount", string="Total Amount", store=1)
    total_percentage = fields.Float(compute="_compute_total_percentage", string="Total Percentage(%)", store=1)
    sale_order_ids = fields.Many2many('sale.order', string='Sale Order', compute="_get_related_sale_order")
    # To be deleted fields
    type = fields.Selection(
        [
            ('date', 'By Date'),
        ],
        'Type', default='date', required=1)

    ########################################################################################
    # Constrains
    # Should limit Percentage not to be above 100%
    @api.constrains('total_percentage')
    def _check_total_percentage(self):
        for invoiceTerm in self:
            ctx = dict(invoiceTerm._context)
            if not ctx.get('from_template'):
                if invoiceTerm.fal_invoice_rules == 'milestone':
                    if invoiceTerm.fal_invoice_rules_type == 'percentage':
                        if invoiceTerm.total_percentage > 100:
                            raise UserError(_("Total Percentage cannot be greater than 100"))
                            if invoiceTerm.fal_invoice_term_line_ids and invoiceTerm.total_percentage < 100:
                                raise UserError(_("Total Percentage cannot be lower than 100"))

    ########################################################################################
    # Formula for Computed Fields
    def _get_related_sale_order(self):
        for rule in self:
            so = self.env['sale.order'].search([('fal_invoice_term_id', '=', rule.id)])
            rule.sale_order_ids = [(6, 0, so.ids)]

    @api.depends('fal_invoice_term_line_ids', 'fal_invoice_term_line_ids.percentage')
    def _compute_total_percentage(self):
        for invoiceTerm in self:
            temp = 0
            for line in invoiceTerm.fal_invoice_term_line_ids:
                temp += line.percentage
            invoiceTerm.total_percentage = temp

    @api.depends('fal_invoice_term_line_ids', 'fal_invoice_term_line_ids.amount')
    def _compute_total_amount(self):
        for invoiceTerm in self:
            temp = 0
            for line in invoiceTerm.fal_invoice_term_line_ids:
                temp += line.amount
            invoiceTerm.total_amount = temp

    #########################################################################################
    # Method if you are in template, to automatically duplicate and create a new terms
    def take_template(self):
        for term in self:
            invoice_rules = term.with_context({'from_template': True}).copy(default={'is_template': False, 'fal_template_id': term.id})
            for line in term.fal_invoice_term_line_ids:
                line.with_context({'from_template': True}).copy(default={'fal_invoice_term_id': invoice_rules.id})

            invoice_rules.onchange_type()

            return {
                'name': _('Invoice Terms'),
                'view_type': 'form',
                'view_mode': 'form',
                'res_model': 'fal.invoice.term',
                'type': 'ir.actions.act_window',
                'res_id': invoice_rules.id,
                'target': 'current'
            }

    #########################################################################################
    # Onchange
    # Get the template information if you select template
    @api.onchange('fal_template_id')
    def _onchange_template(self):
        if self.fal_template_id:
            if len(self.sale_order_ids.filtered(lambda x: x.state in ['sale', 'done'])) > 0:
                raise UserError("You can only modify Date / Forecast Date on Terms Line if it already has sale order related.")
            else:
                self.fal_invoice_term_line_ids = False
                self.fal_invoice_rules = self.fal_template_id.fal_invoice_rules
                self.fal_invoice_rules_type = self.fal_template_id.fal_invoice_rules_type
                self.recurring_rule_type = self.fal_template_id.recurring_rule_type
                self.recurring_interval = self.fal_template_id.recurring_interval
                self.recurring_rule_boundary = self.fal_template_id.recurring_rule_boundary
                self.recurring_rule_count = self.fal_template_id.recurring_rule_count
                self.product_id = self.fal_template_id.product_id.id
                ruleline = []
                for line in self.fal_template_id.fal_invoice_term_line_ids:
                    ruleline.append((0, 0, {
                        'percentage': line.percentage,
                        'company_id': line.company_id.id,
                        'fal_invoice_rules': line.fal_invoice_rules,
                        'fal_invoice_rules_type': line.fal_invoice_rules_type,
                        'date': line.date,
                        'sequence': line.sequence,
                        'product_id': line.product_id.id,
                        'name': line.name,
                        'description': line.description,
                    }))
                self.fal_invoice_term_line_ids = ruleline

    # Manage automation of Subscription Type Milestone
    @api.onchange('fal_invoice_rules', 'recurring_rule_count', 'recurring_rule_type', 'recurring_interval', 'date_start')
    def onchange_type(self):
        temp = []
        if self.fal_invoice_rules == 'subscription':
            # First We Remove the current Invoice Term
            if len(self.sale_order_ids.filtered(lambda x: x.state in ['sale', 'done'])) > 0:
                raise UserError("You can only modify Date / Forecast Date on Terms Line if it already has sale order related.")
            self.fal_invoice_term_line_ids = False
            # Calculate the number of looping we need to do, The interval / jump.
            percent = 100
            int_frequency = percent / self.recurring_rule_count
            int_percent = round(int_frequency, 2)
            seq = 0
            val_order_date = self.date_start
            int_days = self.recurring_interval
            # Do Looping Until Percent is 0
            for index in range(self.recurring_rule_count):
                seq += 1
                if index == (self.recurring_rule_count - 1):
                    temp.append((0, 0, {
                        'percentage': percent,
                        'company_id': self.company_id.id,
                        'fal_invoice_rules': self.fal_invoice_rules,
                        'date': val_order_date,
                        'sequence': seq,
                        'description': "Subscription Term %s" % (seq),
                    }))
                else:
                    temp.append((0, 0, {
                        'percentage': int_percent,
                        'company_id': self.company_id.id,
                        'fal_invoice_rules': self.fal_invoice_rules,
                        'date': val_order_date,
                        'sequence': seq,
                        'description': "Subscription Term %s" % (seq),
                    }))
                if val_order_date:
                    if self.recurring_rule_type == 'daily':
                        val_order_date = val_order_date + relativedelta(days=int_days)
                    elif self.recurring_rule_type == 'weekly':
                        val_order_date = val_order_date + relativedelta(weeks=int_days)
                    elif self.recurring_rule_type == 'monthly':
                        val_order_date = val_order_date + relativedelta(months=int_days)
                    elif self.recurring_rule_type == 'yearly':
                        val_order_date = val_order_date + relativedelta(years=int_days)
                percent -= int_percent
        self.fal_invoice_term_line_ids = temp

    #################################################################################################
    # Override Odoo Meta Method
    # If it's already have relation to sale, do not allow to delete, because it will mess up the link
    def unlink(self):
        if self.sale_order_ids:
            raise UserError("You can't delete Invoice terms if it already has sale order related.")
        return super().unlink()


class FalInvoiceTermLine(models.Model):
    _name = 'fal.invoice.term.line'
    _description = 'Invoice Term Line'
    _order = 'date, sequence, id'
    _inherit = ['mail.thread']

    #############################################################################################
    # Core Models for this feature
    # It holds information of when it will create the invoices, and what kind of invoices it creates

    #############################################################################################
    # Fields Definition
    # 0. Standard Field Definition
    sequence = fields.Integer('Sequence', default=lambda self: self.env['ir.sequence'].next_by_code('term.line.sequence'))
    product_id = fields.Many2one('product.product', 'Product', tracking=True)
    name = fields.Char(string='Description Product', related="product_id.name")
    description = fields.Char(string='Description Line')
    percentage = fields.Float('Percentage (%)', tracking=True, required="1")
    amount = fields.Float('Exact Amount', tracking=True)
    date = fields.Date('Invoice Date', tracking=True)
    invoice_forecast_date = fields.Date("Invoice Forecast Date", tracking=True)
    is_final = fields.Boolean('Is Final Term', compute='_compute_is_final', tracking=True)
    company_id = fields.Many2one('res.company')
    # 1. Templating Process
    is_template = fields.Boolean(string="Is template", related="fal_invoice_term_id.is_template")
    # 2. Type of Invoice Term lines
    #    It will define the behavior when the CRON to create invoice is called
    fal_invoice_rules = fields.Selection([
        ('milestone', 'Invoice Milestone'),
        ('subscription', 'Subscription'),
    ], string='Rules')
    fal_invoice_rules_type = fields.Selection([
        ('percentage', 'By percentage'),
        ('amount', 'By Exact Amount'),
    ], string="Rules Type")
    # 3. Parent-Child Defintion
    #    Each Term Line can create another term line and relate each other,
    #    The concept is that you can manage the term line on the term object, and it will automatically propagate to the childs
    parent_id = fields.Many2one('fal.invoice.term.line', string="Manage On")
    child_ids = fields.One2many('fal.invoice.term.line', 'parent_id', string="Managing")
    # 4. Term can relate to invoice term / sales order
    #    If it related to invoice term, it is used as parent (should be)
    #    If it related to sales Line, it is the childs
    fal_invoice_term_id = fields.Many2one('fal.invoice.term', 'Invoice Term')
    fal_sale_order_line_id = fields.Many2one("sale.order.line", string="Order Line")
    fal_sale_order_id = fields.Many2one("sale.order", related="fal_sale_order_line_id.order_id", string="Sale Order", store=True)
    # 5. If it's managed on sales order line, we need the sales order line info, so It's more clear
    sale_line_product_id = fields.Many2one('product.product', 'Sale Line Product', related="fal_sale_order_line_id.product_id")
    sale_line_name = fields.Text('Sale Line Description', related="fal_sale_order_line_id.name")
    # 6. Info of invoice created
    invoice_id = fields.Many2one("account.move", string="Invoice", copy=False)
    # 7. Info Field
    total_amount = fields.Float(string="Total Amount", compute='_compute_total_amount', store=True)
    # To be deleted module
    invoice_term_type = fields.Selection(
        'Invoice Rule Type', related='fal_invoice_term_id.type',
        tracking=True)

    ###################################################################################################
    # Logic Of Computed Field
    # Amount if term line is percentage
    @api.depends('percentage', 'fal_sale_order_line_id', 'fal_sale_order_line_id.price_unit', 'fal_sale_order_line_id.product_uom_qty')
    def _compute_total_amount(self):
        for term_line in self:
            term_line.total_amount = (term_line.percentage * term_line.fal_sale_order_line_id.price_subtotal) / 100

    # Logic to define of term line is final
    @api.depends('sequence', 'date', 'fal_invoice_term_id', 'fal_invoice_term_id.fal_invoice_term_line_ids')
    def _compute_is_final(self):
        for term_line in self:
            # It either on Invoice Term / Sales order Line
            if term_line.fal_invoice_term_id and term_line.fal_sale_order_line_id:
                # This Shouldn't Be happening
                term_line.is_final = False

            # Separate Function depends on what kind of term line
            last_term_line_id = False
            if term_line.fal_invoice_term_id:
                term_line_ids = term_line.fal_invoice_term_id.fal_invoice_term_line_ids
                last_term_line_id = term_line_ids.sorted(key=lambda x: x.sequence, reverse=True)[0]
            elif term_line.fal_sale_order_line_id:
                term_line_ids = term_line.fal_sale_order_line_id.fal_invoice_milestone_line_date_ids
                last_term_line_id = term_line_ids.sorted(key=lambda x: x.sequence, reverse=True)[0]
            term_line.is_final = True if term_line == last_term_line_id else False

    ##################################################################################################
    # Onchange Field
    # Info of product
    @api.onchange('product_id')
    def onchange_product_id(self):
        self.description = self.product_id.name
    ###################################################################################################
    # Override Odoo Write
    # So that if there is change on here, it applies on all the child
    def write(self, vals):
        res = super(FalInvoiceTermLine, self).write(vals)
        for term in self:
            if 'date' or 'invoice_forecast_date' in vals:
                for termline in term.child_ids.filtered(lambda x: not x.invoice_id):
                    termline.sudo().write({
                        'date': term.date,
                        'invoice_forecast_date': term.invoice_forecast_date,
                    })
        return res

    # If it's already have relation to sale order line, do not allow to delete, because it will mess up the link
    def unlink(self):
        if self.fal_sale_order_line_id:
            raise UserError("You can't delete Invoice terms Line if it already has sale order line related.")
        return super().unlink()

    ###################################################################################################
    # Main Method to generate invoice
    @api.model
    def _cron_generate_invoice_order_line_by_planning_date(self):
        current_date = fields.Date.today()
        term_line_ids = self.search([
            ('date', '<=', current_date),
            ('fal_sale_order_line_id', '!=', False),
            ('invoice_id', '=', False),
            ('fal_sale_order_id.state', '=', 'sale'),
            ('fal_sale_order_id.fal_milestone_by_cron', '=', True)])
        return term_line_ids._generate_invoice_order_line_by_planning_date()

    def _generate_invoice_order_line_by_planning_date(self):
        advance_wizard_obj = self.env['sale.advance.payment.inv']
        for term_line in self:
            orderline = term_line.fal_sale_order_line_id
            order = orderline.order_id
            context_invoice = dict(self.env.context, company_id=order.company_id.id, force_company=order.company_id.id)
            # If Subscription
            # Just Call Odoo Standard Prepare Invoices, but with Qty Predefined
            if term_line.fal_invoice_rules == 'subscription':
                invoice_obj = self.env['account.move']
                vals = order._prepare_invoice()
                qty = orderline.product_uom_qty / order.fal_invoice_term_id.recurring_rule_count
                vals_line = orderline.with_context(context_invoice)._prepare_invoice_line()
                vals_line.update({'quantity': qty})
                vals['invoice_line_ids'].append((0, 0, vals_line))
                inv_id = invoice_obj.with_context(context_invoice).create(vals)
                inv_id._onchange_invoice_line_ids()
                term_line.invoice_id = inv_id.id
                inv_id.invoice_date = term_line.date
            # If Type Milestone, we use Odoo standard Downpayment Method
            else:
                if not term_line.is_final:
                    # Call Odoo downpayment Wizard function
                    wizard_vals = {
                        'advance_payment_method': 'percentage' if order.fal_invoice_term_id.fal_invoice_rules_type == 'percentage' else 'fixed',
                        'amount': term_line.percentage if order.fal_invoice_term_id.fal_invoice_rules_type == 'percentage' else term_line.amount,
                        'product_id': term_line.product_id.id,
                    }
                    advPmnt = advance_wizard_obj.create(wizard_vals)
                    advPmnt.with_context({
                        'active_ids': [order.id],
                        'so_line': orderline,
                        'term_line': term_line}).create_invoices()
                else:
                    # Call Odoo downpayment Wizard function
                    wizard_vals = {
                        'advance_payment_method': 'delivered',
                    }
                    advPmnt = advance_wizard_obj.create(wizard_vals)
                    advPmnt.with_context({
                        'active_ids': [order.id],
                        'so_line': orderline,
                        'term_line': term_line}).create_invoices()
        # If we have 2 or more Lines on sales order, and the date is similar, it's better to have 1 invoice
        # As we don't have merge invoice module, we postpone this feature
        sale_order = self.mapped('fal_sale_order_id')
        merge_wizard_obj = self.env['fal.invoice.merge.wizard']
        for sale in sale_order:
            _type = []
            res = {}
            for term in self.filtered(lambda a: a.fal_sale_order_id == sale):
                _type.append((term.date, term))
            for date, val in _type:
                if date in res:
                    res[date] += val
                else:
                    res[date] = val
            for key in res:
                invoice_ids = []
                date = False
                for term_id in res[key]:
                    invoice_ids.append(term_id.invoice_id.id)
                    date = term_id.date
                    term_id.invoice_id.invoice_date = date
                # Merge Invoice
                if len(invoice_ids) > 1:
                    wizard_vals = {
                        'inv_action': 'remove',
                        'invoice_date': date,
                    }
                    invoice_merge = merge_wizard_obj.with_context({
                        'active_ids': invoice_ids}).create(wizard_vals)
                    inv = invoice_merge.action_merge_invoice()
                    for term_id in res[key]:
                        # put invoice after merge
                        get_inv = False
                        try:
                            get_inv = inv['domain'][0][2][0]
                        except ValueError:
                            get_inv = False
                        term_id.invoice_id = get_inv
        return True

    ################################################################################################
    # Action Method
    # Open Form View on Term Line
    def action_open_form_view(self):
        self.ensure_one()
        if self.invoice_id:
            raise UserError(_('You cannot edit invoice term line that already invoiced'))
        return{
            'name': _('Invoice Rule Line'),
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'fal.invoice.term.line',
            'view_id': self.env.ref('fal_invoice_milestone.fal_invoice_term_line_form').id,
            'type': 'ir.actions.act_window',
            'res_id': self.id,
            'target': 'new',
        }

    def open_change_term_line(self):
        term_line_ids = self.search([
            ('parent_id', '=', self.id),
            ('invoice_id', '=', False),
            ('fal_sale_order_line_id', '!=', False),
        ])
        context = {
            'default_fal_invoice_term_line_ids': [(6, 0, term_line_ids.ids)],
            'default_date': self.date,
            'default_invoice_forecast_date': self.invoice_forecast_date,
            'default_term_line': self.id,
        }
        return {
            'name': _('Change Line'),
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'change.term.line.wizard',
            'view_id': self.env.ref('fal_invoice_milestone.fal_change_term_line_wizard').id,
            'type': 'ir.actions.act_window',
            'target': 'new',
            'context': context,
        }

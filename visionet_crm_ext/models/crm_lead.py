import logging
from odoo import models, api, fields, _
from odoo.exceptions import UserError, ValidationError
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from google.cloud import bigquery
from google.oauth2 import service_account

_logger = logging.getLogger(__name__)

credentials = service_account.Credentials.from_service_account_file(
    '/home/odoo/src/user/visionet_crm_ext/static/pdashboard-295910-0488194fd1cc.json', scopes=["https://www.googleapis.com/auth/cloud-platform"],
)


class CrmLead(models.Model):
    _inherit = 'crm.lead'

    end_user = fields.Many2one('res.partner', string='End User', tracking=True, required=True)
    start_date = fields.Date('Start Date', help="Estimate of Expected Start Date", default=fields.date.today(), tracking=True)
    product = fields.Many2one('product.template', string='Product', tracking=True)
    remarks = fields.Char('Remark', size=100)
    contract_period = fields.Integer(string="Contract Period", tracking=True)
    bill_period = fields.Integer(string="Bill Period", tracking=True)
    project_id = fields.Many2one('visionet.project', string="PID")
    recuring = fields.Boolean('Recuring', default=True)
    initial_value = fields.Float('Initial Value', tracking=True)
    member_ids = fields.One2many('res.users', string="Member ID", related="product.department.member_ids")
    sales_member_ids = fields.One2many('res.users', string="Sales Member", related="team_id.member_ids")
    product_department = fields.Many2one('crm.team', string='Product Department', related='product.department' ,required=True)
    total_weighted_amount = fields.Monetary(string='Total Weighted Amount', currency_field='company_currency', store=True, readonly=True, compute="_amount_total")
    stage_crm = fields.Many2one('crm.stage', string='Sales Cycle', index=True, tracking=True)
    amount_total = fields.Monetary('Amount Total', currency_field='company_currency', tracking=True, compute="_amount_total")
    presales = fields.Many2one('res.users', index=True, tracking=True, default=False, required=True)
    date_deadline = fields.Date('Expected Closing', tracking=True, help="Estimate of the date on which the opportunity will be won.")
    term_line_ids = fields.One2many('fal.invoice.term.line', 'crm_id', string="Term Line", tracking=True)
    is_last_member = fields.Boolean('Last Member', related='user_id.is_last_member')
    invoice_term_id = fields.Many2one('fal.invoice.term', string="Invoice Template")
    vis_probability = fields.Selection([
            ('l', 'L'),
            ('m', 'M'),
            ('h', 'H'),
            ('c', 'C'),
            ('d', 'D'),
        ], default='l', tracking=True)
    is_email_send = fields.Boolean(string='Send email after 30 days', default=False, compute="overdue_thirty", store=True)
    is_email_send_2 = fields.Boolean(string='Send email after 60 days', default=False, compute="overdue_sixty", store=True)

    @api.depends('date_deadline')
    def overdue_thirty(self):
        record = self.search([('active' ,'=', True)])
        for lead in record:
            if lead.date_deadline:
                after_date1 = (datetime.strptime(str(lead.date_deadline), '%Y-%m-%d') + relativedelta(days = 30))
                after_date2 = (datetime.strptime(str(lead.date_deadline), '%Y-%m-%d') + relativedelta(days = 60))
                if datetime.now() >= after_date1 and lead.is_email_send == False:
                    lead.is_email_send = True
                elif datetime.now() <= after_date1:
                    lead.is_email_send = False

    @api.depends('date_deadline')
    def overdue_sixty(self):
        record = self.search([('active' ,'=', True)])
        for lead in record:
            if lead.date_deadline:
                after_date1 = (datetime.strptime(str(lead.date_deadline), '%Y-%m-%d') + relativedelta(days = 30))
                after_date2 = (datetime.strptime(str(lead.date_deadline), '%Y-%m-%d') + relativedelta(days = 60))
                if datetime.now() >= after_date2 and lead.is_email_send_2 == False:
                    lead.is_email_send_2 = True
                elif datetime.now() <= after_date2:
                    lead.is_email_send_2 = False

    @api.constrains('date_deadline', 'start_date')
    def _check_date_crm(self):
        for record in self:
            if record.start_date <= record.date_deadline:
                raise ValidationError('Start Date must be greater than Expected Closing')

    @api.onchange("date_deadline", "start_date")
    def _onchange_dates(self):
        res = {}
        if self.start_date and self.date_deadline and self.start_date <= self.date_deadline:
            res['warning'] = {
                'title': _("Warning on Date"),
                'message': _('Start Date must be greater than Expected Closing')
            }
            return res

    @api.constrains('initial_value', 'bill_period', 'contract_period')
    def _check_initial_value(self):
        for record in self.filtered(lambda x: x.recuring):
            if record.initial_value <= 0:
                raise ValidationError('Iniatial value be greater than 0.00')
            if record.contract_period <= 0:
                raise ValidationError('Contract period be greater than 0')
            if record.bill_period <= 0:
                raise ValidationError('Bill Period must be greater than 0')

    @api.onchange('vis_probability', 'probability')
    def _onchange_vis_probability(self):
        if self.vis_probability == 'l':
            self.automated_probability = self.probability = 25
        elif self.vis_probability == 'm':
            self.automated_probability = self.probability = 50
        elif self.vis_probability == 'h':
            self.automated_probability = self.probability = 75
        elif self.vis_probability == 'c':
            self.automated_probability = self.probability = 100
        else:
            self.automated_probability = self.probability = 0

    @api.onchange('stage_crm', 'recuring', 'initial_value', 'contract_period', 'bill_period')
    def _onchange_stage_crm(self):
        if self.stage_crm:
            self.stage_id = self.stage_crm
        if self.recuring or self.initial_value or self.contract_period or self.bill_period:
            self.write({'invoice_term_id': False})

    @api.depends('term_line_ids', 'term_line_ids.values')
    def _amount_total(self):
        for order in self:
            amount_total = weighted_amount = 0.0
            for line in order.term_line_ids:
                amount_total += line.values
                weighted_amount += line.weighted_amount
            admin = self.env.ref('base.user_admin')
            order.with_user(order.user_id or admin).update({
                'amount_total': amount_total,
                'total_weighted_amount': weighted_amount,
                'expected_revenue': amount_total,
            })

    def _generate_milestone(self):
        for lead in self:
            if lead.recuring == True:
                if lead.contract_period % lead.bill_period == 0:
                    loops = lead.contract_period / lead.bill_period
                    price = lead.initial_value * lead.bill_period
                    # lead.expected_revenue = price
                    invoice_term_id = self.env['fal.invoice.term'].create({
                        'name': lead.name or '',
                        'fal_template_id': False,
                        'fal_invoice_rules': 'subscription',
                        'recurring_interval': lead.bill_period or 1,
                        'recurring_rule_type': 'monthly',
                        'recurring_rule_count': loops or 1,
                        'date_start': lead.start_date,
                        'type': 'date',
                    })
                    invoice_term_id.onchange_type()
                    lead.update({
                        'invoice_term_id': invoice_term_id.id,
                        'term_line_ids': invoice_term_id.fal_invoice_term_line_ids.ids
                    })
                    for i in range(int(loops)):
                        lead.term_line_ids.write({
                            'values': price,
                            'remarks': lead.remarks,
                        })
                else:
                    raise UserError(
                        _("You Can Not Create Invoice with Float")
                    )

            else:
                invoice_term_id = self.env['fal.invoice.term'].create({
                    'name': lead.name or '',
                    'fal_template_id': False,
                    'fal_invoice_rules': 'subscription',
                    'recurring_interval': 1,
                    'recurring_rule_type': 'monthly',
                    'recurring_rule_count': 1,
                    'date_start': lead.start_date,
                    'type': 'date',
                })
                invoice_term_id.onchange_type()
                lead.update({
                    'invoice_term_id': invoice_term_id.id,
                    'term_line_ids': invoice_term_id.fal_invoice_term_line_ids.ids
                })
                for line in lead.term_line_ids:
                    line.write({
                        'values': lead.initial_value,
                        'remarks': lead.remarks,
                    })

            return invoice_term_id

    @api.model_create_multi
    def create(self, vals_list):
        res = super(CrmLead, self).create(vals_list)
        res._generate_milestone()
        return res

    def compute_term(self):
        self.ensure_one()
        self._generate_milestone()

    def push_to_googlebq(self):
        for lead in self:
            client = bigquery.Client(project="pdashboard-295910", credentials=credentials)
            delete = """
                DELETE FROM `pdashboard-295910.SalesPipeline.PipelineOdooDev` WHERE RevenueID = %s
            """ % (lead.id)
            client.query(delete)

            for line in lead.term_line_ids:
                update_query = """
                    INSERT INTO `pdashboard-295910.SalesPipeline.PipelineOdooDev` (Opportunity, RevenueID, Customer, EndUser, StartDate, ExpectedClosing, Product, Probability, ProjectID, SalesDepartment, BusinessRepresentative, ProductDepartment, PresalesMember, InvoiceDate, TotalAmount) VALUES ('%s', %s, '%s', '%s', '%s', '%s', '%s', '%s', '%s', '%s', '%s', '%s', '%s', '%s', '%s')
                """ % (lead.name, lead.id, lead.partner_id.name, lead.end_user.name, lead.start_date.strftime('%Y-%m-%d'), lead.date_deadline.strftime('%Y-%m-%d'), lead.product.name, lead.vis_probability.upper(), lead.project_id and lead.project_id.name or '', lead.team_id.name, lead.user_id.name, lead.product_department.name, lead.presales.name, line.date.strftime('%Y-%m-%d'), int(line.values))
                client.query(update_query)


class CrmTeam(models.Model):
    _inherit = 'crm.team'

    parent_id = fields.Many2one('crm.team', string='Parent Department')
    child_ids = fields.One2many('crm.team', 'parent_id', 'Child Departments')
    invoiced_target = fields.Float(
        string='Invoicing Target',
        compute='_total_target',
        help="Revenue target for the current month (untaxed total of confirmed invoices).")
    department_type = fields.Selection([
        ('sales department', 'Sales Department'),
        ('product department', 'Product Department')], default='sales department', string="Department Type")
    team_member_ids = fields.Many2many('res.users', string='Team Members', check_company=True, domain=[('share', '=', False)], compute='_get_team_member')

    @api.depends('member_ids')
    def _get_team_member(self):
        self.team_member_ids = False
        self.team_member_ids = [(6, 0, self.user_id.team_member_ids.ids)]
        return {'domain': {'member_ids': [('id', '=', self.user_id.team_member_ids.ids)]}}

    @api.depends('member_ids.total_target')
    def _total_target(self):
        for target in self:
            total_target = 0.0
            for line in target.member_ids:
                total_target += line.total_target
            target.update({
                'invoiced_target': total_target,
            })

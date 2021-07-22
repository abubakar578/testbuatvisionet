import logging
from odoo import models, api, fields, _
from datetime import date

from google.cloud import bigquery
from google.oauth2 import service_account

_logger = logging.getLogger(__name__)

credentials = service_account.Credentials.from_service_account_file(
    '/home/odoo/src/user/visionet_crm_ext/static/pdashboard-295910-0488194fd1cc.json', scopes=["https://www.googleapis.com/auth/cloud-platform"],
)


class FalInvoiceTermLine(models.Model):
    _inherit = 'fal.invoice.term.line'
    _description = 'Invoice Term Line'

    crm_id = fields.Many2one('crm.lead', string="CRM ID")
    sales_target_id = fields.Many2one('visionet.target', string="Sales Target")
    values = fields.Float(string="Total Amount", store=True)
    remarks = fields.Char('Remark', size=100)
    percentage = fields.Float('Percentage (%)', tracking=True, required=False)
    weighted_amount = fields.Float(string='Weighted Amount', compute='_compute_weight_amount', readonly=True, store=True)
    target_name_vis = fields.Char(string='Target Name', related='sales_target_id.name', readonly=True, store=True)
    start_date_vis = fields.Date(string='Date Start Visionet', related='sales_target_id.start_date', readonly=True, store=True)
    end_date_vis = fields.Date(string='Date End Visionet', related='sales_target_id.end_date', readonly=True, store=True)
    target_vis = fields.Integer(string='Visionet Total Target', related='sales_target_id.target', readonly=True, store=True)


    # field untuk pivot
    visionet_currency = fields.Many2one("res.currency", string='Currency', related='crm_id.company_currency', readonly=True)
    rel_name = fields.Char(string='Project Name', readonly=True, related='crm_id.name', store=True)
    rel_expected_revenue = fields.Monetary(string='Expected Revenue', currency_field='visionet_currency', readonly=True, related='crm_id.expected_revenue', store=True)
    rel_probability = fields.Float(string='Probability',related='crm_id.probability', readonly=True, store=True)
    rel_prorated_revenue = fields.Monetary(string='Prorated Revenue',related='crm_id.prorated_revenue', currency_field='visionet_currency', readonly=True, store=True)
    rel_partner_id = fields.Many2one('res.partner', string='Customers',related='crm_id.partner_id', readonly=True, store=True)
    rel_end_user = fields.Many2one('res.partner', string='End User',related='crm_id.end_user', readonly=True, store=True)
    rel_date_deadline = fields.Date(string='Date Deadline', related='crm_id.date_deadline', readonly=True, store=True)
    rel_start_date = fields.Date(string='Date Start', related='crm_id.start_date', readonly=True, store=True)
    rel_product = fields.Many2one('product.template', string='Product', related='crm_id.product', readonly=True, store=True)
    rel_vis_probability = fields.Selection(string='vis Probability', related='crm_id.vis_probability', readonly=True, store=True)
    rel_stage_crm = fields.Many2one('crm.stage', string='CRM stage', related='crm_id.stage_crm', readonly=True, store=True)
    rel_project_id = fields.Many2one('visionet.project', string='Project ID', related='crm_id.project_id', readonly=True, store=True)
    rel_recuring = fields.Boolean(string='Checkbox', related='crm_id.recuring', readonly=True, store=True)
    rel_contract_period = fields.Integer(string='Contract Period', related='crm_id.contract_period', readonly=True, store=True)
    rel_bill_period = fields.Integer(string='Bill Period', related='crm_id.bill_period', readonly=True, store=True)
    rel_user_id = fields.Many2one('res.users', string='Business Representative',related='crm_id.user_id', readonly=True, store=True)
    rel_team_id = fields.Many2one('crm.team', string='Sales Department',related='crm_id.team_id', readonly=True, store=True)
    rel_presales = fields.Many2one('res.users', string='Presales', related='crm_id.presales', readonly=True, store=True)
    rel_product_department = fields.Many2one('crm.team', string='Product Department', related='crm_id.product_department', readonly=True, store=True)
    # Big Query
    last_synchronize = fields.Datetime('')

    @api.depends('values', 'crm_id', 'crm_id.probability')
    def _compute_weight_amount(self):
        for rec in self:
            if rec.crm_id and rec.crm_id.probability:
                rec.weighted_amount = rec.values * rec.crm_id.probability / 100
            else:
                rec.weighted_amount = 0.0

    def insert_googlebq(self):
        for milestone in self:
            # Only push if CRM ID Exist
            if milestone.crm_id:
                client = bigquery.Client(project="pdashboard-295910", credentials=credentials)
                update_query = """
                    INSERT INTO `pdashboard-295910.SalesPipeline.PipelineOdooDev` (Opportunity, RevenueID, Customer, EndUser, StartDate, ExpectedClosing, Product, Probability, ProjectID, SalesDepartment, BusinessRepresentative, ProductDepartment, PresalesMember, InvoiceDate, TotalAmount) VALUES ('%s', %s, '%s', '%s', '%s', '%s', '%s', '%s', '%s', '%s', '%s', '%s', '%s', '%s', '%s')
                """ % (milestone.rel_name, milestone.id, milestone.rel_partner_id.name, milestone.rel_end_user.name, milestone.rel_start_date and milestone.rel_start_date.strftime('%Y-%m-%d') or '1999-01-01', milestone.rel_date_deadline and milestone.rel_date_deadline.strftime('%Y-%m-%d') or '1999-01-01', milestone.rel_product.name, milestone.rel_vis_probability and milestone.rel_vis_probability.upper() or 'X', milestone.rel_project_id and milestone.rel_project_id.name or '', milestone.rel_team_id.name, milestone.rel_user_id.name, milestone.rel_product_department.name, milestone.rel_presales.name, milestone.date and milestone.date.strftime('%Y-%m-%d') or '1999-01-01', int(milestone.values))
                client.query(update_query)

    def remove_googlebq(self):
        for milestone in self:
            client = bigquery.Client(project="pdashboard-295910", credentials=credentials)
            delete = """
                DELETE FROM `pdashboard-295910.SalesPipeline.PipelineOdooDev` WHERE RevenueID = %s
            """ % (milestone.id)
            client.query(delete)

    def update_googlebq(self):
        for milestone in self:
            client = bigquery.Client(project="pdashboard-295910", credentials=credentials)
            update = """
                UPDATE `pdashboard-295910.SalesPipeline.PipelineOdooDev` SET Opportunity = '%s', Customer = '%s', EndUser = '%s', StartDate = '%s', ExpectedClosing = '%s', Product = '%s', Probability = '%s', ProjectID = '%s', SalesDepartment = '%s', BusinessRepresentative = '%s', ProductDepartment = '%s', PresalesMember = '%s', InvoiceDate = '%s', TotalAmount = '%s' WHERE RevenueID = %s
            """ % (milestone.rel_name, milestone.rel_partner_id.name, milestone.rel_end_user.name, milestone.rel_start_date and milestone.rel_start_date.strftime('%Y-%m-%d') or '1999-01-01', milestone.rel_date_deadline and milestone.rel_date_deadline.strftime('%Y-%m-%d') or '1999-01-01', milestone.rel_product.name, milestone.rel_vis_probability and milestone.rel_vis_probability.upper() or 'X', milestone.rel_project_id and milestone.rel_project_id.name or '', milestone.rel_team_id.name, milestone.rel_user_id.name, milestone.rel_product_department.name, milestone.rel_presales.name, milestone.date and milestone.date.strftime('%Y-%m-%d') or '1999-01-01', int(milestone.values), milestone.id)
            client.query(update)

    def read_googlebq(self):
        for milestone in self:
            client = bigquery.Client(project="pdashboard-295910", credentials=credentials)
            select = """
                SELECT RevenueID FROM `pdashboard-295910.SalesPipeline.PipelineOdooDev` WHERE RevenueID = %s
            """ % (milestone.id)
            query_res_list = client.query(select)
            for query_res in query_res_list:
                return True
            return False

    def clean_googlebq(self):
        for milestone in self:
            client = bigquery.Client(project="pdashboard-295910", credentials=credentials)
            select = """
                SELECT RevenueID FROM `pdashboard-295910.SalesPipeline.PipelineOdooDev`
            """
            query_res_list = client.query(select)
            for query_res in query_res_list:
                if not self.search([('id', '=', query_res[0])]):
                    delete = """
                        DELETE FROM `pdashboard-295910.SalesPipeline.PipelineOdooDev` WHERE RevenueID = %s
                    """ % (query_res[0])
                    client.query(delete)

    def synchronize_to_googlebq(self):
        admin = self.env.ref('base.user_admin')
        for milestone in self.with_user(admin).search([]).filtered(lambda x: not x.last_synchronize or x.last_synchronize < x.write_date):
            if milestone.crm_id:
                if milestone.read_googlebq():
                    milestone.update_googlebq()
                else:
                    milestone.insert_googlebq()
            else:
                milestone.remove_googlebq()
            milestone.last_synchronize = fields.Datetime.now()

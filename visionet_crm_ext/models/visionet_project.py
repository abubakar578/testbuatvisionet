from odoo import api, fields, models, _
from google.cloud import bigquery
from google.oauth2 import service_account
import logging

_logger = logging.getLogger(__name__)

credentials = service_account.Credentials.from_service_account_file(
    '/home/odoo/src/user/visionet_crm_ext/static/pdashboard-295910-0488194fd1cc.json', scopes=["https://www.googleapis.com/auth/cloud-platform"],
)


class VisionetProject(models.Model):
    _name = 'visionet.project'
    _description = 'Visionet Project'

    name = fields.Char("Project")

    @api.model
    def name_search(self, name, args=None, operator='ilike', limit=100):
        # Before doing name search, we need to call from API
        self.get_pid()
        res = super(VisionetProject, self).name_search(name, args, operator, limit)
        return res

    def get_pid(self):
        client = bigquery.Client(project="pdashboard-295910", credentials=credentials)
        query = """
            SELECT ProjectID
            FROM `pdashboard-295910.SalesPipeline.ProjectIDDev`
        """
        query_job = client.query(query)
        for row in query_job:
            if not self.search([('name', '=', row[0])]):
                self.create({'name': row[0]})


class VisionetTarget(models.Model):
    _name = 'visionet.target'
    _description = 'Visionet Target'

    name = fields.Char("User target")
    user_id = fields.Many2one('res.users')
    start_date = fields.Date(string='Start Date')
    end_date = fields.Date(string='End Date')
    target = fields.Integer(string="Target")
    total_achievement = fields.Integer(string="Achievement", compute='_total_achievement', store=True)
    last_synchronize = fields.Datetime('')

    @api.depends('user_id.invoice_term_line_ids', 'user_id.invoice_term_line_ids.weighted_amount',
        'user_id.invoice_term_line_ids.rel_user_id', 'user_id.invoice_term_line_ids.rel_presales',
        'user_id.invoice_term_line_ids.date', 'user_id', 'start_date', 'end_date', 'target')
    def _total_achievement(self):
        for record in self:
            if record.target:
                domain = ['|', ('rel_user_id', '=', record.user_id.id), ('rel_presales', '=', record.user_id.id)]
                term_line_ids = self.env['fal.invoice.term.line'].search(domain + [('date', '>=', record.start_date), ('date', '<=', record.end_date)])
                amount = sum(term_line_id.weighted_amount for term_line_id in term_line_ids)
                record.write({
                    'total_achievement': amount
                })

    def insert_to_googlebq(self):
        for target in self:
            client = bigquery.Client(project="pdashboard-295910", credentials=credentials)

            insert_query = """
                INSERT INTO `pdashboard-295910.SalesPipeline.SalesTargetDev` (Name, TargetId, StartDate, EndDate, Target) VALUES ('%s', %s, '%s', '%s', %s)
            """ % (target.user_id.name or '', target.id, target.start_date and target.start_date.strftime('%Y-%m-%d') or '1999-01-01', target.end_date and target.end_date.strftime('%Y-%m-%d') or '1999-01-01', target.target or 0)
            client.query(insert_query)

    def remove_googlebq(self):
        for target in self:
            client = bigquery.Client(project="pdashboard-295910", credentials=credentials)
            delete = """
                DELETE FROM `pdashboard-295910.SalesPipeline.SalesTargetDev` WHERE TargetId = %s
            """ % (target.id)
            client.query(delete)

    def update_googlebq(self):
        for target in self:
            client = bigquery.Client(project="pdashboard-295910", credentials=credentials)
            update = """
                UPDATE `pdashboard-295910.SalesPipeline.PipelineOdooDev` SET Name = '%s', StartDate = '%s', EndDate = '%s', Target = %s WHERE TargetId = %s
            """ % (target.user_id.name, target.start_date.strftime('%Y-%m-%d'), target.end_date.strftime('%Y-%m-%d'), target.target or 0, target.id)
            client.query(update)

    def read_googlebq(self):
        for target in self:
            client = bigquery.Client(project="pdashboard-295910", credentials=credentials)
            select = """
                SELECT TargetId FROM `pdashboard-295910.SalesPipeline.SalesTargetDev` WHERE TargetId = %s
            """ % (target.id)
            query_res_list = client.query(select)
            for query_res in query_res_list:
                return True
            return False

    def clean_googlebq(self):
        for target in self:
            client = bigquery.Client(project="pdashboard-295910", credentials=credentials)
            select = """
                SELECT TargetId FROM `pdashboard-295910.SalesPipeline.SalesTargetDev`
            """
            query_res_list = client.query(select)
            for query_res in query_res_list:
                if not self.search([('id', '=', query_res[0])]):
                    delete = """
                        DELETE FROM `pdashboard-295910.SalesPipeline.SalesTargetDev` WHERE TargetId = %s
                    """ % (query_res[0])
                    client.query(delete)

    def synchronize_to_googlebq(self):
        admin = self.env.ref('base.user_admin')
        for target in self.with_user(admin).search([]).filtered(lambda x: not x.last_synchronize or x.last_synchronize < x.write_date):
            if target.user_id:
                if target.read_googlebq():
                    target.update_googlebq()
                else:
                    target.insert_to_googlebq()

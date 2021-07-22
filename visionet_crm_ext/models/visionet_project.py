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
            LIMIT 20
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
    total_achievement = fields.Integer(string="Achievement", compute="_total_achievement", tracking=True, store=True)

    def _total_achievement(self):
        for record in self:
            if record.target:
                term_line_ids = self.env['fal.invoice.term.line'].search([
                    ('rel_user_id', '=', record.user_id.id),
                    ('date', '>=', record.start_date),
                    ('date', '<=', record.end_date)])
                amount = sum(term_line_id.weighted_amount for term_line_id in term_line_ids)
                record.write({
                    'total_achievement': amount
                })

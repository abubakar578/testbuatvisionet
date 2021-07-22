# -*- coding: utf-8 -*-
from odoo import models, fields


class Meeting(models.Model):
    _inherit = 'calendar.event'

    presales = fields.Many2one('res.users', index=True, tracking=True)

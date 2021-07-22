# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from collections import defaultdict
from datetime import date, datetime
from dateutil.relativedelta import relativedelta
import logging
import pytz

from odoo import api, exceptions, fields, models, _
from odoo.osv import expression

from odoo.tools.misc import clean_context
from odoo.addons.base.models.ir_model import MODULE_UNINSTALL_FLAG

_logger = logging.getLogger(__name__)


class MailActivity(models.Model):
    _inherit = 'mail.activity'

    # ------------------------------------------------------
    # ORM overrides
    # ------------------------------------------------------

    @api.model
    def create(self, values):
        activity = super(MailActivity, self).create(values)
        # post message on activity, after creating it
        record = self.env[activity.res_model].browse(activity.res_id)
        record.message_post(
            body="Activity %s: %s Created" % (activity.res_name or '', activity.summary or ''),
            mail_activity_type_id=activity.activity_type_id.id,
        )
        return activity

    def write(self, values):
        res = super(MailActivity, self).write(values)
        # post message on activity, after modifying it
        record = self.env[self.res_model].browse(self.res_id)
        record.message_post(
            body="Activity %s: %s Modified" % (self.res_name or '', self.summary or ''),
            mail_activity_type_id=self.activity_type_id.id,
        )
        return res

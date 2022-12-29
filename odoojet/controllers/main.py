import functools
import logging
from odoo import http
from odoo.http import request
from odoo.addons.web.controllers.main import DataSet


_logger = logging.getLogger(__name__)


class DataSetinherit(DataSet):

    @http.route('/web/dataset/call_button', type='json', auth="user")
    def call_button(self, model, method, args, kwargs):
        res = super(DataSetinherit, self).call_button(model, method, args, kwargs)
        rule = request.env['odoojet.rule'].search([
            ('model_name', '=', model),
            ('btn_name', '=', method),
        ])
        if rule:
            rule_model = request.env["odoojet.rule"]
            rule_model.sudo().create_logs(
                request.env.uid,
                model,
                args[0],
                "Button %s" % method,
                None,
                None,
            )
        return res
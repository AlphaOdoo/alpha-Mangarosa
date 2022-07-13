from odoo import models, fields, api
from odoo.exceptions import UserError, ValidationError


class hrexpense(models.Model):
    _inherit = 'hr.expense'

    partner_id = fields.Many2one(comodel_name='res.partner',
                                 string='Proveedor',
                                 ondelete='set null', required=False)

    control_code = fields.Char(string='Codigo de Control', required=False)

    authorization_code = fields.Char(string='Codigo Autorizacion', required=False)

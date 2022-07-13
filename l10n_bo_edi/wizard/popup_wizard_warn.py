from odoo import models, fields, api

class Popupwarn(models.TransientModel):
    _name = "popup_warn_wizard"
    _description = "Simple popup warning"
    
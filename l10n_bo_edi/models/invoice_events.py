from odoo import fields, models


class Invoice_events(models.Model):
    _name = 'invoice_event'
    _description = 'BO EDI Invoice Events'

    code = fields.Char('code')

    description = fields.Char('Message')

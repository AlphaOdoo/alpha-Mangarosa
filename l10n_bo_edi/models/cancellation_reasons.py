from odoo import fields, models


class CancellationReasons(models.Model):
    _name = 'cancellation_reasons'
    _description = 'cancellation_reasons'

    code = fields.Integer('code')

    description = fields.Text('description')

    active = fields.Boolean(
        'Active', help='Allows you to hide the cancellation reasons without removing it.', default=True)

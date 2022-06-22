from odoo import fields, models, api


class SinItems(models.Model):
    _name = 'sin_items'
    _description = 'Items provided by SIN'

    sin_code = fields.Integer(string='ProductService Code')

    description = fields.Text(string='Description')

    activity_code = fields.Many2one(
        'l10n_bo.company.activities', string='Activity Code')

    active = fields.Boolean(
        'Active', help='Allows you to hide the Sin Items without removing it.', default=True)

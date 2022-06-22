from odoo import fields, models, api


class MeasureUnit(models.Model):
    _name = 'measure_unit'
    _description = 'Measure items provided by SIN'

    measure_unit_code = fields.Integer(string='Measure Unit Code')

    description = fields.Text(string='Description')

    active = fields.Boolean(
        'Active', help='Allows you to hide the Measure Unit without removing it.', default=True)

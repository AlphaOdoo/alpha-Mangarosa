from odoo import fields, models


class SellingPoint(models.Model):
    _name = 'selling_point'
    _description = 'selling_point'

    id_selling_point = fields.Integer(
        string='Selling Point Code', required=True)

    description = fields.Text(string='Description')

    branch_office_id = fields.Many2one(
        comodel_name='branch_office', string='Branch Office', ondelete='cascade', required=True)

    user_ids = fields.One2many(
        'res.users', 'l10n_bo_selling_point_id', string='Users in Charge')

    cufd_ids = fields.One2many(
        'cufd_log', 'selling_point', string='Cufd Related Codes')

    # pos_ids = fields.One2many(
    #     'pos.config', 'l10n_bo_selling_point_id', string='POS Related')

    invoice_dosage_ids = fields.One2many(
        'invoice_dosage', 'selling_point_id', string='Invoice Dosages')

    active = fields.Boolean(
        'Active', help='Allows you to hide the selling point without removing it.', default=True)

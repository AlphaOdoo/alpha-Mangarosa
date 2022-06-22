from odoo import fields, models


class CancelledInvoices(models.Model):
    _name = 'cancelled_invoices'
    _description = 'SIN cancelled invoices'

    payment_reference = fields.Char('payment_reference')

    # reason_id = fields.Many2one(
    #     'cancellation_reasons', string='Cancellation Reason')

    date = fields.Datetime('date')

    reversed = fields.Boolean('reversed')

    active = fields.Boolean(
        'Active', help='Allows you to hide the cancelled invoice without removing it.', default=True)

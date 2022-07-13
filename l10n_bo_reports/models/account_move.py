
from email.policy import default
from odoo import models, fields, api
from odoo.exceptions import UserError, ValidationError

class Asiento(models.Model):
    _inherit="account.move"

    origin = fields.Char(compute='_compute_origin',string='Origen', default='')
    correlative = fields.Char(string='Correlativo')
    corre = fields.Char(string='Corre')
    

    # @api.onchange('corre')
    # def _onchange_correlativo(self):
    #     self.correlative = "J222"

    def _compute_origin(self):
        if(self.ref):        
            proc= ""
            for c in range(len(self.ref)):
                if (self.ref[c] != '-'):
                    proc=proc+self.ref[c]
                else:
                    break
            self.origin=proc


    # @api.onchage('journal_id')
    # def _compute_correlativo(self):
    #     if(self.journal_id== 'Valoración del Inventario'):
    #         orders= self.env['account.move'].search([('journal_id', '=', 'Valoración del Inventario')], order='correlative desc',limit=1,)
    # # 2022-06-00001
    # # OL-2022-0001

    #     sequence=int(orders.correlative[8:13])
    #     from datetime import datetime
    #     now = datetime.now()
    #     year = now.year
    #     month = now.month
    #     self.correlative = year + "-" + month

        # totalRegistros=20
        # # accounts = seft.env['account.move'].search(['name'])
        # accounts = self.env['account.move']
        # names = accounts


        # while(num<=totalRegistros):
        #     name = str(names[num])
        #     if(name == "")
        
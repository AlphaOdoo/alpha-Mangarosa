import time
import json
import datetime
import io
from odoo import fields, models, _
from odoo.exceptions import ValidationError
from odoo.tools import date_utils
try:
    from odoo.tools.misc import xlsxwriter
except ImportError:
    import xlsxwriter


class PurchaseBookWizard(models.TransientModel):
    _name = "purchase_book_wizard"
    _description = "Purchase Book Report Fast Wizard"

    begin_date = fields.Datetime(
        string="Start Date",  default=time.strftime('%Y-%m-01'), required=True)
    end_date = fields.Datetime(
        string="End Date",  default=datetime.datetime.now(), required=True)
    # id = ''

    dui = fields.Text('DUI')
    auth_number = fields.Text('Authorization Number')
    control_code = fields.Text('Control Code')

    def _employee_get(self):
        record = self.env['purchase.order'].search(
            # [('name', '=', 'P00016')])
            [])
        return record

    def _partner_get(self, name):
        record = self.env['res.partner'].search(
            [('name', '=', name)])
        return record

    def print_xlsx(self):
        print('ENTRA AL BOTON')
        # Busqueda por fechas
        invoice_ids = self.env['account.move'].search(
            ['&', ('invoice_date', '>=', self.begin_date),
             ('invoice_date', '<=', self.end_date),
             ('journal_id.type', '=', 'purchase'),
             ('state', '=', 'posted')
             ])

        # valida que la fecha inicio sea inferior a fecha fin
        if self.begin_date > self.end_date:
            raise ValidationError('Start Date must be less than End Date')

        # valida que hayan dartos en la data
        if (len(invoice_ids) == 0):
            raise ValidationError(
                'There are no invoices in the selected range of dates')

        data = {}
        # TODO iterar sobre cada objeto y mapear lo requerido
        for index, inv in enumerate(invoice_ids):
            partnerData = self._partner_get(inv.partner_id.name)
            invoice_content = {}
            if(partnerData.vat != False):
                invoice_content['partner_id'] = partnerData.vat
            else:
                invoice_content['partner_id'] = ' '
            invoice_content['partner'] = partnerData.name
            invoice_content['name'] = inv.name
            invoice_content['invoice_date'] = inv.invoice_date
            invoice_content['amount_total'] = inv.amount_total
            invoice_content['amount_tax'] = inv.amount_tax
            invoice_content['amount_ICE'] = ' '
            invoice_content['amount_IEHD'] = ' '
            invoice_content['amount_IPJ'] = ' '
            invoice_content['tax_ids'] = ' '
            invoice_content['no_credit'] = ' '
            invoice_content['external_amounts'] = ' '
            invoice_content['external_purchases'] = ' '
            invoice_content['price_subtotal'] = ' '
            invoice_content['iva'] = ' '
            invoice_content['gift_cart'] = ' '
            invoice_content['base_cf'] = ' '
            invoice_content['credit'] = ' '
            invoice_content['puchase_type'] = ' '
            if(inv.auth_number != False):
                invoice_content['auth_number'] = inv.auth_number
            else:
                invoice_content['auth_number'] = 0
            if(inv.control_code != False):
                invoice_content['control_code'] = inv.control_code
            else:
                invoice_content['control_code'] = 0
            if(inv.dui != False):
                invoice_content['dui'] = inv.dui
            else:
                invoice_content['dui'] = 0

            data[index] = invoice_content
        return {
            'type': 'ir.actions.report',
            'data': {'model': 'purchase_book_wizard',
                     'options': json.dumps(data, default=date_utils.json_default),
                     'output_format': 'xlsx',
                     'report_name': 'template purchase',
                     },
            'report_type': 'xlsx',
        }

    def get_xlsx_report(self, data, response):
        i = 8  # inicio de celdas a partir de la cabecera
        j = 1  # Nro
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        sheet = workbook.add_worksheet()
        sheet.set_column('A:X', 25)
        cell_format = workbook.add_format({'font_size': '12px'})
        title = workbook.add_format(
            {'align': 'left', 'bold': True, 'font_size': '16px'})
        title.set_font_color('blue')
        head = workbook.add_format(
            {'align': 'center', 'bold': True, 'font_size': '12px'})
        head.set_pattern(2)
        head.set_bg_color('blue')
        head.set_font_color('white')
        txt = workbook.add_format({'font_size': '10px'})
        sheet.merge_range('B2:I3', 'LIBRO DE COMPRAS', title)
        sheet.merge_range('B3:C3', '(Expresado en Bolivianos)', txt)
        sheet.write('A7', 'N??', head)
        sheet.write('B7', 'Especificaci??n', head)
        sheet.write('C7', 'NIT Proveedor', head)
        sheet.write('D7', 'Razon Social Proveedor', head)
        sheet.write('E7', 'C??digo de Autorizaci??n', head)
        sheet.write('F7', 'N??mero de Factura', head)
        sheet.write('G7', 'Numero DUI/DIM', head)
        sheet.write('H7', 'Fecha de Factura', head)
        sheet.write('I7', 'Importe Total Compra', head)
        sheet.write('J7', 'Importe ICE', head)
        sheet.write('K7', 'Importe IEHD', head)
        sheet.write('L7', 'Importe IPJ', head)
        sheet.write('M7', 'Tasas', head)
        sheet.write('N7', 'Otro NO Sujeto a credito Fiscal', head)
        sheet.write('O7', 'Importes Extranjeros', head)
        sheet.write('P7', 'Importe Compras Grabadas a Tasa Cero', head)
        sheet.write('Q7', 'Subtotal', head)
        sheet.write(
            'R7', 'Descuentos Bonificaciones Rebajas Sujetas al IVA', head)
        sheet.write('S7', 'Importe GIFT CARD', head)
        sheet.write('T7', 'Importe Base CF', head)
        sheet.write('U7', 'Credito Fiscal', head)
        sheet.write('V7', 'Tipo Compra', head)
        sheet.write('W7', 'C??digo de Control', head)

        for index, inv in enumerate(data.items()):
            sheet.write('A'+str(i), j, cell_format)
            sheet.write('C'+str(i), str(inv[1]['partner_id']), txt)
            sheet.write('D'+str(i), str(inv[1]['partner']), txt)
            sheet.write('E'+str(i), str(inv[1]['auth_number']), txt)
            sheet.write('F'+str(i), str(inv[1]['name']), txt)
            sheet.write('G'+str(i), str(inv[1]['dui']), txt)
            sheet.write('H'+str(i), str(inv[1]['invoice_date']), txt)
            sheet.write('I'+str(i), str(inv[1]['amount_total']), txt)
            sheet.write('J'+str(i), '0,00', txt)
            sheet.write('K'+str(i), '0,00', txt)
            sheet.write('L'+str(i), '0,00', txt)
            sheet.write('M'+str(i), str(inv[1]['amount_tax']), cell_format)
            sheet.write('N'+str(i), '0,00', txt)
            sheet.write('O'+str(i), '0,00', txt)
            sheet.write('P'+str(i), '0,00', txt)
            sheet.write('Q'+str(i), str(inv[1]['price_subtotal']), cell_format)
            sheet.write('R'+str(i), '0,00', txt)
            sheet.write('S'+str(i), '0,00', txt)
            sheet.write('T'+str(i), '0,00', txt)
            sheet.write(
                'U'+str(i), str(inv[1]['amount_total'] * 0.13), cell_format)
            sheet.write('V'+str(i), '0,00', txt)
            sheet.write('W'+str(i), str(inv[1]['control_code']), txt)
            i = i + 1
            j = j + 1

        workbook.close()
        output.seek(0)
        response.stream.write(output.read())
        output.close()

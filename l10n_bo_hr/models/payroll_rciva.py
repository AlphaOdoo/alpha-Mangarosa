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


class PayrollRciva(models.TransientModel):
    # _name = "excel_rciva_payroll"
    _name = "payroll_rciva"
    _description = "Payroll RCIVA"
    start_date = fields.Datetime(
        string="Start Date",  default=time.strftime('%Y-%m-01'), required=True)
    end_date = fields.Datetime(
        string="End Date",  default=datetime.datetime.now(), required=True)

    def print_xlsx(self):
        # Busqueda por fechas
        invoice_ids = self.env['hr.employee'].search(
            [])

        # valida que la fecha inicio sea inferior a fecha fin

        # valida que hayan dartos en la data
        if (len(invoice_ids) == 0):
            raise ValidationError(
                'There are no invoices in the selected range of dates')

        data = {}
        # TODO iterar sobre cada objeto y mapear lo requerido
        for index, inv in enumerate(invoice_ids):
            invoice_content = {}
            invoice_content['name'] = inv.name
            invoice_content['birthday'] = inv.birthday
            invoice_content['identification_id'] = inv.identification_id
            invoice_content['gender'] = inv.gender
            invoice_content['country_of_birth'] = inv.country_of_birth
            data[index] = invoice_content
        return {
            'type': 'ir.actions.report',
            'data': {'model': 'payroll_rciva',
                     'options': json.dumps(data, default=date_utils.json_default),
                     'output_format': 'xlsx',
                     'report_name': 'template rciva',
                     },
            'report_type': 'xlsx',
        }

    def get_xlsx_rciva_report(self, data, response):
        print('rciva: ', data)
        i = 8  # inicio de celdas a partir de la cabecera
        j = 1  # Nro
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        sheet = workbook.add_worksheet()
        cell_format = workbook.add_format({'font_size': '12px'})
        # head = workbook.add_format(
        #     {'align': 'center', 'bold': True, 'font_size': '20px'})
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
        sheet.merge_range('B2:I3', 'PLANILLA RC IVA', title)

        # sheet.write('B7', 'Año', head)
        sheet.write('B7', 'Nro', head)
        sheet.write('C7', 'Periodo', head)
        sheet.write('D7', 'Codigo Dependiente RC-IVA', head)
        sheet.write('E7', 'NOMBRES', head)
        sheet.write('F7', 'PRIMER APELLIDO', head)
        sheet.write('G7', 'SEGUNDO APELLIDO', head)
        sheet.write('H7', 'Numero de Documento de Identidad', head)
        sheet.write('I7', 'Tipo de Documento', head)
        sheet.write(
            'J7', 'Novedades (I=Incorporacion V=Vigente D=Desvinculado)', head)
        sheet.write('K7', 'Monto de Ingreso Neto', head)
        sheet.write('L7', 'Dos(2) SAlarios Minimos no imponibles', head)
        sheet.write(
            'M7', 'Importe sujeto a impuesto (base imponible)', head)
        sheet.write('N7', 'Impuesto RC-IVA', head)
        sheet.write(
            'O7', '13% de los dos (2) Salarios Minimos Nacionales', head)
        sheet.write('P7', 'Impuesto Neto RC-IVA', head)
        sheet.write('Q7', 'F-110 Casilla 693', head)
        sheet.write('R7', 'Saldo a Favor del Fisco', head)
        sheet.write('S7', 'Saldo a Favor del Dependiente', head)
        sheet.write(
            'T7', 'Saldo a Favor del Dependiente del Periodo Anterior', head)
        sheet.write(
            'U7', 'Mantenimiento del valor del Saldo a favor del Dependiente del periodo anterior', head)
        sheet.write('V7', 'Saldo del periodo anterior Actualizado', head)

        sheet.write('W7', 'Saldo utilizado', head)
        sheet.write('X7', 'Saldo RC-IVA sujeto a retención', head)
        sheet.write(
            'Y7', 'PAgo a Cuenta SIETE-RG periodo anterior', head)
        sheet.write('Z7', 'Impuesto RC-IVA retenido', head)
        sheet.write(
            'AA7', 'Saldo de credito fiscal a Favor del dependiente para seguir el mes siguiente', head)
        sheet.write(
            'AB7', 'Saldo de pago a cuenta SIETE-RG a favor del dependiente para el mes siguiente', head)
        for index, inv in enumerate(data.items()):
            sheet.write('B'+str(i), j, txt)
            sheet.write('H'+str(i), str(inv[1]['identification_id']), txt)
            sheet.write('E'+str(i), str(inv[1]['name']), txt)
            sheet.write('F'+str(i), str(inv[1]['name']), txt)
            sheet.write('G'+str(i), str(inv[1]['name']), txt)
            sheet.write('I'+str(i), str(inv[1]['country_of_birth']), txt)

            sheet.write('C'+str(i), '0,00', txt)
            sheet.write('D'+str(i), '0,00', txt)
            sheet.write('J'+str(i), '0,00', txt)
            sheet.write('K'+str(i), '0,00', txt)
            sheet.write('L'+str(i), '0,00', txt)
            sheet.write('M'+str(i), '0,00', txt)
            sheet.write('N'+str(i), '0,00', txt)
            sheet.write('O'+str(i), '0,00', txt)
            sheet.write('P'+str(i), '0,00', txt)
            sheet.write('Q'+str(i), '0,00', txt)
            sheet.write('R'+str(i), '0,00', txt)
            sheet.write('S'+str(i), '0,00', txt)
            sheet.write('T'+str(i), '0,00', txt)
            sheet.write('U'+str(i), '0,00', txt)
            sheet.write('V'+str(i), '0,00', txt)
            sheet.write('W'+str(i), '0,00', txt)
            sheet.write('X'+str(i), '0,00', txt)
            sheet.write('Y'+str(i), '0,00', txt)
            sheet.write('Z'+str(i), '0,00', txt)
            sheet.write('AA'+str(i), '0,00', txt)
            sheet.write('AB'+str(i), '0,00', txt)

            #sheet.write('J'+str(i), str(inv[1]['gender']), txt)
            i = i + 1
            j = j + 1
        workbook.close()
        output.seek(0)
        response.stream.write(output.read())
        output.close()

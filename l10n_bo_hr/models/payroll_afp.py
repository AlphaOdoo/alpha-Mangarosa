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


class PayrollAfp(models.TransientModel):
    _name = "payroll_afp"
    _description = "Payroll to AFP"
    start_date = fields.Datetime(
        string="Start Date",  default=time.strftime('%Y-%m-01'), required=True)
    end_date = fields.Datetime(
        string="End Date",  default=datetime.datetime.now(), required=True)

    def print_xlsx(self):
        # Busqueda por fechas
        invoice_ids = self.env['hr.employee'].search(
            [])

        # valida que la fecha inicio sea inferior a fecha fin
        if self.start_date > self.end_date:
            raise ValidationError('Start Date must be less than End Date')

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
            'data': {'model': 'payroll_afp',
                     'options': json.dumps(data, default=date_utils.json_default),
                     'output_format': 'xlsx',
                     'report_name': 'template afp',
                     },
            'report_type': 'xlsx',
        }

    def get_xlsx_afp_report(self, data, response):
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
        sheet.merge_range('B2:I3', 'PLANILLA AFP', title)
        # sheet.write('B6', 'From:', cell_format)
        # sheet.merge_range('C6:D6', data['start_date'], txt)
        # sheet.write('F6', 'To:', cell_format)
        # sheet.merge_range('G6:H6', data['end_date'], txt)
        sheet.write('B7', 'Nro', head)
        sheet.write('C7', 'Apellido Paterno', head)
        sheet.write('D7', 'Apellido Materno', head)
        sheet.write('E7', 'Nombres', head)
        sheet.write('F7', 'Codigo de Asegurado', head)
        sheet.write('G7', 'Cargo', head)
        sheet.write('H7', 'Días del mes trabajado', head)
        sheet.write('I7', 'Fecha Ingreso', head)
        sheet.write('J7', 'Años', head)
        sheet.write('K7', '%', head)
        sheet.write('L7', 'Haber Basico', head)
        sheet.write('M7', 'Bono de antiguedad', head)
        sheet.write('N7', 'Otros haberes', head)
        sheet.write('O7', 'Total GAnado', head)
        sheet.write('P7', 'RC-IVA', head)
        sheet.write('Q7', 'Sistema Integral de Pensiones', head)
        sheet.write('R7', 'Aporte Solidario', head)
        sheet.write('S7', 'Aporte NAl. Solidario', head)
        sheet.write('T7', 'Prestamos Anticipos', head)
        sheet.write('U7', 'Otros descuentos', head)
        sheet.write('V7', 'TOTAL DESCUENTOS', head)
        sheet.write('W7', 'LIQUIDO PAGABLE', head)
        sheet.write('X7', 'REGIONAL', head)
        for index, inv in enumerate(data.items()):
            sheet.write('B'+str(i), j, txt)
            #sheet.write('E'+str(i), str(inv[1]['identification_id']), txt)
            #sheet.write('E'+str(i), str(inv[1]['birthday']), txt)
            sheet.write('C'+str(i), str(inv[1]['name']), txt)
            sheet.write('D'+str(i), str(inv[1]['name']), txt)
            sheet.write('E'+str(i), str(inv[1]['name']), txt)
            #sheet.write('I'+str(i), str(inv[1]['country_of_birth']), txt)
            sheet.write('J'+str(i), str(inv[1]['gender']), txt)

            sheet.write('F'+str(i), '0,00', txt)
            sheet.write('G'+str(i), '0,00', txt)
            sheet.write('H'+str(i), '0,00', txt)
            sheet.write('I'+str(i), '0,00', txt)
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
            i = i + 1
            j = j + 1
        workbook.close()
        output.seek(0)
        response.stream.write(output.read())
        output.close()

    def regla(self):
        return self.env.ref('l10n_bo_hr.consumo_regla').report_action(self)

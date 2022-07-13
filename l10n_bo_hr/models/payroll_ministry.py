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


class PayrollMinistry(models.TransientModel):
    _name = "payroll_ministry"
    _description = "Payroll to Ministery"
    start_date = fields.Datetime(
        string="Start Date",  default=time.strftime('%Y-%m-01'), required=True)
    end_date = fields.Datetime(
        string="End Date",  default=datetime.datetime.now(), required=True)

    # def print_xlsx(self):
    #     if self.start_date > self.end_date:
    #         raise ValidationError('Start Date must be less than End Date')
    #     data = {
    #         'start_date': self.start_date,
    #         'end_date': self.end_date,
    #     }
    #     return {
    #         'type': 'ir.actions.report',
    #         'data': {'model': 'excel_ministry_payroll',
    #                  'options': json.dumps(data, default=date_utils.json_default),
    #                  'output_format': 'xlsx',
    #                  'report_name': 'template ministry',
    #                  },
    #         'report_type': 'xlsx',
    #     }
    def _rule_get(self):
        record = self.env['hr.salary.rule'].search(
            [('code', '=', 'pay_ministery_001')])
        return record

    def print_xlsx(self):
        #regla = self._rule_get()
        #print('regla', regla.amount_python_compute.result)
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
            'data': {'model': 'payroll_ministry',
                     'options': json.dumps(data, default=date_utils.json_default),
                     'output_format': 'xlsx',
                     'report_name': 'template ministry',
                     },
            'report_type': 'xlsx',
        }

    def get_xlsx_ministry_report(self, data, response):
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
        sheet.merge_range(
            'B2:I3', 'PLANILLA PARA MINISTERIO DE TRABAJO', title)
        # sheet.write('B6', 'From:', cell_format)
        # sheet.merge_range('C6:D6', data['start_date'], txt)
        # sheet.write('F6', 'To:', cell_format)
        # sheet.merge_range('G6:H6', data['end_date'], txt)
        sheet.write('B7', 'Nro', head)
        sheet.write('C7', 'Tipo de Documento de Identidad', head)
        sheet.write('D7', 'Numero de Documento de Identidad', head)
        sheet.write('E7', 'Fecha de Nacimiento', head)
        sheet.write('F7', 'Apellido Paterno', head)
        sheet.write('G7', 'Apellido Materno', head)
        sheet.write('H7', 'Nombre', head)
        sheet.write('I7', 'Pais', head)
        sheet.write('J7', 'Sexo', head)
        sheet.write('K7', 'Jubilado', head)
        sheet.write('L7', 'Aporta a la AFP?', head)
        sheet.write('M7', 'Persona con Discapacidad?', head)
        sheet.write('N7', 'Tutor de persona con discapacidad', head)
        sheet.write('O7', 'Fecha Ingreso', head)
        sheet.write('P7', 'Fecha Retiro', head)
        sheet.write('Q7', 'Motivo Retiro', head)
        sheet.write('R7', 'Caja de Salud', head)
        sheet.write('S7', 'AFP a la que aporta', head)
        sheet.write('T7', 'NUA/CUA', head)
        sheet.write('U7', 'Sucursal o ubicacion adicional', head)
        sheet.write('V7', 'Clasificacion laboral', head)
        sheet.write('W7', 'Cargo', head)
        sheet.write('X7', 'Modalidad de contrato', head)
        sheet.write('Y7', 'Tipo Contrato', head)
        sheet.write('Z7', 'Días pagados', head)
        sheet.write('AA7', 'Horas Pagadas', head)
        sheet.write('AB7', 'Haber BAsico', head)
        sheet.write('AC7', 'Bono de antiguedad', head)
        sheet.write('AD7', 'Horas extra', head)
        sheet.write('AE7', 'Monto Horas extra', head)
        sheet.write('AF7', 'Horas recargo nocturno', head)
        sheet.write('AG7', 'Monto horas extra nocturnas', head)
        sheet.write('AH7', 'Horas extra dominicales', head)
        sheet.write('AI7', 'Monto Horas extra dominicales', head)
        sheet.write('AJ7', 'Domingos Trabajados', head)
        sheet.write('AK7', 'Monto Domingo Trabajado', head)
        sheet.write('AL7', 'Nro. Dominicales', head)
        sheet.write('AM7', 'SAlario Dominical', head)
        sheet.write('AN7', 'Bono produccion', head)
        sheet.write('AO7', 'Subsidio Frontera', head)
        sheet.write('AP7', 'Otros bonos y pagos', head)
        sheet.write('AQ7', 'RC-IVA', head)
        sheet.write('AR7', 'aporte a caja de salud', head)
        sheet.write('AS7', 'otros descuentos', head)
        for index, inv in enumerate(data.items()):
            sheet.write('B'+str(i), j, cell_format)
            sheet.write('E'+str(i), str(inv[1]['identification_id']), txt)
            sheet.write('E'+str(i), str(inv[1]['birthday']), txt)
            sheet.write('F'+str(i), str(inv[1]['name']), txt)
            sheet.write('G'+str(i), str(inv[1]['name']), txt)
            sheet.write('H'+str(i), str(inv[1]['name']), txt)
            sheet.write('I'+str(i), str(inv[1]['country_of_birth']), txt)
            sheet.write('J'+str(i), str(inv[1]['gender']), txt)

            sheet.write('C'+str(i), '0,00', txt)
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
            sheet.write('AC'+str(i), '0,00', txt)
            sheet.write('AD'+str(i), '0,00', txt)
            sheet.write('AE'+str(i), '0,00', txt)
            sheet.write('AF'+str(i), '0,00', txt)
            sheet.write('AG'+str(i), '0,00', txt)
            sheet.write('AH'+str(i), '0,00', txt)
            sheet.write('AI'+str(i), '0,00', txt)
            sheet.write('AJ'+str(i), '0,00', txt)
            sheet.write('AK'+str(i), '0,00', txt)
            sheet.write('AL'+str(i), '0,00', txt)
            sheet.write('AM'+str(i), '0,00', txt)
            sheet.write('AN'+str(i), '0,00', txt)
            sheet.write('AO'+str(i), '0,00', txt)
            sheet.write('AP'+str(i), '0,00', txt)
            sheet.write('AQ'+str(i), '0,00', txt)
            sheet.write('AR'+str(i), '0,00', txt)
            sheet.write('AS'+str(i), '0,00', txt)

            i = i + 1
            j = j + 1

        workbook.close()
        output.seek(0)
        response.stream.write(output.read())
        output.close()

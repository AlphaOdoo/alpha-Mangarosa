import time
import json
import datetime
import io
import logging
from odoo import fields, models, _
from odoo.exceptions import ValidationError
from odoo.tools import date_utils

try:
    from psycopg2 import sql
except ImportError:
    import sql
try:
    from odoo.tools.misc import xlsxwriter
except ImportError:
    import xlsxwriter

_logger = logging.getLogger(__name__)


#  cuenta_bancaria, Fecha Documento, Tipo Transaccion, Numero de Doc, Datos, destinatario, Ingreso, Egreso
#   siempre comenzar en la columna A


class BankBookExcelWizard(models.TransientModel):
    _name = "bankbook_xlsx_report_wizard"
    _description = "Bankbook Report Fast Wizard"

    # cabcera
    head_bank = ["Cuenta Bancaria", "Fecha Documento", "Tipo Transaccion",
                 "Numero de Doc", "Datos", "destinatario", "Ingreso", "Egreso", "Saldo"]

    account = fields.Many2one('res.partner.bank', string='cuenta')
    start_date = fields.Datetime(
        string="Start Date", default=time.strftime('%Y-%m-01'), required=True)
    end_date = fields.Datetime(
        string="End Date", default=datetime.datetime.now(), required=True)

    def print_xlsx(self):
        if self.start_date > self.end_date:
            raise ValidationError('Start Date must be less than End Date')
        data = {
            'start_date': self.start_date,
            'end_date': self.end_date,
        }
        return {
            'type': 'ir.actions.report',
            'data': {'model': 'bankbook_xlsx_report_wizard',
                     'options': json.dumps(data, default=date_utils.json_default),
                     'output_format': 'xlsx',
                     'report_name': 'Excel Report',
                     },
            'report_type': 'xlsx',
        }

    def get_xlsx_report(self, data, response):
        _logger.debug(
            "Entro a get xlsx report  ************************************")
        row = 7
        lines = []
        fechaI = self.start_date
        fechaF = self.end_date
        account = self.account
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        sheet = workbook.add_worksheet()
        cell_format = workbook.add_format({'font_size': '12px'})
        head = workbook.add_format(
            {'align': 'center', 'bold': True, 'font_size': '20px'})
        txt = workbook.add_format({'font_size': '10px'})
        sheet.merge_range('B2:I3', 'EXCEL REPORT', head)
        sheet.write('B6', 'From:', cell_format)
        sheet.merge_range('C6:D6', data['start_date'], txt)
        sheet.write('F6', 'To:', cell_format)
        sheet.merge_range('G6:H6', data['end_date'], txt)
        _logger.debug(
            "Praparando para entrar a head libreta Bancaria *****************************")
        row = self.head_BankBook(row, sheet)
        _logger.debug(
            "Praparando para entrar get move bank *****************************")
        lines = self.get_movebank(self.account)
        _logger.debug(
            "Praparando para entrar a bidy *****************************")
        self.body_bankbook(row, sheet, lines,
                           data['start_date'], data['end_date'], account)
        workbook.close()
        output.seek(0)
        response.stream.write(output.read())
        output.close()

    def head_BankBook(self, row, sheet):
        _logger.debug(
            "Entro head libreta bancaria *****************************")
        column = 0
        # bold = sheet.add_format({'bold': True})
        for item in self.head_bank:
            sheet.write(row, column, item)
            column += 1
        row = row + 1
        return row

    def body_bankbook(self, row, sheet, body, fechaI, fechaF, account):
        # row es la fila donde comenzar
        # body es una lista de listas, body[0] es una lista con todo los valores que tiene head
        _logger.debug(
            "Entro body libreta bancaria *************************************")
        column = 8
        sumSaldo = 0
        # fechaI = self.start_date
        # fechaF = self.end_date
        # account = self.account
        row, sumSaldo = self.sum_previous_balance(
            row, sheet, body, fechaI, fechaF, account)
        for item in body:
            if (item[1] >= (datetime.datetime.strptime(fechaI, '%Y-%m-%d %H:%M:%S').date())) and (item[1] <= (datetime.datetime.strptime(fechaF, '%Y-%m-%d %H:%M:%S').date())) and (item[0] == account):
                sheet.write_row(row, 0, item)
                formula = '=G' + str(row) + '-H' + str(row) + 'I' + str(row-1)
                sheet.write_formula(row, column, formula)
                row += 1
        return row

    def sum_previous_balance(self, row, sheet, body, fechaI, fechaF, account):
        # row es la fila donde comenzar
        # body es una lista de listas, body[0] es una lista con todo los valores que tiene head
        _logger.debug(
            "Entro sum_previous_balance   *************************************")
        # fechaI = self.start_date
        # _logger.debug(self.start_date)
        _logger.debug((datetime.datetime.strptime(
            fechaI, '%Y-%m-%d %H:%M:%S').date()))
        _logger.debug(
            "Entro body libreta bancaria *************************************")
        sumSaldo = 0
        for item in body:
            if (item[1] < (datetime.datetime.strptime(fechaI, '%Y-%m-%d %H:%M:%S').date())) and (item[0] == account):
                sumSaldo = sumSaldo + item[8]
        sheet.write(row, 8, sumSaldo)
        row += 1
        return row, sumSaldo

    def get_movebank(self, bank):
        _logger.debug(
            "Entro a get move bank ejecutar el sql******************************************")
        lines = []
        sql_select = sql.SQL(
            """
        select rpb.acc_number as NumCuenta, aml.date as Fecha , rb.name as Banvo, aml.move_name as NumeroDocumento, aml.name as datos, rp.display_name as destinatario, CASE WHEN aml.amount_residual > 0 THEN aml.amount_residual ELSE '0' END AS Credito, CASE WHEN aml.amount_residual < 0 THEN aml.amount_residual ELSE '0' END AS Debito, aml.amount_residual
        -- aj.code,
        from public.account_journal AS aj
        LEFT JOIN public.account_move_line aml on aml.journal_id = aj.id
        LEFT JOIN public.res_partner as rp on aml.partner_id = rp.id
        LEFT JOIN public.res_partner_bank rpb on rpb.id = aj.bank_account_id 
        LEFT JOIN public.res_bank rb on rb.id = rpb.bank_id
        where 
        aj.type like 'bank'
        AND aml.amount_residual != 0         
        """)
        # % self.start_date % self.end_date
        # -- and aml.date >= % s
        # -- and aml.date <= % s AND rpb.id = %s % bank
        self._cr.execute(sql_select)
        lines = self._cr.fetchall()
        _logger.debug(lines)

        return lines

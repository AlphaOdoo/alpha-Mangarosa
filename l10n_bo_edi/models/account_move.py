from ast import If
import base64
from email.mime import base
from email.policy import default
from io import BytesIO
import logging
import itertools
import base64
import re
import readline
import shutil
from statistics import mode
from time import time
import qrcode
import math

from datetime import datetime, timedelta
from odoo import fields, models, api
from pytz import timezone
import zeep
from zeep import client
from hashlib import sha256
from odoo.exceptions import UserError, Warning, ValidationError

# Digital Signature
# from html import unescape
# import xml.etree.ElementTree as ET
# import lxml.etree as etree
# import xml.dom.minidom
# import os

import gzip
import hashlib
# import asyncio
import time
import asyncio


_logger = logging.getLogger(__name__)


class AccountMove(models.Model):
    _inherit = 'account.move'
    _description = 'Account move inherit'

    l10n_bo_cuf = fields.Text(
        string='CUF Code', help='(Código Unico de Facturación) Code referred to Point of Attention', readonly=True)

    l10n_bo_cufd = fields.Text(
        string='CUFD Code', help='(Código Unico de Facturación Diaria) Code provided by SIN, generated daily, identifies the invoice along with a number', readonly=True)

    efact_control_code = fields.Text(
        string='CUFD Control Code', help='Control Code, given along CUFD', readonly=True)

    l10n_bo_invoice_number = fields.Text(
        string='Invoice Number', help='Along with CUFD Code, helps in identifying the invoice', readonly=True)

    l10n_bo_selling_point = fields.Many2one(
        'selling_point', string='Selling Point', readonly=True)

    l10n_bo_branch_office = fields.Many2one(
        'branch_office', string='Branch Office', readonly=True)

    l10n_bo_emission_type = fields.Many2one(
        'emission_types', string='Emission Type Selection')

    qr_code = fields.Binary("QR Code", attachment=True, store=True)

    # def _default_state(self):
    #     return self.env['document_status']
    l10n_bo_document_status = fields.Many2one(
        'document_status', string='Document Status')

    # l10n_bo_cancellation_reason = fields.Many2one(
    #     'cancellation_reasons', string='Cancellation Reason')

    # Campos Provisionales Certificacion
    cafc = fields.Text(string='cafc', default='123')
    montoGiftCard = fields.Text(string='montoGiftCard', default='')
    ###

    # @api.depends('res.config.settings.l10n_bo_invoicing_type')
    def get_e_invoice_type(self):
        self.e_billing = self.env['ir.config_parameter'].sudo().get_param('res.config.settings.l10n_bo_invoicing_type')
    e_billing = fields.Boolean(  # Electronic Invoicing Flag
        compute='get_e_invoice_type', default = False)  # default=_getInvoiceType # default=True
    
    representation_format = fields.Boolean('rep_format', default = False) # Graphic Representation Format flag
    representation_size = fields.Boolean('rep_size') # Graphic Representation Size flag

    is_drafted = fields.Boolean('is_drafted', default = False) # True if invoice has been drafted after confirmation
    is_cancelled = fields.Boolean('is_cancelled', default = False) # True if invoice has been cancelled
    is_confirmed = fields.Boolean(string='is_confirmed', default = False)
    
    def get_journal_type(self):
        self.journal_type = self.journal_id.type
    journal_type = fields.Char(compute='get_journal_type')
    

    # def get_invoice_type(self):
    #     if ("INV" not in self.name):
    #         self.inv_type = True
    #     else:
    #         self.inv_type = False
    def get_invoice_type(self):
        if (self.journal_id.type == 'sale'):
            self.inv_type = True
        else:
            self.inv_type = False
    inv_type = fields.Boolean(compute='get_invoice_type')  # Invoice/Bill Flag


    def get_total_converted(self):
        currency_name = self.invoice_line_ids.mapped('sale_line_ids').order_id.pricelist_id.currency_id.name
        if type(currency_name) == str:
            if "USD" in currency_name:
                self.total_conv = self.amount_total * 6.96
        else:
            self.total_conv = 0.0
    total_conv = fields.Float(compute='get_total_converted')
    
    def get_literal_number(self):
        if self.total_conv == 0.0:
            self.total_lit = self.numero_to_letras(self.amount_total)
        else:
            self.total_lit = self.numero_to_letras(self.total_conv)
    total_lit = fields.Char(compute='get_literal_number')

    # def get_discount_amount(self): 
    #     self.disc_amount = self.amount_total * self.discount / 100
    # disc_amount = fields.Boolean(string='discount amount')
    
    ### Standard Billing Vars ###
    dui = fields.Text('DUI')
    auth_number = fields.Text('Authorization Number')
    control_code = fields.Text('Control Code')

    # @api.onchange('dosage_id')
    # def onchange_dosage_id(self):
        # if self.dosage_id:
        #     self.reversed_inv_id = self.env['cancelled_invoices'].search([('invoice_dosage_id', '=', self.dosage_id.id)])
    
    # @api.depends('dosage_id')
    # def _filter_cancelled(self):
    #     if self.dosage_id:
    #         self.reversed_inv_id = self.env['cancelled_invoices'].search([('invoice_dosage_id', '=', self.dosage_id.id)])
    #     else:
    #         self.reversed_inv_id = []
    dosage_id = fields.Many2one('invoice_dosage', string='Selected Dosage')
    reversed_inv_id = fields.Many2one('cancelled_invoices', string='Reversed Invoice:', help='Select only if you want to get the cancelled invoice number (reverse cancellation)')

    # def view_init(self, fields_list):  # Init method of lifecycle #
    #     print(self.getInvoiceType()["modality"])
    #     if self.getInvoiceType()["modality"] == 1:
    #         self.e_billing = True
    #     else:
    #         self.e_billing = False
    #     return super().view_init(fields_list)


    def _employee_get(self):
        record = self.env['res.users'].search(
            [('name', '=', self.env.user.name)])
        return record

    def get_name_sep(self, inv_line):
        idx_begin = inv_line.find(']') + 1
        return inv_line[idx_begin:]

    def get_code_sep(self, inv_line):
        idx_begin = inv_line.find('[')
        idx_end = inv_line.find(']') + 1
        return inv_line[idx_begin:idx_end]

    def check_usd_total(self):
        currency_name = self.invoice_line_ids.mapped('sale_line_ids').order_id.pricelist_id.currency_id.name
        if "USD" in currency_name:
            return True
        else:
            return False
    
    def testAsync(self):
        # res_cufd = asyncio.run(self.getCUFD())
        print('/////////////PRUEBA ASINCRONA//////////')
        # print(res_cufd[0])
        # print(res_cufd[1])
        # print(res_cufd[2])
        ## TODO En caso de requerir emitir facturas a CLientes externos:
        # print(self.amount_total_signed)
        # print(self.partner_id.property_account_position_id.name)
        ## ?? Test de verificacion tabla empty
        check_fields = self.env["cufd_log"].search([])
        if check_fields:
            print("ok")
        else:
            print("no")
        currency_name = self.invoice_line_ids.mapped('sale_line_ids').order_id.pricelist_id.currency_id.name
        print(self.total_conv)
        print('/////////////PRUEBA FINALIZADA//////////')


    async def getCUFD(self):
        now = datetime.now(
            timezone('America/Argentina/Buenos_Aires')) - timedelta(hours=1)
        
        selling_point= self.getBranchOffice()[2]
        current_cufd = self.env['cufd_log'].search(['&', (
            'begin_date',
            '<=', now),
            ('end_date',
             '>=', now)])
            #  '>=', now), ('selling_point', '=', selling_point.id_selling_point)])

        if not current_cufd:
            new_cufd_obj = await asyncio.wait_for(asyncio.create_task(self._generate_cufd(3)), timeout= 60.0)
            print(new_cufd_obj)
            self.env['cufd_log'].create({
                    # "id_cufd" : 1 , #?? Pendiente incremento dependiendo el ultimo registro
                    "cufd" : new_cufd_obj.codigo,
                    "controlCode": new_cufd_obj.codigoControl,
                    "begin_date": self.getTime().strftime("%Y-%m-%d %H:%M:%S"),
                    "end_date": new_cufd_obj.fechaVigencia.strftime("%Y-%m-%d %H:%M:%S"),
                    "invoice_number": 1,
                    # "selling_point": selling_point.id_selling_point, ##!! psycopg2.ProgrammingError: can't adapt type 'selling_point'
                    "selling_point": selling_point.id
                })
        # time.sleep(3)
        current_cufd = self.env['cufd_log'].search(['&', (
            'begin_date',
            '<=', now),
            ('end_date',
             '>=', now)])
            #  '>=', now), ('selling_point', '=', selling_point.id_selling_point)])

        # print('TIEMPOS' + self.getTime().strftime("%Y-%m-%d %H:%M:%S") + " " + new_cufd_obj.fechaVigencia.strftime("%Y-%m-%d %H:%M:%S"))
        # print('SEGUNDA BUSQUEDA CUFD' + str(current_cufd.end_date) + " " + str(current_cufd.cufd))
 
        cufd_data = [current_cufd.cufd,
                     current_cufd.invoice_number, current_cufd.controlCode, current_cufd]

        ##TODO Revisar porque varian horas cuando se edita un registro de cufd_log
        # print(self.env['cufd_log'].search([]).begin_date)
        # print(self.env['cufd_log'].search([]).end_date)
        return cufd_data

    def _getEmissionType(self):
        emission_type = self.env['ir.config_parameter'].get_param(
            'res.config.settings.l10n_bo_emission_type')
        return emission_type

    def getBranchOffice(self):
        branch_office_data = [self._employee_get().l10n_bo_is_seller,
                              self._employee_get().l10n_bo_branch_office_id,
                              self._employee_get().l10n_bo_selling_point_id
                              ]
        return branch_office_data

    def _getCompanyNIT(self):
        nit = self.env.company.vat
        return nit

    async def set_bo_edi_info(self):
        # cufd = self.getCUFD()
        cufd = await asyncio.wait_for(asyncio.create_task(self.getCUFD()), timeout= 60.0) # 1 min
        _logger.info(cufd)
        ## TODO agregar verificacion de valor retornado en "cufd" antes de llenar campos
        self.l10n_bo_branch_office = self.getBranchOffice()[1]
        self.l10n_bo_selling_point = self.getBranchOffice()[2]
        self.l10n_bo_cufd = cufd[0]
        self.efact_control_code = cufd[2]
        self.l10n_bo_invoice_number = cufd[1]
        # self.l10n_bo_cuf = self.getCuf()
        self.write({'l10n_bo_cuf':self.getCuf()})

        if self.l10n_bo_cufd and self.l10n_bo_cuf:
            return True
        else:
            return False
        # raise Warning("CUFD not retrieved, cannot send invoice")
        # _logger.info(self._getEmissionType())
        # self.getheaderInvoiceData()

    def clean(self):
        self.l10n_bo_cufd = ""
        self.l10n_bo_invoice_number = 0

    def getCuf(self):
        nit = str(self._getCompanyNIT())
        if not nit:
            raise Warning("There is no VAT/NIT for the current company")
        
        now = datetime.now(
            timezone('America/Argentina/Buenos_Aires')) - timedelta(hours=1)
        # time = now.strftime("%Y%m%d%H%M%S%f")
        time = now.strftime("%Y%m%d%H%M%S" + "000")
        branch_office = str(self._employee_get(
        ).l10n_bo_branch_office_id.id_branch_office)
        modality = str(1)
        emission_type = str(1)
        invoice_type = str(1)
        document_type = str(1)
        # invoice_number = str(self.getCUFD()[1])
        invoice_number = str(self.l10n_bo_invoice_number)
        selling_point = str(self.getBranchOffice()[2].id_selling_point)

        zero_str = str(str(self._addZeros('nit', nit)) + str(time[0:17]) + str(self._addZeros('branch_office', branch_office))
                       + str(emission_type) + str(modality) + str(invoice_type) + str(self._addZeros('document_type', document_type)) +
                       str(self._addZeros('invoice_number', invoice_number)) + str(self._addZeros('selling_point', selling_point)))
        mod11_str = str(self._Mod11(zero_str, 1, 9, False))
        base16_str = str(self._Base16(zero_str + mod11_str))
        cuf = base16_str + str(self.efact_control_code) ##//TODO Revisar codigocontrol mal obtenido al generar el primer cufd del dia
        # _logger.info('/////////////////////////////////////////')
        # print(zero_str)
        # print(mod11_str)
        # print(base16_str)
        # _logger.info('/////////////////////////////////////////')
        return cuf

    def _addZeros(self, field, value):
        if field == 'nit':
            if len(value) == 9:
                return '0000' + value
            elif len(value) == 10:
                return '000' + value
        elif field == 'branch_office':
            if len(value) == 1:
                return '000' + value
            elif len(value) == 2:
                return '00' + value
            elif len(value) == 3:
                return '0' + value
        elif field == 'document_type':
            if len(value) == 1:
                return '0' + value
            elif len(value) == 2:
                return value
        elif field == 'invoice_number':
            if len(value) == 1:
                return '000000000' + value
            elif len(value) == 2:
                return '00000000' + value
            elif len(value) == 3:
                return '0000000' + value
            elif len(value) == 4:
                return '0000000' + value
        elif field == 'selling_point':
            if len(value) == 1:
                return '000' + value
            elif len(value) == 2:
                return '00' + value
            elif len(value) == 3:
                return '0' + value

    # def _Mod11(self, cadena):
    #     factores = itertools.cycle((2, 3, 4, 5, 6, 7))
    #     suma = 0
    #     for digito, factor in zip(reversed(cadena), factores):
    #         suma += int(digito)*factor
    #     control = 11 - suma % 11
    #     if control == 10:
    #         return 1
    #     else:
    #         return control

    def _Mod11(self, cadena, numDig, limMult, x10):
        mult = None
        suma = None
        i = None
        n = None
        dig = None

        if not x10:
            numDig = 1

        n = 1
        while n <= numDig:
            suma = 0
            mult = 2
            for i in range(len(cadena) - 1, -1, -1):
                suma += (mult * int(cadena[i: i + 1]))
                mult += 1
                if mult > limMult:
                    mult = 2
            if x10:
                dig = math.fmod((math.fmod((suma * 10), 11)), 10)
            else:
                dig = math.fmod(suma, 11)
            if dig == 10:
                cadena += "1"
            if dig == 11:
                cadena += "0"
            if dig < 10:
                cadena += str(round(dig))
            n += 1
        result = cadena[len(cadena) - numDig : len(cadena)]
        return result

    def _Base16(self, cadena):
        hex_val = (hex(int(cadena))[2:]).upper()
        return hex_val

    def _Base16decode(self, cadena):
        print(int("0x" + cadena, 0))

    # def pruebaMod(self):
    #     stri = '00001234567892019011316372123100001110100000000010000'
    #     a = self._Mod11(stri)
    #     cadena = stri + str(a)
    #     _logger.info(cadena)
    #     _logger.info(str(self._Base16(cadena)))

    # def _getSiatToken(self, login, nit, password):
    #     client = zeep.Client(
    #         wsdl='https://pilotosiatservicios.impuestos.gob.bo/v1/ServicioAutenticacionSoap?wsdl')
    #     params = {'DatosUsuarioRequest': {
    #         'login': login,
    #         'nit': nit,
    #         'password': password
    #     }
    #     }
    #     result = client.service.token(**params)
    #     _logger.info(str(result['token']))
    #     return result['token']

    def getTime(self):
        now = datetime.now(
            timezone('America/Argentina/Buenos_Aires')) - timedelta(hours=1)
        return now

    # def log_method(self):
    #     _logger.info('///////////////////DFE INFO//////////////')
    #     _logger.info(self._employee_get().l10n_bo_branch_office_id)
    #     self.getCUFD()
    #     _logger.info(
    #         '/////////////////////////////////////////////////////////')

    def getheaderInvoiceData(self, invoice_state = 1):
        # self.set_bo_edi_info()
        # data_cufd = self.getCUFD() ##//TODO pendiente generacion dinamica CUFD async
        invoice_header = {
            'nit': self._getCompanyNIT(),
            'company_name': self.env.company.name,
            'city_name': self.env.company.city,
            'phone': self.env.company.phone,
            'invoice_number': self.l10n_bo_invoice_number,
            'cuf': self.l10n_bo_cuf,
            # 'cufd': self.getCUFD(), GENERAR
            'cufd': self.l10n_bo_cufd,
            'branch_office_id': self._employee_get().l10n_bo_branch_office_id.id_branch_office,
            'company_address': self.env.company.street,
            'selling_point_id': self._employee_get().l10n_bo_selling_point_id.id_selling_point,
            'current_time': self.getTime().strftime("%Y-%m-%dT%H:%M:%S.000"),
            'client_name': self.partner_id.name,
            # # client_id_type : self.env['id_type'].search(
            # #     [('id_type_code', '=', self.partner_id.l10n_bo_id_type.id_type_code)])
            # 'client_id_type': self.partner_id.l10n_bo_id_type.id_type_code, # PEND
            'client_id_type': '1',
            'client_id': self.partner_id.vat,
            # 'payment_method': self.partner_id.property_payment_method_id,  # PEND
            'payment_method': '1',
            'total_untaxed': self.amount_untaxed,
            'total': self.amount_total,
            # 'currency_type': self.env['ir.config_parameter'].get_param(
            #     'res.config.settings.currency_id')  # PEND
            'currency_type': '1'
        }
        # Cambiar Parametro de Tipo Factura segun se requiera
        additional_data = self._getAdditionalData(0, invoice_state)
        set_xml_res = self._setXML(invoice_header, self._getInvoiceItemsData(),
                     additional_data, invoice_state)
        _logger.info('///////////////RESPUESTA FACTURA DEVUELTA///////////////////')
        _logger.info(set_xml_res[0])
        _logger.info('//////////////////////////////////')

        ##//!! VERIFICAR razón por la cual warnings no permiten guardar dato cuf (set_bo_edi_info)
        if set_xml_res[0]:
            now = self.getTime()
            current_cufd = self.env['cufd_log'].search(['&', (
            'begin_date',
            '<=', now),
            ('end_date',
             '>=', now)])
            # current_cufd.update({'invoice_number': 2}) ## int(current_cufd.invoice_number)  + 1 
            current_cufd.write({'invoice_number': int(current_cufd.invoice_number) + 1}) ##//TODO Pendiente aumento de correlativo CUFD
            # raise Warning('SIN Invoice posted succesfully!')
            # self.trigger_popup(1)
            return True
        else :
            ## raise SIN error
            # raise Warning('Invoice rejected by SIN: ' + set_xml_res[1])
            # print("Invoice rejected", 'Invoice rejected by SIN: ' + set_xml_res[1])
            # self.trigger_popup(2)
            return False

    def _getInvoiceItemsData(self):
        items = self.invoice_line_ids
        return items

    def _getAdditionalData(self, invoice_type, invoice_state):
        cafc = self.env['bo_edi_params'].search(
            [('name', '=', 'CAFC')]).value
        header_start = ()
        additional_header_tags = ""
        # additional_item_tags = ""
        xml_end = ""
        if (invoice_type == 0):  # Factura Compra Venta
            header_start = ("<facturaElectronicaCompraVenta"
                            ' xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"'
                            # "xmlns:xsd='http://www.w3.org/2001/XMLSchema'"
                            ' xsi:noNamespaceSchemaLocation="facturaElectronicaCompraVenta.xsd">')
            if invoice_state:
                additional_header_tags = (
                    F"<montoGiftCard xsi:nil='true'/>"
                    F"<descuentoAdicional xsi:nil='true'/>"
                    F"<codigoExcepcion xsi:nil='true'/>"
                    F"<cafc xsi:nil='true'/>"
                )
            else:
                additional_header_tags = (
                    F"<montoGiftCard xsi:nil='true'/>"
                    F"<descuentoAdicional xsi:nil='true'/>"
                    F"<codigoExcepcion xsi:nil='true'/>"
                    F"<cafc>{cafc}</cafc>"
                )
            # additional_item_tags = additional_item_tags + ""
            xml_end = "</facturaElectronicaCompraVenta>"
        # elif (invoice_type == 1): ## Factura Tasa Cero
        #     ## header_start = ...
        #     ## additional_tags = .....
        additional_data = {'start': header_start,
                           'additionalHeader': additional_header_tags,
                           # 'additionalItems': additional_item_tags
                           'end': xml_end
                           }
        return additional_data

    def _setXML(self, headerInvoiceData, invoiceItems, additionalData, invoice_state = 1):
        xml = ''
        startHeader = additionalData['start']
        xmlHeader = ("<cabecera>"
                     F"<nitEmisor>{headerInvoiceData['nit']}</nitEmisor>"
                     F"<razonSocialEmisor>{headerInvoiceData['company_name']}</razonSocialEmisor>"
                     F"<municipio>{headerInvoiceData['city_name']}</municipio>"
                     F"<telefono>{headerInvoiceData['phone']}</telefono>"
                     F"<numeroFactura>{headerInvoiceData['invoice_number']}</numeroFactura>"
                     ##?? borrar
                    #  F"<numeroFactura>2</numeroFactura>"
                     F"<cuf>{headerInvoiceData['cuf']}</cuf>"
                     F"<cufd>{headerInvoiceData['cufd']}</cufd>"
                     F"<codigoSucursal>{headerInvoiceData['branch_office_id']}</codigoSucursal>"
                     F"<direccion>{headerInvoiceData['company_address']}</direccion>"
                     F"<codigoPuntoVenta>{headerInvoiceData['selling_point_id']}</codigoPuntoVenta>"
                     F"<fechaEmision>{headerInvoiceData['current_time']}</fechaEmision>"
                     F"<nombreRazonSocial>{headerInvoiceData['client_name']}</nombreRazonSocial>"
                     F"<codigoTipoDocumentoIdentidad>{headerInvoiceData['client_id_type']}</codigoTipoDocumentoIdentidad>"
                     F"<numeroDocumento>{headerInvoiceData['client_id']}</numeroDocumento>"
                     '<complemento xsi:nil="true"/>'
                     F"<codigoCliente>{headerInvoiceData['client_id']}</codigoCliente>"
                     # PEND
                     F"<codigoMetodoPago>{headerInvoiceData['payment_method']}</codigoMetodoPago>"
                     "<numeroTarjeta xsi:nil='true'/>"
                    #  F"<montoTotal>{headerInvoiceData['total_untaxed']}</montoTotal>" # ERROR DE Impuestos, verificacion de montos
                     F"<montoTotal>{headerInvoiceData['total']}</montoTotal>"
                     F"<montoTotalSujetoIva>{headerInvoiceData['total']}</montoTotalSujetoIva>"
                     F"<codigoMoneda>2</codigoMoneda>"  # PEND
                     F"<tipoCambio>1</tipoCambio>"  # PEND
                     F"<montoTotalMoneda>{headerInvoiceData['total']}</montoTotalMoneda>"
                     )
        xmlHeader = xmlHeader + additionalData['additionalHeader']
        xmlHeader = xmlHeader + ("<leyenda>Ley N° 453: Está prohibido importar, distribuir o comercializar productos prohibidos o retirados en el país de origen por atentar a la integridad física y a la salud.</leyenda>"  # PEND RND
                                 "<usuario>bduchen</usuario>"
                                 # PEND
                                 F"<codigoDocumentoSector>{headerInvoiceData['currency_type']}</codigoDocumentoSector>")
        endHeader = "</cabecera>"
        xml = xml + startHeader + xmlHeader + endHeader

        for item in invoiceItems:
            xmlItem = ("<detalle>"
                       F"<actividadEconomica>{item.product_id.sin_item.activity_code.code}</actividadEconomica>"
                       F"<codigoProductoSin>{item.product_id.sin_item.sin_code}</codigoProductoSin>"
                       F"<codigoProducto>{item.product_id.default_code}</codigoProducto>"
                       F"<descripcion>{item.name}</descripcion>"
                       F"<cantidad>{item.quantity}</cantidad>"
                       F"<unidadMedida>{item.product_id.measure_unit.measure_unit_code}</unidadMedida>"  # PEND
                       F"<precioUnitario>{item.price_unit}</precioUnitario>"
                       "<montoDescuento xsi:nil='true'/>"
                    #    F"<subTotal>{item.price_subtotal}</subTotal>"
                       F"<subTotal>{headerInvoiceData['total']}</subTotal>" # ERROR DE Impuestos, verificacion de montos
                       '<numeroSerie xsi:nil="true"/>'
                       '<numeroImei xsi:nil="true"/>'
                       "</detalle>")
            xml = xml + xmlItem

        xml = xml + additionalData['end']

        # _logger.info(str(xmlHeader))
        xml_path = self.env['bo_edi_params'].search(
            [('name', '=', 'XML')]).value
        xml_signed_path = ''
        if invoice_state:
            xml_signed_path = self.env['bo_edi_params'].search(
                [('name', '=', 'XMLSIGNED')]).value
        else:
            xml_signed_path = self.env['bo_edi_params'].search(
                [('name', '=', 'EMPAQUETADO')]).value
        xml_signed_server_path = self.env['bo_edi_params'].search(
            [('name', '=', 'XMLSIGNEDSERVER')]).value
        key_path = self.env['bo_edi_params'].search(
            [('name', '=', 'KEY')]).value
        cert_path = self.env['bo_edi_params'].search(
            [('name', '=', 'CERTIFICADO')]).value
        cred_path = self.env['bo_edi_params'].search(
            [('name', '=', 'CREDENTIALSPATH')]).value
        xsd_compraventa_path = self.env['bo_edi_params'].search(
            [('name', '=', 'XSDCompraVenta')]).value  ##?? borrar
        pwd_cert_path = self.env['bo_edi_params'].search(
            [('name', '=', 'PWDCERTIFICADO')]).value

        invoice_number = headerInvoiceData['invoice_number']
        ##?? borrar
        # invoice_number = "2"

        with open(xml_path + str(invoice_number).zfill(4) + '.xml', 'w') as xml_file:
            xml_file.write(xml)
            xml_file.close()

        xml_signed = self.env['sin_sync'].sign_xml(
            xml, cred_path, key_path, cert_path, xml_signed_server_path + str(invoice_number).zfill(4))
        
        with open(xml_signed_path + str(invoice_number).zfill(4) + '.xml', 'w') as xml_signed_file:
            xml_signed_file.write(xml_signed)
            xml_signed_file.close()

        self._zip_xml(xml_signed_path + str(invoice_number).zfill(
            4) + '.xml', xml_signed_path + str(invoice_number).zfill(4) + '.gz')



        zip = open(xml_signed_path +
                   str(invoice_number).zfill(4) + '.gz', 'rb')
        zip_content = zip.read() 

        hashed_xml = self._get_file_hash(xml_signed_path +
                                         str(invoice_number).zfill(4) + '.gz')

        # send_invoice_res = self.env['sin_sync'].send_invoice(
        #     self.l10n_bo_cufd, zip_content, hashed_xml)

        if invoice_state:
            send_invoice_res = self._req_send_invoice(self.l10n_bo_cufd, zip_content, hashed_xml)

            if send_invoice_res.codigoEstado == 908:
                return [True, send_invoice_res.codigoDescripcion]
            elif send_invoice_res.codigoEstado == 902:
                raise Warning("Invoice Rejected, Reason: " + send_invoice_res.mensajesList[0].descripcion + " Code: " + str(send_invoice_res.codigoEstado))
            else:
                _logger.info('///////////////RESPUESTA FACTURA///////////////////')
                _logger.info("Invoice Rejected, Reason: " + send_invoice_res.mensajesList[0].descripcion + " Code: " + str(send_invoice_res.codigoEstado))
                _logger.info('//////////////////////////////////')
                raise Warning("Invoice Rejected, Reason: " + send_invoice_res.mensajesList[0].descripcion + " Code: " + str(send_invoice_res.codigoEstado))
                return [False, send_invoice_res.codigoDescripcion]
        else :
            ##?? generacion de factura por contingencia
            return [True, "Generacion de Factura XML Contingencia finalizada"]

    def _zip_xml(self, xml_path, output_path):
        with open(xml_path, 'rb') as f_input:
            with gzip.open(output_path, 'wb') as f_output:
                shutil.copyfileobj(f_input, f_output)
    
    ########### Digital Signature Algorithms ################

    def _NumberTobase64(self, cNumber):
        sResp = ""
        cCociente = 1

        while cCociente > 0:
            cCociente = 1
            cTemp = cNumber
            while cTemp >= 64:
                cTemp -= 64
                cCociente += 1
            cCociente -= 1
            cResiduo = cTemp
            sResp = self.dictionaryBase64[cResiduo] + sResp
            cNumber = cCociente
        return sResp

    def _XmlTobase64(self, xmlPath):
        with open(xmlPath, "rb") as file:
            encoded = base64.encodebytes(file.read()).decode("utf-8")
        return encoded

    def _StringTobase64(self, string):
        encodedString = base64.b64encode(bytes(string, 'utf-8'))
        return encodedString

    def _GetHashSha256(self, input):
        hash = sha256(input.encode('utf-8')).hexdigest()
        return hash

    def _get_file_hash(self, file_path):
        BLOCK_SIZE = 65536  # The size of each read from the file

        # Create the hash object, can use something other than `.sha256()` if you wish
        file_hash = hashlib.sha256()
        with open(file_path, 'rb') as f:  # Open the file to read it's bytes
            # Read from the file. Take in the amount declared above
            fb = f.read(BLOCK_SIZE)
            while len(fb) > 0:  # While there is still data being read from the file
                file_hash.update(fb)  # Update the hash
                fb = f.read(BLOCK_SIZE)  # Read the next block from the file

        return file_hash.hexdigest()  # Get the digest of the hash

    def _read_private_key(self, private_key_pem, passphrase=None):
        """Reads a private key PEM block and returns a RSAPrivatekey

        :param private_key_pem: The private key PEM block
        :param passphrase: Optional passphrase needed to decrypt the private key
        :returns: a RSAPrivatekey object
        """
        if passphrase and isinstance(passphrase, str):
            passphrase = passphrase.encode("utf-8")
        if isinstance(private_key_pem, str):
            private_key_pem = private_key_pem.encode('utf-8')

        try:
            return serialization.load_pem_private_key(private_key_pem, passphrase,
                                                      backends.default_backend())
        except Exception:
            raise logging.exception.NeedsPassphrase

    ########### Report ################

    # def open_report_consume(self, context=None):
        # # if ids:
        # #     if not isinstance(ids, list):
        # #         ids = [ids]
        # #     context = dict(context or {}, active_ids=ids,
        # #                    active_model=self._name)
        # return {
        #     'type': 'ir.actions.report.xml',
        #     'report_name': 'l10n_bo_edi.graphic_representation_template',
        #     'context': context,
        # }

    def print_report(self):
        # datas = {
        #     'inv': self,
        #     'items': self.invoice_line_ids
        # }
        self.generate_qr_code()
        if not self.e_billing:
            return self.env.ref('l10n_bo_edi.invoice_report').report_action(self)
        else:
            if self.representation_format:
                return self.env.ref('l10n_bo_edi.graphic_representation').report_action(self)
            else:
                return self.env.ref('l10n_bo_edi.graphic_representation_pdf').report_action(self)
            
    def generate_qr_code(self):
       
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        if not self.e_billing:
            qr.add_data(str(self.env.company.vat) + '|' + 
                        str(self.l10n_bo_invoice_number) + '|' + 
                        str(self.auth_number) + '|' + 
                        str(self.getTime().strftime("%d/%m/%Y")) + '|' +
                        str(round(self.amount_total)) + '|' + 
                        str(round(self.amount_total)) + '|' + 
                        str(self.control_code))
        else:
            if self.representation_size:
                qr.add_data('https://pilotosiat.impuestos.gob.bo/consulta/QR?nit=' + str(self._getCompanyNIT()) + '&cuf='+ str(self.l10n_bo_cuf) + '&numero=' + str(self.l10n_bo_invoice_number) + '&t=2')
            else:
                qr.add_data('https://pilotosiat.impuestos.gob.bo/consulta/QR?nit=' + str(self._getCompanyNIT()) + '&cuf='+ str(self.l10n_bo_cuf) + '&numero=' + str(self.l10n_bo_invoice_number) + '&t=1')
        qr.make(fit=True)
        img = qr.make_image()
        temp = BytesIO()
        img.save(temp, format="JPEG")
        qr_image = base64.b64encode(temp.getvalue())
        self.qr_code = qr_image
        print(self.qr_code)

    ########### SIN Requests ################

    async def _generate_cufd(self, tipo_codigo):

        # self.env['sin_sync'].check_communication()
        ambience = str(self.env['bo_edi_params'].search(
            [('name', '=', 'AMBIENTE')]).value)
        modality = str(self.env['modalities'].search(
            [('description', '=', 'ELECTRONICA')]).id_modality)
        # selling_point = str(self.env['selling_point'].search(
        #     [('description', '=', 'PUNTO DE VENTA 0')]).id_selling_point)
        selling_point = str(self.getBranchOffice()[2].id_selling_point)
        # branch_office = str(self.env['branch_office'].search(
        #     [('description', '=', 'CASA MATRIZ')]).id_branch_office)
        branch_office = str(self.getBranchOffice()[1].id_branch_office)
        # cuis = str(self.env['bo_edi_params'].search(
        #     [('name', '=', 'CUIS-0')]).value)
        cuis = str(self.getBranchOffice()[2].cuis)
        system_code = str(self.env['bo_edi_params'].search(
            [('name', '=', 'CODIGOSISTEMA')]).value)
        nit = str(self.env['bo_edi_params'].search(
            [('name', '=', 'NIT')]).value)

        return await asyncio.wait_for(asyncio.create_task(
          self.env['sin_sync'].get_cufd(
                ambience,
                modality,
                selling_point,
                system_code,
                branch_office,
                cuis,
                nit,
                tipo_codigo
            )  
        ), timeout= 60.0) 
        # return await (self.env['sin_sync'].get_cufd(
        #     ambience,
        #     modality,
        #     selling_point,
        #     system_code,
        #     branch_office,
        #     cuis,
        #     nit,
        #     tipo_codigo
        # ))
    
    def _req_send_invoice(self, cufd, zip_content, hashed_xml):

        selling_point = str(self.getBranchOffice()[2].id_selling_point)
        branch_office = str(self.getBranchOffice()[1].id_branch_office)
        cuis = str(self.getBranchOffice()[2].cuis)
        code_modality = str(self.env['modalities'].search(
            [('description', '=', 'ELECTRONICA')]).id_modality)
        ambience = str(self.env['bo_edi_params'].search(
            [('name', '=', 'AMBIENTE')]).value)
        system_code = str(self.env['bo_edi_params'].search(
            [('name', '=', 'CODIGOSISTEMA')]).value)
        nit = str(self.env['bo_edi_params'].search(
            [('name', '=', 'NIT')]).value)
        emission_type = str(self.env['bo_edi_params'].search(
            [('name', '=', 'TIPOEMISION')]).value)
        # emission_type = 2 ##?? BORRAR

        return self.env['sin_sync'].send_invoice(emission_type, ambience, code_modality, selling_point, system_code, branch_office, cuis, nit,
            self.l10n_bo_cufd, zip_content, hashed_xml)
            
    def _req_cancel_invoice(self, cuf ,cufd , reason_code):
        selling_point = str(self.getBranchOffice()[2].id_selling_point)
        branch_office = str(self.getBranchOffice()[1].id_branch_office)
        id_ambience = str(self.env['bo_edi_params'].search(
            [('name', '=', 'AMBIENTE')]).value)
        id_sector_type = str(self.env['sector_types'].search(
            [('description', '=', 'FACTURA COMPRA-VENTA')]).id_sector_type)
        id_emission = str(self.env['bo_edi_params'].search(
            [('name', '=', 'TIPOEMISION')]).value)
        id_modality = str(self.env['modalities'].search(
            [('description', '=', 'ELECTRONICA')]).id_modality)
        system_code = str(self.env['bo_edi_params'].search(
            [('name', '=', 'CODIGOSISTEMA')]).value)
        
        return self.env['sin_sync'].cancel_invoice(cufd, cuf, reason_code, id_ambience, id_sector_type, id_emission, id_modality, selling_point, system_code, branch_office)

    def _req_send_event(self, reason_code, cufd_even, cufd, description, begin_date, end_date):
        id_ambience = str(self.env['bo_edi_params'].search(
            [('name', '=', 'AMBIENTE')]).value)
        selling_point = str(self.getBranchOffice()[2].id_selling_point)
        branch_office = str(self.getBranchOffice()[1].id_branch_office)
        system_code = str(self.env['bo_edi_params'].search(
            [('name', '=', 'CODIGOSISTEMA')]).value)
        cuis = str(self.getBranchOffice()[2].cuis)
        nit = str(self.env['bo_edi_params'].search(
            [('name', '=', 'NIT')]).value)
        
        return self.env['sin_sync'].send_invoice_event(id_ambience, selling_point, system_code, 
                                                        branch_office, cuis, nit, cufd, reason_code,
                                                        description, begin_date, end_date, cufd_even)

    def sync_activities(self):
        # self.env['sin_sync'].cert_sync_catal(50, 0)
        self.cert_invoices_cancellations(20)
    
    def cert_invoices_cancellations(self, iterations):
        for i in range(iterations):
            self.check_conectivity()
            time.sleep(5)
            # self.invoice_cancellation( self.l10n_bo_cufd, self.l10n_bo_cuf, 1)

    # def cert_invoices_generate(self, iterations):
    #     for i in range(iterations):
            
    ########### AUXILIARES ################
    
    # def create_notification(self):
    #     return {
    #         'type': 'ir.actions.client',
    #         'tag': 'display_notification',
    #         'params': {
    #             'title': 'Warning!',
    #             'message': 'You cannot do this action now',
    #             'sticky': True,
    #         }
    #     }

    ########### Anulaciones ################

    def button_cancel(self):
        if (self.e_billing):
            ##TODO PENDIENTE REGISTRO DE FACTURAS ANULADAS E-BILLING (MANEJO DE CORRELATIVOS)    
            if (self.journal_id.type == 'sale' or self.journal_id.type == 'purchase'):
                self.is_cancelled = True
                super(AccountMove, self).button_cancel()
                return {
                    "type": "ir.actions.act_window",
                    "res_model": "invoice_cancel_reason_wizard",
                    "context": {'cuf':self.l10n_bo_cuf, 'cufd': self.l10n_bo_cufd },
                    "view_type": "form",
                    "view_mode": "form",
                    "target": "new",
                }
        else:
            new_cancel_inv = {
                "invoice_num" : self.l10n_bo_invoice_number,
                "inv_reversed": False,
                "date": self.getTime().strftime("%Y-%m-%d %H:%M:%S"),
                "account_move_id": self.id,
                "invoice_dosage_id": self.dosage_id.id
            }
            self.env['cancelled_invoices'].create(new_cancel_inv)
            super(AccountMove, self).button_cancel()
            
        
    
    def invoice_cancellation(self,cuf, cufd, reason_code = 0):
        if not reason_code:
            raise Warning('You must select an invoice cancelation reason')
        else:
            res_cancel = self._req_cancel_invoice(cuf ,cufd , reason_code)
            if (res_cancel.codigoEstado != 905):
                _logger.info('///////////////RESPUESTA ANULACION FACTURA///////////////////')
                _logger.info('There was an error cancelling the invoice, Reason: ' + res_cancel.mensajesList[0].descripcion + " Code: " + str(res_cancel.codigoEstado))
                _logger.info('//////////////////////////////////')
                raise Warning('There was an error cancelling the invoice, Reason: ' + res_cancel.mensajesList[0].descripcion + " Code: " + str(res_cancel.codigoEstado))

            # self.is_cancelled = True
            # super(AccountMove, self).button_cancel() ##//TODO Averiguar la manera de llamar a metodo super origen desde otro metodo

    def button_draft(self):
        print("Invoice Drafted")
        self.is_drafted = True
        super(AccountMove, self).button_draft()

    ########### INVOICE EVENTS & INVOICE PACKAGES ################
    def check_conectivity(self):

        emission_type_obj = str(self.env['bo_edi_params'].search(
            [('name', '=', 'TIPOEMISION')]))
        
        status_obj = self.env['bo_edi_params'].search(
            [('name', '=', 'ONLINE')])
        current_status = status_obj.value
        # current_status = False

        # current_status = self.env['ir.config_parameter'].get_param(
        #     'res.config.settings.l10n_bo_invoicing_current_status')

        internet_status = self.env['sin_sync'].conexion()
        # internet_status = False

        sin_ws_status = True
        if internet_status:

            sin_ws_status = self.env['sin_sync'].check_communication()

            if self.getBranchOffice()[1] and self.getBranchOffice()[2]: # Valida Punto de venta del usuario ##!! VERIFICAR y Adicionalmente analizar rutas de archivos para cada punto venta

                res_fill_codes = asyncio.run(self.set_bo_edi_info())
                print(res_fill_codes)
                if not res_fill_codes:
                    raise Warning("CUFD not retrieved, cannot send invoice")
            else:
                raise Warning('The current user doesn''t have branch office nor a selling point configured')

            if sin_ws_status.codigo == 926 and self.l10n_bo_cufd:
                sin_ws_status = True
            else:
                sin_ws_status = False
        else:
            sin_ws_status = False

        print(current_status)
        print(sin_ws_status)
        print(internet_status)

        if sin_ws_status and internet_status:
            if current_status:
                ## FLUJO NORMAL
                check_hom = 0
                for item in self.invoice_line_ids:
                    if not item.product_id.sin_item.sin_code and not item.product_id.sin_item.activity_code.code:
                        check_hom = 1
                        
                if check_hom: # Valida Homologacion de todos los productos
                    raise Warning('One of the Invoice items is not homologated')
                else:
                    return self.getheaderInvoiceData(1)
            else:
                ## FIN DE SUCESO Y ENVIO DE PAQUETE
                # current_status = True
                status_obj.write({"value" : True})

                # Cambio de tipo de Emision
                emission_type_obj.write({"value" : 1})
                
                ##TODO Agregar condicion de misma fecha
                # current_incident = self.env['invoice_incident'].search(['&', (
                #                     'begin_date',
                #                     '=', 'end_date'),
                #                     ('sin_code',
                #                     '=', "")])
                
                current_incident = self.env['invoice_incident'].search(
                                    [('sin_code', '=', "")])
                
                current_incident.write({"end_date": self.getTime().strftime("%Y-%m-%d %H:%M:%S")})

                # current_incident.write({"begin_date": "2022-06-13 15:00:05"})
                # current_incident.write({"end_date": "2022-06-13 15:05:10"})

                print(str(current_incident))
                
                res_incident_sent = self._req_send_event(current_incident.invoice_event_id.code, current_incident.cufd_log_id.cufd,
                                                           self.l10n_bo_cufd, current_incident.description, current_incident.begin_date, current_incident.end_date )
                
                if(str(res_incident_sent).strip() != "None"):
                    print(res_incident_sent)
                    current_incident.write({"sin_code" : str(res_incident_sent)})
                else:
                    raise Warning("There was an error sending the invoice event")
                # current_incident.write({"sin_code"})

        else:
            if current_status:
                ## INICIO DE SUCESO Y CREACION DE PAQUETE
                
                # current_status = False ## Método para cambio de modo
                status_obj.write({"value" : False})

                # Cambio de tipo de Emision
                emission_type_obj.write({"value" : 2})

                ## Creación suceso
                new_incident = {}
                if not internet_status:
                    new_incident = {
                        "invoice_event_id": 1,
                        "description": "Corte de Servicio de Internet",
                        "begin_date": self.getTime().strftime("%Y-%m-%d %H:%M:%S"),
                        "end_date": self.getTime().strftime("%Y-%m-%d %H:%M:%S"),
                        "selling_point_id": (self.getBranchOffice()[2]).id_selling_point,
                        "incident_status_id": 1,
                        "sin_code": "",
                        "cufd_log_id": (self.getCUFD()[3]).id_cufd ##TODO usar Ultimo cufd (search fecha mayor)
                    }
                elif not sin_ws_status:
                    new_incident = {
                        "invoice_event_id": 2,
                        "description": "Falla de Comunicación con Servicio Web de Impuestos",
                        "begin_date": self.getTime().strftime("%Y-%m-%d %H:%M:%S"),
                        "end_date": self.getTime().strftime("%Y-%m-%d %H:%M:%S"),
                        "selling_point_id": (self.getBranchOffice()[2]).id_selling_point,
                        "incident_status_id": 1,
                        "sin_code": "",
                        "cufd_log_id": (self.getCUFD()[3]).id_cufd ##TODO usar Ultimo cufd (search fecha mayor)
                    }
                self.env['invoice_incident'].create(new_incident)

            res_offline_inv = self.getheaderInvoiceData(0)
            


    ########### STANDARD BILLING ################

    def generate_control_code(self):
        if (self.journal_id.type == 'sale'):
            if self.dosage_id:
                auth_num = str(self.dosage_id['auth_number'])
                nit_client = str(self.partner_id.vat)
                inv_date = str(self.getTime().strftime("%Y%m%d"))
                total = str(round(self.amount_total))
                key = str(self.dosage_id['key'])
                inv_num = ''

                if self.reversed_inv_id:
                    inv_num = str(self.reversed_inv_id['invoice_num'])
                    self.reversed_inv_id['inv_reversed'] = True
                else:
                    inv_num = str(self.dosage_id['invoice_number'])
                    self.dosage_id['invoice_number'] += 1

                self.l10n_bo_invoice_number = inv_num
                self.auth_number = auth_num
                self.control_code = self.env['standard_billing'].controlCode(
                    auth_num, inv_num, nit_client, inv_date, total, key)
            else:
                raise Warning('You must select an invoice dosage')
        else:
            if not self.auth_number or not self.control_code or not self.l10n_bo_invoice_number:
                raise Warning("You must fill the 'BO Information' fields")
            
    def action_post(self):
        if (self.journal_id.type == 'sale' or self.journal_id.type == 'purchase'):
            if self.e_billing and self.inv_type: ## Si la modalidad es electronica...
                # self.getheaderInvoiceData()
                if self.is_drafted and not self.is_cancelled:
                    raise Warning("We cannot resend the current invoice, in order to resend it please cancel and confirm")
                else:
                    res_conectivity = self.check_conectivity()
                    print(res_conectivity)
                    if res_conectivity:
                        self.is_confirmed = True
                        self.print_report()
            else: ## Si la modalidad es estandar
                nit = self.partner_id.vat
                currency_name = self.invoice_line_ids.mapped('sale_line_ids').order_id.pricelist_id.currency_id.name
                if not nit:
                    raise Warning("There is no VAT/NIT for the client company")
                else:
                    self.generate_control_code()
                    self.is_confirmed = True
                    self.print_report()
        super(AccountMove, self).action_post()
    
    ########### HELPERS ################

    def trigger_popup(self, type):
        print("entra")
        if type == 1:
            return {
                "type": "ir.actions.act_window",
                "res_model": "popup_success_wizard",
                "view_type": "form",
                "view_mode": "form",
                "target": "new",
            }
        else:
            return {
                "type": "ir.actions.act_window",
                "res_model": "popup_warn_wizard",
                "view_type": "form",
                "view_mode": "form",
                "target": "new",
            }
    
    def numero_to_letras(self, numero):
        indicador = [("",""),("MIL","MIL"),("MILLON","MILLONES"),("MIL","MIL"),("BILLON","BILLONES")]
        entero = int(numero)
        decimal = int(round((numero - entero)*100))
        contador = 0
        numero_letras = ""
        while entero >0:
            a = entero % 1000
            if contador == 0:
                en_letras = self.convierte_cifra(a,1).strip()
            else :
                en_letras = self.convierte_cifra(a,0).strip()
            if a==0:
                numero_letras = en_letras+" "+numero_letras
            elif a==1:
                if contador in (1,3):
                    numero_letras = indicador[contador][0]+" "+numero_letras
                else:
                    numero_letras = en_letras+" "+indicador[contador][0]+" "+numero_letras
            else:
                numero_letras = en_letras+" "+indicador[contador][1]+" "+numero_letras
            numero_letras = numero_letras.strip()
            contador = contador + 1
            entero = int(entero / 1000)
        print(str(decimal))
        if str(decimal) == '0':
            numero_letras = numero_letras +" con " + str(decimal) +"0/100"
        else:
            numero_letras = numero_letras +" con " + str(decimal) +"/100"
        return numero_letras  

    def convierte_cifra(self,numero,sw):
        lista_centana = ["",("CIEN","CIENTO"),"DOSCIENTOS","TRESCIENTOS","CUATROCIENTOS","QUINIENTOS","SEISCIENTOS","SETECIENTOS","OCHOCIENTOS","NOVECIENTOS"]
        lista_decena = ["",("DIEZ","ONCE","DOCE","TRECE","CATORCE","QUINCE","DIECISEIS","DIECISIETE","DIECIOCHO","DIECINUEVE"),
                        ("VEINTE","VEINTI"),("TREINTA","TREINTA Y "),("CUARENTA" , "CUARENTA Y "),
                        ("CINCUENTA" , "CINCUENTA Y "),("SESENTA" , "SESENTA Y "),
                        ("SETENTA" , "SETENTA Y "),("OCHENTA" , "OCHENTA Y "),
                        ("NOVENTA" , "NOVENTA Y ")
                    ]
        lista_unidad = ["",("UN" , "UNO"),"DOS","TRES","CUATRO","CINCO","SEIS","SIETE","OCHO","NUEVE"]
        centena = int (numero / 100)
        decena = int((numero -(centena * 100))/10)
        unidad = int(numero - (centena * 100 + decena * 10))
        #print "centena: ",centena, "decena: ",decena,'unidad: ',unidad
        texto_centena = ""
        texto_decena = ""
        texto_unidad = ""
        #Validad las centenas
        texto_centena = lista_centana[centena]
        if centena == 1:
            if (decena + unidad)!=0:
                texto_centena = texto_centena[1]
            else :
                texto_centena = texto_centena[0]
        #Valida las decenas
        texto_decena = lista_decena[decena]
        if decena == 1 :
            texto_decena = texto_decena[unidad]
        elif decena > 1 :
            if unidad != 0 :
                texto_decena = texto_decena[1]
            else:
                texto_decena = texto_decena[0]
        #Validar las unidades
        #print "texto_unidad: ",texto_unidad
        if decena != 1:
            texto_unidad = lista_unidad[unidad]
            if unidad == 1:
                texto_unidad = texto_unidad[sw]
        return "%s %s %s" %(texto_centena,texto_decena,texto_unidad)



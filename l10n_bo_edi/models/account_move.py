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
import qrcode
import math

from datetime import datetime, timedelta
from odoo import fields, models, api
from pytz import timezone
import zeep
from zeep import client
from hashlib import sha256
from odoo.exceptions import UserError, Warning

# Digital Signature
# from html import unescape
# import xml.etree.ElementTree as ET
# import lxml.etree as etree
# import xml.dom.minidom
# import os

import gzip
import hashlib

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

    # def getInvoiceType(self):
    #     # invoice_type = self.env['ir.config_parameter'].get_param(
    #     #     'res.config.settings.l10n_bo_invoicing_type')
    #     invoice_type = {"modality": 0, "type": 0}
    #     invoice_type["modality"] = 0
    #     if ("INV" not in self.name):
    #         invoice_type["type"] = 0
    #     else:
    #         invoice_type["type"] = 1
    #     return invoice_type

    e_billing = fields.Boolean(  # Electronic Invoicing Flag
        'e_billing')  # default=_getInvoiceType # default=True

    def get_invoice_type(self):
        if ("INV" not in self.name):
            self.inv_type = True
        else:
            self.inv_type = False
    inv_type = fields.Boolean(compute='get_invoice_type')  # Invoice/Bill Flag

    ### Standard Billing Vars ###
    dosage_id = fields.Many2one('invoice_dosage', string='Selected Dosage')
    dui = fields.Text('DUI')
    auth_number = fields.Text('Authorization Number')
    control_code = fields.Text('Control Code')

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

    def _getCUFD(self):
        now = datetime.now(
            timezone('America/Argentina/Buenos_Aires')) - timedelta(hours=1)
        current_cufd = self.env['cufd_log'].search(['&', (
            'begin_date',
            '<=', now),
            ('end_date',
             '>=', now)])

        cufd_data = [current_cufd.cufd,
                     current_cufd.invoice_number, current_cufd.controlCode]
        # Revisar porque varian horas cuando se edita un registro de cufd_log
        print(self.env['cufd_log'].search([]).begin_date)
        print(self.env['cufd_log'].search([]).end_date)
        return cufd_data

    def _getEmissionType(self):
        emission_type = self.env['ir.config_parameter'].get_param(
            'res.config.settings.l10n_bo_emission_type')
        return emission_type

    def _getBranchOffice(self):
        branch_office_data = [self._employee_get().l10n_bo_is_seller,
                              self._employee_get().l10n_bo_branch_office_id,
                              self._employee_get().l10n_bo_selling_point_id
                              ]
        return branch_office_data

    def _getCompanyNIT(self):
        nit = self.env.company.vat
        return nit

    def set_bo_edi_info(self):
        self.l10n_bo_branch_office = self._getBranchOffice()[1]
        self.l10n_bo_selling_point = self._getBranchOffice()[2]
        self.l10n_bo_cufd = self._getCUFD()[0]
        self.efact_control_code = self._getCUFD()[2]
        self.l10n_bo_cuf = self.getCuf()
        self.l10n_bo_invoice_number = self._getCUFD()[1]
        _logger.info(self._getEmissionType())

    def clean(self):
        self.l10n_bo_cufd = ""
        self.l10n_bo_invoice_number = 0

    def getCuf(self):
        nit = str(self._getCompanyNIT())
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
        invoice_number = str(self._getCUFD()[1])
        selling_point = str(self._getBranchOffice()[2].id_selling_point)

        zero_str = str(str(self._addZeros('nit', nit)) + str(time[0:17]) + str(self._addZeros('branch_office', branch_office))
                       + str(emission_type) + str(modality) + str(invoice_type) + str(self._addZeros('document_type', document_type)) +
                       str(self._addZeros('invoice_number', invoice_number)) + str(self._addZeros('selling_point', selling_point)))
        mod11_str = str(self._Mod11(zero_str, 1, 9, False))
        base16_str = str(self._Base16(zero_str + mod11_str))
        cuf = base16_str + str(self._getCUFD()[2])
        _logger.info('/////////////////////////////////////////')
        # print(self._Base16decode(
        #     '45D2C55C3ED51CACD69168B422F75811C52A9E06A14741E7C73176D74'))
        print(zero_str)
        print(mod11_str)
        print(base16_str)
        _logger.info('/////////////////////////////////////////')
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
            for i in range(cadena.length() - 1, -1, -1):
                suma += (mult * int(cadena.substring(i, i + 1)))
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
                cadena += str(dig)
            n += 1
        return cadena.substring(cadena.length() - numDig, cadena.length())

    def _Base16(self, cadena):
        hex_val = (hex(int(cadena))[2:]).upper()
        return hex_val

    def _Base16decode(self, cadena):
        print(int("0x" + cadena, 0))

    def pruebaMod(self):
        stri = '00001234567892019011316372123100001110100000000010000'
        a = self._Mod11(stri)
        cadena = stri + str(a)
        _logger.info(cadena)
        _logger.info(str(self._Base16(cadena)))

    def _getSiatToken(self, login, nit, password):
        client = zeep.Client(
            wsdl='https://pilotosiatservicios.impuestos.gob.bo/v1/ServicioAutenticacionSoap?wsdl')
        params = {'DatosUsuarioRequest': {
            'login': login,
            'nit': nit,
            'password': password
        }
        }
        result = client.service.token(**params)
        _logger.info(str(result['token']))
        return result['token']

    def getTime(self):
        now = datetime.now(
            timezone('America/Argentina/Buenos_Aires')) - timedelta(hours=1)
        return now

    def log_method(self):
        _logger.info('///////////////////DFE INFO//////////////')
        _logger.info(self._employee_get().l10n_bo_branch_office_id)
        self._getCUFD()
        _logger.info(
            '/////////////////////////////////////////////////////////')

    def getheaderInvoiceData(self):
        invoice_header = {
            'nit': self._getCompanyNIT(),
            'company_name': self.env.company.name,
            'city_name': self.env.company.city,
            'phone': self.env.company.phone,
            'invoice_number': str(self._getCUFD()[1]),
            'cuf': self.getCuf(),
            # 'cufd': self._getCUFD(), GENERAR
            'cufd': self._getCUFD()[0],
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
        additional_data = self._getAdditionalData(0)
        self._setXML(invoice_header, self._getInvoiceItemsData(),
                     additional_data)

    def _getInvoiceItemsData(self):
        items = self.invoice_line_ids
        return items

    def _getAdditionalData(self, Invoice_type):
        header_start = ()
        additional_header_tags = ""
        # additional_item_tags = ""
        xml_end = ""
        if (Invoice_type == 0):  # Factura Compra Venta
            header_start = ("<facturaElectronicaCompraVenta"
                            ' xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"'
                            # "xmlns:xsd='http://www.w3.org/2001/XMLSchema'"
                            ' xsi:noNamespaceSchemaLocation="facturaElectronicaCompraVenta.xsd">')
            additional_header_tags = (
                F"<montoGiftCard xsi:nil='true'/>"
                F"<descuentoAdicional xsi:nil='true'/>"
                F"<codigoExcepcion xsi:nil='true'/>"
                F"<cafc xsi:nil='true'/>"
            )
            # additional_item_tags = additional_item_tags + ""
            xml_end = "</facturaElectronicaCompraVenta>"
        # elif (Invoice_type == 1): ## Factura Tasa Cero
        #     ## header_start = ...
        #     ## additional_tags = .....
        additional_data = {'start': header_start,
                           'additionalHeader': additional_header_tags,
                           # 'additionalItems': additional_item_tags
                           'end': xml_end
                           }
        return additional_data

    def _setXML(self, headerInvoiceData, invoiceItems, additionalData):
        xml = ''
        startHeader = additionalData['start']
        xmlHeader = ("<cabecera>"
                     F"<nitEmisor>{headerInvoiceData['nit']}</nitEmisor>"
                     F"<razonSocialEmisor>{headerInvoiceData['company_name']}</razonSocialEmisor>"
                     F"<municipio>{headerInvoiceData['city_name']}</municipio>"
                     F"<telefono>{headerInvoiceData['phone']}</telefono>"
                     F"<numeroFactura>{headerInvoiceData['invoice_number']}</numeroFactura>"
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
                     F"<montoTotal>{headerInvoiceData['total_untaxed']}</montoTotal>"
                     F"<montoTotalSujetoIva>{headerInvoiceData['total']}</montoTotalSujetoIva>"
                     F"<codigoMoneda>2</codigoMoneda>"  # PEND
                     F"<tipoCambio>1</tipoCambio>"  # PEND
                     F"<montoTotalMoneda>{headerInvoiceData['total']}</montoTotalMoneda>"
                     )
        xmlHeader = xmlHeader + additionalData['additionalHeader']
        xmlHeader = xmlHeader + ("<leyenda>Ley N° 453: Está prohibido importar, distribuir o comercializar productos expirados o prontos a expirar.</leyenda>"  # PEND RND
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
                       F"<unidadMedida>1</unidadMedida>"  # PEND
                       F"<precioUnitario>{item.price_unit}</precioUnitario>"
                       "<montoDescuento xsi:nil='true'/>"
                       F"<subTotal>{item.price_subtotal}</subTotal>"
                       '<numeroSerie xsi:nil="true"/>'
                       '<numeroImei xsi:nil="true"/>'
                       "</detalle>")
            xml = xml + xmlItem

        xml = xml + additionalData['end']

        # _logger.info(str(xmlHeader))
        xml_path = self.env['bo_edi_params'].search(
            [('name', '=', 'XML')]).value
        xml_signed_path = self.env['bo_edi_params'].search(
            [('name', '=', 'XMLSIGNED')]).value
        key_path = self.env['bo_edi_params'].search(
            [('name', '=', 'KEY')]).value
        cert_path = self.env['bo_edi_params'].search(
            [('name', '=', 'CERTIFICADO')]).value
        cred_path = self.env['bo_edi_params'].search(
            [('name', '=', 'CREDENTIALSPATH')]).value
        xsd_compraventa_path = self.env['bo_edi_params'].search(
            [('name', '=', 'XSDCompraVenta')]).value
        pwd_cert_path = self.env['bo_edi_params'].search(
            [('name', '=', 'PWDCERTIFICADO')]).value

        with open(xml_path + str(headerInvoiceData['invoice_number']).zfill(4) + '.xml', 'w') as xml_file:
            # root = etree.fromstring(xml)
            # xml_file.write(etree.tostring(root, pretty_print=True).decode())
            xml_file.write(xml)
            xml_file.close()

        xml_signed = self.env['sin_sync'].sign_xml(
            xml, cred_path, key_path, cert_path, xml_signed_path + str(headerInvoiceData['invoice_number']).zfill(4))

        with open(xml_signed_path + str(headerInvoiceData['invoice_number']).zfill(4) + '.xml', 'w') as xml_signed_file:
            xml_signed_file.write(xml_signed)
            xml_signed_file.close()

        # print(xml_signed)

        # with open(xml_signed_path + str(headerInvoiceData['invoice_number']).zfill(4) + '.xml')

        self._zip_xml(xml_signed_path + str(headerInvoiceData['invoice_number']).zfill(
            4) + '.xml', '/home/alphabrad/Odoo/signTests/Signed/' + str(headerInvoiceData['invoice_number']).zfill(4) + '.gz')

        zip = open('/home/alphabrad/Odoo/signTests/Signed/' +
                   str(headerInvoiceData['invoice_number']).zfill(4) + '.gz', 'rb')
        zip_content = zip.read()  # Sin efecto, devuelve array de bytes en diferente encoding
        #---------#
        # zip_path = '/home/alphabrad/Odoo/signTests/Signed/' + \
        #     str(headerInvoiceData['invoice_number']).zfill(4) + '.gz'
        # zip_encode = gzip.open(zip_path, 'rb')
        # zip_content = zip_encode.read()
        #---------#
        # with open('/home/alphabrad/Odoo/signTests/Signed/' + str(headerInvoiceData['invoice_number']).zfill(4) + '.gz', encoding='utf-8') as zip_file:
        #     zip_content = zip_file.read()

        hashed_xml = self._get_file_hash('/home/alphabrad/Odoo/signTests/Signed/' +
                                         str(headerInvoiceData['invoice_number']).zfill(4) + '.gz')
        self.env['sin_sync'].send_invoice(
            self._getCUFD()[0], zip_content, hashed_xml)

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
        return self.env.ref('l10n_bo_edi.graphic_representation').report_action(self)

    def generate_qr_code(self):
        # qr_code = fields.Binary("QR Code", attachment=True, store=True)
        print(self.qr_code)
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data('https://pilotosiat.impuestos.gob.bo/consulta/QR?nit=1020469023&cuf=45D2C55C3ECD884CE113604C9E2F09F78513A113E15110B533774DC74&numero=3&t=1')
        qr.make(fit=True)
        img = qr.make_image()
        temp = BytesIO()
        img.save(temp, format="PNG")
        qr_image = base64.b64encode(temp.getvalue())
        self.qr_code = qr_image
        print(self.qr_code)

    ########### Tests ################

    def ws_codControl(self):
        # self.env['sin_sync'].check_communication()
        ambience = str(self.env['ambience'].search(
            [('description', '=', 'PRUEBAS')]).id_ambience)
        modality = str(self.env['modalities'].search(
            [('description', '=', 'ELECTRONICA')]).id_modality)
        selling_point = str(self.env['selling_point'].search(
            [('description', '=', 'PUNTO DE VENTA 0')]).id_selling_point)
        branch_office = str(self.env['branch_office'].search(
            [('description', '=', 'CASA MATRIZ')]).id_branch_office)
        system_code = str(self.env['bo_edi_params'].search(
            [('name', '=', 'CODIGOSISTEMA')]).value)
        cuis = str(self.env['bo_edi_params'].search(
            [('name', '=', 'CUIS')]).value)
        nit = str(self.env['bo_edi_params'].search(
            [('name', '=', 'NIT')]).value)
        return (self.env['sin_sync'].get_cufd(
            ambience,
            modality,
            selling_point,
            system_code,
            branch_office,
            cuis,
            nit,
            1
        ))

    def sync_activities(self):
        self.env['sin_sync'].cert_sync_catal(50, 0)

    ########### Anulaciones ################

    def button_cancel(self):
        print("//////////////////////")
        print("INHERITANCE BABY")
        print("//////////////////////")

        super(AccountMove, self).button_cancel()

    ########### STANDARD BILLING ################

    def generate_control_code(self):
        if self.dosage_id:
            auth_num = str(self.dosage_id['auth_number'])
            inv_num = str(self.dosage_id['invoice_number'])
            nit_client = str(self.partner_id.vat)
            inv_date = str(self.getTime().strftime("%Y%m%d"))
            total = str(round(self.amount_total))
            key = str(self.dosage_id['key'])

            self.control_code = self.env['standard_billing'].controlCode(
                auth_num, inv_num, nit_client, inv_date, total, key)
            self.auth_number = auth_num
            self.l10n_bo_invoice_number = inv_num
            self.dosage_id['invoice_number'] += 1
        else:
            if "INV" in self.name:
                raise Warning('You must select an invoice dosage')

    def action_post(self):
        self.generate_control_code()
        super(AccountMove, self).action_post()

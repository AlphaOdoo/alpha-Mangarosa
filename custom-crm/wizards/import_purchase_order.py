# -*- coding: utf-8 -*-

import logging
import os
import csv
import tempfile
from odoo.exceptions import UserError
from odoo import api, fields, models, _, SUPERUSER_ID
from datetime import datetime, timedelta, date
import xlrd, mmap, xlwt
import base64, binascii

try:
    from psycopg2 import sql
except ImportError:
    import sql

_logger = logging.getLogger(__name__)


class ImportPurchaseOrder(models.TransientModel):

    _name = "wizards.import.purchase.order"
    _description = "wizards.import.purchase.order"

    file_data = fields.Binary('Archive', required=True,)
    file_name = fields.Char('File Name')
    partner_id = fields.Many2one('res.partner', string='Partner', required=True, domain=[('supplier', '=', True)])

    def _default_order(self):
        return self.env['purchase.order'].browse(self._context.get('active_id'))

    def _default_company(self):
        return self.env['res.company'].browse(self._context.get('company_id')) or self.env.company

    def import_button(self):
        if not self.csv_validator(self.file_name):
            raise UserError(_("The file must be an .xls/.xlsx extension"))

        # file_path = tempfile.gettempdir()+'/file.xlsx'
        # data = self.file_data
        # f = open(file_path,'wb')
        # f.write(data.decode('base64'))
        # f.close()

        fp = tempfile.NamedTemporaryFile(suffix=".xlsx")
        fp.write(binascii.a2b_base64(self.file_data))  # self.xls_file is your binary field
        fp.seek(0)
        # workbook = xlrd.open_workbook(file_path, on_demand = True)
        workbook = xlrd.open_workbook(fp.name)
        worksheet = workbook.sheet_by_index(0)
        first_row = []  # The row where we stock the name of the column
        for col in range(worksheet.ncols):
            first_row.append(worksheet.cell_value(0, col))
        _logger.debug('Sacando el encabezado ****************')
        _logger.debug(first_row)
        # transform the workbook to a list of dictionaries
        archive_lines = []
        for row in range(1, worksheet.nrows):
            elm = {}
            for col in range(worksheet.ncols):
                elm[first_row[col]] = worksheet.cell_value(row, col)
            _logger.debug('Sacando el cuerpo ****************')
            _logger.debug(elm)
            archive_lines.append(elm)

        purchase_order_obj = self.env['purchase.order']
        product_obj = self.env['product.product']
        product_template_obj = self.env['product.template']
        purchase_order_line_obj = self.env['purchase.order.line']
        self.valid_columns_keys(archive_lines)
        self.valid_product_code(archive_lines, product_obj)
        # self.valid_prices(archive_lines)
        
        vals = {
            'partner_id': self.partner_id.id,
            'date_planned': datetime.now(),
        }
        purchase_order_id = purchase_order_obj.create(vals)
        cont = 0
        for line in archive_lines:
            cont += 1
            code = str(line.get('Referencia Interna', ""))
            product_id = product_obj.search([('default_code', '=', code)])
            quantity = line.get(u'Cant.', 0)
            leadtime = line.get('Lead time', "")
            price_unit = line.get('Venta Total', "") / quantity
            # product_uom = product_template_obj.search([('default_code','=',code)])
            taxes = product_id.supplier_taxes_id.filtered(lambda r: not product_id.company_id or r.company_id == product_id.company_id)
            tax_ids = taxes.ids
            if purchase_order_id and product_id:
                vals = {
                    'order_id': purchase_order_id.id,
                    'product_id': product_id.id,
                    'company_id': purchase_order_id.company_id.id,
                    'customer_lead': leadtime,
                    'product_qty': float(quantity),
                    'price_unit': price_unit,
                    # 'date_planned': datetime.now(),
                    'product_uom': product_id.product_tmpl_id.uom_po_id.id,
                    'name': product_id.name,
                    'taxes_id': [(6,  0, tax_ids)],
                }
                purchase_order_line_id = purchase_order_line_obj.create(vals)
                Tag1_id = self.env['account.analytic.tag'].search([('name', '=', line.get('Tag 1'))]).id
                Tag2_id = self.env['account.analytic.tag'].search([('name', '=', line.get('Tag 2'))]).id
                Tag3_id = self.env['account.analytic.tag'].search([('name', '=', line.get('Tag 3'))]).id
                sql_select = sql.SQL(
                    '''
                    INSERT INTO account_analytic_tag_purchase_order_line_rel (purchase_order_line_id,account_analytic_tag_id) VALUES 
                    ( ''' + chr(39) + str(purchase_order_line_id) + chr(39) + ''' , ''' + chr(39) + str(Tag1_id) + chr(39) + ''' ),    
                    ( ''' + chr(39) + str(purchase_order_line_id) + chr(39) + ''' , ''' + chr(39) + str(Tag2_id) + chr(39) + ''' ),    
                    ( ''' + chr(39) + str(purchase_order_line_id) + chr(39) + ''' , ''' + chr(39) + str(Tag3_id) + chr(39) + ''' )'''
                )
                self._cr.execute(sql_select)
                self._cr.execute('commit')

        if self._context.get('open_order', False):
            return purchase_order_id.action_view_order(purchase_order_id.id)
        return {'type': 'ir.actions.act_window_close'}

    def find_parnert(self, record):
        return self.env['res.partner'].search([('name', '=', record.get('Proveedor'))])

    def create_parnert(self, record):
        _logger.debug("entro a crear partner en sale order")
        _logger.debug(record.get('Proveedor'))
        partner = record.get('Proveedor')
        comp_id = self.env.company.id
        _logger.debug(comp_id)
        # self.env['res.partner'].create({
        #     'name': partner,
        #     'company_id': comp_id,
        # })
        vals = {
            'name': partner,
            'customer_rank': 1,
            'supplier_rank': 0,
            'company_id': comp_id,
            'company_type': 'company',
            'type': 'contact',
        }
        return self.env['res.partner'].create(vals)

    def create_product(self, record):
        product_category_obj = self.env['product.category']
        partner = self.find_parnert(record)
        if partner:
            _logger.debug("hay partner huuuura")
        else:
            _logger.debug("no hay partner  chingaaaos")
            partner = self.create_parnert(record)
        _logger.debug("CREANDO PRODUCTO NUEVO")
        ventt = float(record.get('Venta Total'))
        _logger.debug(ventt)
        _logger.debug(record)
        _logger.debug(record.get('Producto'))
        _logger.debug(record.get('Cant.'))
        cant = float(record.get('Cant.'))
        leadtime = record.get('Lead time', "")
        product_code = record.get('Referencia Interna', "")
        std_price = float(ventt / cant)
        _logger.debug(std_price)
        cat_id = product_category_obj.search([('complete_name', '=', record.get('Sub Categoria'))]).id
        _logger.debug(cat_id)
        comp_id = self.env.company.id
        _logger.debug('Esta la compañiaaa')
        _logger.debug(comp_id)
        type_option = self.get_valid_type(record.get('Tipo'))
        _logger.debug(type_option)

        seller = self.env['product.supplierinfo'].create({
            'name': partner.id,
            'price': record.get('Precio Lista Unitario'),
            'delay': leadtime,
            'product_code': product_code,
        })

        self.env['product.template'].create({
            'name': record.get('Producto'),
            'description_sale': record.get('Descripción'),
            'description_purchase': record.get('Descripción'),
            'standard_price': record.get('Precio Lista Unitario'),
            'list_price': std_price,
            'default_code': record.get('Referencia Interna'),
            'categ_id': cat_id,
            'company_id': comp_id,
            'type': type_option,
            'invoice_policy': 'order',
            'tracking': 'serial',
            'sale_ok': 'true',
            'purchase_ok': 'true',
            'seller_ids': [seller.id],
            'sin_item': self.env['sin_items'].search([('sin_code', '=', record.get('SIN Items'))]).id,
            'measure_unit': self.env['measure_unit'].search([('description', '=', record.get('Measure Items'))]).id,
        })

    def find_product(self, record):
        return self.env['product.template'].search([('default_code', '=', record.get('Referencia Interna'))])

    @api.model
    def valid_prices(self, archive_lines):
        cont = 0
        for line in archive_lines:
            cont += 1
            price = line.get('price', "")
            if price != "":
                price = str(price).replace("$", "").replace(",", ".")
            try:
                price_float = float(price)
            except:
                raise UserError("The price of the line item %s does not have an appropriate format, for example: '100.00' - '100'"%cont)

        return True

    @api.model
    def get_valid_price(self, price, cont):
        if price != "":
            price = str(price).replace("$", "").replace(",", ".")
        try:
            price_float = float(price)
            return price_float
        except:
            raise UserError("The price of the line item %s does not have an appropriate format, for example: '100.00' - '100'"%cont)
        return False

    @api.model
    def get_valid_type(self, typeA):
        cad = ''
        try:
            if typeA != "":
                if typeA == 'Comsumible':
                    cad = 'consu'
                    _logger.debug('tipo consu ***********************' + cad)
                elif typeA == 'Servicio':
                    cad = 'service'
                    _logger.debug('tipo service ***********************' + cad)
                elif typeA == 'Almacenable':
                    cad = 'product'
                    _logger.debug('tipo product ***********************' + cad)
                else:
                    car = 'Error en el Type'
                    _logger.debug('tipo consu ***********************' + cad)
                    raise UserError('Error al crear el tipo de producto')
                    return ''
            return cad
        except:
            raise UserError(
                "The type of the line item %s does not have an appropriate format, Cunsumible, Servicio, Almacenable")
        return False

    @api.model
    def valid_product_code(self, archive_lines, product_obj, product_template_obj):
        cont = 0
        for line in archive_lines:
            cont += 1
            code = str(line.get('Referencia Interna', ""))
            product_id = product_template_obj.search([('default_code', '=', code)])
            if len(product_id) > 1:
                raise UserError("The product code of line %s is duplicated in the system."%cont)
            if not product_id:
                self.create_product(line)
                # raise UserError("The product code of line %s can't be found in the system."%cont)

    @api.model
    def valid_columns_keys(self, archive_lines):
        columns = archive_lines[0].keys()
        # print "columns>>",columns
        text = "The file must contain the following columns: \n The following columns are not in the file:"; text2 = text
        # Item
        # Referencia Interna
        # Producto
        # Descripción
        # Sub Categoria
        # Lead time
        # Tipo
        # tracking
        # Tiempo de Garantia(meses)
        # Proveedor
        # Cant.
        # Precio Lista Unitario
        # Total Proveedor
        # Venta Total
        # Tag 1
        # Tag 2
        # Tag 3

        if not 'Item' in columns:
            text += "\n| Item |"
        if not 'Referencia Interna' in columns:
            text += "\n| Referencia Interna |"
        if not 'Producto' in columns:
            text += "\n| Producto |"
        if not 'Descripción' in columns:
            text += "\n| Descripción |"
        if not 'Sub Categoria' in columns:
            text += "\n| Sub Categoria |"
        if not 'Tipo' in columns:
            text += "\n| Tipo |"
        if not 'Lead time' in columns:
            text += "\n| Lead time |"
        if not 'Tiempo de Garantia(meses)' in columns:
            text += "\n| Tiempo de Garantia(meses) |"
        if not 'Proveedor' in columns:
            text += "\n| Proveedor |"
        if not u'Cant.' in columns:
            text += "\n| Cant. |"
        if not 'Precio Lista Unitario' in columns:
            text += "\n| Precio Lista Unitario |"
        if not 'Total Proveedor' in columns:
            text += "\n| Total Proveedor |"
        if not 'Venta Total' in columns:
            text += "\n| Venta Total |"
        if not 'Tag 1' in columns:
            text += "\n| Tag 1 |"
        if not 'Tag 2' in columns:
            text += "\n| Tag 2 |"
        if not 'Tag 3' in columns:
            text += "\n| Tag 3 |"
        if not 'SIN Items' in columns:
            text += "\n| SIN Items|"
        if not 'Measure Items' in columns:
            text += "\n| Measure Items |"
        if text != text2:
            raise UserError(text)

        return True

    @api.model
    def csv_validator(self, xml_name):
        name, extension = os.path.splitext(xml_name)
        return True if extension == '.xls' or extension == '.xlsx' else False
        

class purchase_order(models.Model):
    _inherit = 'purchase.order'

    # @api.multi
    def action_view_order(self, purchase_order_id):
        action = self.env.ref('purchase.purchase_rfq').read()[0]
        action['views'] = [(self.env.ref('purchase.purchase_order_form').id, 'form')]
        action['res_id'] = purchase_order_id

        return action
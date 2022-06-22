from asyncio import streams
from odoo import fields, models

import zeep
from zeep import client

import codecs


class SinSync(models.Model):
    _name = 'sin_sync'
    _description = 'Recurrent SIN Api calls'

    def _get_token(self):
        return self.env['bo_edi_params'].search(
            [('name', '=', 'TOKENAPI')]).value

    # SERVICIO DE OBTENCIÓN DE CÓDIGOS

    def check_communication(self):
        token = self._get_token()
        settings = zeep.Settings(
            extra_http_headers={'apikey': str(token)})
        client = zeep.Client(
            wsdl='https://pilotosiatservicios.impuestos.gob.bo/v2/FacturacionCodigos?wsdl',
            settings=settings)
        result = client.service.verificarComunicacion()
        print(result)

    def get_cufd(self, ambiente, modalidad, puntoventa, codSistema, codSucursal, cuis, nit, tipoCodigo):
        token = self._get_token()
        settings = zeep.Settings(
            extra_http_headers={'apikey': str(token)})
        client = zeep.Client(
            wsdl='https://pilotosiatservicios.impuestos.gob.bo/v2/FacturacionCodigos?wsdl',
            settings=settings)
        params = {'SolicitudCufd': {
            'codigoAmbiente': ambiente,
            'codigoModalidad': modalidad,
            'codigoPuntoVenta': puntoventa,
            'codigoSistema': codSistema,
            'codigoSucursal': codSucursal,
            'cuis': cuis,
            'nit': nit
        }
        }
        result = client.service.cufd(**params)
        if (tipoCodigo == 0):  # CodigoControl
            return result.codigoControl
        else:  # CUFD
            return result.codigo

    # SERVICIO DE SINCRONIZACIÓN DE DATOS

    def _sync_general(self, ambiente, puntoventa, codSistema, codSucursal, cuis, nit):
        token = self._get_token()
        settings = zeep.Settings(
            extra_http_headers={'apikey': str(token)})
        client = zeep.Client(
            wsdl='https://pilotosiatservicios.impuestos.gob.bo/v2/FacturacionSincronizacion?wsdl',
            settings=settings)
        params = {'SolicitudSincronizacion': {
            'codigoAmbiente': ambiente,
            'codigoPuntoVenta': puntoventa,
            'codigoSistema': codSistema,
            'codigoSucursal': codSucursal,
            'cuis': cuis,
            'nit': nit
        }
        }
        return {'client': client, 'params': params, 'ambience': ambiente}

    def sync_activities(self, ws_method):
        client = ws_method['client']
        params = ws_method['params']
        ambiente = int(ws_method['ambience'])
        result = client.service.sincronizarActividades(**params)

        if (ambiente == 1):
            activities = self.env['l10n_bo.company.activities']
            activities.search([]).unlink()
            print(activities.search([]))
            for activity in result.listaActividades:
                new_record = {
                    'code': activity.codigoCaeb,
                    'name': activity.descripcion,
                    'type': activity.tipoActividad
                }
                activities.create(new_record)
            for act in activities.search([]).name:
                print(act.type)

        # Método para comparacion de registros existentes y adicion de nuevos pendiente
        # for activity in result.listaActividades:
        #     db_activity = self.env['l10n_bo.company.activities'].search(
        #         [('code', '=', activity.codigoCaeb)])
        #     print(db_activity.name)
        #     if not hasattr(db_activity, 'code'):
        #         new_record = {
        #             'code': activity.codigoCaeb,
        #             'name': activity.descripcion,
        #             'type': activity.tipoActividad
        #         }
        #         self.env['l10n_bo.company.activities'].create(new_record)
        #         print('Nuevos registros: ')
        #         print(self.env['l10n_bo.company.activities'].search([]))

    def sync_fecha_hora(self, ws_method):
        client = ws_method['client']
        params = ws_method['params']
        ambiente = int(ws_method['ambience'])
        result = client.service.sincronizarFechaHora(**params)

        date_time = self.env['boedi_date_time']
        if (ambiente == 1):
            date_time.search([]).unlink()
            print(date_time.search([]))
            new_record = {
                'date_time': result.fechaHora
            }
            date_time.create(new_record)

        print(date_time.search([]).date_time)

    def sync_actividades_doc_sector(self, ws_method):
        client = ws_method['client']
        params = ws_method['params']
        ambiente = int(ws_method['ambience'])
        result = client.service.sincronizarListaActividadesDocumentoSector(
            **params)

        if (ambiente == 1):
            activities_doc_sec = self.env['activity_doc_sector']
            activities_doc_sec.search([]).unlink()
            print(activities_doc_sec.search([]))
            for act_doc_sec in result.listaActividadesDocumentoSector:
                new_record = {
                    'activity_code': act_doc_sec.codigoActividad,
                    'sector_doc_code': act_doc_sec.codigoDocumentoSector,
                    'sector_doc_type': act_doc_sec.tipoDocumentoSector
                }
                activities_doc_sec.create(new_record)
            for act in activities_doc_sec.search([]):
                print(act.activity_code)

    def sync_invoice_caption(self, ws_method):
        client = ws_method['client']
        params = ws_method['params']
        ambiente = int(ws_method['ambience'])
        result = client.service.sincronizarListaLeyendasFactura(
            **params)

        if (ambiente == 1):
            inv_caption = self.env['invoice_caption']
            inv_caption.search([]).unlink()
            print(inv_caption.search([]))
            for inv_cap in result.listaLeyendas:
                new_record = {
                    'activity_code': inv_cap.codigoActividad,
                    'description': inv_cap.descripcionLeyenda
                }
                inv_caption.create(new_record)
            for cap in inv_caption.search([]):
                print(cap.description)

    def sync_messages_service(self, ws_method):
        client = ws_method['client']
        params = ws_method['params']
        ambiente = int(ws_method['ambience'])
        result = client.service.sincronizarListaMensajesServicios(
            **params)

        if (ambiente == 1):
            message_serv = self.env['messages_service']
            message_serv.search([]).unlink()
            print(message_serv.search([]))
            for mes_serv in result.listaCodigos:
                new_record = {
                    'code': mes_serv.codigoClasificador,
                    'description': mes_serv.descripcion
                }
                message_serv.create(new_record)
            for mes in message_serv.search([]):
                print(mes.description)

    def sync_sin_items(self, ws_method):
        client = ws_method['client']
        params = ws_method['params']
        ambiente = int(ws_method['ambience'])
        result = client.service.sincronizarListaProductosServicios(
            **params)

        if (ambiente == 1):
            sin_items = self.env['sin_items']
            sin_items.search([]).unlink()
            print(sin_items.search([]))
            for sin_item in result.listaCodigos:
                new_record = {
                    'sin_code': sin_item.codigoProducto,
                    'description': sin_item.descripcionProducto,
                    'activity_code': sin_item.codigoActividad
                }
                sin_items.create(new_record)
            for item in sin_items.search([]):
                print(item.description)

    def sync_invoice_events(self, ws_method):
        client = ws_method['client']
        params = ws_method['params']
        ambiente = int(ws_method['ambience'])
        result = client.service.sincronizarParametricaEventosSignificativos(
            **params)

        if (ambiente == 1):
            invoice_event = self.env['invoice_event']
            invoice_event.search([]).unlink()
            print(invoice_event.search([]))
            for inv_ev in result.listaCodigos:
                new_record = {
                    'code': inv_ev.codigoClasificador,
                    'description': inv_ev.descripcion
                }
                invoice_event.create(new_record)
            for inv in invoice_event.search([]):
                print(inv.description)

    def sync_null_reasons(self, ws_method):
        client = ws_method['client']
        params = ws_method['params']
        ambiente = int(ws_method['ambience'])
        result = client.service.sincronizarParametricaMotivoAnulacion(
            **params)

        if (ambiente == 1):
            null_reason = self.env['null_reason']
            null_reason.search([]).unlink()
            print(null_reason.search([]))
            for null_re in result.listaCodigos:
                new_record = {
                    'code': null_re.codigoClasificador,
                    'description': null_re.descripcion
                }
                null_reason.create(new_record)
            for reas in null_reason.search([]):
                print(reas.description)

    def sync_native_country(self, ws_method):
        client = ws_method['client']
        params = ws_method['params']
        ambiente = int(ws_method['ambience'])
        result = client.service.sincronizarParametricaPaisOrigen(
            **params)

        if (ambiente == 1):
            native_country = self.env['native_country']
            native_country.search([]).unlink()
            print(native_country.search([]))
            for nat_co in result.listaCodigos:
                new_record = {
                    'code': nat_co.codigoClasificador,
                    'description': nat_co.descripcion
                }
                native_country.create(new_record)
            for nat in native_country.search([]):
                print(nat.description)

    def sync_id_type(self, ws_method):
        client = ws_method['client']
        params = ws_method['params']
        ambiente = int(ws_method['ambience'])
        result = client.service.sincronizarParametricaTipoDocumentoIdentidad(
            **params)

        if (ambiente == 1):
            id_type = self.env['id_type']
            id_type.search([]).unlink()
            print(id_type.search([]))
            for id_t in result.listaCodigos:
                new_record = {
                    'id_type_code': id_t.codigoClasificador,
                    'description': id_t.descripcion
                }
                id_type.create(new_record)
            for id_ty in id_type.search([]):
                print(id_ty.description)

    def sync_document_sec_type(self, ws_method):
        client = ws_method['client']
        params = ws_method['params']
        ambiente = int(ws_method['ambience'])
        result = client.service.sincronizarParametricaTipoDocumentoSector(
            **params)

        if (ambiente == 1):
            document_sec_type = self.env['document_sec_type']
            document_sec_type.search([]).unlink()
            print(document_sec_type.search([]))
            for doc_sec_type in result.listaCodigos:
                new_record = {
                    'code': doc_sec_type.codigoClasificador,
                    'description': doc_sec_type.descripcion
                }
                document_sec_type.create(new_record)
            for doc_sec in document_sec_type.search([]):
                print(doc_sec.description)

    # Métodos de Facturacion Electrónica

    def send_invoice(self, cufd, xml_file, xml_hash):

        code_doc_sec = '1'
        code_emission_type = '1'
        code_modality = str(self.env['modalities'].search(
            [('description', '=', 'ELECTRONICA')]).id_modality)
        ambience = str(self.env['ambience'].search(
            [('description', '=', 'PRUEBAS')]).id_ambience)
        selling_point = str(self.env['selling_point'].search(
            [('description', '=', 'PUNTO DE VENTA 0')]).id_selling_point)
        branch_office = str(self.env['branch_office'].search(
            [('description', '=', 'CASA MATRIZ')]).id_branch_office)
        system_code = str(self.env['bo_edi_params'].search(
            [('name', '=', 'CODIGOSISTEMA')]).value)
        cuis = str(self.env['bo_edi_params'].search(
            [('name', '=', 'CUIS-0')]).value)
        nit = str(self.env['bo_edi_params'].search(
            [('name', '=', 'NIT')]).value)
        invoice_type = '1'
        date = str(self.env['account.move'].getTime().strftime(
            "%Y-%m-%dT%H:%M:%S.%f"))

        token = self._get_token()
        settings = zeep.Settings(
            extra_http_headers={'apikey': str(token)})
        client = zeep.Client(
            wsdl='https://pilotosiatservicios.impuestos.gob.bo/v2/ServicioFacturacionCompraVenta?wsdl',
            settings=settings)
        # print('-------------------------------------------')
        # print(xml_file.decode(encoding='Latin'))
        # print('-------------------------------------------')
        # print(xml_hash)
        # print('-------------------------------------------')
        # print(date)
        params = {'SolicitudServicioRecepcionFactura': {
            'codigoAmbiente': ambience,
            'codigoDocumentoSector': code_doc_sec,
            'codigoEmision': code_emission_type,
            'codigoModalidad': code_modality,
            'codigoPuntoVenta': selling_point,
            'codigoSistema': system_code,
            'codigoSucursal': branch_office,
            'cufd': cufd,
            'cuis': cuis,
            'nit': nit,
            'tipoFacturaDocumento': invoice_type,
            'archivo': xml_file,
            # Omitir ultimos 3 dígitos de los microsegundos
            # 'fechaEnvio': date[:-3],
            'fechaEnvio': str(date[:-6]) + '000',
            'hashArchivo': xml_hash
        }
        }
        print(params)
        result = client.service.recepcionFactura(**params)
        print(result)

    def sign_xml(self, xml, credentials_path, pk, cert, signed_path):
        token = self._get_token()
        settings = zeep.Settings(
            extra_http_headers={'apikey': str(token)})
        client = zeep.Client(
            wsdl='http://127.0.0.1:8080/FirmaDigital/FirmaDigital?wsdl',
            settings=settings)

        params = {
            'arg0': str(xml),
            'arg1': credentials_path,
            'arg2': pk,
            'arg3': cert,
            'arg4': signed_path
        }

        result = client.service.firmarXML(**params)
        return result

    # Método de consumo Certificación Catalogos

    def cert_sync_catal(self, iterations, sellingPoint):
        ambience = str(self.env['ambience'].search(
            [('description', '=', 'PRUEBAS')]).id_ambience)
        selling_point = str(sellingPoint)
        branch_office = str(self.env['branch_office'].search(
            [('description', '=', 'CASA MATRIZ')]).id_branch_office)
        system_code = str(self.env['bo_edi_params'].search(
            [('name', '=', 'CODIGOSISTEMA')]).value)
        cuis = ''
        if (sellingPoint == 0):
            cuis = str(self.env['bo_edi_params'].search(
                [('name', '=', 'CUIS-0')]).value)
        elif (sellingPoint == 1):
            cuis = str(self.env['bo_edi_params'].search(
                [('name', '=', 'CUIS-1')]).value)
        nit = str(self.env['bo_edi_params'].search(
            [('name', '=', 'NIT')]).value)

        ws_method_sync = self._sync_general(ambience,
                                            selling_point,
                                            system_code,
                                            branch_office,
                                            cuis,
                                            nit)

        for i in range(iterations):
            self.sync_document_sec_type(
                ws_method_sync
            )
        print('Prueba Finalizada')

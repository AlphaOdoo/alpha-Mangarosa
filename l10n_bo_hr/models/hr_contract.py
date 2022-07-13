from odoo import models, fields, api
from odoo.exceptions import UserError, ValidationError


class custom_contract(models.Model):
    _inherit = 'hr.contract'

    salary_advance = fields.Monetary(string='Adelanto de sueldo')

    transport_assignment = fields.Monetary(string='Asignación Transporte')

    allowance_periods = fields.Monetary(string='Asignación Viaticos')

    premium_bonus = fields.Monetary(string='Prima')

    bonus = fields.Monetary(string='Aguinaldo')

    health_manager_id = fields.Many2one(comodel_name='res.partner', string='Ente gestor de salud',
                                        ondelete='cascade',
                                        required=False,
                                        default=False,
                                        domain="['|', ('company_id', '=', False), ('company_id', '=', company_id)]")

    avc_number = fields.Char(required=False, string='AVC-04')

    insured_code = fields.Char(string='Codigo Asegurado')
    nua_cua = fields.Integer(string='NUA/CUA')
    contributes_afp = fields.Boolean(
        string='Aporta AFP', required=False, default=False)
    disabled_person = fields.Boolean(
        string='Persona con Discapacidad', required=False, default=False)
    disabled_person_tutor = fields.Boolean(
        string='Tutor Persona con Discapacidad', required=False, default=False)
    retiree = fields.Boolean(
        string='ES Jubilado', required=False, default=False)

    afp_manager_id = fields.Many2one(comodel_name='res.partner', string='Gestor AFP',
                                     ondelete='cascade',
                                     required=False,
                                     default=False,
                                     domain="['|', ('company_id', '=', False), ('company_id', '=', company_id)]")

    divisa = fields.Selection(string='Divisa',
                              selection=[('bolivianos', 'BOB'),
                                         ('dolares', 'USD'),
                                         ('euros', 'EUR')],
                              copy=False, default='bolivianos')

    # Campos Sandra Omonte
    contract_modality = fields.Selection(string='Modalidad Contrato',
                                         selection=[('tiempoindef', 'Tiempo indefinido'),
                                                    ('plazofijo', 'A plazo fijo'),
                                                    ('eventual',
                                                     'Condicional o Eventual'),
                                                    ('temporada', 'Por Temporada'),
                                                    ('servicio', 'Por realizacion de Servicio')],
                                         copy=False, default='tiempoindef')
    contract_type_expiration = fields.Date(
        string='Vencimiento tipo de contratacion')
    calculate_overtime = fields.Boolean(
        string='Calcula Horas Extras', default=False)
    cbu = fields.Integer(string='CBU')
    settlement_start_date = fields.Date('Fecha Inicio Finiquito')
    dismissal_date = fields.Date('Fecha retiro')
    dismissal_reason = fields.Text('Motivo Retiro')
    # bank_company =  fields.Many2one(comodel_name='res.bank', string='Banco')
    # cta_bank =  fields.Many2one(comodel_name='res.partner.bank', string='Cuenta Banco',
    #                          domain="[('id_bank','=',bank_company')")
    #Campos Erick
    contract_type_c = fields.Selection(string='Tipo de contrato',
                              selection=[('Escrito', 'Escrito'),
                                         ('Verbal', 'Verbal')],
                              copy=False, default='Escrito')
    #contract_modality_c = fields.Selection(string='Modalida de contrato',
                              #selection=[ ('euros', 'EUR')],
                              #copy=False, default='bolivianos')

import logging
from odoo import api, fields, models

_logger = logging.getLogger(__name__)


class ResConfigSettings(models.TransientModel):

    _inherit = 'res.config.settings'

    # l10n_bo_dfe_service_provider = fields.Selection(related='company_id.l10n_bo_dfe_service_provider', readonly=False,
    #                                                 help='Please select your company service provider for DFE service.')
    # # l10n_cl_activity_description = fields.Char(
    # #     string='Glosa Giro', related='company_id.l10n_cl_activity_description', readonly=False)
    # l10n_bo_company_activity_ids = fields.Many2many('l10n_bo.company.activities', string='Activities Names',
    #                                                 related='company_id.l10n_bo_company_activity_ids', readonly=False,
    #                                                 help='Please select the SIN registered economic activities codes for the company')

    l10n_bo_sync_time = fields.Datetime(
        string='Sync Time', help='Set the synchronization time for the SIN values')

    # SIN Codes

    l10n_bo_system_code = fields.Text(
        string='System Code', help='Code given by SIN in order to emit invoices')

    l10n_bo_CUIS_code = fields.Text(
        string='CUIS Code', help='Code given by SIN in order to emit electronic invoices')

    # l10n_bo_current_cuf = fields.Text(
    #     string='Current CUF Code', help='(Código Unico de Facturación) Code referred to Point of Attention', readonly=True)

    l10n_bo_current_cufd = fields.Text(
        string='Current CUFD Code', help='(Código Unico de Facturación Diaria) Code provided by SIN, generated daily, identifies the invoice along with a number', readonly=True)

    ###

    # Selling Points

    l10n_bo_active_selling_point = fields.Many2one(
        comodel_name='selling_point', string='Active Attention Point')

    l10n_bo_current_invoice_number = fields.Text(
        string='Current Invoice Number', help='Along with CUFD Code, helps in identifying the invoice', readonly=True)

    ###

    l10n_bo_invoicing_modality = fields.Many2one(
        'modalities', string='Modality Selection')

    l10n_bo_emission_type = fields.Many2one(
        'emission_types', string='Emission Type Selection')

    l10n_bo_sector_type = fields.Many2one(
        'sector_types', string='Sector Type Selection')

    l10n_bo_ambience = fields.Many2one('ambience', string='Ambience')

    l10n_bo_invoice_package_number = fields.Integer(
        string='Package Number', help='Set the number of invoices per package')

    module_l10n_bo_reports = fields.Boolean(string='Accounting Reports')

    l10n_bo_invoicing_type = fields.Boolean('Invoicing Type')

    @api.onchange('l10n_bo_invoicing_type')
    def _invoice_type_change(self):
        if self.l10n_bo_invoicing_type == False:
            for i in self.env['account.move'].search([]):
                i.e_billing = False
        else:
            for i in self.env['account.move'].search([]):
                i.e_billing = True

    # Metodos Requeridos para el correcto registro y obtencion

    def set_values(self):
        res = super(ResConfigSettings, self).set_values()
        self.env['ir.config_parameter'].sudo().set_param(
            'res.config.settings.l10n_bo_invoicing_type', self.l10n_bo_invoicing_type)
        # self.env['ir.config_parameter'].sudo().set_param(
        #     'res.config.settings.l10n_bo_emission_type', self.l10n_bo_emission_type)
        # self.env['ir.config_parameter'].sudo().set_param(
        #     'res.config.settings.l10n_bo_invoicing_modality', self.l10n_bo_invoicing_modality)
        # self.env['ir.config_parameter'].sudo().set_param(
        #     'res.config.settings.l10n_bo_ambience', self.l10n_bo_ambience)
        # self.env['ir.config_parameter'].sudo().set_param(
        #     'res.config.settings.l10n_bo_system_code', self.l10n_bo_system_code)
        # self.env['ir.config_parameter'].sudo().set_param(
        #     'res.config.settings.l10n_bo_CUIS_code', self.l10n_bo_CUIS_code)
        # self.env['ir.config_parameter'].sudo().set_param(
        #     'res.config.settings.l10n_bo_invoice_package_number', self.l10n_bo_invoice_package_number)
        return res

    @api.model
    def get_values(self):
        res = super(ResConfigSettings, self).get_values()
        get_param = self.env['ir.config_parameter'].sudo().get_param
        get_invoicing_type = get_param(
            'res.config.settings.l10n_bo_invoicing_type')
        # get_invoicing_modality = get_param(
        #     'res.config.settings.l10n_bo_invoicing_modality')
        # get_ambience = get_param(
        #     'res.config.settings.l10n_bo_ambience')
        res.update(
            l10n_bo_invoicing_type=get_invoicing_type,
            # l10n_bo_invoicing_modality=get_invoicing_modality,
            # l10n_bo_ambience=get_ambience
        )
        return res

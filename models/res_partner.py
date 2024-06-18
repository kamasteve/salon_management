# -*- coding: utf-8 -*-
###################################################################################
#
#    Cybrosys Technologies Pvt. Ltd.
#    Copyright (C) 2021-TODAY Cybrosys Technologies (<https://www.cybrosys.com>).
#
#    Author: AVINASH NK(<https://www.cybrosys.com>)
#
#    This program is free software: you can modify
#    it under the terms of the GNU Affero General Public License (AGPL) as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <https://www.gnu.org/licenses/>.
#
###################################################################################

from odoo import fields, models,api
from datetime import datetime, timedelta

class Partner(models.Model):
    _inherit = 'res.partner'

    partner_salon = fields.Boolean(string="Is a Salon Partner")
    last_salon_order_date = fields.Date(string='Last Sale Order Date', compute='_compute_last_sale_order_date')
    total_salon_amount_orders = fields.Integer(string='Total Sale Orders', compute='_compute_total_sale_orders')
    total_salon_amount = fields.Float(string='Total Sales Amount', compute='_compute_total_sales_amount')
    day_gone = fields.Integer("Days Since the last Visit")
    phone = fields.Char("Phone",required=True)
    mobile = fields.Char(string='Computed Mobile', compute='_compute_computed_mobile')


    _sql_constraints = [
        ('phone_unique', 'UNIQUE(phone)', 'Phone number must be unique!')
    ]

    @api.depends('phone')
    def _compute_computed_mobile(self):
        for partner in self:
            if partner.phone:
                partner.mobile = '+254' + partner.phone
            else:
                partner.mobile = ''
    def _compute_last_sale_order_date(self):
        SaleOrder = self.env['salon.order']
        for partner in self:
            last_order = SaleOrder.search([('partner_id', '=', partner.id)], order='date desc', limit=1)
            partner.last_salon_order_date = last_order.date if last_order else False
            if last_order:
               #last_order_date = last_order.date()  # Extracting the date part if datetime object
               current_date = datetime.now().date()
               days_gone = current_date - partner.last_salon_order_date
               print(days_gone)
               partner.day_gone = days_gone.days
            else:
                partner.day_gone = 0



    def _compute_total_sale_orders(self):
        SaleOrder = self.env['salon.order']
        for partner in self:
            total_orders = SaleOrder.search_count([('partner_id', '=', partner.id)])
            partner.total_salon_amount_orders = total_orders

    def _compute_total_sales_amount(self):
        SaleOrder = self.env['salon.order']
        for partner in self:
            total_amount = SaleOrder.search([('partner_id', '=', partner.id)]).mapped('price_subtotal')
            partner.total_salon_amount = sum(total_amount)
class EmployeeTargets(models.Model):
    _name = 'employee.targets'
    _description = 'Employee Targets'

    employee_id = fields.Many2one('hr.employee', string='Employee', required=True)
    target_date = fields.Date(string='Target Date', required=True)
    target_amount = fields.Float(string='Target Amount', required=True)

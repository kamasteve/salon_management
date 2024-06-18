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

from datetime import date, datetime, timedelta

from odoo import api, fields, models
from odoo.tools.translate import _
from odoo.exceptions import UserError, ValidationError


class SalonOrder(models.Model):
    _name = 'salon.order'
    _description = 'Salon Order'

    name = fields.Char(string='Salon', required=True, copy=False, readonly=True,
                       default='Draft Salon Order')
    start_time = fields.Datetime(
        string="Start time", default=fields.Datetime.now, required=True)
    end_time = fields.Datetime(string="End time")
    date = fields.Datetime(
        string="Date", required=True, default=fields.Datetime.now)
    color = fields.Integer(string="Color", default=6)
    partner_id = fields.Many2one(
        'res.partner', string="Customer",
        help="""If the customer is a regular customer,
        then you can add the customer in your database""", store=True)
    customer_name = fields.Char(string="Name")
    currency_id = fields.Many2one(
        'res.currency', string='Currency', required=True,
        default=lambda self: self.env.user.company_id.currency_id.id)
    chair_id = fields.Many2one('salon.chair', string="Chair")
    price_subtotal = fields.Monetary(string='Total', readonly=True, store=True,
                                     compute='_compute_price_subtotal')
    time_taken_total = fields.Float(string="Total time")
    note = fields.Text('Terms and conditions')
    order_line_ids = fields.One2many(
        'salon.order.line', 'salon_order_id', string="Order Lines",copy=True)
    stage_id = fields.Many2one('salon.stage', string="Stages",
                               group_expand='_read_group_stage_ids',default=1,copy=False)
    inv_stage_identifier = fields.Boolean(string="Stage Identifier")
    validation_controller = fields.Boolean(
        string="Validation controller", default=False)
    booking_identifier = fields.Boolean(string="Booking Identifier")
    user_id = fields.Many2one('res.users', string="Chair User")
    salon_order_created_user = fields.Integer(string="Salon Order Created User",
                                              default=lambda self: self._uid)
    count = fields.Integer(string='Delivery Orders', compute='_compute_count')
    service_card_no = fields.Char("Service Card number", required=True)
    attedants_tips = fields.Monetary("Tips")
    payment_ref = fields.Char("Payment Ref")
    phone = fields.Char("Phone",required=True)
    salon_payment_method = fields.Many2one('salon.payment.method',string='Payment Method',
        help='Select the preferred payment method.',required=True
    )
    _sql_constraints = [
        ('service_card_no_uniq', 'unique (service_card_no)', 'Service Card number must be unique!')
    ]
    @api.onchange('phone')
    def search_partner_by_phone(self):
        if self.phone:
           self.partner_id = self.env['res.partner'].search([('phone', '=', self.phone)]).id
        else:
            self.partner_id = False

    @api.depends('order_line_ids.price_subtotal')
    def _compute_price_subtotal(self):
        """
        compute price_subtotal
        """
        amount_untaxed = 0.0
        total_time_taken = 0.0
        for order in self:
            for line in order.order_line_ids:
                amount_untaxed += line.price_subtotal
                total_time_taken += line.time_taken
        self.price_subtotal = amount_untaxed
        time_takes = total_time_taken
        hours = int(time_takes)
        minutes = (time_takes - hours) * 60
        start_time_store = datetime.strptime(
            str(self.start_time).split(".")[0], "%Y-%m-%d %H:%M:%S")
        self.write(
            {
                'end_time': start_time_store + timedelta(
                    hours=hours, minutes=minutes),
                'time_taken_total': total_time_taken,
            })

    def _compute_count(self):
        """
        compute invoice count of salon orders
        """
        for orders in self:
            orders.count = self.env['account.move'].search_count(
                [('invoice_origin', '=', self.name)])

    def action_view_invoice_salon(self):
        """
        function to open invoice of the salon order
        """
        return {
            'name': 'Invoices',
            'domain': [('invoice_origin', '=', self.name)],
            'res_model': 'account.move',
            'view_id': False,
            'view_mode': 'tree,form',
            'type': 'ir.actions.act_window',
        }

    @api.model
    def _read_group_stage_ids(self, stages, domain, order):
        """
        return the stages to stage_ids
        """
        stage_ids = self.env['salon.stage'].search([])
        return stage_ids

    def write(self, values):
        """
        manage drag and drop in salon order kanban view
        """
        if 'stage_id' in values.keys():
            if self.stage_id.id == 3:
                if values['stage_id'] != 4:
                    raise ValidationError(_("You can't perform that move!"))
                else:
                    time_taken_chair = self.chair_id.total_time_taken_chair
                    self.chair_id.total_time_taken_chair = (
                            time_taken_chair - self.time_taken_total)
            if self.stage_id.id == 4:
                raise ValidationError(
                    _("You can't move a salon order from Closed stage!"))
            if self.stage_id.id == 5:
                raise ValidationError(
                    _("You can't move a salon order from Cancel stage!"))
            if self.stage_id.id == 1:
                if values['stage_id'] not in [2, 5]:
                    raise ValidationError(_("You can't perform that move!"))
            if self.stage_id.id == 2:
                if values['stage_id'] == 5:
                    time_taken_chair = self.chair_id.total_time_taken_chair
                    self.chair_id.total_time_taken_chair = (
                            time_taken_chair - self.time_taken_total)
                elif values['stage_id'] == 1 or values['stage_id'] == 4:
                    raise ValidationError(_("You can't perform that move!"))
                elif values['stage_id'] == 3 and not self.inv_stage_identifier:
                    self.action_create_invoice()
        if 'stage_id' in values.keys() and self.name == "Draft Salon Order":
            if values['stage_id'] == 2:
                self.action_validate()
                self.action_confirm()
        write_values = super(SalonOrder, self).write(values)
        self.update_number_of_orders()
        return write_values

    def action_confirm(self):
        """
        confirm salon order
        """
        sequence_code = 'salon.order.sequence'
        order_date = str(self.date)
        order_date = order_date[0:10]
        self.name = self.env['ir.sequence'].with_context(
            ir_sequence_date=order_date).next_by_code(sequence_code)
        if self.partner_id:
            self.partner_id.partner_salon = True
        self.stage_id = 2
        self.update_number_of_orders()
        self.chair_id.total_time_taken_chair += self.time_taken_total
        self.user_id = self.chair_id.user_id
        self.action_create_invoice()
        self.compute_commison()
    def compute_commison(self):

        for service in self.order_line_ids:
            attedants_number = len(service.service_attedants) #self.env['service.attedants'].search_count([('salon_order_id', '=', service.id)])
            print(attedants_number)
            #raise ValidationError(attedants_number)
            #raise UserError(attedants_number)
            commssion_percentage = service.service_id.commsion
            commission_amount = (service.price - service.discount_amount) * commssion_percentage
            price_subtotal = service.price - service.discount_amount
            attedant_sale = (service.price - service.discount_amount)/attedants_number
            attedants_tips = self.attedants_tips/attedants_number
            for attedants in service.service_attedants:
                commission_obj = self.env['service.commission']
                commission_data = {
                    'service_id': service.service_id.id,
                    'attedants': attedants.id,
                    'commission_amount': commission_amount/attedants_number,
                    'salon_order_id': self.id,
                    'date': self.date,
                    'attedant_sale':attedant_sale,
                    'attedants_tips':attedants_tips,
                    'currency_id': self.currency_id.id,
                    'discount': service.discount_amount,
                }
                new_commission = commission_obj.create(commission_data)




    def action_validate(self):
        """
        validate salon order
        """
        self.validation_controller = True
        self.update_number_of_orders()

    def action_close(self):
        """
        close salon order
        """
        self.stage_id = 4
        self.update_number_of_orders()

    def action_cancel(self):
        """
        cancel salon order
        """
        self.stage_id = 5
        self.update_number_of_orders()

    def action_update_total(self):
        """
        update total amount in salon order
        """
        for order in self:
            amount_untaxed = 0.0
            for line in order.order_line_ids:
                amount_untaxed += line.price_subtotal
            order.price_subtotal = amount_untaxed

    @api.onchange('chair_id')
    def _onchange_chair_id(self):
        """
        onchange function of chair_id field
        """
        if 'active_id' in self._context.keys():
            self.chair_id = self._context['active_id']

    def action_create_invoice(self):
        """
        function to create invoice
        """
        if self.partner_id:
            supplier = self.partner_id
        else:
            supplier = self.partner_id.search(
                [("name", "=", "Salon Default Customer")])
        lines = []
        product_id = self.env['product.product'].search(
            [("name", "=", "Salon Service")])
        for records in self.order_line_ids:
            if product_id.property_account_income_id.id:
                income_account = product_id.property_account_income_id.id
            elif product_id.categ_id.property_account_income_categ_id.id:
                income_account = product_id.categ_id.\
                    property_account_income_categ_id.id
            else:
                raise UserError(
                    _("Please define income account for this product: "
                      "'%s' (id:%d).") % (product_id.name, product_id.id))
            value = (0, 0, {
                        'name': records.service_id.name,
                        'account_id': income_account,
                        'price_unit': records.price,
                        'quantity': 1,
                        'tax_ids': False,
                        'product_id': product_id.id,
                    })
            lines.append(value)
        invoice_line = {
            'move_type': 'out_invoice',
            'partner_id': supplier.id,
            'invoice_user_id': self.env.user.id,
            'invoice_origin': self.name,
            'invoice_line_ids': lines,
        }
        inv = self.env['account.move'].create(invoice_line)
        action = self.env.ref('account.action_move_out_invoice_type',
                              raise_if_not_found=False)
        result = {
            'name': action.name,
            'type': 'ir.actions.act_window',
            'views': [[False, 'form']],
            'target': 'current',
            'res_id': inv.id,
            'res_model': 'account.move',
        }
        self.inv_stage_identifier = True
        self.stage_id = 3
        invoiced_records = self.env['salon.order'].search(
            [('stage_id', 'in', [3, 4]), ('chair_id', '=', self.chair_id.id)])
        total = 0
        for rows in invoiced_records:
            invoiced_date = str(rows.date)
            invoiced_date = invoiced_date[0:10]
            if invoiced_date == str(date.today()):
                total = total + rows.price_subtotal
        self.chair_id.collection_today = total
        self.update_number_of_orders()
        inv.action_post()

        # Register payments
        payment_vals = {
            'payment_type': 'inbound',  # customer payment
            'partner_id': supplier.id,
            'payment_method_id': self.env.ref('account.account_payment_method_manual_in').id,
            'journal_id': self.env['account.journal'].search([('type', '=', 'bank')], limit=1).id,  # assuming bank journal
            'date': fields.Date.today(),
            'amount': inv.amount_total,
            'ref': self.payment_ref,
            'currency_id': inv.currency_id.id,
            #'invoice_line_ids': inv.invoice_line_ids,
        }
        payment = self.env['account.payment'].create(payment_vals)

        # Post the payment
        payment.action_post()
        return result

    def unlink(self):
        """
        unlink/delete salon order
        """
        for order in self:
            if order.stage_id.id == 3 or order.stage_id.id == 4:
                raise UserError(_("You can't delete an invoiced salon order!"))
        return super(SalonOrder, self).unlink()

    def update_number_of_orders(self):
        """
        function to update the number of active orders for the chair
        """
        self.chair_id.number_of_orders = len(self.env['salon.order'].search(
            [("chair_id", "=", self.chair_id.id), ("stage_id", "in", [2, 3])]))


class SalonOrderLine(models.Model):
    _name = 'salon.order.line'
    _description = 'Salon Order Lines'

    service_id = fields.Many2one('salon.service', string="Service")
    currency_id = fields.Many2one(
        'res.currency', string='Currency', required=True,
        default=lambda self: self.env.user.company_id.currency_id.id)
    price = fields.Monetary(string="Price")
    salon_order_id = fields.Many2one(
        'salon.order', string="Salon Order", required=True, ondelete='cascade',
        index=True, copy=False)
    price_subtotal = fields.Monetary(string='Subtotal',store=True)
    time_taken = fields.Float(string='Time Taken')
    discount = fields.Float('Discount')
    product_used = fields.Many2many('product.product')
    service_attedants = fields.Many2many('hr.employee')
    discount_percentage = fields.Float(string='Discount (%)', digits='Discount',readonly=True)
    discount_amount = fields.Monetary(string='Discount Amount', compute='_compute_discount_amount', readonly=False,store=True)
    product = fields.Many2one("product.product",'Service Product')
    units = fields.Integer("Quantity")

    @api.depends('discount_percentage', 'price')
    def _compute_discount_amount(self):
        for line in self:
            #line.discount_amount = (line.price * line.discount_percentage) / 100
            if not line.product:
               line.price_subtotal = line.price - line.discount_amount
            else:
                 line.price_subtotal = (line.price * line.units) - line.discount_amount

    @api.onchange('discount_amount')
    def _onchange_discount_amount(self):
        for line in self:
            #line.discount_amount = (line.price * line.discount_percentage) / 100
            if not line.product:
               line.price_subtotal = line.price - line.discount_amount
            else:
               line.price_subtotal = (line.price * line.units) - line.discount_amount

    @api.onchange('service_id')
    def _onchange_service_id(self):
        """
        onchange function of service_id field
        """
        self.price = self.service_id.price
        #self.price_subtotal = self.service_id.price - self.discount
        self.time_taken = self.service_id.time_taken
    @api.onchange('product','units')
    def update_price(self):
        for line in self:
            if line.product:
                total = line.units * line.product.list_price
                print(total)
                line.price = line.product.list_price
                line.price_subtotal = total - self.discount_amount



class SalonPaymentMethod(models.Model):
    _name = 'salon.payment.method'
    _description = " A list of all available payments methods"
    name = fields.Char("Payment Method")
    code = fields.Char("Payment Code")

class SalonPaymentMethod(models.Model):
    _name = 'salon.service.categories'
    _description = " Salon Service Categories "
    name = fields.Char("Category Name")
    description = fields.Char("Description")
class ProductsUsed(models.Model):
    _name = 'product.used'
    _description = " A list of products used per service"
    _rec_name = "product"
    product = fields.Many2one('product.template')
    quantity = fields.Float("Quantity Used")
    salon_order_id = fields.Many2one(
        'salon.order.line', string="Salon Order", required=True, ondelete='cascade',
        index=True, copy=False)
    service_id = fields.Many2one('salon.service', string="Service")
    product_serial = fields.Char("Product Serial")
    active = fields.Boolean("On Store")
class ServiceAttedants(models.Model):
    _name = 'service.attedants'
    _description = " A list of attedants in a service"
    name = fields.Many2one('hr.employee')
    salon_order_id = fields.Many2one(
        'salon.order.line', string="Salon Order", required=True, ondelete='cascade',
        index=True, copy=False)
    service_id = fields.Many2one('salon.service', string="Service")
class ServiceCommission(models.Model):
    _name = 'service.commission'
    _description = "Cmmisson to attedants on service delivered"
    attedants = fields.Many2one('hr.employee', "Attendants")
    salon_order_id = fields.Many2one(
        'salon.order', string="Salon Order", required=True, ondelete='cascade',
        index=True, copy=False)
    currency_id = fields.Many2one(
        'res.currency', string='Currency', required=True,
        default=lambda self: self.env.user.company_id.currency_id.id)
    commission_amount = fields.Monetary(string='Commission Amount')
    discount = fields.Monetary(string='Discount Amount')
    attedant_sale = fields.Monetary("Sale Amount")
    date = fields.Date("Service Date")
    status = fields.Boolean("Is Paid")
    service_id = fields.Many2one('salon.service', string="Service")
    attedants_tips = fields.Monetary("Tip")
    service_card_no = fields.Char("Service Card number", related='salon_order_id.service_card_no',store=True)

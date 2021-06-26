# -*- coding: utf-8 -*-
# Copyright (c) 2021, Innomat, Asprotec and libracore and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
import erpnext
from frappe.utils import cint, cstr, flt
from frappe import _
from frappe.website.website_generator import WebsiteGenerator


from six import string_types


class BOMTemplate(WebsiteGenerator):

    def get_bom_material_detail(self, args=None):
        """ Get raw material details like uom, desc and rate"""
        if not args:
            args = frappe.form_dict.get('args')

        if isinstance(args, string_types):
            import json
            args = json.loads(args)

        item = self.get_item_det(args['item_code'])

        args['bom_no'] = args['bom_no'] or item and cstr(
            item[0]['default_bom']) or ''
        args['transfer_for_manufacture'] = (cstr(args.get('include_item_in_manufacturing', '')) or
                                            item and item[0].include_item_in_manufacturing or 0)
        args.update(item[0])

        rate = self.get_rm_rate(args)
        ret_item = {
            'item_name'	: item and args['item_name'] or '',
            'description': item and args['description'] or '',
            'image'		: item and args['image'] or '',
            'stock_uom'	: item and args['stock_uom'] or '',
            'uom'			: item and args['stock_uom'] or '',
            'conversion_factor': 1,
            'bom_no'		: args['bom_no'],
            'rate'			: rate,
            'qty'			: args.get("qty") or args.get("stock_qty") or 1,
            'stock_qty'	: args.get("qty") or args.get("stock_qty") or 1,
            'base_rate'	: rate,
            'include_item_in_manufacturing': cint(args['transfer_for_manufacture']) or 0
        }

        return ret_item

    def get_item_det(self, item_code):
        item = frappe.db.sql("""select name, item_name, docstatus, description, image,
            is_sub_contracted_item, stock_uom, default_bom, last_purchase_rate, include_item_in_manufacturing
            from `tabItem` where name=%s""", item_code, as_dict=1)

        if not item:
            frappe.throw(
                _("Item: {0} does not exist in the system").format(item_code))

        return item

    def get_rm_rate(self, arg):
        return 1.0 #flt(self.get_valuation_rate(arg) / 1)

    def get_valuation_rate(self, args):
        """ Get weighted average of valuation rate from all warehouses """

        total_qty, total_value, valuation_rate = 0.0, 0.0, 0.0
        for d in frappe.db.sql("""select actual_qty, stock_value from `tabBin`
            where item_code=%s""", args['item_code'], as_dict=1):
                total_qty += flt(d.actual_qty)
                total_value += flt(d.stock_value)

        if total_qty:
            valuation_rate =  total_value / total_qty

        if valuation_rate <= 0:
            last_valuation_rate = frappe.db.sql("""select valuation_rate
                from `tabStock Ledger Entry`
                where item_code = %s and valuation_rate > 0
                order by posting_date desc, posting_time desc, creation desc limit 1""", args['item_code'])

            valuation_rate = flt(last_valuation_rate[0][0]) if last_valuation_rate else 0

        if not valuation_rate:
            valuation_rate = frappe.db.get_value("Item", args['item_code'], "valuation_rate")

        return valuation_rate
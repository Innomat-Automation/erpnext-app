# Copyright (c) 2021, Innomat, Asprotec and libracore and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
import ast          # to parse str to dict (from JS calls)

def execute(filters=None):
    columns = get_columns()
    data = get_data(filters)
    return columns, data

def get_columns():
    return [
        {"label": _("Item Code"), "fieldname": "item_code", "fieldtype": "Link", "options": "Item", "width": 140},
        {"label": _("Item Name"), "fieldname": "item_name", "width": 100},
        {"label": _("Item Group"), "fieldname": "item_group", "fieldtype": "Link", "options": "Item Group", "width": 100},
        {"label": _("Supplier"), "fieldname": "supplier", "fieldtype": "Link", "options": "Supplier", "width": 100},
        {"label": _("UOM"), "fieldname": "stock_uom", "fieldtype": "Link", "options": "UOM", "width": 50},
        {"label": _("Actual Qty"), "fieldname": "actual_qty", "fieldtype": "Float", "width": 100, "convertible": "qty"},
        #{"label": _("Planned Qty"), "fieldname": "planned_qty", "fieldtype": "Float", "width": 100, "convertible": "qty"},
        {"label": _("Ordered Qty"), "fieldname": "ordered_qty", "fieldtype": "Float", "width": 100, "convertible": "qty"},
        {"label": _("Reserved Qty"), "fieldname": "reserved_qty", "fieldtype": "Float", "width": 100, "convertible": "qty"},
        {"label": _("Safety Stock"), "fieldname": "safety_stock", "fieldtype": "Float", "width": 100, "convertible": "qty"},
        {"label": _("Projected Qty"), "fieldname": "projected_qty", "fieldtype": "Float", "width": 100, "convertible": "qty"},
        {"label": _("To order"), "fieldname": "to_order", "fieldtype": "Float", "width": 100}
    ]

@frappe.whitelist()
def get_data(filters):
    item_code_filter = ""
    if type(filters) is str:
        filters = ast.literal_eval(filters)
    else:
        filters = dict(filters)
    if 'item_code' in filters:
        item_code_filter += """ AND `raw`.`item_code` = '{item_code}'""".format(item_code=filters['item_code'])
    if 'item_name' in filters:
        item_code_filter += """ AND `raw`.`item_name` LIKE '%{item_name}%'""".format(item_name=filters['item_name'])
    if 'item_group' in filters:
        item_code_filter = """ AND `raw`.`item_group` = '{item_group}'""".format(item_group=filters['item_group'])
    if 'supplier' in filters:
        item_code_filter = """ AND `raw`.`supplier` = '{supplier}'""".format(supplier=filters['supplier'])
    
    sql_query = """SELECT 
                `raw`.`item_code` AS `item_code`,
                `raw`.`item_name` AS `item_name`,
                `raw`.`item_group` AS `item_group`,
                `raw`.`stock_uom` AS `stock_uom`,
                `raw`.`safety_stock` AS `safety_stock`,
                SUM(`raw`.`actual_qty`) AS `actual_qty`,
                SUM(`raw`.`planned_qty`) AS `planned_qty`,
                SUM(`raw`.`ordered_qty`) AS `ordered_qty`,
                (SUM(`raw`.`reserved_qty`) + SUM(`raw`.`reserved_qty_for_production`) + SUM(`raw`.`reserved_qty_for_sub_contract`)) AS `reserved_qty`,
                SUM(`raw`.`projected_qty`) AS `projected_qty`,
                `raw`.`supplier` AS `supplier`,
                (`raw`.`safety_stock` - SUM(`raw`.`projected_qty`)) AS `to_order`
            FROM
                (SELECT 
                    `tabBin`.`item_code` AS `item_code`,
                    `tabItem`.`item_name` AS `item_name`,
                    `tabItem`.`item_group` AS `item_group`,
                    `tabItem`.`stock_uom` AS `stock_uom`,
                    `tabItem`.`safety_stock` AS `safety_stock`,
                    `tabBin`.`actual_qty` AS `actual_qty`,
                    `tabBin`.`planned_qty` AS `planned_qty`,
                    `tabBin`.`ordered_qty` AS `ordered_qty`,
                    `tabBin`.`reserved_qty` AS `reserved_qty`,
                    `tabBin`.`reserved_qty_for_production` AS `reserved_qty_for_production`, 
                    `tabBin`.`reserved_qty_for_sub_contract` AS `reserved_qty_for_sub_contract`,
                    `tabBin`.`projected_qty` AS `projected_qty`,
                    (SELECT `tabItem Default`.`default_supplier`
                     FROM `tabItem Default`
                     WHERE `tabItem Default`.`parent` = `tabItem`.`item_code`
                     ORDER BY `default_supplier` DESC
                     LIMIT 1) AS `supplier`
                FROM `tabBin`
                LEFT JOIN `tabItem` ON `tabBin`.`item_code` = `tabItem`.`name`) AS `raw`
            WHERE 
              `raw`.`projected_qty` < `raw`.`safety_stock` 
              {item_code_filter}
            GROUP BY `raw`.`item_code`;""".format(
              item_code_filter=item_code_filter)
    
    data = frappe.db.sql(sql_query, as_dict=True)
    
    return data

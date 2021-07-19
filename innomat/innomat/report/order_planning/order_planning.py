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
        item_code_filter += """ AND `tabItem`.`item_code` = '{item_code}'""".format(item_code=filters['item_code'])
    if 'item_name' in filters:
        item_code_filter += """ AND `tabItem`.`item_name` LIKE '%{item_name}%'""".format(item_name=filters['item_name'])
    if 'item_group' in filters:
        item_code_filter = """ AND `tabItem`.`item_group` = '{item_group}'""".format(item_group=filters['item_group'])
    if 'supplier' in filters:
        item_code_filter = """ AND `tabItem Default`.`default_supplier` = '{supplier}'""".format(supplier=filters['supplier'])
    
    sql_query = """SELECT 
                    `tabBin`.`item_code` AS `item_code`,
                    `tabItem`.`item_name` AS `item_name`,
                    `tabItem`.`item_group` AS `item_group`,
                    `tabItem`.`stock_uom` AS `stock_uom`,
                    `tabItem`.`safety_stock` AS `safety_stock`,
                    SUM(`tabBin`.`actual_qty`) AS `actual_qty`,
                    SUM(`tabBin`.`planned_qty`) AS `planned_qty`,
                    SUM(`tabBin`.`ordered_qty`) AS `ordered_qty`,
                    (SUM(`tabBin`.`reserved_qty`) + SUM(`tabBin`.`reserved_qty_for_production`) + SUM(`tabBin`.`reserved_qty_for_sub_contract`)) AS `reserved_qty`,
                    SUM(`tabBin`.`projected_qty`) AS `projected_qty`,
                    (SELECT `tabItem Default`.`default_supplier`
                     FROM `tabItem Default`
                     WHERE `tabItem Default`.`parent` = `tabItem`.`item_code`
                     LIMIT 1) AS `supplier`,
                    (`tabItem`.`safety_stock` - SUM(`tabBin`.`projected_qty`)) AS `to_order`
                FROM `tabBin`
                LEFT JOIN `tabItem` ON `tabBin`.`item_code` = `tabItem`.`name`
            WHERE 
              `tabBin`.`projected_qty` < `tabItem`.`safety_stock` {item_code_filter}
            GROUP BY `tabBin`.`item_code`;""".format(
              item_code_filter=item_code_filter)
    
    data = frappe.db.sql(sql_query, as_dict=True)
    
    return data

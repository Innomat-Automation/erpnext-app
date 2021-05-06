# Copyright (c) 2021, Innomat, Asprotec and libracore and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
import ast
from datetime import datetime, timedelta
from frappe.utils import cint

def execute(filters=None):
    columns = get_columns()
    data = get_data(filters)
    return columns, data

def get_columns():
    return [
        {"label": _("Item"), "fieldname": "item_code", "fieldtype": "Link", "options": "Item", "width": 120},
        {"label": _("Item Name"), "fieldname": "item_name", "fieldtype": "Data", "width": 140},
        {"label": _("Item Group"), "fieldname": "item_group", "fieldtype": "Link", "options": "Item Group", "width": 120},        
        {"label": _("Buying Rate"), "fieldname": "buying_rate", "fieldtype": "Currency", "width": 100},
        {"label": _("Valuation Rate"), "fieldname": "valuation_rate", "fieldtype": "Currency", "width": 100},
        {"label": _("Last Purchase Rate"), "fieldname": "last_purchase_rate", "fieldtype": "Currency", "width": 100},
        {"label": _("Selling Rate"), "fieldname": "selling_rate", "fieldtype": "Currency", "width": 100},
        {"label": _("Margin"), "fieldname": "margin", "fieldtype": "Percent", "width": 80},
        {"label": _(""), "fieldname": "blank", "fieldtype": "Data", "width": 20}
    ]

def get_data(filters):
    if type(filters) is str:
        filters = ast.literal_eval(filters)
    else:
        filters = dict(filters)
    # get additional conditions
    conditions = ""
    if 'item_code' in filters and filters['item_code']:
        conditions += """ AND `tabItem`.`item_code` = "{0}" """.format(filters['item_code'])
    if 'item_name' in filters and filters['item_name']:
        conditions += """ AND `tabItem`.`item_code` LIKE "%{0}%" """.format(filters['item_name'])
    if 'item_group' in filters and filters['item_group']:
        conditions += """ AND `tabItem`.`item_group` = "{0}" """.format(filters['item_group'])
    
    # prepare query
    sql_query = """SELECT *, 
           (100 * (`selling_rate` - `buying_rate`) / `selling_rate`) AS `margin`
           FROM ( 
            SELECT
            `tabItem`.`item_code`AS `item_code`,
            `tabItem`.`item_name`AS `item_name`,
            `tabItem`.`item_group`AS `item_group`,
            IFNULL((SELECT `price_list_rate`
             FROM `tabItem Price` AS `tabBuying Rates`
             WHERE `tabBuying Rates`.`item_code` = `tabItem`.`item_code`
               AND `tabBuying Rates`.`buying` = 1
               AND `tabBuying Rates`.`valid_from` <= DATE(NOW())
             ORDER BY `tabBuying Rates`.`modified` DESC
             LIMIT 1), 0) AS `buying_rate`,
            IFNULL((SELECT `price_list_rate`
             FROM `tabItem Price` AS `tabSelling Rates`
             WHERE `tabSelling Rates`.`item_code` = `tabItem`.`item_code`
               AND `tabSelling Rates`.`selling` = 1
               AND `tabSelling Rates`.`valid_from` <= DATE(NOW())
             ORDER BY `tabSelling Rates`.`modified` DESC
             LIMIT 1), 0) AS `selling_rate`, 
            `tabItem`.`valuation_rate`AS `valuation_rate`, 
            `tabItem`.`last_purchase_rate`AS `last_purchase_rate`
          FROM `tabItem`
          WHERE `tabItem`.`is_sales_item` = 1
          {conditions}
        ORDER BY `tabItem`.`item_code` ASC) AS `raw`;
      """.format(conditions=conditions)
    
    data = frappe.db.sql(sql_query, as_dict=True)

    return data

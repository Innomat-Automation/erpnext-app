# Copyright (c) 2021, Innomat, Asprotec and libracore and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _

def execute(filters=None):
    columns = get_columns()
    data = get_data(filters)
    return columns, data

def get_columns():
    return [
        {"label": _("Date"), "fieldname": "date", "fieldtype": "Date", "width": 100},
        {"label": _("Due Date"), "fieldname": "due_date", "fieldtype": "Date", "width": 100},
        {"label": _("Sales Order"), "fieldname": "sales_order", "fieldtype": "Link", "options": "Sales Order", "width": 110},
        {"label": _("Customer"), "fieldname": "customer", "fieldtype": "Link", "options": "Customer", "width": 110},
        {"label": _("Customer Name"), "fieldname": "customer_name", "fieldtype": "Data", "width": 200},
        {"label": _("Amount"), "fieldname": "amount", "fieldtype": "Currency", "width": 120},
        {"label": _(""), "fieldname": "blank", "fieldtype": "Data", "width": 20}
    ]

def get_data(filters):   
    # prepare query
    sql_query = """SELECT
        `tabSales Order`.`name` AS `sales_order`,
        `tabSales Order`.`customer` AS `customer`,
        `tabSales Order`.`customer_name` AS `customer_name`,
        `tabSales Order Akonto`.`date` AS `due_date`,
        `tabSales Order Akonto`.`creation_date` AS `date`,
        `tabSales Order Akonto`.`amount` AS `amount`
      FROM `tabSales Order Akonto` 
      LEFT JOIN `tabSales Order` ON `tabSales Order`.`name` = `tabSales Order Akonto`.`parent`
      WHERE
        `tabSales Order`.`docstatus` = 1
        AND (`tabSales Order Akonto`.`payment` IS NULL OR `tabSales Order Akonto`.`payment` = "")
        AND (`tabSales Order Akonto`.`amount` > 0)
        AND (`tabSales Order Akonto`.`sales_invoice` IS NULL OR `tabSales Order Akonto`.`sales_invoice` = "")
      ORDER BY -`tabSales Order Akonto`.`creation_date` DESC, `tabSales Order Akonto`.`date` ASC;
      """
    
    data = frappe.db.sql(sql_query, as_dict=True)

    return data

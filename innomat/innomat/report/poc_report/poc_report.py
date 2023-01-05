# Copyright (c) 2013, Innomat, Asprotec and libracore and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
import ast


def execute(filters=None):
    columns = get_columns()
    data = get_data(filters)
    return columns, data

def get_columns():
    return [
        {"label": _("Project"), "fieldname": "project", "fieldtype": "Link", "options": "Project", "width": 120},
        {"label": _("Sales Order"), "fieldname": "sales_order", "fieldtype": "Link", "options" :"Sales Order", "width": 140},
		{"label": _("Verkaufspreis"), "fieldname": "sales_price", "fieldtype": "Currency", "width": 120},
        {"label": _("Akonto gezahlt"), "fieldname": "akonto_paid", "fieldtype": "Currency", "width": 120},        
        {"label": _("Akonto offen"), "fieldname": "akonto_open", "fieldtype": "Currency", "width": 120},
        {"label": _("Paid Sales Invoice"), "fieldname": "invoice", "fieldtype": "Currency", "width": 120},
        {"label": _("Hours"), "fieldname": "hours", "fieldtype": "Float", "width": 120},
        {"label": _("Stunden berechnet"), "fieldname": "hours_calc", "fieldtype": "Currency", "width": 120},
        {"label": _("Purchase Invoice"), "fieldname": "purchase_invoice", "fieldtype": "Currency", "width": 120},
        {"label": _("Eingangsrechnungen bewertet"), "fieldname": "purchase_invoice_calc", "fieldtype": "Currency", "width": 120},
        {"label": _("Geleistet"), "fieldname": "geleistet", "fieldtype": "Currency", "width": 120},
		{"label": _("Differez"), "fieldname": "diff", "fieldtype": "Currency", "width": 120}
    ]

def get_data(filters):
    if type(filters) is str:
        filters = ast.literal_eval(filters)
    else:
        filters = dict(filters)
	
    sql_query = """SELECT `project`,sales_order,sales_price,akonto_paid,akonto_open,invoice,hours,hours_calc,purchase_invoice,purchase_invoice_calc,geleistet,diff FROM
					(SELECT
					`tabProject`.`sales_order` As sa,
					`tabProject`.`name` as project, 
					`tabProject`.`sales_order` as sales_order,
					`tabSales Order`.`base_rounded_total` as sales_price,
					@akonto1 := (SELECT IFNULL(SUM(`tabSales Order Akonto`.`amount`), 0)
					FROM `tabSales Order Akonto`
					LEFT JOIN `tabSales Order` ON `tabSales Order`.`name` = `tabSales Order Akonto`.`parent`
					LEFT JOIN `tabSales Invoice` ON `tabSales Invoice`.`name` = `tabSales Order Akonto`.`sales_invoice`
					WHERE `tabSales Order`.`docstatus` = 1
					AND `tabSales Order`.`name` = `tabProject`.`sales_order`
        			AND (`tabSales Order Akonto`.`amount` > 0)
					AND `tabSales Invoice`.`status` = "Paid"
					AND `tabSales Invoice`.`posting_date` <= "{to_date}"
					AND `tabSales Invoice`.`is_akonto` = 1) as akonto_paid,
					@akonto2 := (SELECT IFNULL(SUM(`tabSales Invoice`.`base_rounded_total`), 0)
					FROM `tabSales Order Akonto`
					LEFT JOIN `tabSales Order` ON `tabSales Order`.`name` = `tabSales Order Akonto`.`parent`
					LEFT JOIN `tabSales Invoice` ON `tabSales Invoice`.`name` = `tabSales Order Akonto`.`sales_invoice`
					WHERE `tabSales Order`.`docstatus` = 1
					AND `tabSales Order`.`name` = `tabProject`.`sales_order`
        			AND (`tabSales Order Akonto`.`amount` > 0)
					AND (`tabSales Invoice`.`status` = "Unpaid" OR `tabSales Invoice`.`status` = "Overdue")
					AND `tabSales Invoice`.`posting_date` <= "{to_date}"
					AND `tabSales Invoice`.`is_akonto` = 1) as akonto_open,
					@salinvoces1 := (SELECT IFNULL(SUM(`tabSales Invoice`.`base_rounded_total`), 0)
                     FROM `tabSales Invoice`
                     WHERE `tabSales Invoice`.`docstatus` = 1
                       AND `tabSales Invoice`.`project` = `tabProject`.`name`
					   AND `tabSales Invoice`.`is_akonto` = 0
					   AND `tabSales Invoice`.`posting_date` <= "{to_date}") AS `invoice`,
					@hours1 := (SELECT IFNULL(SUM(`tabTimesheet Detail`.`hours`), 0)
                     FROM `tabTimesheet Detail`
                     WHERE `tabTimesheet Detail`.`docstatus` = 1
                       AND `tabTimesheet Detail`.`project` = `tabProject`.`name`
					   AND `tabTimesheet Detail`.`to_time` <= "{to_date}") AS `hours`,
					@hours2 := @hours1 * 105.0 As `hours_calc`,
					@purinvoces1 := (SELECT IFNULL(SUM(`tabPurchase Invoice Item`.`rate`), 0)
                     FROM `tabPurchase Invoice Item`
					 LEFT JOIN `tabPurchase Invoice` ON `tabPurchase Invoice Item`.parent = `tabPurchase Invoice`.`name`
                     WHERE `tabPurchase Invoice Item`.`docstatus` = 1
                       AND `tabPurchase Invoice Item`.`project` = `tabProject`.`name`
					   AND `tabPurchase Invoice`.`posting_date` <= "{to_date}") AS `purchase_invoice`,
					@purinvoces2 := @purinvoces1 * 1.15 AS `purchase_invoice_calc`,
					@result := @hours2 + @purinvoces2 AS `geleistet`,
					@difference := @result - (@akonto1 + @akonto2 + @salinvoces1) AS `diff`
		   	FROM `tabProject`
			LEFT JOIN `tabSales Order` ON `tabSales Order`.`name` = `tabProject`.`sales_order`
		   	WHERE `tabProject`.`status` = 'Open' 
		   	AND `tabProject`.`company` = "{company}") As complete
		   	WHERE diff != 0.0;""".format(to_date=filters['to_date'], company=filters['company'])

    # sql_query = """SELECT
	# 				`tabProject`.`name` as project, 
	# 				`tabProject`.`sales_order`,
	# 				@akonto1 := (SELECT IFNULL(SUM(`tabSales Order Akonto`.`amount`), 0)
	# 				FROM `tabSales Order Akonto`
	# 				LEFT JOIN `tabSales Order` ON `tabSales Order`.`name` = `tabSales Order Akonto`.`parent`
	# 				LEFT JOIN `tabPayment Entry` ON `tabPayment Entry`.`name` = `tabSales Order Akonto`.`payment`
	# 				WHERE `tabSales Order`.`docstatus` = 1
	# 				AND `tabSales Order`.`name` = `tabProject`.`sales_order`
	# 				AND (`tabPayment Entry`.`posting_date` < "{to_date}")
	# 				AND (`tabSales Order Akonto`.`file` IS NOT NULL AND `tabSales Order Akonto`.`file` <> "")
    #     			AND (`tabSales Order Akonto`.`amount` > 0)
	# 				AND (`tabSales Order Akonto`.`date` < "{to_date}")) AS akonto_paid,
	# 				@akonto2 := (SELECT IFNULL(SUM(`tabSales Order Akonto`.`amount`), 0)
	# 				FROM `tabSales Order Akonto`
	# 				LEFT JOIN `tabSales Order` ON `tabSales Order`.`name` = `tabSales Order Akonto`.`parent`
	# 				LEFT JOIN `tabPayment Entry` ON `tabPayment Entry`.`name` = `tabSales Order Akonto`.`payment`
	# 				WHERE `tabSales Order`.`docstatus` = 1
	# 				AND `tabSales Order`.`name` = `tabProject`.`sales_order`
	# 				AND (`tabPayment Entry`.`posting_date` > "{to_date}" OR `tabSales Order Akonto`.`payment` IS NULL OR `tabSales Order Akonto`.`payment` = "")
	# 				AND (`tabSales Order Akonto`.`file` IS NOT NULL AND `tabSales Order Akonto`.`file` <> "")
    #     			AND (`tabSales Order Akonto`.`amount` > 0)
	# 				AND (`tabSales Order Akonto`.`date` < "{to_date}")) AS akonto_open,
	# 				@salinvoces1 := (SELECT IFNULL(SUM(`tabSales Invoice Item`.`rate`), 0)
    #                  FROM `tabSales Invoice Item`
	# 				 LEFT JOIN `tabSales Invoice` ON `tabSales Invoice Item`.parent = `tabSales Invoice`.`name`
    #                  WHERE `tabSales Invoice Item`.`docstatus` = 1
    #                    AND `tabSales Invoice`.`project` = `tabProject`.`name`
	# 				   AND `tabSales Invoice`.`posting_date` <= "{to_date}") AS `invoice`,
	# 				@hours1 := (SELECT IFNULL(SUM(`tabTimesheet Detail`.`hours`), 0)
    #                  FROM `tabTimesheet Detail`
    #                  WHERE `tabTimesheet Detail`.`docstatus` = 1
    #                    AND `tabTimesheet Detail`.`project` = `tabProject`.`name`
	# 				   AND `tabTimesheet Detail`.`to_time` <= "{to_date}") AS `hours`,
	# 				@hours2 := @hours1 * 125.0 As `hours_calc`,
	# 				@purinvoces1 := (SELECT IFNULL(SUM(`tabPurchase Invoice Item`.`rate`), 0)
    #                  FROM `tabPurchase Invoice Item`
	# 				 LEFT JOIN `tabPurchase Invoice` ON `tabPurchase Invoice Item`.parent = `tabPurchase Invoice`.`name`
    #                  WHERE `tabPurchase Invoice Item`.`docstatus` = 1
    #                    AND `tabPurchase Invoice Item`.`project` = `tabProject`.`name`
	# 				   AND `tabPurchase Invoice`.`posting_date` <= "{to_date}") AS `purchase_invoice`,
	# 				@purinvoces2 := @purinvoces1 * 1.15 AS `purchase_invoice_calc`,
	# 				@result := @hours2 + @purinvoces2 AS `geleistet`,
	# 				@difference := @akonto1 + @akonto2 + @salinvoces1 - @result AS `diff`
	# 	   FROM `tabProject`
	# 	   WHERE `tabProject`.`status` = 'Open' 
	# 	   AND `tabProject`.`company` = "{company}"
    #   ;""".format(to_date=filters['to_date'], company=filters['company'])
    

    data = frappe.db.sql(sql_query, as_dict=True)
	
    return data
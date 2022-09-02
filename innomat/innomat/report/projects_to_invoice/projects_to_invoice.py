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
        {"label": _("Project"), "fieldname": "project", "fieldtype": "Link", "options": "Project", "width": 120},
        {"label": _("Finished"), "fieldname": "finished", "fieldtype": "Check", "width": 10},
        {"label": _("Status Light"), "fieldname": "status_light", "fieldtype": "Data", "width": 100},
        {"label": _("Task"), "fieldname": "tasks", "fieldtype": "Integer", "width": 20},
        {"label": _("Sales Order"), "fieldname": "sales_order", "fieldtype": "Link", "options": "Sales Order", "width": 80},
        {"label": _("Customer"), "fieldname": "customer", "fieldtype": "Link", "options": "Customer", "width": 80},
        {"label": _("Customer name"), "fieldname": "customer_name", "fieldtype": "Data", "width": 120},
        {"label": _("Volume"), "fieldname": "volume", "fieldtype": "Currency", "width": 100},
        {"label": _("Akonto open"), "fieldname": "akonto_amount", "fieldtype": "Currency", "width": 100},
        {"label": _("Akonto unpaid"), "fieldname": "unpaid_akonto_amount", "fieldtype": "Currency", "width": 100},
        {"label": _("DN open"), "fieldname": "dn_amount", "fieldtype": "Currency", "width": 100},
        {"label": _("DN draft"), "fieldname": "draft_dn_amount", "fieldtype": "Currency", "width": 100},
        {"label": _("TS open"), "fieldname": "ts_amount", "fieldtype": "Currency", "width": 100},
        {"label": _(""), "fieldname": "blank", "fieldtype": "Data", "width": 20}
    ]

def get_data(filters):
    if type(filters) is str:
        filters = ast.literal_eval(filters)
    else:
        filters = dict(filters)
    # get additional conditions
    if 'company' in filters and filters['company']:
        company = filters['company']
    if 'date' in filters and filters['date']:
        date = filters['date']
    
    # projects that have open akonto / uninvoice delivery notes / uninvoice hours
    projects = frappe.db.sql(
        """SELECT 
                `projects`.`project`,
                `tabProject`.`sales_order`,
                `tabProject`.`finished`,
                `tabProject`.`status_light` AS `status_light`,
                `tabProject`.`customer`,
                `tabProject`.`customer_name`,
                (SELECT SUM(`tabSales Order Item`.`base_amount`) 
                 FROM `tabSales Order Item` 
                 WHERE `tabSales Order Item`.`parent` = `tabProject`.`sales_order`
                   AND `tabSales Order Item`.`by_effort` = 0) AS `volume`, 
                (SELECT COUNT(`tabTask`.`subject`) 
                 FROM `tabTask` 
                 WHERE `tabTask`.`project` = `projects`.`project`
                   AND `tabTask`.`status` != "Cancelled"
                   AND `tabTask`.`status` != "Completed") AS `tasks`, 
                SUM(`projects`.`akonto_amount`) AS `akonto_amount`,
                SUM(`projects`.`unpaid_akonto_amount`) AS `unpaid_akonto_amount`,
                SUM(`projects`.`dn_amount`) AS `dn_amount`,
                SUM(`projects`.`draft_dn_amount`) AS `draft_dn_amount`,
                SUM(`projects`.`ts_amount`) AS `ts_amount`,
                (SELECT SUM(`tabSales Invoice`.`outstanding_amount`)
                 FROM `tabSales Invoice`
                 WHERE `tabSales Invoice`.`project` = `projects`.`project`
                   AND `tabSales Invoice`.`docstatus` = 1
                   AND `tabSales Invoice`.`outstanding_amount` <> 0) AS `unpaid_invoice`,
                `projects`.`date`
           FROM 
           (
            /* open akonto */
            SELECT 
                (SELECT `tabProject`.`name`
                 FROM `tabProject` 
                 WHERE `tabProject`.`sales_order` = `tabSales Order Akonto`.`parent`) AS `project`,
                `tabSales Order Akonto`.`amount` AS `akonto_amount`,
                0 AS `unpaid_akonto_amount`,
                0 AS `dn_amount`,
                0 AS `draft_dn_amount`,
                0 AS `ts_amount`,
                `tabSales Order Akonto`.`date` AS `date`
            FROM `tabSales Order Akonto`
            LEFT JOIN `tabSales Order` ON `tabSales Order`.`name` = `tabSales Order Akonto`.`parent`
            WHERE `tabSales Order Akonto`.`file` IS NULL
              AND `tabSales Order`.`company` = "{company}"
            
            /* unpaid akonto */
            UNION SELECT 
                (SELECT `tabProject`.`name`
                 FROM `tabProject` 
                 WHERE `tabProject`.`sales_order` = `tabSales Order Akonto`.`parent`) AS `project`,
                 0 AS `akonto_amount`,
                `tabSales Order Akonto`.`amount` AS `unpaid_akonto_amount`,
                0 AS `dn_amount`,
                0 AS `draft_dn_amount`,
                0 AS `ts_amount`,
                `tabSales Order Akonto`.`creation_date` AS `date`
            FROM `tabSales Order Akonto`
            LEFT JOIN `tabSales Order` ON `tabSales Order`.`name` = `tabSales Order Akonto`.`parent`
            WHERE `tabSales Order Akonto`.`file` IS NOT NULL
              AND `tabSales Order Akonto`.`payment` IS NULL
              AND `tabSales Order`.`company` = "{company}"
                      
            /* uninvoice delivery notes */
            UNION SELECT 
                    `tabDelivery Note`.`project` AS `project`,
                    0 AS `akonto_amount`,
                    0 AS `unpaid_akonto_amount`,
                    `tabDelivery Note`.`base_net_total` AS `dn_amount`,
                    0 AS `draft_dn_amount`,
                    0 AS `ts_amount`,
                    `tabDelivery Note`.`posting_date` AS `date`
                FROM `tabDelivery Note`
                WHERE `tabDelivery Note`.`status` = "To Bill"
                  AND `tabDelivery Note`.`docstatus` = 1
                  AND `tabDelivery Note`.`project` IS NOT NULL
                  AND `tabDelivery Note`.`company` = "{company}"
            
            /* draft delivery notes */
            UNION SELECT 
                    `tabDelivery Note`.`project` AS `project`,
                    0 AS `akonto_amount`,
                    0 AS `unpaid_akonto_amount`,
                    0 AS `dn_amount`,
                    `tabDelivery Note`.`base_net_total` AS `draft_dn_amount`,
                    0 AS `ts_amount`,
                    `tabDelivery Note`.`posting_date` AS `date`
                FROM `tabDelivery Note`
                WHERE `tabDelivery Note`.`docstatus` = 0
                  AND `tabDelivery Note`.`project` IS NOT NULL
                  AND `tabDelivery Note`.`company` = "{company}"
                  
            /* uninvoiced timesheet hours */
            UNION SELECT 
                    `tabTimesheet Detail`.`project` AS `project`,
                    0 AS `akonto_amount`,
                    0 AS `unpaid_akonto_amount`,
                    0 AS `dn_amount`,
                    0 AS `draft_dn_amount`,
                    (`tabTimesheet Detail`.`hours` * IFNULL(`tabItem Price`.`price_list_rate`, 120)) AS `ts_amount`,
                    DATE(`tabTimesheet Detail`.`from_time`) AS `date`
                FROM `tabTimesheet Detail`
                LEFT JOIN `tabTimesheet` ON `tabTimesheet Detail`.`parent` = `tabTimesheet`.`name`
                LEFT JOIN `tabTask` ON `tabTimesheet Detail`.`task` = `tabTask`.`name`
                LEFT JOIN `tabProject` ON `tabProject`.`name` = `tabTimesheet Detail`.`project`
                LEFT JOIN `tabSales Invoice Item` ON `tabTimesheet Detail`.`name` = `tabSales Invoice Item`.`ts_detail`
                LEFT JOIN `tabItem Price` ON (`tabItem Price`.`item_code` = `tabTask`.`item_code` AND `tabItem Price`.`selling` = 1)
                WHERE `tabTimesheet`.`docstatus` = 1
                   AND `tabProject`.`company` = "{company}"
                   AND `tabTimesheet Detail`.`by_effort` = 1
                   AND `tabTimesheet Detail`.`do_not_invoice` = 0
                   AND `tabSales Invoice Item`.`ts_detail` IS NULL
           ) AS `projects`
           LEFT JOIN `tabProject` ON `projects`.`project` = `tabProject`.`name`
           WHERE `projects`.`project` IS NOT NULL
             AND `projects`.`project` != ""
             AND `projects`.`date` <= "{date}"
             AND (akonto_amount > 0 OR unpaid_akonto_amount > 0 OR dn_amount > 0 OR draft_dn_amount > 0 OR ts_amount > 0)
           GROUP BY `projects`.`project`
           ORDER BY  `projects`.`project` ASC
            ;""".format(company=company, date=date), as_dict=True)
    
    data = projects

    # processing
    totals = {'volume': 0, 'akonto_amount': 0, 'unpaid_akonto_amount': 0, 'dn_amount': 0, 'draft_dn_amount': 0, 'ts_amount': 0}
    for row in data:
        totals['volume'] += row['volume'] or 0
        totals['akonto_amount'] += row['akonto_amount'] or 0
        totals['unpaid_akonto_amount'] += row['unpaid_akonto_amount'] or 0
        totals['dn_amount'] += row['dn_amount'] or 0
        totals['draft_dn_amount'] += row['draft_dn_amount'] or 0
        totals['ts_amount'] += row['ts_amount'] or 0
    data.append({
        'customer_name': "Total",
        'volume': totals['volume'],
        'unpaid_akonto_amount': totals['unpaid_akonto_amount'],
        'akonto_amount': totals['akonto_amount'] ,
        'dn_amount': totals['dn_amount'],
        'draft_dn_amount': totals['draft_dn_amount'],
        'ts_amount': totals['ts_amount']
    })
    return data

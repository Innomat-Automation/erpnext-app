# Copyright (c) 2019-2021, asprotec ag and contributors
# For license information, please see license.txt

import frappe
from frappe import _

"""
Get all timesheets
"""
@frappe.whitelist()
def get_timesheet_entrys(project,employee):
    sql_query = """SELECT 
           `tabTimesheet Detail`.`activity_type` AS `activity_type`,
           `tabTimesheet Detail`.`from_time` AS `from_time`,
           `tabTimesheet Detail`.`to_time` AS `to_time`,
           `tabTimesheet`.`employee` AS `employee`,
           `tabTimesheet`.`employee_name` AS `employee_name`,
           `tabTimesheet Detail`.`hours` AS `hours`,
           `tabTimesheet`.`name` AS `timesheet`,
           `tabTimesheet Detail`.`name` AS `ts_detail`,
           `tabTimesheet Detail`.`external_remarks` AS `external_remarks`
         FROM `tabTimesheet Detail`
         LEFT JOIN `tabTimesheet` ON `tabTimesheet Detail`.`parent` = `tabTimesheet`.`name`
         LEFT JOIN `tabAcceptance Report Time Entry` ON `tabTimesheet Detail`.`name` = `tabAcceptance Report Time Entry`.`ts_detail`
         WHERE 
               `tabTimesheet Detail`.`project` = "{project}"
           AND `tabTimesheet`.`employee` = "{employee}"
           AND `tabAcceptance Report Time Entry`.`ts_detail` IS NULL;
    """.format(project=project, employee=employee)
    time_logs = frappe.db.sql(sql_query, as_dict=True)
    return time_logs

"""
Get all delivery notes
"""
@frappe.whitelist()
def get_delivery_notes(project):
    sql_query = """SELECT 
           `tabDelivery Note Item`.`item_code` AS `item_code`,
           `tabDelivery Note Item`.`description` AS `description`,
           `tabDelivery Note Item`.`qty` AS `qty`,
           `tabDelivery Note Item`.`name` AS `dn_entry`,
           `tabDelivery Note`.`name` AS `dn`
         FROM `tabDelivery Note Item`
         LEFT JOIN `tabDelivery Note` ON `tabDelivery Note Item`.`parent` = `tabDelivery Note`.`name`
         LEFT JOIN `tabAcceptance Report Delivery` ON `tabDelivery Note Item`.`name` = `tabAcceptance Report Delivery`.`dn_entry`         WHERE 
               `tabDelivery Note`.`project` = "{project}"
           AND `tabAcceptance Report Delivery`.`dn_entry` IS NULL;
    """.format(project=project)
    dn_logs = frappe.db.sql(sql_query, as_dict=True)
    return dn_logs


@frappe.whitelist()
def create_acceptance_report(project,employee):
    ts = get_timesheet_entrys(project,employee)
    dn = get_delivery_notes(project)

    pr = frappe.get_doc("Project",project)
    customer = frappe.get_doc("Customer", pr.customer);

    ar = frappe.get_doc({
        "doctype": "Acceptance Report",
        "title": pr.title,
        "customer": pr.customer,
        "customer_name": pr.customer_name,
        "project" : project,
        "employee" : employee,
        "company" : pr.company,
        "po_no" : pr.po_no,
        "po_date" : pr.po_date
    })

    for t in ts:
        ar.append("timesheets", {
            "activity_type" : t.activity_type,
			"from_time" : t.from_time,
            "to_time" : t.to_time,
            "hours" : t.hours,
            "remarks" : t.external_remarks,
            "ts" : t.ts,
            "ts_detail" : t.ts_detail
            })

    for d in dn:
        ar.append("delivery", {
            "item_code" : d.item_code,
			"description" : d.description,
            "qty" : d.qty,
            "dn" : d.dn,
            "dn_entry" : d.dn_entry
        })
    
    ar.insert()
    frappe.db.commit()
    return ar.name
            

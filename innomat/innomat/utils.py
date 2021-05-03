# Copyright (c) 2019-2021, libracore and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from datetime import datetime

"""
This function will return the BOM cost/rate for calculations (e.g. quotation)
"""
@frappe.whitelist()
def get_bom_rate(item_code):
    boms = frappe.get_all("BOM", 
           filters={'item': item_code, 'is_active': 1, 'is_default': 1}, 
           fields=['name', 'total_cost'])
    if len(boms) > 0:
        return boms[0]['total_cost']
    else:
        return 0
    
"""
This function will udate the item description based on a BOM
"""
@frappe.whitelist()
def update_description_from_bom(bom):
    b = frappe.get_doc("BOM", bom)
    description = ""
    for i in b.items:
        if not "res" in i.uom:
            if i.uom == "Stk":
                description += "{qty} Stk {name}<br>".format(qty=i.qty, name=i.item_name)
            else:
                description += "{name}<br>".format(name=i.item_name)
    item = frappe.get_doc("Item", b.item)
    item.description = description
    item.save()
    return

"""
Return the next available project key
"""
@frappe.whitelist()
def get_project_key():
    data = frappe.db.sql("""SELECT IFNULL(MAX(`project_key`), CONCAT(SUBSTRING(CURDATE(), 3, 2), "0000")) AS `key`
                            FROM `tabProject`
                            WHERE `project_key` LIKE CONCAT(SUBSTRING(CURDATE(), 3, 2), "%");""", as_dict=True)
    last_id = int(data[0]['key'])
    return (last_id + 1)

"""
Create a new project with tasks from a sales order
"""
@frappe.whitelist()
def create_project(sales_order):
    key = get_project_key()
    so = frappe.get_doc("Sales Order", sales_order)
    company_key = "IN"
    if "Asprotec" in so.company:
        company_key = "AS"
    # create project 
    new_project = frappe.get_doc({
        "doctype": "Project",
        "project_key": key,
        "project_name": "{0}P{1}".format(company_key, key),
        "project_type": "Project",
        "is_active": "Yes",
        "status": "Open",
        "expected_start_date": datetime.now(),
        "expected_end_date": so.delivery_date,
        "customer": so.customer,
        "customer_name": so.customer_name,
        "sales_order": sales_order,
        "title": "{0}P{1} {2}".format(company_key, key, so.customer_name)
    })
    new_project.insert()
    
    # create tasks for each item
    for i in so.items:
        expected_time = i.qty;
        boms = frappe.get_all("BOM", 
                filters={'item': i.item_code, 'is_default': 1}, 
                fields=['name', 'total_hours'])
        if boms and len(boms) > 0:
            expected_time = boms[0]['total_hours']
        new_task = frappe.get_doc({
            "doctype": "Task",
            "subject": i.item_name,
            "project": new_project.name,
            "status": "Open",
            "expected_time": expected_time,
            "description": i.description,
            "sales_order": sales_order,
            "sales_order_item": i.name
        })
        new_task.insert()
    frappe.db.commit()
    return new_project.name

"""
Get timehseet lock date
"""
@frappe.whitelist()
def get_timesheet_lock_date():
    return frappe.get_value("Innomat Settings", "Innomat Settings", "lock_timesheets_until") 

""" 
Shortcut to create delivery notes from timesheet
"""
@frappe.whitelist()
def create_dn(project, item, qty, description):
    pj = frappe.get_doc("Project", project)
    new_dn = frappe.get_doc({
        "doctype": "Delivery Note",
        "customer": pj.customer
    })
    item_dict = {
        'item_code': item,
        'qty': qty
    }
    if description and description != "":
        item_dict['description'] = description
    row = new_dn.append('items', item_dict)
    new_dn.insert()
    return new_dn.name

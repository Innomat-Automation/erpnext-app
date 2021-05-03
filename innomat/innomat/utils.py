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
        boms = frappe.get_all("BOM", 
                filters={'item': i.item_code, 'is_default': 1}, 
                fields=['name', 'total_hours'])
        if boms and len(boms) > 0:
            expected_time = boms[0]['total_hours']
            # create one task per BOM position
            bom = frappe.get_doc("BOM", boms[0]['name'])
            for bom_item in bom.items:
                new_task = frappe.get_doc({
                    "doctype": "Task",
                    "subject": bom_item.item_name,
                    "project": new_project.name,
                    "status": "Open",
                    "expected_time": bom_item.qty,
                    "description": bom_item.description,
                    "sales_order": sales_order,
                    "sales_order_item": i.name,
                    "item_code": bom_item.item_code,
                    "by_effort": i.by_effort
                })
                new_task.insert()
        else:
            new_task = frappe.get_doc({
                "doctype": "Task",
                "subject": i.item_name,
                "project": new_project.name,
                "status": "Open",
                "expected_time": i.qty,
                "description": i.description,
                "sales_order": sales_order,
                "sales_order_item": i.name,
                "item_code": i.item_code,
                "by_effort": i.by_effort
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
def create_dn(project, item, qty, description, timesheet):
    pj = frappe.get_doc("Project", project)
    new_dn = frappe.get_doc({
        "doctype": "Delivery Note",
        "customer": pj.customer,
        "project": project,
        "company": pj.company
    })
    item_dict = {
        'item_code': item,
        'qty': qty,
        'against_timesheet': timesheet,
        'sales_item_group': "Service"
    }
    if description and description != "":
        item_dict['description'] = description
    row = new_dn.append('items', item_dict)
    row = new_dn.append('sales_item_groups', {'group': 'Service', 'title': 'Service', 'sum_caption': 'Summe Service'})
    new_dn.insert()
    return new_dn.name

""" 
Shortcut to create on call fees from timesheet
"""
@frappe.whitelist()
def create_on_call_fee(project, date, timesheet):
    pj = frappe.get_doc("Project", project)
    date = datetime.strptime(date, "%Y-%m-%d")
    new_dn = frappe.get_doc({
        "doctype": "Delivery Note",
        "customer": pj.customer,
        "project": project,
        "company": pj.company
    })
    item_dict = {
        'item_code': frappe.get_value("Innomat Settings", "Innomat Settings", "on_call_fee_item"),
        'qty': 1,
        'description': "Pikettpauschale {0}".format(date.strftime("%d.%m.%Y")),
        'against_timesheet': timesheet,
        'sales_item_group': "Service"
    }
    row = new_dn.append('items', item_dict)
    row = new_dn.append('sales_item_groups', {'group': 'Service', 'title': 'Service', 'sum_caption': 'Summe Service'})
    new_dn.insert()
    return new_dn.name

"""
On submit of timesheet, create delivery notes from travel entries
"""
@frappe.whitelist()
def create_travel_notes(timesheet, travel_key):
    ts = frappe.get_doc("Timesheet", timesheet)
    travel = {}
    for d in ts.time_logs:
        if d.activity_type == travel_key and d.project:
            # if project key does not yet exist, create it
            if d.project not in travel:
                travel[d.project] = []
            # insert billing item
            travel[d.project].append({
                'date': d.from_time,
                'travel_type': d.travel_type,
                'kilometers': d.kilometers,
                'travel_fee': d.travel_fee,
                'ts_detail': d.name
            })
         
    # grouped by project, create delivery notes
    dns = []
    for k, v in travel.items():
        pj = frappe.get_doc("Project", k)
        new_dn = frappe.get_doc({
            "doctype": "Delivery Note",
            "customer": pj.customer,
            "project": k,
            "company": pj.company
        })
        for value in v:
            if "wagen" in value['travel_type']:
                item_dict = {
                    'item_code': frappe.get_value("Innomat Settings", "Innomat Settings", "mileage_item"),
                    'qty': value['kilometers'],
                    'description': "Anfahrt {0}".format(value['date'].strftime("%d.%m.%Y")),
                    'against_timesheet': timesheet,
                    'ts_detail': value['ts_detail'],
                    'sales_item_group': "Service"
                }
            else:
                item_dict = {
                    'item_code': frappe.get_value("Innomat Settings", "Innomat Settings", "travel_fee_item"),
                    'qty': 1,
                    'rate': value['travel_fee'],
                    'description': "Anfahrt {0}".format(value['date'].strftime("%d.%m.%Y")),
                    'against_timesheet': timesheet,
                    'ts_detail': value['ts_detail'],
                    'sales_item_group': "Service"
                }
            
            row = new_dn.append('items', item_dict)
        row = new_dn.append('sales_item_groups', {'group': 'Service', 'title': 'Service', 'sum_caption': 'Summe Service'})
        new_dn.insert()
        dns.append(new_dn.name)
    return ", ".join(dns)

"""
Get not-invoiced service project time records
"""
def get_uninvoiced_service_time_records(project, from_date=None, to_date=None):
    time_conditions = ""
    if from_date:
        time_conditions += """ AND DATE(`tabTimesheet Detail`.`from_time`) >= "{from_date}" """.format(from_date=from_date)
    if to_date:
        time_conditions += """ AND DATE(`tabTimesheet Detail`.`from_time`) <= "{to_date}" """.format(to_date=to_date)
    sql_query = """SELECT 
           `tabTimesheet Detail`.`activity_type` AS `activity_type`,
           `tabTimesheet Detail`.`from_time` AS `from_time`,
           `tabTimesheet`.`employee` AS `employee`,
           `tabTimesheet`.`employee_name` AS `employee_name`,
           `tabTimesheet Detail`.`hours` AS `hours`,
           `tabActivity Type`.`invoicing_item` AS `invoicing_item`,
           `tabTimesheet`.`name` AS `timesheet`,
           `tabTimesheet Detail`.`name` AS `ts_detail`
         FROM `tabTimesheet Detail`
         LEFT JOIN `tabTimesheet` ON `tabTimesheet Detail`.`parent` = `tabTimesheet`.`name`
         LEFT JOIN `tabActivity Type` ON `tabTimesheet Detail`.`activity_type` = `tabActivity Type`.`name`
         LEFT JOIN `tabSales Invoice Item` ON `tabTimesheet Detail`.`name` = `tabSales Invoice Item`.`ts_detail`
         WHERE 
           `tabTimesheet`.`docstatus` = 1
           {time_conditions}
           AND `tabTimesheet Detail`.`project` = "{project}"
           AND `tabTimesheet Detail`.`by_effort` = 1
           AND `tabTimesheet Detail`.`activity_type` != "Reisetätigkeit"
           AND `tabSales Invoice Item`.`ts_detail` IS NULL;
    """.format(project=project, time_conditions=time_conditions)
    time_logs = frappe.db.sql(sql_query, as_dict=True)
    return time_logs
    
"""
Create sales invoice when service project completes
"""
@frappe.whitelist()
def create_sinv_from_project(project, from_date=None, to_date=None, sales_item_group="Service"):
    time_logs = get_uninvoiced_service_time_records(project, from_date, to_date)
    if len(time_logs) > 0:
        pj = frappe.get_doc("Project", project)
        new_sinv = frappe.get_doc({
            "doctype": "Sales Invoice",
            "customer": pj.customer,
            "project": project,
            "company": pj.company
        })
        for t in time_logs:
            row = new_sinv.append('items', {
                'item_code': t['invoicing_item'],
                'qty': t['hours'],
                'description': "{0} ({1})".format(t['from_time'].strftime("%d.%m.%Y"), t['employee_name']),
                'against_timesheet': t['timesheet'],
                'ts_detail': t['ts_detail'],
                'sales_item_group': sales_item_group
            })
        # create sales invoice
        row = new_sinv.append('sales_item_groups', {
            'group': sales_item_group, 
            'title': sales_item_group, 
            'sum_caption': 'Summe {0}'.format(sales_item_group)})
        new_sinv.insert()
        return new_sinv.name
    else:
        return _("Nothing to invoice")

"""
Bulk create sales invoices for not-invoiced timesheet positions in service projects
"""
@frappe.whitelist()
def create_sinvs_for_date_range(from_date, to_date):
    # find all service projects in this period
    sql_query = """
        SELECT `tabProject`.`name` AS `project`
        FROM `tabTimesheet Detail` 
        LEFT JOIN `tabProject` ON `tabTimesheet Detail`.`project` = `tabProject`.`name`
        LEFT JOIN `tabTimesheet` ON `tabTimesheet Detail`.`parent` = `tabTimesheet`.`name`
        LEFT JOIN `tabSales Invoice Item` ON `tabTimesheet Detail`.`name` = `tabSales Invoice Item`.`ts_detail`
        WHERE `tabTimesheet`.`docstatus` = 1
          AND DATE(`tabTimesheet Detail`.`from_time`) >= "{from_date}"
          AND DATE(`tabTimesheet Detail`.`from_time`) <= "{to_date}"
          AND `tabProject`.`project_type` = "Service"
          AND `tabTimesheet Detail`.`project` IS NOT NULL
          AND `tabSales Invoice Item`.`ts_detail` IS NULL
        GROUP BY `tabProject`.`name`;
    """.format(from_date=from_date, to_date=to_date)
    projects = frappe.db.sql(sql_query, as_dict=True)
    invoices = []
    for p in projects:
        sales_invoice = create_sinv_from_project(p['project'], from_date, to_date)
        if "Nothing" not in sales_invoice:
            invoices.append(sales_invoice)
    if len(invoices) > 0:
        return ", ".join(invoices)
    else:
        return _("Nothing to invoice")

"""
Allow to create part delivery from sales order
"""
@frappe.whitelist()
def create_part_delivery(sales_order, percentage):
    so = frappe.get_doc("Sales Order", sales_order)
    new_dn = frappe.get_doc({
            "doctype": "Delivery Note",
            "customer": so.customer,
            "project": so.project,
            "company": so.company,
            "customer_address": so.customer_address,
            "contact_person": so.contact_person,
            "shipping_Address_name": so.shipping_address_name,
            "currency": so.currency,
            "selling_price_list": so.selling_price_list,
            "taxes_and_charges": so.taxes_and_charges,
            "payment_terms_template": so.payment_terms_template
        })
    for item in so.items:
        new_dn.append("items", {
            'item_code': item.item_code,
            'rate': item.rate,
            'description': item.description,
            'qty': item.qty * (float(percentage) / 100),
            'against_sales_order': so.name,
            'so_detail': item.name
        })
    for sig in so.sales_item_groups:
        new_dn.append("sales_item_groups", {
            'group': sig.group,
            'title': sig.title,
            'sum_caption': sig.sum_caption
        })
    for t in so.taxes:
        new_dn.append("taxes", {
            'charge_type': t.charge_type,
            'account_head': t.account_head,
            'description': t.description,
            'rate': t.rate
        })
    new_dn.insert()
    return new_dn.name

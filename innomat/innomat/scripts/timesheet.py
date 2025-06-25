
# Copyright (c) 2019-2021, asprotec ag and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from datetime import datetime, timedelta
from frappe.utils.file_manager import save_file
from frappe.utils.pdf import get_pdf
from erpnextswiss.erpnextswiss.common_functions import get_primary_address
from innomat.innomat.utils import get_currency
from frappe.utils import cint

"""
Get timehseet lock date
"""
@frappe.whitelist()
def get_timesheet_lock_date():
    return frappe.get_value("Innomat Settings", "Innomat Settings", "lock_timesheets_until") 

"""
Check if all projects are open. Returns list of closed projects if one ore more projects are closed.
"""
@frappe.whitelist()
def check_projects_open(projects):
    sql_query = """SELECT `name`, `status`
                   FROM `tabProject`
                   WHERE `tabProject`.`name` IN ({projects})
                     AND `tabProject`.`status` != "Open";""".format(projects=projects)
    closed_projects = frappe.db.sql(sql_query, as_dict=True)
    if closed_projects and len(closed_projects) > 0:
        result = []
        for c in closed_projects:
            result.append(c['name'])
        return ", ".join(result)
    else:
        return None
     
""" 
Shortcut to create delivery notes from timesheet
"""
@frappe.whitelist()
def create_dn(project, item, qty, description, timesheet):
    pj = frappe.get_doc("Project", project)
    currency = get_currency(pj)
    new_dn = frappe.get_doc({
        "doctype": "Delivery Note",
        "customer": pj.customer,
        "project": project,
        "company": pj.company,
        "currency": currency
    })
    if project.startswith("A"):
        new_dn.cost_center = "Frauenfed - I"
    else:
        new_dn.cost_center = "Herisau - I"
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
    currency = get_currency(pj)
    date = datetime.strptime(date, "%Y-%m-%d")
    new_dn = frappe.get_doc({
        "doctype": "Delivery Note",
        "customer": pj.customer,
        "project": project,
        "company": pj.company,
        "currency": currency
    })
    if project.startswith("A"):
            new_dn.cost_center = "Frauenfed - I"
    else:
        new_dn.cost_center = "Herisau - I"
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
                'ts_detail': d.name,
                'external_reamrks': d.external_remarks
            })
         
    # grouped by project, create delivery notes
    dns = []
    for k, v in travel.items():
        pj = frappe.get_doc("Project", k)
        currency = get_currency(pj)
        new_dn = frappe.get_doc({
            "doctype": "Delivery Note",
            "customer": pj.customer,
            "project": k,
            "company": pj.company,
            "currency": currency
        })
        if k.startswith("A"):
            new_dn.cost_center = "Frauenfed - I"
        else:
            new_dn.cost_center = "Herisau - I"
        for value in v:
            if "wagen" in value['travel_type']:
                description = "Anfahrt {0}".format(value['date'].strftime("%d.%m.%Y"))
                if 'external_remarks' in value and value['external_remarks']:
                    description += "<br>" + value['external_remarks']
                item_dict = {
                    'item_code': frappe.get_value("Innomat Settings", "Innomat Settings", "mileage_item"),
                    'qty': value['kilometers'],
                    'description': description,
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
Create a service report PDF and attach
"""
@frappe.whitelist()
def create_service_report(contact, timesheet, project):
    # create data record and collect data
    print_format = frappe.get_value("Innomat Settings", "Innomat Settings", "service_report_print_format")
    timesheet = frappe.get_doc("Timesheet", timesheet)
    project = frappe.get_doc("Project", project)
    data = {
        'doc': {
            'name': timesheet.name,
            'company': project.company,
            'customer': project.customer,
            'customer_name': project.customer_name,
            'address': get_primary_address(target_type="Customer", target_name=project.customer),
            'contact': contact,
            'owner': timesheet.owner,
            'transaction_date': timesheet.start_date,
            'items': []
        }
    }
    # add timesheet entries
    for ts in timesheet.time_logs:
        if ts.project == project.name:
            data['doc']['items'].append({
                'item_name': ts.activity_type,
                'description': ts.external_remarks,
                'qty': ts.hours,
                'uom': 'h'
            })
    # search for delivered items
    sql_query = """SELECT `item_name`, `description`, `qty`, `uom`
                   FROM `tabDelivery Note Item`
                   LEFT JOIN `tabDelivery Note` ON `tabDelivery Note Item`.`parent` = `tabDelivery Note`.`name`
                   WHERE `tabDelivery Note Item`.`against_timesheet` = "{timesheet}"
                     AND `tabDelivery Note`.`project` = "{project}";
                """.format(timesheet=timesheet.name, project=project.name)
    materials = frappe.db.sql(sql_query, as_dict=True)
    for m in materials:
        data['doc']['items'].append({
                'item_name': m['item_name'],
                'description': m['description'],
                'qty': m['qty'],
                'uom': m['uom']
            })
    # generate print foramt
    print_format_html = frappe.get_value("Print Format", print_format, "html")
    html = frappe.render_template(print_format_html, data)
    pdf = get_pdf(html)
    # store pdf and attach to project
    filename = "{0}_{1}.pdf".format(timesheet.name, project.name)
    save_file(fname=filename, content=pdf, 
        dt="Project", dn=project.name, is_private=1)
        
    return filename


"""
Close completed tasks from timesheet
"""
@frappe.whitelist()
def close_completed_tasks(timesheet, close=1):
    close = cint(close)
    ts = frappe.get_doc("Timesheet", timesheet)
    for d in ts.time_logs:
        if d.task and d.completed:
            t = frappe.get_doc("Task", d.task)
            if close == 1:
                t.status = "Completed"
            else:
                t.progress = 80         # required, otherwise, re-opining is not possible due to validation
                t.status = "Open"
            t.save()
    frappe.db.commit()
    return

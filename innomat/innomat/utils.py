# Copyright (c) 2019-2021, libracore and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from datetime import datetime, timedelta
from frappe.utils.password import get_decrypted_password
from frappe.utils.file_manager import save_file
from frappe.utils.pdf import get_pdf
from erpnextswiss.erpnextswiss.common_functions import get_primary_address

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
                if "h" in bom_item.uom:
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
            if "h" in i.uom:
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
Create a project from a project tenplate (not standard way, because of invoicing items!)
"""
@frappe.whitelist()
def create_project_from_template(template, company, customer):
    key = get_project_key()
    template = frappe.get_doc("Project Template", template)
    customer = frappe.get_doc("Customer", customer)
    company_key = "IN"
    if "Asprotec" in company:
        company_key = "AS"
    # create project 
    new_project = frappe.get_doc({
        "doctype": "Project",
        "project_key": key,
        "project_name": "{0}{2}{1}".format(company_key, key, template.project_type[0]),
        "project_type": template.project_type,
        "is_active": "Yes",
        "status": "Open",
        "expected_start_date": datetime.now(),
        "expected_end_date": (datetime.now() + timedelta(days=+30)),
        "customer": customer.name,
        "customer_name": customer.customer_name,
        "title": "{0}P{1} {2}".format(company_key, key, customer.customer_name)
    })
    new_project.insert()
    
    # create tasks for each item
    for t in template.tasks:
        new_task = frappe.get_doc({
            "doctype": "Task",
            "subject": t.subject,
            "project": new_project.name,
            "status": "Open",  
            "expected_time": (8 * t.duration),  # template duration is in hours
            "description": t.description,
            "item_code": t.item_code,
            "by_effort": t.by_effort
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
           `tabTask`.`item_code` AS `invoicing_item`,
           `tabTimesheet`.`name` AS `timesheet`,
           `tabTimesheet Detail`.`name` AS `ts_detail`,
           `tabTimesheet Detail`.`external_remarks` AS `external_remarks`
         FROM `tabTimesheet Detail`
         LEFT JOIN `tabTimesheet` ON `tabTimesheet Detail`.`parent` = `tabTimesheet`.`name`
         LEFT JOIN `tabTask` ON `tabTimesheet Detail`.`task` = `tabTask`.`name`
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
            description = "{0} ({1})".format(t['from_time'].strftime("%d.%m.%Y"), t['employee_name'])
            if t['external_remarks']:
                description += "<br>" + t['external_remarks']
            row = new_sinv.append('items', {
                'item_code': t['invoicing_item'],
                'qty': t['hours'],
                'description': description,
                'against_timesheet': t['timesheet'],
                'ts_detail': t['ts_detail'],
                'sales_item_group': sales_item_group
            })
        # create sales invoice
        row = new_sinv.append('sales_item_groups', {
            'group': sales_item_group, 
            'title': sales_item_group, 
            'sum_caption': 'Summe {0}'.format(sales_item_group)})
        # append open delivery note items if there are any
        delivery_notes = frappe.get_all("Delivery Note", filters={'project': project, 'docstatus': 1, 'status': 'To Bill'}, fields=['name'])
        for d in delivery_notes:
            dn = frappe.get_doc("Delivery Note", d['name'])
            for dn_pos in dn.items:
                row = new_sinv.append('items', {
                    'item_code': dn_pos.item_code,
                    'qty': dn_pos.qty,
                    'description': dn_pos.description,
                    'delivery_note': dn.name,
                    'dn_detail': dn_pos.name,
                    'sales_item_group': dn_pos.sales_item_group
                })
        new_sinv.insert()
        return """<a href="/desk#Form/Sales Invoice/{0}">{0}</a>""".format(new_sinv.name)
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

"""
Decrypt access password
"""
@frappe.whitelist()
def decrypt_access_password(cdn):
    password = get_decrypted_password("Equipment Access", cdn, "password", False)
    return password
    
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
This function will create the next akonto invoice and store/attach the pdf
"""
@frappe.whitelist()
def create_akonto(sales_order):
    sales_order = frappe.get_doc("Sales Order", sales_order)
    for a in (sales_order.akonto or []):
        if not a.creation_date:
            data = {
                'doc': sales_order,
                'date': a.date,
                'percent': a.percent
            }
            template = frappe.get_doc("Print Format", "Akonto")
            html = frappe.render_template(template.html, data)
            # create pdf
            pdf = frappe.utils.pdf.get_pdf(html)
            # save and attach pdf
            file_name = ("{0}_Akonto_{1}.pdf".format(sales_order.name, a.idx)).replace(" ", "_").replace("/", "_")
            save_file(file_name, pdf, "Sales Order", sales_order.name, is_private=1)
            # reference in Akonto table
            a.file = file_name
            a.creation_date = datetime.now()
            sales_order.save()
            break
    return

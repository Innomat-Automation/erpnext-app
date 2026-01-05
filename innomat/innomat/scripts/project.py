
# Copyright (c) 2019-2021, asprotec ag and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import get_link_to_form
from datetime import datetime, timedelta
from innomat.innomat.utils import get_currency, get_sales_tax_rule, get_project_key


""" 
Find related draft documents from delivery notes and expense claims
"""
@frappe.whitelist()
def find_drafts(project):
    data = {'delivery_notes': [], 'urls': [], 'expense_claims': [], 'has_drafts': 0, 'timesheets': []}
    draft_dns = frappe.get_all("Delivery Note", filters={'project': project, 'docstatus': 0}, fields=['name'])
    if draft_dns and len(draft_dns) > 0:
        data['has_drafts'] = 1
        for dn in draft_dns:
            data['delivery_notes'].append(dn['name'])
            data['urls'].append(get_link_to_form("Delivery Note", dn['name']))
    
    expense_claims = frappe.db.sql("""SELECT `tabExpense Claim`.`name`
                                      FROM `tabExpense Claim Detail`
                                      LEFT JOIN `tabExpense Claim` ON `tabExpense Claim Detail`.`parent` = `tabExpense Claim`.`name`
                                      WHERE `tabExpense Claim`.`docstatus` = 0
                                        AND `tabExpense Claim Detail`.`project` = "{project}"
                                      GROUP BY `tabExpense Claim`.`name`;""".format(project=project), as_dict=True)
    if expense_claims and len(expense_claims) > 0:
        data['has_drafts'] = 1
        for ec in expense_claims:
            data['expense_claims'].append(ec['name'])
            data['urls'].append(get_link_to_form("Expense Claim", ec['name']))
    
    timesheets = frappe.db.sql("""SELECT `tabTimesheet`.`name`
                                      FROM `tabTimesheet Detail`
                                      LEFT JOIN `tabTimesheet` ON `tabTimesheet Detail`.`parent` = `tabTimesheet`.`name`
                                      WHERE `tabTimesheet`.`docstatus` = 0
                                        AND `tabTimesheet Detail`.`project` = "{project}"
                                      GROUP BY `tabTimesheet`.`name`;""".format(project=project), as_dict=True)
    if timesheets and len(timesheets) > 0:
        data['has_drafts'] = 1
        for ts in timesheets:
            data['timesheets'].append(ts['name'])
            data['urls'].append(get_link_to_form("Timesheet", ts['name']))
            
    return data


"""
Create sales invoice when service project completes
"""
@frappe.whitelist()
def create_sinv_from_project(project, from_date=None, to_date=None, sales_item_group="Service", debug=False):
    # fetch billable hours
    time_logs = get_uninvoiced_service_time_records(project, from_date, to_date)
    # fetch open delivery notes
    delivery_notes = get_uninvoiced_delivery_notes(project)
    if len(time_logs) > 0 or len(delivery_notes) > 0:
        pj = frappe.get_doc("Project", project)
        currency = get_currency(pj)
        new_sinv = frappe.get_doc({
            "doctype": "Sales Invoice",
            "customer": pj.customer,
            "project": project,
            "company": pj.company,
            "taxes_and_charges": get_sales_tax_rule(pj.customer, pj.company),
            "currency": currency
        })
        if project.startswith("A"):
            new_sinv.cost_center = "Frauenfeld - I"
        else:
            new_sinv.cost_center = "Herisau - I"
        # if Sales order exist get discount
        if pj.sales_order and pj.sales_order != "":
            sales_order = frappe.get_doc("Sales Order",pj.sales_order)
            new_sinv.additional_discount_percentage_akonto = sales_order.additional_discount_percentage
            new_sinv.additional_discount_amount_akonto = sales_order.discount_amount
        
        cost_center = frappe.get_value("Company", pj.company, "cost_center")
        for t in time_logs:
            description = "{0} ({1})".format(t['from_time'].strftime("%d.%m.%Y"), t['employee_name'])
            if t.activity_type == "Reisetätigkeit":
                description += "<br>Reisetätigkeit"
            if t['external_remarks']:
                description += "<br>" + t['external_remarks'].replace("\n","<br>")
            row = new_sinv.append('items', {
                'item_code': t['invoicing_item'],
                'qty': t['hours'],
                'uom': 'h',
                'description': description,
                'against_timesheet': t['timesheet'],
                'ts_detail': t['ts_detail'],
                'sales_item_group': sales_item_group,
                'cost_center': cost_center,
                'sales_order': pj.sales_order
            })
        # insert sales item groups
        row = new_sinv.append('sales_item_groups', {
            'group': sales_item_group, 
            'title': sales_item_group, 
            'sum_caption': 'Summe {0}'.format(sales_item_group)})
        # append open delivery note items if there are any
        for d in delivery_notes:
            dn_pos = frappe.get_doc("Delivery Note Item", d['dn_detail'])
            row = new_sinv.append('items', {
                    'item_code': dn_pos.item_code,
                    'qty': dn_pos.qty,
                    'uom': dn_pos.uom,
                    'description': dn_pos.description,
                    'delivery_note': d.name,
                    'dn_detail': dn_pos.name,
                    'sales_item_group': dn_pos.sales_item_group,
                    'rate': dn_pos.rate,
                    'cost_center': cost_center,
                    'sales_order': pj.sales_order
            })
        # insert taxes
        tax_template = frappe.get_doc("Sales Taxes and Charges Template", new_sinv.taxes_and_charges)
        for t in tax_template.taxes:
            new_sinv.append('taxes', {
                'charge_type': t.charge_type,
                'account_head': t.account_head,
                'description': t.description,
                'rate': t.rate
            })
        # check and pull down payments
        payments = frappe.db.sql("""SELECT `tabPayment Entry Reference`.`parent`, `tabPayment Entry Reference`.`allocated_amount`, `tabPayment Entry Reference`.`name` 
                                    FROM `tabPayment Entry Reference` 
                                    LEFT JOIN `tabPayment Entry` ON `tabPayment Entry Reference`.`parent` = `tabPayment Entry`.`name`
                                    WHERE `tabPayment Entry`.`docstatus` = 1
                                      AND `tabPayment Entry Reference`.`reference_doctype` = "Sales Order"
                                      AND `tabPayment Entry Reference`.`reference_name` = "{sales_order}";""".format(sales_order=pj.sales_order), as_dict=True)
        if payments and len(payments) > 0:
            for payment in payments:
                new_sinv.append('advances', {
                    'reference_type': "Payment Entry",
                    'reference_name': payment['parent'],
                    'reference_row': payment['name'],
                    'advance_amount': payment['allocated_amount'],
                    'allocated_amount': payment['allocated_amount'],
                    'remarks': "Auto allocated {0} from {1}".format(payment['allocated_amount'], payment['parent'])
                })
        # create sales invoice
        if debug:
            frappe.log_error("{0}".format(new_sinv.as_dict()), "SINV from Project Debug")
        new_sinv.insert()
        return """<a href="/desk#Form/Sales Invoice/{0}">{0}</a>""".format(new_sinv.name)
    else:
        return _("Nothing to invoice")


"""
Bulk create sales invoices for not-invoiced timesheet positions in service projects
"""
@frappe.whitelist()
def create_sinvs_for_date_range(from_date, to_date, company):
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
          AND `tabProject`.`company` = "{company}"
        GROUP BY `tabProject`.`name`;
    """.format(from_date=from_date, to_date=to_date, company=company)
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
Create a project from a project tenplate (not standard way, because of invoicing items!)
"""
@frappe.whitelist()
def create_project_from_template(template, company, customer, cost_center, po_no=None, po_date=None):
    key = get_project_key()
    template = frappe.get_doc("Project Template", template)
    customer = frappe.get_doc("Customer", customer)
    cost_center_key = "IN"
    if "Frauenfeld" in cost_center:
        company_key = "AS"
    if "Hitzkirch" in cost_center:
        company_key = "ST"
    # create project 
    new_project = frappe.get_doc({
        "doctype": "Project",
        "project_key": key,
        "project_name": "{0}{2}{1}".format(company_key, key, template.project_type[0]),
        "project_type": template.project_type,
        "is_active": "Yes",
        "status": "Open",
        "po_no" : po_no,
        "po_date" : po_date,
        "expected_start_date": datetime.now(),
        "expected_end_date": (datetime.now() + timedelta(days=+30)),
        "customer": customer.name,
        "customer_name": customer.customer_name,
        "title": "{0}{3}{1} {2}".format(company_key, key, (po_no or customer.customer_name), template.project_type[0]),
        "company": company
    })

    if frappe.session.user and frappe.get_value("Employee",{'user_id':frappe.session.user},'name'):
        new_project.append("project_team", {
            "employee": frappe.get_value("Employee",{'user_id':frappe.session.user},'name'),
            "project_manager": 1
        })
        new_project.project_manager = frappe.get_value("Employee",{'user_id':frappe.session.user},'name')
        new_project.project_manager_name = frappe.get_value("Employee",{'user_id':frappe.session.user},'employee_name')

    new_project.insert(ignore_permissions=True)         # ignore user permissions, so that a Service member can create a new project

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
           AND `tabTimesheet Detail`.`do_not_invoice` = 0
           /* AND `tabTimesheet Detail`.`activity_type` != "Reisetätigkeit" (on effort will be invoiced) */
           AND `tabSales Invoice Item`.`ts_detail` IS NULL;
    """.format(project=project, time_conditions=time_conditions)
    time_logs = frappe.db.sql(sql_query, as_dict=True)
    return time_logs

def get_uninvoiced_delivery_notes(project):
    sql_query = """SELECT 
           `tabDelivery Note`.`name` AS `name`,
           `tabDelivery Note Item`.`name` AS `dn_detail`
         FROM `tabDelivery Note Item`
         LEFT JOIN `tabDelivery Note` ON `tabDelivery Note Item`.`parent` = `tabDelivery Note`.`name`
         LEFT JOIN `tabSales Invoice Item` ON `tabDelivery Note Item`.`name` = `tabSales Invoice Item`.`dn_detail`
         WHERE 
           `tabDelivery Note`.`docstatus` = 1
           AND `tabDelivery Note`.`project` = "{project}"
           AND `tabSales Invoice Item`.`dn_detail` IS NULL;
    """.format(project=project)
    delivery_notes = frappe.db.sql(sql_query, as_dict=True)
    return delivery_notes


    return frappe.get_all("Delivery Note", filters={'project': project, 'docstatus': 1, 'status': 'To Bill'}, fields=['name'])
 

""" 
This will mark a related project not invoiced when a Sales Invoice is cancelled or trashed (hooks)
"""
def unset_project_invoiced(sales_invoice, method):
    if sales_invoice.project:
        project = frappe.get_doc("Project", sales_invoice.project)
        if project.is_invoiced == 1:
            project.is_invoiced = 0;
            project.status = "Open"
            project.save()
            frappe.db.commit()
    return

"""
This function will update  the project cost values
"""
def update_project_costs():
    projects = frappe.get_all("Project", filters={'status': 'Open'}, fields=['name', 'sales_order'])
    for p in projects:
        update_project(p)
    return


def update_project(p):
    if p['sales_order']:
        planning_data = get_sales_order_materials(p['sales_order'])
        planned_cost = planning_data['total_mat']
        services_offered = planning_data['total_services']
        planned_hours = planning_data['total_hours']
        planned_hours_budget = planning_data['total_hours_budget']
    else:
        planned_cost = 0
        planned_hours = 0
        planned_hours_budget = 0
        services_offered = 0
    actual_cost = get_project_material_cost(p['name'])
    actual_time_costs = get_project_time_cost(p['name'])
    sum_services = get_project_service_cost(p['name'])
    sum_expense_claim = get_expense_claims_cost(p['name'])
    project = frappe.get_doc("Project", p['name'])
    # only update it required
    if project.planned_hours != planned_hours or project.stundenbudget_plan != planned_hours_budget or project.planned_material_cost != planned_cost or project.services_offered != services_offered or project.stundenbudget_aktuell != actual_time_costs or project.actual_material_cost != actual_cost or project.sum_services != sum_services or project.sum_expense_claim != sum_expense_claim:
        project.planned_hours = planned_hours
        project.stundenbudget_plan = planned_hours_budget
        project.planned_material_cost = planned_cost
        project.services_offered = services_offered
        project.stundenbudget_aktuell = actual_time_costs
        project.actual_material_cost = actual_cost
        project.sum_services = sum_services
        project.sum_expense_claim = sum_expense_claim;
        
        try:
            project.save()
        except Exception as err:
            frappe.log_error(err, "Update material cost {0}".format(p['name']))
    frappe.db.commit()

"""
Get project material cost based on purchase orders
"""
def get_project_service_cost(project):
    data = frappe.db.sql("""SELECT SUM(`net_amount`) AS `cost`
                            FROM `tabPurchase Invoice Item`
                            LEFT JOIN `tabPurchase Invoice` ON `tabPurchase Invoice Item`.`parent` = `tabPurchase Invoice`.`name`
                            LEFT JOIN `tabItem` ON `tabPurchase Invoice Item`.`item_code` = `tabItem`.`item_code`
                            WHERE `tabPurchase Invoice`.`docstatus` = 1
                              AND `tabPurchase Invoice Item`.`project` = "{project}"
                              AND `tabItem`.`is_stock_item` = 0
                        ;""".format(project=project), as_dict=True)

    if data and len(data) > 0:
        return data[0]['cost']
    else:
        return 0

def get_project_material_cost(project):
    data = frappe.db.sql("""SELECT SUM(`credit_in_account_currency`) AS `cost`
                            FROM `tabGL Entry`
                            LEFT JOIN `tabDelivery Note` ON `tabGL Entry`.`voucher_no` = `tabDelivery Note`.`name`
                            WHERE `tabGL Entry`.`docstatus` = 1
                              AND `tabDelivery Note`.`docstatus` = 1
                              AND `tabDelivery Note`.`project` = "{project}"
                        ;""".format(project=project), as_dict=True)

    if data and len(data) > 0:
        return data[0]['cost']
    else:
        return 0


"""
Get project time cost
"""
def get_project_time_cost(project):
    data = frappe.db.sql("""SELECT SUM(`tabTimesheet Detail`.`hours` * `tabEmployee`.`internal_rate_per_hour`) AS `cost`
            FROM `tabTimesheet Detail` 
            LEFT JOIN `tabTimesheet` ON `tabTimesheet`.`name` = `tabTimesheet Detail`.`parent`
            LEFT JOIN `tabEmployee` ON `tabEmployee`.`name` = `tabTimesheet`.`employee`
            WHERE `tabTimesheet`.`docstatus` = 1
              AND `tabTimesheet Detail`.`project` = "{project}"
              AND (`tabTimesheet Detail`.`by_effort` = 0 
                OR (`tabTimesheet Detail`.`by_effort` = 1 AND `tabTimesheet Detail`.`do_not_invoice` = 1)
            )
        ;""".format(project=project), as_dict=True)
    if data and len(data) > 0:
        return data[0]['cost']
    else:
        return 0


def get_expense_claims_cost(project):
    data = frappe.db.sql("""SELECT SUM(`tabExpense Claim Detail`.`amount` * `tabExpense Claim Detail`.`qty`) AS `cost`
            FROM `tabExpense Claim Detail` 
            WHERE `tabExpense Claim Detail`.`docstatus` = 1
              AND `tabExpense Claim Detail`.`project` = "{project}"
        ;""".format(project=project), as_dict=True)
    if data and len(data) > 0:
        return data[0]['cost']
    else:
        return 0
    

"""
Get all required material with costs from a sales order (based on BOM or purchase item
"""
def get_sales_order_materials(sales_order):
    sales_order= frappe.get_doc("Sales Order", sales_order)
    data = {'total_mat' : 0, 'total_services': 0, 'total_hours': 0, 'total_hours_budget': 0, 'items': []}
    for item in sales_order.items:
        if "h" in item.uom:
            if item.by_effort == 0:
                # single per-hour item
                data['total_hours'] += item.qty
                data['total_hours_budget'] += item.qty * frappe.get_value("Item", item.item_code, "valuation_rate")
        else:
            # check if there is a BOM
            boms = frappe.get_all("BOM", filters={'item': item.item_code, 'is_active': 1, 'is_default': 1, 'docstatus': 1}, fields=['name'])
            if boms and len(boms) > 0:
                # get pricing from BOM
                bom = frappe.get_doc("BOM", boms[0]['name'])
                for i in bom.items:
                    if "h" in i.uom:
                        # this is a per-hours item
                        data['total_hours'] += item.qty * i.qty
                        data['total_hours_budget'] += item.qty * i.qty * frappe.get_value("Item", i.item_code, "valuation_rate")
                    else:
                        # this is a material position
                        data['items'].append({
                            'item_code': i.item_code, 
                            'qty': item.qty * i.qty, 
                            'cost': item.qty * i.amount
                        })

                        if frappe.get_value("Item", item.item_code, "is_stock_item"):
                            data['total_mat'] += item.qty * i.amount
                        else:
                            data['total_services'] += item.qty * i.amount
            else:
                # no BOM, use valuation rate
                value = frappe.get_value("Item", item.item_code, "valuation_rate")
                if not value:
                    value = frappe.get_value("Item", item.item_code, "last_purchase_rate")
                data['items'].append({
                    'item_code': item.item_code, 
                    'qty': item.qty, 
                    'cost': item.qty * value
                })

                if frappe.get_value("Item", item.item_code, "is_stock_item"):
                    data['total_mat'] += item.qty * value
                else:
                    data['total_services'] += item.qty * value
    return data
    

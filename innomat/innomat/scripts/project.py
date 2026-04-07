
# Copyright (c) 2019-2021, asprotec ag and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import get_link_to_form
from datetime import datetime, timedelta, date
from innomat.innomat.utils import get_currency, get_sales_tax_rule, get_project_key
from erpnext.stock.get_item_details import get_item_details
from erpnext.setup.utils import get_exchange_rate

# Artikel, von dem wir den ILV-Satz nehmen, wenn in einem Artikel keiner hinterlegt ist
FALLBACK_ITEM_FOR_ILV_RATE = 'ENG-SW'

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
                                        AND `tabExpense Claim Detail`.`project` = %(project)s
                                      GROUP BY `tabExpense Claim`.`name`;""", {"project": project}, as_dict=True)
    if expense_claims and len(expense_claims) > 0:
        data['has_drafts'] = 1
        for ec in expense_claims:
            data['expense_claims'].append(ec['name'])
            data['urls'].append(get_link_to_form("Expense Claim", ec['name']))

    timesheets = frappe.db.sql("""SELECT `tabTimesheet`.`name`
                                      FROM `tabTimesheet Detail`
                                      LEFT JOIN `tabTimesheet` ON `tabTimesheet Detail`.`parent` = `tabTimesheet`.`name`
                                      WHERE `tabTimesheet`.`docstatus` = 0
                                        AND `tabTimesheet Detail`.`project` = %(project)s
                                      GROUP BY `tabTimesheet`.`name`;""", {"project": project}, as_dict=True)
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
        if pj.cost_center:
            new_sinv.cost_center = pj.cost_center
        else:
            # The project's cost center is usually set in project.js
            # The following is a fallback which will not consider all special cases (particularly not internal dev projects)
            cc = None
            if pj.department:
                department_doc = frappe.get_doc("Department", pj.department)
                cc = department_doc.default_cost_center
            if not cc:
                company_doc = frappe.get_doc("Company", pj.company)
                cc = company_doc.cost_center
            new_sinv.cost_center = cc

        # if Sales order exist get discount
        if pj.sales_order and pj.sales_order != "":
            sales_order = frappe.get_doc("Sales Order",pj.sales_order)
            new_sinv.additional_discount_percentage_akonto = sales_order.additional_discount_percentage
            new_sinv.additional_discount_amount_akonto = sales_order.discount_amount

        # Time logs: Use cost center from Timesheet Detail
        # Rationale: We periodically make bookings to ensure all salary is debited to the "right" cost centers according to timesheets, so when we bill hours, we can directly credit the cost center given in timesheets.
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
                'cost_center': t['cost_center'],
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
                    # In SINV-Item for materials, we use the project cost center.
                    # This is correct iff we ensure that material used from "wrong" stock location/department (other department than that of the project) gets transferred to the project's location before it is destocked,
                    # so that its internal valuation is credited to its original cost center and debited from the project cost center.
                    # [Note that the project cost center is identical to the department cost center here, as internal projects will never have sales invoices.]
                    'cost_center': new_sinv.cost_center,
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
                                      AND `tabPayment Entry Reference`.`reference_name` = %(sales_order)s;""", {"sales_order": pj.sales_order}, as_dict=True)
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
          AND DATE(`tabTimesheet Detail`.`from_time`) >= %(from_date)s
          AND DATE(`tabTimesheet Detail`.`from_time`) <= %(to_date)s
          AND `tabProject`.`project_type` = "Service"
          AND `tabTimesheet Detail`.`project` IS NOT NULL
          AND `tabSales Invoice Item`.`ts_detail` IS NULL
          AND `tabProject`.`company` = %(company)s
        GROUP BY `tabProject`.`name`;"""
    projects = frappe.db.sql(sql_query, {"from_date": from_date, "to_date": to_date, "company": company}, as_dict=True)
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
    company_key = company[0:2].upper()
    if "Frauenfeld" in cost_center:
        company_key = "AS"
    department = frappe.get_value("Department", {"default_cost_center": cost_center}, "name") or ''
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
        "company": company,
        "cost_center": cost_center,
        "department": department,
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
        item = frappe.get_doc("Item", t.item_code)
        new_task = frappe.get_doc({
            "doctype": "Task",
            "subject": t.subject,
            "project": new_project.name,
            "status": "Open",
            "expected_time": (8 * t.duration),  # template duration is in hours
            "ilv_rate": item.ilv_rate,
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
        time_conditions += """ AND DATE(`tabTimesheet Detail`.`from_time`) >= %(from_date)s """.format(from_date=from_date)
    if to_date:
        time_conditions += """ AND DATE(`tabTimesheet Detail`.`from_time`) <= %(to_date)s """.format(to_date=to_date)
    sql_query = """SELECT
           `tabTimesheet Detail`.`activity_type` AS `activity_type`,
           `tabTimesheet Detail`.`from_time` AS `from_time`,
           `tabTimesheet`.`employee` AS `employee`,
           `tabTimesheet`.`employee_name` AS `employee_name`,
           `tabTimesheet Detail`.`hours` AS `hours`,
           `tabTask`.`item_code` AS `invoicing_item`,
           `tabTimesheet`.`name` AS `timesheet`,
           `tabTimesheet Detail`.`name` AS `ts_detail`,
           `tabTimesheet Detail`.`external_remarks` AS `external_remarks`,
           `tabTimesheet Detail`.`cost_center` AS `cost_center`
         FROM `tabTimesheet Detail`
         LEFT JOIN `tabTimesheet` ON `tabTimesheet Detail`.`parent` = `tabTimesheet`.`name`
         LEFT JOIN `tabTask` ON `tabTimesheet Detail`.`task` = `tabTask`.`name`
         LEFT JOIN `tabSales Invoice Item` ON `tabTimesheet Detail`.`name` = `tabSales Invoice Item`.`ts_detail`
         WHERE
           `tabTimesheet`.`docstatus` = 1
           {time_conditions}
           AND `tabTimesheet Detail`.`project` = %(project)s
           AND `tabTimesheet Detail`.`by_effort` = 1
           AND `tabTimesheet Detail`.`do_not_invoice` = 0
           /* AND `tabTimesheet Detail`.`activity_type` != "Reisetätigkeit" (on effort will be invoiced) */
           AND `tabSales Invoice Item`.`ts_detail` IS NULL;
    """.format(time_conditions=time_conditions)
    time_logs = frappe.db.sql(sql_query, {"project": project, "from_date": from_date, "to_date": to_date}, as_dict=True)
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
           AND `tabDelivery Note`.`project` = %(project)s
           AND `tabSales Invoice Item`.`dn_detail` IS NULL;
    """
    delivery_notes = frappe.db.sql(sql_query, {"project": project}, as_dict=True)
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
def update_project_costs(all_projects=False):
    if all_projects:
        filters = {}
    else:
        filters = {'status': 'Open'}
    projects = frappe.get_all("Project", filters=filters, fields=['name', 'sales_order'])
    for p in projects:
        update_project(p)
    return


def update_project(p):
    # Fallback cost supplements required for labor cost calculations
    project_doc = frappe.get_doc("Project", p['name'])
    fallback_gk, fallback_vvgk = get_fallback_cost_supplements(p['name'])
    fallback_ilv_rate = get_fallback_ilv_rate()

    # Update labor costs on Task level
    task_totals = {
        'actual_hours': 0,
        'actual_direct_cost': 0,
        'actual_production_cost': 0,
        'actual_prime_cost': 0,
        'forecast_hours': 0,
        'forecast_labor_as_direct_cost': 0,
        'forecast_labor_as_production_cost': 0,
        'forecast_labor_as_prime_cost': 0,
        'forecast_revenue': 0,
    }
    task_totals_by_effort = task_totals.copy()
    project_tasks = frappe.get_all("Task", filters={'project': p['name']}, fields=['name'])
    for task in project_tasks:
        task_data = get_task_labor_cost(task['name'], fallback_gk, fallback_vvgk, fallback_ilv_rate, project_doc)
        # Calculate totals of hours, costs and cost forecasts over all tasks
        # (separate sums for "by effort" tasks)
        for key in task_totals.keys():
            if task_data['by_effort']:
                task_totals_by_effort[key] += task_data[key]
            else:
                task_totals[key] += task_data[key]

        # Only update Task if required
        task_doc = frappe.get_doc("Task", task['name'])
        if task_doc.actual_labor_as_direct_cost != task_data['actual_direct_cost'] or task_doc.actual_labor_as_production_cost != task_data['actual_production_cost'] or task_doc.actual_labor_as_prime_cost != task_data['actual_prime_cost']:
            task_doc.actual_labor_as_direct_cost = task_data['actual_direct_cost']
            task_doc.actual_labor_as_production_cost = task_data['actual_production_cost']
            task_doc.actual_labor_as_prime_cost = task_data['actual_prime_cost']

            try:
                task_doc.save()
            except Exception as err:
                frappe.log_error(err, "Update task {0}".format(task['name']))

    # Project-level forecasts: Include "other" (non-task-specific) hours
    project_data = {
        'forecast_hours': task_totals['forecast_hours'] + project_doc.actual_labor_hours - task_totals['actual_hours'],
        'forecast_labor_as_direct_cost': task_totals['forecast_labor_as_direct_cost'] + project_doc.actual_labor_as_direct_cost - task_totals['actual_direct_cost'],
        'forecast_labor_as_production_cost': task_totals['forecast_labor_as_production_cost'] + project_doc.actual_labor_as_production_cost - task_totals['actual_production_cost'],
        'forecast_labor_as_prime_cost': task_totals['forecast_labor_as_prime_cost'] + project_doc.actual_labor_as_prime_cost - task_totals['actual_prime_cost'],
        'forecast_hours_by_effort': task_totals_by_effort['forecast_hours'] + project_doc.labor_by_effort_hours - task_totals_by_effort['actual_hours'],
        'forecast_labor_by_effort_as_direct_cost': task_totals_by_effort['forecast_labor_as_direct_cost'] + project_doc.labor_by_effort_as_direct_cost - task_totals_by_effort['actual_direct_cost'],
        'forecast_labor_by_effort_as_production_cost': task_totals_by_effort['forecast_labor_as_production_cost'] + project_doc.labor_by_effort_as_production_cost - task_totals_by_effort['actual_production_cost'],
        'forecast_labor_by_effort_as_prime_cost': task_totals_by_effort['forecast_labor_as_prime_cost'] + project_doc.labor_by_effort_as_prime_cost - task_totals_by_effort['actual_prime_cost'],
    }

    # Calculate costs on project level
    project_data['actual_material_cost'] = get_project_material_cost(p['name'])
    actual_labor_cost = get_project_labor_cost(p['name'], fallback_gk, fallback_vvgk)
    project_data.update(actual_labor_cost)
    project_data['sum_services'] = get_project_service_cost(p['name'])
    project_data['sum_expense_claim'] = get_expense_claims_cost(p['name'])

    # Budget values from Sales Order
    if project_doc.sales_order:
        planning_data = get_sales_order_materials(project_doc.sales_order)
        project_data.update(planning_data)
    else:
        project_data.update({'planned_material_cost': 0, 'services_offered': 0, 'planned_hours': 0, 'planned_hours_by_effort': 0, 'stundenbudget_plan': 0, 'planned_hours_ilv': 0, 'planned_hours_by_effort_ilv': 0, 'planned_revenue': 0, 'planned_revenue_by_effort': 0})

    # Revenue forecasts
    project_data['forecast_revenue'] = project_doc.planned_revenue # TODO - we could consider extra sales orders, credit notes etc. here
    project_data['forecast_revenue_by_effort'] = task_totals_by_effort['forecast_revenue']

    # Status light: Calculate EBIT budget & forecast values (NOTE - not stored for now as it's quick to calculate)
    prime_cost_budget = project_data['planned_material_cost'] + project_data['services_offered'] + project_data['planned_hours_ilv'] + project_data['planned_hours_by_effort_ilv']
    ebit_budget = project_data['planned_revenue'] + project_data['planned_revenue_by_effort'] - prime_cost_budget
    material_fc = max(project_data['planned_material_cost'], project_data['actual_material_cost'])
    thirdparty_fc = max(project_data['services_offered'], project_data['sum_services'])
    prime_cost_fc = material_fc + thirdparty_fc + project_data['forecast_labor_as_prime_cost'] + project_data['forecast_labor_by_effort_as_prime_cost']
    ebit_fc = project_data['forecast_revenue'] + project_data['forecast_revenue_by_effort'] - prime_cost_fc
    if ebit_fc < 0:
        project_data['status_light'] = '🔴' # red: EBIT negative
    elif ebit_fc < ebit_budget:
        project_data['status_light'] = '🟡' # yellow: EBIT < budget
    else:
        project_data['status_light'] = '🟢' # green: EBIT >= budget

    # Only update Project if required
    project_changed = False
    for key in project_data.keys():
        if project_data[key] != project_doc.get(key):
            project_changed = True
            break

    if project_changed:
        for key in project_data.keys():
            setattr(project_doc, key, project_data[key])
        try:
            project_doc.save()
        except Exception as err:
            frappe.log_error(err, "Update project {0}".format(p['name']))

    frappe.db.commit()


"""
Get a project's third party services cost (cost of non-stock items) based on purchase invoices
"""
def get_project_service_cost(project):
    data = frappe.db.sql("""SELECT IFNULL(SUM(`net_amount`), 0) AS `cost`
                            FROM `tabPurchase Invoice Item`
                            LEFT JOIN `tabPurchase Invoice` ON `tabPurchase Invoice Item`.`parent` = `tabPurchase Invoice`.`name`
                            LEFT JOIN `tabItem` ON `tabPurchase Invoice Item`.`item_code` = `tabItem`.`item_code`
                            WHERE `tabPurchase Invoice`.`docstatus` = 1
                              AND `tabPurchase Invoice Item`.`project` = %(project)s
                              AND `tabItem`.`is_stock_item` = 0
                        ;""", {"project": project}, as_dict=True)

    if data and len(data) > 0:
        return data[0]['cost']
    else:
        return 0

"""
Get a project's material cost (cost of stock items) from purchase invoices and delivery notes
Since the stock valuation rate in delivery notes (used for perpetual inventory) is only available as a per-document sum, we make a comparison between Delivery Note Items and Purchase Invoice Items.
The value of any (stock-kept) PI Items that are not listed in a Delivery Note is then added to the total valuation of the Delivery Notes.
If no submitted Delivery Notes are available, this will simply return the total value of all (stock-kept) Purchase Invoice Items.
"""
def get_project_material_cost(project):
    total_cost = get_project_material_cost_from_delivery_notes(project)
    pinv_data = frappe.db.sql("""SELECT `tabPurchase Invoice Item`.`item_code`, SUM(`qty`) AS `total_qty`, AVG(`net_rate`) AS `avg_rate`
                            FROM `tabPurchase Invoice Item`
                            LEFT JOIN `tabPurchase Invoice` ON `tabPurchase Invoice Item`.`parent` = `tabPurchase Invoice`.`name`
                            LEFT JOIN `tabItem` ON `tabPurchase Invoice Item`.`item_code` = `tabItem`.`item_code`
                            WHERE `tabPurchase Invoice`.`docstatus` = 1
                              AND `tabPurchase Invoice Item`.`project` = %(project)s
                              AND `tabItem`.`is_stock_item` = 1
                            GROUP BY `tabItem`.`item_code`
                        ;""", {"project": project}, as_dict=True)
    if not pinv_data or len(pinv_data) == 0:
        return 0

    for item in pinv_data:
        dn_item_data = frappe.db.sql("""
        SELECT SUM(`qty`) AS `total_qty`
        FROM `tabDelivery Note Item`
        LEFT JOIN `tabDelivery Note` ON `tabDelivery Note Item`.`parent` = `tabDelivery Note`.`name`
        WHERE `tabDelivery Note`.`docstatus` = 1
          AND `tabDelivery Note`.`project` = %(project)s
          AND `tabDelivery Note Item`.`item_code` = %(item_code)s
        """, {"project": project, "item_code": item['item_code']}, as_dict=True)
        if dn_item_data and len(dn_item_data) > 0:
            delta_qty = item['total_qty'] - (dn_item_data[0]['total_qty'] or 0)
            if delta_qty > 0:
                total_cost += item['avg_rate'] * delta_qty

    return total_cost

"""
The GL entries of delivery notes reflect the valuation of all stock items delivered.
These entries are created because 'Perpetual Inventory' is enabled.
Non-stock items are not included and no per-item valuation is stored.
"""
def get_project_material_cost_from_delivery_notes(project):
    data = frappe.db.sql("""SELECT SUM(`credit_in_account_currency`) AS `cost`
                            FROM `tabGL Entry`
                            LEFT JOIN `tabDelivery Note` ON `tabGL Entry`.`voucher_no` = `tabDelivery Note`.`name`
                            WHERE `tabGL Entry`.`docstatus` = 1
                              AND `tabDelivery Note`.`docstatus` = 1
                              AND `tabDelivery Note`.`project` = %(project)s
                        ;""", {"project": project}, as_dict=True)

    if data and len(data) > 0:
        return data[0]['cost'] or 0
    else:
        return 0


"""
Get a project's direct labor cost according to internal costing rates, and production/prime cost estimated using cost supplements
"""
def get_project_labor_cost(project, fallback_gk, fallback_vvgk):
    # The query returns the direct cost, production cost and prime cost for a project, where
    # direct cost = internal rate * hours,
    # production cost = direct cost * (1 + cost supplement "GK"), and
    # prime cost = production cost * (1 + cost supplement "VVGK")

    # Note that
    # - the internal rate is taken from timesheets where available (fallback to internal rate of Employee)
    # - the cost supplements are also taken from timesheets (fallback to cost supplements of Company if zero)
    # - the cost supplements are stored in percent and thus have to be divided by 100
    # - labor costs by effort are calculated separately

    labor_cost = {
        'actual_labor_as_direct_cost': 0,
        'actual_labor_as_production_cost': 0,
        'actual_labor_as_prime_cost': 0,
        'actual_labor_hours': 0,
        'labor_by_effort_as_direct_cost': 0,
        'labor_by_effort_as_production_cost': 0,
        'labor_by_effort_as_prime_cost': 0,
        'labor_by_effort_hours': 0,
    }

    billability_conditions = {
        'actual_labor': '(`tabTimesheet Detail`.`by_effort` = 0 OR (`tabTimesheet Detail`.`by_effort` = 1 AND `tabTimesheet Detail`.`do_not_invoice` = 1))',
        'labor_by_effort': '(`tabTimesheet Detail`.`by_effort` = 1 AND `tabTimesheet Detail`.`do_not_invoice` = 0)',
    }

    for labor_type, sql_cond in billability_conditions.items():
        data = frappe.db.sql("""SELECT SUM(`tabTimesheet Detail`.`hours` * IFNULL(NULLIF(`tabTimesheet`.`internal_rate_per_hour`, 0), `tabEmployee`.`internal_rate_per_hour`)) AS `direct_cost`,
                SUM( `tabTimesheet Detail`.`hours` * IFNULL(NULLIF(`tabTimesheet`.`internal_rate_per_hour`, 0), `tabEmployee`.`internal_rate_per_hour`) *
                     (1.0 + 0.01 * IFNULL(NULLIF(`tabTimesheet`.`cost_supplement_gk`, 0), %(fallback_gk)s)) ) AS `production_cost`,
                SUM( `tabTimesheet Detail`.`hours` * IFNULL(NULLIF(`tabTimesheet`.`internal_rate_per_hour`, 0), `tabEmployee`.`internal_rate_per_hour`) *
                     (1.0 + 0.01 * IFNULL(NULLIF(`tabTimesheet`.`cost_supplement_gk`, 0), %(fallback_gk)s)) *
                     (1.0 + 0.01 * IFNULL(NULLIF(`tabTimesheet`.`cost_supplement_vvgk`, 0), %(fallback_vvgk)s)) ) AS `prime_cost`,
                SUM(`tabTimesheet Detail`.`hours`) as `hours`
                FROM `tabTimesheet Detail`
                LEFT JOIN `tabTimesheet` ON `tabTimesheet`.`name` = `tabTimesheet Detail`.`parent`
                LEFT JOIN `tabEmployee` ON `tabEmployee`.`name` = `tabTimesheet`.`employee`
                WHERE `tabTimesheet`.`docstatus` = 1
                  AND `tabTimesheet Detail`.`project` = %(project)s
                  AND {by_effort_condition}
            ;""".format(by_effort_condition=sql_cond), {"project": project, "fallback_gk": fallback_gk, "fallback_vvgk": fallback_vvgk}, as_dict=True)
        # If nothing goes wrong, this will set all six values of labor_cost
        if data and len(data) > 0:
            for cost_field, cost_value in data[0].items():
                if cost_field != 'hours':
                    labor_cost[labor_type + '_as_' + cost_field] = cost_value
            labor_cost[labor_type + '_hours'] = data[0]['hours']

    return labor_cost



"""
Get a task's direct labor cost, as well as production/prime cost, and cost forecasts based on the task's average hourly rate.
This function now ignores "by effort" and "do_not_invoice" flags, it simply sums up the hours assigned to the task, so that labor costs are available for all tasks.
"""
def get_task_labor_cost(task, fallback_gk, fallback_vvgk, fallback_ilv_rate, project_doc):
    data = frappe.db.sql("""SELECT
            IFNULL(SUM(`tabTimesheet Detail`.`hours` * IFNULL(NULLIF(`tabTimesheet`.`internal_rate_per_hour`, 0), `tabEmployee`.`internal_rate_per_hour`)), 0) AS `actual_direct_cost`,
            IFNULL(SUM( `tabTimesheet Detail`.`hours` * IFNULL(NULLIF(`tabTimesheet`.`internal_rate_per_hour`, 0), `tabEmployee`.`internal_rate_per_hour`) *
                 (1.0 + 0.01 * IFNULL(NULLIF(`tabTimesheet`.`cost_supplement_gk`, 0), %(fallback_gk)s)) ), 0) AS `actual_production_cost`,
            IFNULL(SUM( `tabTimesheet Detail`.`hours` * IFNULL(NULLIF(`tabTimesheet`.`internal_rate_per_hour`, 0), `tabEmployee`.`internal_rate_per_hour`) *
                 (1.0 + 0.01 * IFNULL(NULLIF(`tabTimesheet`.`cost_supplement_gk`, 0), %(fallback_gk)s)) *
                 (1.0 + 0.01 * IFNULL(NULLIF(`tabTimesheet`.`cost_supplement_vvgk`, 0), %(fallback_vvgk)s)) ), 0) AS `actual_prime_cost`,
            IFNULL(`tabTask`.`expected_time` * IFNULL(NULLIF(IFNULL(NULLIF(`tabTask`.`ilv_rate`, 0), `tabItem`.`ilv_rate`), 0), %(fallback_ilv_rate)s), 0) AS `budget_prime_cost`,
            IFNULL(`tabTask`.`expected_time`, 0) AS `budget_hours`,
            IFNULL(`tabTask`.`actual_time`, 0) AS `actual_hours`,
            IF(`tabTask`.`status` IN ('Cancelled','Completed'), 1, 0) AS `completed`,
            `tabTask`.`by_effort` AS `by_effort`,
            `tabTask`.`item_code` AS `item_code`
            FROM `tabTask`
            LEFT JOIN `tabItem` ON `tabTask`.`item_code` = `tabItem`.`item_code`
            LEFT JOIN `tabTimesheet Detail` ON `tabTask`.`name` = `tabTimesheet Detail`.`task`
            LEFT JOIN `tabTimesheet` ON `tabTimesheet Detail`.`parent` = `tabTimesheet`.`name`
            LEFT JOIN `tabEmployee` ON `tabTimesheet`.`employee` = `tabEmployee`.`name`
            WHERE `tabTimesheet`.`docstatus` = 1
              AND `tabTask`.`name` = %(task)s
        ;""", {"task": task, "fallback_gk": fallback_gk, "fallback_vvgk": fallback_vvgk, "fallback_ilv_rate": fallback_ilv_rate}, as_dict=True)
    # As the overall project labor costs are not calculated from task labor costs, we can safely include "by effort" tasks and unbillable hours here
    # - these will be useful to show accurate stats for every role/task.
    # We do return the `by_effort` field in order to calculate separate sums in  project-level forecasts.

    if data and len(data) > 0:
        task_data = data[0]
        if task_data['completed']:
            task_data['forecast_hours'] = task_data['actual_hours']
            task_data['forecast_labor_as_prime_cost'] = task_data['actual_prime_cost']
            task_data['forecast_labor_as_production_cost'] = task_data['actual_production_cost']
            task_data['forecast_labor_as_direct_cost'] = task_data['actual_direct_cost']
        else:
            prime_fc_rate = 0
            prod_fc_rate = 0
            direct_fc_rate = 0
            if task_data['actual_hours'] > 0:
                prime_fc_rate = task_data['actual_prime_cost'] / task_data['actual_hours']
                prod_fc_rate = task_data['actual_production_cost'] / task_data['actual_hours']
                direct_fc_rate = task_data['actual_direct_cost'] / task_data['actual_hours']
            elif task_data['budget_hours'] > 0:
                prime_fc_rate = task_data['budget_prime_cost'] / task_data['budget_hours']
                prod_fc_rate = prime_fc_rate / (1 + 0.01 * fallback_vvgk)
                direct_fc_rate = prod_fc_rate / (1 + 0.01 * fallback_gk)
            task_data['forecast_hours'] = max(task_data['budget_hours'], task_data['actual_hours'])
            delta_hours = task_data['forecast_hours'] - task_data['actual_hours']
            task_data['forecast_labor_as_prime_cost'] = task_data['actual_prime_cost'] + delta_hours * prime_fc_rate
            task_data['forecast_labor_as_production_cost'] = task_data['actual_production_cost'] + delta_hours * prod_fc_rate
            task_data['forecast_labor_as_direct_cost'] = task_data['actual_direct_cost'] + delta_hours * direct_fc_rate

        if task_data['by_effort']:
            task_billing_rate = get_billing_rate(task_data['item_code'], project_doc)
            task_data['forecast_revenue'] = task_data['forecast_hours'] * task_billing_rate
        else:
            task_data['forecast_revenue'] = 0

        return task_data
    else:
        return {'actual_direct_cost': 0, 'actual_production_cost': 0, 'actual_prime_cost': 0, 'forecast_hours': 0, 'forecast_labor_as_prime_cost': 0, 'forecast_labor_as_production_cost': 0, 'forecast_labor_as_direct_cost': 0, 'forecast_revenue': 0}


def get_expense_claims_cost(project):
    data = frappe.db.sql("""SELECT SUM(`tabExpense Claim Detail`.`amount` * `tabExpense Claim Detail`.`qty`) AS `cost`
            FROM `tabExpense Claim Detail`
            WHERE `tabExpense Claim Detail`.`docstatus` = 1
              AND `tabExpense Claim Detail`.`project` = %(project)s
        ;""", {"project": project}, as_dict=True)
    if data and len(data) > 0:
        return data[0]['cost']
    else:
        return 0


"""
Get all required material with costs from a sales order (based on BOM or purchase item
"""
def get_sales_order_materials(sales_order):
    data = {'planned_material_cost' : 0, 'services_offered': 0, 'planned_hours': 0, 'planned_hours_by_effort': 0, 'stundenbudget_plan': 0, 'planned_hours_ilv': 0, 'planned_hours_by_effort_ilv': 0, 'planned_revenue': 0, 'planned_revenue_by_effort': 0, 'items': []}
    sales_order_doc = frappe.get_doc("Sales Order", sales_order)
    for item in sales_order_doc.items:
        if "h" in item.uom:
            ilv_rate = item.ilv_rate or get_fallback_ilv_rate(item.item_code)
            if item.by_effort == 0:
                # single per-hour item
                data['planned_hours'] += item.qty
                data['stundenbudget_plan'] += item.qty * frappe.get_value("Item", item.item_code, "valuation_rate") # legacy budget calc from valuation rate
                data['planned_hours_ilv'] += item.qty * ilv_rate
                data['planned_revenue'] += item.amount
            else:
                data['planned_hours_by_effort'] += item.qty
                data['planned_hours_by_effort_ilv'] += item.qty * ilv_rate
                data['planned_revenue_by_effort'] += item.amount
        else:
            data['planned_revenue'] += item.amount
            # check if there is a BOM
            boms = frappe.get_all("BOM", filters={'item': item.item_code, 'is_active': 1, 'is_default': 1, 'docstatus': 1}, fields=['name'])
            if boms and len(boms) > 0:
                # get pricing from BOM
                bom = frappe.get_doc("BOM", boms[0]['name'])
                for i in bom.items:
                    if "h" in i.uom:
                        # this is a per-hours item
                        data['planned_hours'] += item.qty * i.qty
                        data['stundenbudget_plan'] += item.qty * i.qty * frappe.get_value("Item", i.item_code, "valuation_rate") # legacy budget calc from valuation rate
                        ilv_rate = i.ilv_rate or get_fallback_ilv_rate(i.item_code)
                        data['planned_hours_ilv'] += item.qty * i.qty * ilv_rate
                        # NOTE - there is no 'by_effort' field in BOM items, therefore all BOM hours go into regular planned hours
                    else:
                        # this is a material position
                        #data['items'].append({
                        #    'item_code': i.item_code,
                        #    'qty': item.qty * i.qty,
                        #    'cost': item.qty * i.amount
                        #})

                        if frappe.get_value("Item", item.item_code, "is_stock_item"):
                            data['planned_material_cost'] += item.qty * i.amount
                        else:
                            data['services_offered'] += item.qty * i.amount
            else:
                # no BOM, use valuation rate
                value = frappe.get_value("Item", item.item_code, "valuation_rate")
                if not value:
                    value = frappe.get_value("Item", item.item_code, "last_purchase_rate")
                #data['items'].append({
                #    'item_code': item.item_code,
                #    'qty': item.qty,
                #    'cost': item.qty * value
                #})

                if frappe.get_value("Item", item.item_code, "is_stock_item"):
                    data['planned_material_cost'] += item.qty * value
                else:
                    data['services_offered'] += item.qty * value
    # Apply any discounts on revenue totals
    # ("total" is before additional discounts and "net_total" is after; both are without taxes)
    data['planned_revenue'] = data['planned_revenue'] * sales_order_doc.net_total / sales_order_doc.total
    data['planned_revenue_by_effort'] = data['planned_revenue_by_effort'] * sales_order_doc.net_total / sales_order_doc.total
    return data


"""
Return a fallback value for an Item's ILV (Interne Leistungsverrechnung) hourly rate, to be used when no value is present in a Sales Order Item
"""
def get_fallback_ilv_rate(item_code=None):
    rate = None
    if item_code:
        rate = frappe.get_value("Item", item_code, "ilv_rate")
    if not rate:
        rate = frappe.get_value("Item", FALLBACK_ITEM_FOR_ILV_RATE, "ilv_rate")
    return rate or 0


"""
Get cost supplements either from project's sales order or from company
To be used as a fallback if no supplements are available in Timesheet
NOTE - we get data directly from DB here to minimize overhead, as this function is used in various contexts where eg. the Project doc may not have been loaded
"""
def get_fallback_cost_supplements(project_name=None, company=None):
    fallback_gk = 0
    fallback_vvgk = 0
    if project_name:
        sales_order, company = frappe.get_value("Project", project_name, ["sales_order", "company"])
        if sales_order:
            fallback_gk, fallback_vvgk = frappe.get_value("Sales Order", sales_order, ["cost_supplement_gk", "cost_supplement_vvgk"])
    if company:
        if not fallback_gk:
            fallback_gk = frappe.get_value("Company", company, "cost_supplement_gk")
        if not fallback_vvgk:
            fallback_vvgk = frappe.get_value("Company", company, "cost_supplement_vvgk")
    return fallback_gk, fallback_vvgk


"""
Get the default project for an employee's "unproductive" activities. Also return the company alongside it, as this saves a server request on Timesheets.
"""
@frappe.whitelist()
def get_employee_default_project(employee):
    employee_doc = frappe.get_doc("Employee", employee)
    if not employee_doc:
        raise Exception(_("Employee '{0}' not found").format(employee))
    company = employee_doc.get('company')
    dept = employee_doc.get('department')
    if not company:
        raise Exception(_("Employee '{0}' has no Company assigned").format(employee))
    company_doc = frappe.get_doc("Company", employee_doc.company)
    cc = company_doc.get('cost_center')
    if not cc:
        raise Exception(_("Company '{0}' has no default cost center assigned").format(company))
    if dept:
        dept_doc = frappe.get_doc("Department", dept)
        if dept_doc.default_cost_center:
            cc = dept_doc.default_cost_center
    cc_doc = frappe.get_doc("Cost Center", cc)
    default_project = cc_doc.get('default_project')
    if not default_project:
        raise Exception(_("Cost Center '{0}' has no default project for general operating costs").format(cc))
    return {'company': company, 'default_project': default_project}


"""
Get the last billing rate used for an Item within the given Project.
Failing that, determine the default rate at which an Item would be billed in a given Project's context.
"""
def get_billing_rate(item_code, project_doc):
    # Get the last used billing rate of this item on the project
    prev_rate = frappe.db.sql("""SELECT `tabSales Invoice Item`.`rate`
        FROM `tabSales Invoice` INNER JOIN `tabSales Invoice Item` ON `tabSales Invoice Item`.`parent` = `tabSales Invoice`.`name`
        WHERE `tabSales Invoice`.`project` = %(project)s AND `tabSales Invoice Item`.`item_code` = %(item)s
        ORDER BY `tabSales Invoice`.`creation` DESC LIMIT 1;""", {"project": project_doc.name, "item": item_code}, as_dict=True)
    if prev_rate and len(prev_rate) > 0 and prev_rate[0]['rate'] > 0:
        return prev_rate[0]['rate']

    # From here on, we need the Customer and Item to exist, and there has to be a price list
    if not project_doc.customer or not frappe.db.exists("Item", item_code):
        return 0
    price_list = frappe.get_value("Customer", project_doc.customer, "default_price_list")
    if not price_list:
        price_list = frappe.defaults.get_global_default("selling_price_list")
    if not price_list:
        return 0

    # All this data is required for get_item_details() to return something useful
    project_currency = get_currency(project_doc)
    exchange_rate = get_exchange_rate(project_currency, "CHF", date.today())
    item_details = get_item_details({
        "item_code": item_code,
        "customer": project_doc.customer,
        "currency": project_currency,
        "conversion_rate": exchange_rate,
        "price_list": price_list,
        "company": project_doc.company,
        "transaction_date": date.today(),
        "doctype": "Sales Invoice"})
    return item_details.price_list_rate
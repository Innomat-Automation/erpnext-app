

# Copyright (c) 2019-2022, asprotec ag and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils.file_manager import save_file
from datetime import datetime, timedelta
from innomat.innomat.utils import get_project_key
from frappe.model.mapper import get_mapped_doc
from frappe.contacts.doctype.address.address import get_company_address
from frappe.model.utils import get_fetch_values

"""
Create a new project with tasks from a sales order
"""
@frappe.whitelist()
def create_project(sales_order,combine_bom):
    key = get_project_key()
    so = frappe.get_doc("Sales Order", sales_order)
    cost_center = frappe.get_value("Company", so.company, "cost_center")
    company_key = "IN"
    if "Asprotec" in so.company:
        company_key = "AS"
    # create project 
    new_project = frappe.get_doc({
        "doctype": "Project",
        "project_key": key,
        "project_name": "{0}P{1}".format(company_key, key),
        "project_type": "Project",
        "object": so.object,
        "is_active": "Yes",
        "status": "Open",
        "expected_start_date": datetime.now(),
        "expected_end_date": so.delivery_date,
        "customer": so.customer,
        "customer_name": so.customer_name,
        "sales_order": sales_order,
        "title": "{0}P{1} {2}".format(company_key, key, (so.object or so.customer_name)),
        "company": so.company
    })
    new_project.insert()
    
    # create tasks for each item
    dn_items = []   # collect time hours not per effort
    for i in so.items:
        hours = 0.0 # sum hours when combine the tasks 
        boms = frappe.get_all("BOM", 
                filters={'item': i.item_code, 'is_default': 1}, 
                fields=['name', 'total_hours'])
        if boms and len(boms) > 0:
            expected_time = boms[0]['total_hours']
            # create one task per BOM position
            bom = frappe.get_doc("BOM", boms[0]['name'])
            for bom_item in bom.items:
                if "h" in bom_item.uom:
                    if combine_bom == '1':
                        hours += (bom_item.qty * i.qty)
                    else:
                        new_task = frappe.get_doc({
                            "doctype": "Task",
                            "subject": bom_item.item_name,
                            "project": new_project.name,
                            "status": "Open",
                            "expected_time": (bom_item.qty * i.qty),
                            "description": bom_item.description,
                            "sales_order": sales_order,
                            "sales_order_item": i.name,
                            "item_code": bom_item.item_code,
                            "by_effort": i.by_effort
                        })
                        new_task.insert()
                if bom_item.need_task:
                    if combine_bom == '1':
                        hours += (bom_item.qty * i.qty)
                    else:
                        new_task = frappe.get_doc({
                            "doctype": "Task",
                            "subject": bom_item.item_name,
                            "project": new_project.name,
                            "status": "Open",
                            "expected_time": (bom_item.hours * i.qty),
                            "description": bom_item.description,
                            "sales_order": sales_order,
                            "sales_order_item": i.name,
                            "item_code": bom_item.item_code,
                            "by_effort": i.by_effort
                        })
                        new_task.insert()
            
            if combine_bom == '1':
                new_task = frappe.get_doc({
                    "doctype": "Task",
                    "subject": i.item_name,
                    "project": new_project.name,
                    "status": "Open",
                    "expected_time": hours,
                    "description": i.description,
                    "sales_order": sales_order,
                    "sales_order_item": i.name,
                    "item_code": i.item_code,
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
            i_item = frappe.get_doc("Item",i.item_code)    
            if i_item.need_task:
                new_task = frappe.get_doc({
                    "doctype": "Task",
                    "subject": i.item_name,
                    "project": new_project.name,
                    "status": "Open",
                    "expected_time": (i_item.hours * i.qty),
                    "description": i.description,
                    "sales_order": sales_order,
                    "sales_order_item": i.name,
                    "item_code": i.item_code,
                    "by_effort": i.by_effort
                })
                new_task.insert()
        # mark for DN creation
        if i.by_effort == 0:
            dn_items.append({
                'item_code': i.item_code,
                'item_name': i.item_name,
                'description': i.description,
                'qty': i.qty,
                'uom': i.uom,
                'rate': i.rate,
                'so_detail': i.name,
                'against_sales_order': so.name,
                'warehouse': i.warehouse,
                'cost_center': cost_center
            })
            
    # create delivery note for all non-per-effort items
    if len(dn_items) > 0:
        new_dn = frappe.get_doc({
            'doctype': "Delivery Note",
            'customer': so.customer,
            'company': so.company,
            'project': new_project.name,
            'currency': so.currency
        })
        for item in dn_items:
            new_dn.append('items', item)
        for sales_item_group in so.sales_item_groups:
            new_dn.append('sales_item_groups', {
                'group': sales_item_group.group, 
                'title': sales_item_group.title, 
                'sum_caption': sales_item_group.sum_caption
            })
        new_dn.insert()
        
    frappe.db.commit()
    return new_project.name


   
"""
This function will create the next akonto invoice
"""
@frappe.whitelist()
def create_akonto(source_name, target_doc=None, ignore_permissions=False):
    def postprocess(source, target):
        set_missing_values(source, target)
        #Get the advance paid Journal Entries in Sales Invoice Advance
        if target.get("allocate_advances_automatically"):
            target.set_advances()

    def set_missing_values(source, target):
        target.is_pos = 0
        target.ignore_pricing_rule = 1
        target.is_akonto = 1
        target.sales_order = source.name
        
        target.flags.ignore_permissions = True
        target.run_method("set_missing_values")
        target.run_method("calculate_taxes_and_totals")

        # set company address
        target.update(get_company_address(target.company))
        if target.company_address:
            target.update(get_fetch_values("Sales Invoice", 'company_address', target.company_address))

    def update_item(source, target, source_parent):
        target.amount = flt(source.amount) - flt(source.billed_amt)
        target.base_amount = target.amount * flt(source_parent.conversion_rate)
        target.qty = target.amount / flt(source.rate) if (source.rate and source.billed_amt) else source.qty - source.returned_qty

        if source_parent.project:
            target.cost_center = frappe.db.get_value("Project", source_parent.project, "cost_center")
        if not target.cost_center and target.item_code:
            item = get_item_defaults(target.item_code, source_parent.company)
            item_group = get_item_group_defaults(target.item_code, source_parent.company)
            target.cost_center = item.get("selling_cost_center") \
                or item_group.get("selling_cost_center")

    doclist = get_mapped_doc("Sales Order", source_name, {
        "Sales Order": {
            "doctype": "Sales Invoice",
            "field_map": {
                "party_account_currency": "party_account_currency",
                "payment_terms_template": "payment_terms_template"
            },
            "validation": {
                "docstatus": ["=", 1]
            }
        },
        "Sales Taxes and Charges": {
            "doctype": "Sales Taxes and Charges",
            "add_if_empty": True
        },
        "Sales Team": {
            "doctype": "Sales Team",
            "add_if_empty": True
        }
    }, target_doc, postprocess, ignore_permissions=ignore_permissions)

    return doclist
    
    
    for a in (sales_order.akonto or []):
        if not a.creation_date:
            data = {
                'doc': sales_order,
                'date': a.date,
                'percent': a.percent,
                'idx': a.idx,
                'remarks': a.remarks,
                'amount': round(a.amount, 2),
                'print_total_and_percent': a.print_total_and_percent
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
            # create payment record
            create_akonto_payment(sales_order.name, a.amount, "Akonto {0}".format(a.idx))
            break
    return

def get_akonto_account(company, currency):
    accounts = frappe.db.sql("""
        SELECT `akonto_account` 
        FROM `tabInnomat Settings Account`
        WHERE `parentfield` = "akonto_accounts"
          AND `company` = "{company}"
          AND `akonto_currency` = "{currency}";""".format(company=company, currency=currency), as_dict=True)
    if accounts and len(accounts) > 0:
        return accounts[0]['akonto_account']
    else:
        frappe.throw( _("Please configure akonto accounts in Innomat Settings") )
        
def create_akonto_payment(sales_order, amount, akonto_reference):
    so = frappe.get_doc("Sales Order", sales_order)
    account = get_akonto_account(so.company, so.currency)
    
    # create payment entry
    new_pe = frappe.get_doc({
        'doctype': "Payment Entry",
        'company': so.company,
        'payment_type': "Receive",
        'party_type': "Customer",
        'party': so.customer,
        'posting_date': datetime.now(),
        'paid_to': account,
        'received_amount': amount,
        'paid_amount': amount,
        'reference_no': akonto_reference,
        'reference_date': datetime.now(),
        'remarks': "Akonto payment {0} from {1}".format(akonto_reference, so.name)
    })
    new_pe.append('references', {
        'reference_doctype': "Sales Order",
        'reference_name': so.name,
        'allocated_amount': amount
    })
    new_pe.insert()
    # check for currency conversion differences and write them off
    if new_pe.difference_amount != 0:
        company_settings = frappe.get_doc("Company", so.company)
        new_pe.append("deductions", {
            'account': company_settings.round_off_account,
            'cost_center': company_settings.round_off_cost_center,
            'amount': new_pe.difference_amount
        })
        new_pe.save()
    new_pe.submit()
    frappe.db.commit()
    return
        
            
@frappe.whitelist()
def add_akonto_payment_reference(sales_order, payment_entry):
    sales_order = frappe.get_doc("Sales Order", sales_order)
    for a in (sales_order.akonto or []):
        if not a.payment:
            a.payment = payment_entry
            a.save()
            break
    return

@frappe.whitelist()
def get_akonto_deduction_content(payment_entry):
    pe = frappe.get_doc("Payment Entry", payment_entry)
    account = get_akonto_account(pe.company, pe.paid_from_account_currency)
    cost_center = frappe.get_value("Company", pe.company, "cost_center")
    return {'account': account, 'cost_center': cost_center, 'amount': (-1) * pe.paid_amount }

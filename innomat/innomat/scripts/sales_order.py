

# Copyright (c) 2019-2021, asprotec ag and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils.file_manager import save_file
from datetime import datetime, timedelta
from innomat.innomat.utils import get_project_key



"""
Create a new project with tasks from a sales order
"""
@frappe.whitelist()
def create_project(sales_order):
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
            "payment_terms_template": so.payment_terms_template,
            "currency": so.currency
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
                'percent': a.percent,
                'idx': a.idx,
                'remarks': a.remarks,
                'amount': a.amount,
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

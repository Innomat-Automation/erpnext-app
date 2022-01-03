# Copyright (c) 2019-2021, libracore and contributors
# For license information, please see license.txt

import frappe
from frappe import _
import json 

"""
This function will return the BOM cost/rate for calculations (e.g. quotation)
"""
@frappe.whitelist()
def get_bom_rate(item_code):
    boms = frappe.get_all("BOM", 
           filters={'item': item_code, 'is_active': 1, 'is_default': 1}, 
           fields=['name', 'total_cost'])
    if len(boms) > 0:
        return {'source': boms[0]['name'], 'rate': boms[0]['total_cost']}
    else:
        return {'source': None, 'rate': 0}
    
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
This function checks the rates (price list or BOM) in a quotation or sales order against the current values
"""
@frappe.whitelist()
def check_rates(doctype, docname):
    doc = frappe.get_doc(doctype, docname)
    changes = []
    for i in doc.items:
        if i.bom_rate:
            rate = get_bom_rate(i.item_code)
            if rate['rate'] != i.bom_rate:
                changes.append({
                    'idx': i.idx,
                    'item_code': i.item_code,
                    'item_name': i.item_name,
                    'doc_rate': i.bom_rate,
                    'current_rate': rate['rate'],
                    'remarks': "{0} &gt; {1}".format(i.from_bom, rate['source'])
                })
        elif i.price_list_rate:
            rates = frappe.get_all("Item Price", filters={'item_code': i.item_code, 'selling': 1}, fields=['name', 'price_list_rate'])
            if rates and len(rates) > 0:
                if rates[0]['price_list_rate'] != (i.base_price_list_rate or i.price_list_rate):
                    changes.append({
                        'idx': i.idx,
                        'item_code': i.item_code,
                        'item_name': i.item_name,
                        'doc_rate': (i.base_price_list_rate or i.price_list_rate),
                        'current_rate': rates[0]['price_list_rate'],
                        'remarks': "{0}".format(rates[0]['name'])
                    })
    html = frappe.render_template("innomat/templates/includes/price_info.html", {'changes': changes})
    return {'html': html}



"""
Find currency for project
"""
def get_currency(project):
    if project.sales_order:
        sales_order = frappe.get_doc("Sales Order", project.sales_order)
        currency = sales_order.currency
    elif project.customer:
        customer = frappe.get_doc("Customer", project.customer)
        currency = customer.default_currency or "CHF"
    else:
        currency = "CHF"
    return currency


"""
Fetch correct sales tax rule
"""
@frappe.whitelist()
def get_sales_tax_rule(customer, company):
    territory = frappe.get_value("Customer", customer, "territory")
    tax_code = "302" if territory == "Schweiz" else "000"
    rules = frappe.get_all("Sales Taxes and Charges Template", filters={'tax_code': tax_code, 'company': company}, fields=['name'])
    if rules and len(rules) > 0:
        return rules[0]['name']
    else:
        return None




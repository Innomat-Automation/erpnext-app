

# Copyright (c) 2019-2021, asprotec ag and contributors
# For license information, please see license.txt


import frappe
from frappe import _
import json
from innomat.innomat.utils import get_currency

"""
On submit of an expense claim, create delivery notes from travel entries
"""
@frappe.whitelist()
def create_expense_notes(expense_claim, expense_key):
    ts = frappe.get_doc("Expense Claim", expense_claim)
    expense_key = json.loads(expense_key)
    travel = {}
    for d in ts.expenses:
        if d.expense_type in expense_key and d.project:
            # if project key does not yet exist, create it
            if d.project not in travel:
                travel[d.project] = []
            # insert billing item
            travel[d.project].append({
                'date': d.expense_date,
                'expense_type': d.expense_type,
                'amount': d.amount,
                'ec_detail': d.name,
                'description': d.description
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
        for value in v:
            description = "Spesen {0}".format(value['date'].strftime("%d.%m.%Y"))
            if value['description']:
                description += "<br>" + value['description']
            item_dict = {
                'item_code': frappe.get_value("Innomat Settings", "Innomat Settings", "travel_fee_item"),
                'qty': 1,
                'rate': value['amount'],
                'description': description,
                'against_expense_claim': expense_claim,
                'ec_detail': value['ec_detail'],
                'sales_item_group': "Service"
            }
            
            row = new_dn.append('items', item_dict)
        row = new_dn.append('sales_item_groups', {'group': 'Service', 'title': 'Service', 'sum_caption': 'Summe Service'})
        new_dn.insert()
        dns.append(new_dn.name)
    return ", ".join(dns)
# Copyright (c) 2019-2021, asprotec ag and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from datetime import datetime
from frappe.utils import add_to_date
from innomat.innomat.utils import get_sales_tax_rule

"""
Create sales invoice when service contract time is comming
"""
@frappe.whitelist()
def create_sinv_from_service_contract(contract):
    #Check the periode date
    contract_doc = frappe.get_doc("Service Contract",contract);
    last_period = frappe.db.sql("""SELECT `tabService Contract Period`.`parent`, `tabService Contract Period`.`end_date` 
                                    FROM `tabService Contract Period` 
                                    WHERE `tabService Contract Period`.`parent` = "{contract}"
                                    ORDER BY `tabService Contract Period`.`end_date` desc;""".format(contract=contract), as_dict=True)

    if len(last_period) == 0 or last_period[0].end_date < datetime.now().date():
        customer = frappe.get_doc("Customer", contract_doc.customer)
        currency = customer.default_currency or "CHF"
        new_sinv = frappe.get_doc({
            "doctype": "Sales Invoice",
            "customer": customer.name,
            "service_contract": contract,
            "company": contract_doc.company,
            "taxes_and_charges": get_sales_tax_rule(contract_doc.customer, contract_doc.company),
            "currency": currency
        })
        cost_center = frappe.get_value("Company", contract_doc.company, "cost_center")
        for t in contract_doc.services:
            row = new_sinv.append('items', {
                    'item_code': t.item,
                    'qty': t.qty,
                    'uom': 'Stk',
                    'rate': t.rate,
                    'description': t.description,
                    'cost_center': cost_center
                })
        
        tax_template = frappe.get_doc("Sales Taxes and Charges Template", new_sinv.taxes_and_charges)
        for t in tax_template.taxes:
            new_sinv.append('taxes', {
                'charge_type': t.charge_type,
                'account_head': t.account_head,
                'description': t.description,
                'rate': t.rate
            })

        new_sinv.insert()

        #Create periods entry
        if len(last_period) == 0:
            startdate = contract_doc.start_date;
        else:
            startdate = add_to_date(last_period[0].end_date, days = 1)

        if contract_doc.period_duration == "Week":
            enddate = add_to_date(startdate, days=7);
        elif contract_doc.period_duration == "Month":
            enddate = add_to_date(startdate, months=1);
        elif contract_doc.period_duration == "Year":
            enddate = add_to_date(startdate, year=1);
        elif contract_doc.period_duration == "2 Year":
            enddate = add_to_date(startdate, year=2);
        elif contract_doc.period_duration == "3 Year":
            enddate = add_to_date(startdate, year=3);
        elif contract_doc.period_duration == "5 Year":
            enddate = add_to_date(startdate, year=5);
        else:
            enddate = startdate

        row = contract_doc.append('periods', {
                    'start_date': startdate,
                    'end_date': enddate,
                    'invoice': new_sinv.name
                })
        contract_doc.save()

        return """<a href="/desk#Form/Sales Invoice/{0}">{0}</a>""".format(new_sinv.name)
    else:
        return _("Nothing to invoice")

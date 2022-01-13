import frappe
from frappe import _

def execute():
    try:
        invoices = frappe.get_all('Sales Order',filters={'docstatus': 1});

        for invoice in invoices:
            inv_doc = frappe.get_doc('Sales Order',invoice.name)
            net_amount = 0.0
            if len(inv_doc.akonto) > 0:
                net_amount = 0.0
                for item in inv_doc.items:
                    if item.by_effort == 0:
                        net_amount += item.net_amount
                if net_amount == 0.0: 
                    net_amount = 0.01
                
                for akonto in inv_doc.akonto:
                    akonto.netto = net_amount * (akonto.percent / 100.0)
                
                inv_doc.save()
        
        frappe.db.commit();
       
    except Exception as err:
        print("Unable to set akonto netto value")
    return

    

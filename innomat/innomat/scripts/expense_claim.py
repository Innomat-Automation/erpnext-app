

# Copyright (c) 2019-2025, asprotec ag and contributors
# For license information, please see license.txt


import frappe
from frappe import _
import json
from innomat.innomat.utils import get_currency
from frappe.utils.pdf import get_pdf
import os.path
from PyPDF2 import PdfFileMerger,PdfFileReader
import io
from PIL import Image

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
        if k.startswith("A"):
            cost_center = "Frauenfed - I"
        else:
            cost_center = "Herisau - I"
        currency = get_currency(pj)
        new_dn = frappe.get_doc({
            "doctype": "Delivery Note",
            "customer": pj.customer,
            "project": k,
            "company": pj.company,
            "currency": currency,
            "cost_center": cost_center
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
                'sales_item_group': "Service",
                'cost_center': cost_center                              # technically covered by before_save:innomat.innomat.utils.apply_cost_center
            }
            
            row = new_dn.append('items', item_dict)
        row = new_dn.append('sales_item_groups', {'group': 'Service', 'title': 'Service', 'sum_caption': 'Summe Service'})
        new_dn.insert()
        dns.append(new_dn.name)
    return ", ".join(dns)


""" Get Invoices for extern"""
@frappe.whitelist()
def get_expense_claim_attachement(fromdate,todate,company):
    pdf_merge = PdfFileMerger(False);
    error = [];

    expeneses = frappe.get_all('Expense Claim',
                                filters={'company': ['=', str(company)],'posting_date' : ['between',[fromdate,todate]],'docstatus': 1},
                                order_by='posting_date');

    for expense in expeneses:
        exp_doc = frappe.get_doc('Expense Claim',expense.name);
        html = frappe.get_print('Expense Claim','Spesenuebersicht', doc=exp_doc)
        pdf = get_pdf(html)
        pdf_merge.append(PdfFileReader(io.BytesIO(pdf)))
        
        # Add Attached files
        attached_files = frappe.get_all('File',filters={'attached_to_name':exp_doc.name});
        if attached_files:
            for filename in attached_files:
                file_object = frappe.get_doc('File',filename.name);
                if str(file_object.file_url).lower().endswith(".pdf"):
                    try:
                        pdf_merge.append(frappe.get_site_path() + str(file_object.file_url));
                    except:
                        error.append(exp_doc.name + ":" + filename.name)
                        pass
                if str(file_object.file_url).lower().endswith(".png") or str(file_object.file_url).lower().endswith(".gif") or str(file_object.file_url).lower().endswith(".jpg"):
                    try:
                        image = Image.open(frappe.utils.get_path('private' if file_object.is_private else 'public', 'files', file_object.file_name));
                        im = image.convert('RGB');
                        pdf_bytes_io = io.BytesIO()
                        im.save(pdf_bytes_io,"pdf")
                        pdf_merge.append(pdf_bytes_io);
                    except:
                        error.append(exp_doc.name + ":" + filename.name)
                        pass    
    if error:
        frappe.log_error("Error at read Expenses Attachements : {0}".format(error))
    outputStream = io.BytesIO();
    pdf_merge.write(outputStream);
    frappe.local.response.filename = "result.pdf"
    frappe.local.response.filecontent = outputStream.getvalue() # custom function
    frappe.local.response.type = "pdf"


import frappe
from frappe import _
from frappe.utils.pdf import get_pdf
import os.path
from PyPDF2 import PdfFileMerger,PdfFileReader
import io


""" 
This function allows to insert a purchase invoice with minimal input
"""
@frappe.whitelist()
def quick_pinv(date, gross_amount, supplier, expense_account, purchase_taxes, remarks, company):
    # prepare values
    gross_amount = float(gross_amount)
    cost_center = frappe.get_value("Company", company, "cost_center")
    # create base document
    new_pinv = frappe.get_doc({
        'doctype': "Purchase Invoice",
        'company': company,
        'supplier': supplier,
        'posting_date': date,
        'taxes_and_charges': purchase_taxes,
        'bill_no': remarks,
        'bill_date': date,
        'set_posting_time': 1,
        'is_proposed': 1
    })
    # check taxation
    taxes_template = frappe.get_doc("Purchase Taxes and Charges Template", purchase_taxes)
    if taxes_template.taxes and len(taxes_template.taxes) > 0:
        tax_rate = taxes_template.taxes[0].rate
        net_amount = round(gross_amount / ((100 + tax_rate) / 100), 2)
    else:
        tax_rate = 0
        net_amount = gross_amount
    # add item position
    item = frappe.get_value("Innomat Settings", "Innomat Settings", "quick_pinv_item")
    new_pinv.append("items", {
        'item_code': item,
        'description': remarks,
        'qty': 1,
        'rate': net_amount,
        'expense_account': expense_account,
        'cost_center': cost_center
    })
    # add taxes
    for t in taxes_template.taxes:
        new_pinv.append("taxes", {
            'account_head': t.account_head,
            'charge_type': t.charge_type,
            'rate': t.rate,
            'description': t.description
        })
    # insert new record
    new_pinv.insert()
    new_pinv.submit()
    frappe.db.commit()
    return new_pinv.name


""" Get Invoices for extern"""
@frappe.whitelist()
def get_invoices(fromdate,todate,company):
    pdf_merge = PdfFileMerger();

    invoices = frappe.get_all('Purchase Invoice',
                                filters={'company': ['=', str(company)],'due_date' : ['between',[fromdate,todate]],'docstatus': 1},
                                order_by='due_date');

    for invoice in invoices:
        attached_files = frappe.get_all('File',filters={'attached_to_name':invoice.name});
        no_invoice = True;
        if attached_files:
            for filename in attached_files:
                file_object = frappe.get_doc('File',filename.name);
                if str(file_object.file_url).endswith(".pdf"):
                    pdf_merge.append(frappe.get_site_path() + str(file_object.file_url));
                    no_invoice = False;
        
        if no_invoice:
            inv_doc = frappe.get_doc('Purchase Invoice',invoice.name);
            html = frappe.get_print('Purchase Invoice', doc=inv_doc)
            pdf = get_pdf(html)
            pdf_merge.append(PdfFileReader(io.BytesIO(pdf)))
    
    outputStream = io.BytesIO();
    pdf_merge.write(outputStream);
    frappe.local.response.filename = "result.pdf"
    frappe.local.response.filecontent = outputStream.getvalue() # custom function
    frappe.local.response.type = "pdf"


""" Get Invoices for extern"""
@frappe.whitelist()
def get_sales_invoices(fromdate,todate,company):
    pdf_merge = PdfFileMerger();

    invoices = frappe.get_all('Sales Invoice',
                                filters={'company': ['=', str(company)],'due_date' : ['between',[fromdate,todate]],'docstatus': 1},
                                order_by='due_date');

    for invoice in invoices:
        inv_doc = frappe.get_doc('Sales Invoice',invoice.name);
        html = frappe.get_print('Sales Invoice','Ausgangsrechnung', doc=inv_doc)
        pdf = get_pdf(html)
        pdf_merge.append(PdfFileReader(io.BytesIO(pdf)))
    
    outputStream = io.BytesIO();
    pdf_merge.write(outputStream);
    frappe.local.response.filename = "result.pdf"
    frappe.local.response.filecontent = outputStream.getvalue() # custom function
    frappe.local.response.type = "pdf"


""" Get Akonto for extern"""
@frappe.whitelist()
def get_sales_akonto(fromdate,todate,company):
    pdf_merge = PdfFileMerger();

    akontos = frappe.db.sql("""SELECT `tabSales Order Akonto`.`name` FROM `tabSales Order Akonto` 
                            LEFT JOIN `tabSales Order` ON `tabSales Order Akonto`.`parent` = `tabSales Order`.`name` 
                            WHERE `tabSales Order`.`company` = "{company}"
                            AND DATE(`tabSales Order Akonto`.`date`) >= "{fromdate}"
                            AND  DATE(`tabSales Order Akonto`.`date`) <= "{todate}"
                            ORDER BY `tabSales Order Akonto`.`date`""".format(company = company, fromdate= fromdate, todate = todate),as_dict =True);

    for invoice in akontos:
        attached_files = frappe.get_doc('Sales Order Akonto',invoice.name);
        if attached_files.file:
            if os.path.isfile(frappe.get_site_path() + "/private/files/" + str(attached_files.file)):
                pdf_merge.append(frappe.get_site_path() + "/private/files/" + str(attached_files.file));
            
    outputStream = io.BytesIO();
    pdf_merge.write(outputStream);
    frappe.local.response.filename = "result.pdf"
    frappe.local.response.filecontent = outputStream.getvalue() # custom function
    frappe.local.response.type = "pdf"
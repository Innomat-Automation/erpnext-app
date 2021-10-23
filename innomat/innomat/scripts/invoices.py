
import frappe
from frappe import _
from frappe.utils.pdf import get_pdf
import os.path
from PyPDF2 import PdfFileMerger,PdfFileReader
import io


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
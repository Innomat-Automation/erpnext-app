# Copyright (c) 2019-2021, Asprotec AG and contributors
# For license information, please see license.txt
# functions for migration from old systems


import frappe
from urllib.request import urlopen
from bs4 import BeautifulSoup
import urllib.request
import os


def disable_email():
    frappe.db.set_value('Email Account','Benachrichtigung','enable_outgoing',0)
    frappe.db.commit()


def update_items_default_supplier():
    items = frappe.get_all("Item")

    for item in items:
        update_item_default_supplier(item)



def update_item_default_supplier(itemname):
    item = frappe.get_doc("Item",itemname);

    if len(item.supplier_items) <= 0:
        return

    for default in item.item_defaults:
        if default.default_supplier == None:
            default.default_supplier = item.supplier_items[0].supplier
    
    item.save()
    frappe.db.commit()


def load_siemens_images():
    item = frappe.get_all("Item",fields=['item_code'])

    for i in item:
        doc = frappe.get_doc("Item",i.item_code)
        if (doc.supplier_items is not None and len(doc.supplier_items) > 0 and doc.supplier_items[0].supplier == 'L-0001' and doc.image is None):
            try:
                url = "https://mall.industry.siemens.com/mall/de/ch/Catalog/Product/" + doc.item_code
                page = urlopen(url)
                soup = BeautifulSoup(page,'html.parser')
                desc = soup.find('div', {"class":"pictureArea pictureAreaCursor"})
                if desc != None:
                    for image in desc.findAll('img'):
                        src = image['src']
                        filename = '/files/siemens/' + doc.item_code + '.jpg'
                        try :
                            urllib.request.urlretrieve(src,frappe.local.site  + "/public" + filename)
                            frappe.db.set_value("Item", i.item_code, "image", filename)

                            if not frappe.db.exists("File",doc.item_code + '.jpg'):
                                new_file = frappe.get_doc({
                                        "doctype": "File",
                                        "file_name": doc.item_code + '.jpg',
                                        "attached_to_doctype": "Item",
                                        "attached_to_name": i.item_code,
                                        "attached_to_field": None,
                                        "file_url": str(filename),
                                        "file_size": os.stat(frappe.local.site + "/public" + filename).st_size,
                                        "is_private": 0}).insert()
                                print(filename);
                        except:
                            pass
            except: 
                pass
    
    frappe.db.commit()
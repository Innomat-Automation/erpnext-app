# Copyright (c) 2019-2021, Asprotec AG and contributors
# For license information, please see license.txt
# functions for migration from old systems


import frappe


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
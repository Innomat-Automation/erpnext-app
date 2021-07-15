# Copyright (c) 2019-2021, Asprotec AG and contributors
# For license information, please see license.txt
# functions for migration from old systems


import frappe


def disable_email():
    frappe.db.set_value('Email Account','Benachrichtigung','enable_outgoing',0)
    frappe.db.commit()
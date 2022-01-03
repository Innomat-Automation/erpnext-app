

# Copyright (c) 2019-2021, asprotec ag and contributors
# For license information, please see license.txt


import frappe
from frappe import _
from frappe.utils.password import get_decrypted_password

"""
Decrypt access password
"""
@frappe.whitelist()
def decrypt_access_password(cdn):
    password = get_decrypted_password("Equipment Access", cdn, "password", False)
    return password
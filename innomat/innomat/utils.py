# Copyright (c) 2019-2021, libracore and contributors
# For license information, please see license.txt

import frappe
from frappe import _

"""
This function will return the BOM cost/rate for calculations (e.g. quotation)
"""
@frappe.whitelist()
def get_bom_rate(item_code)
    boms = frappe.get_all("BOM", 
           filters={'item': item_code, 'is_active': 1, 'is_default': 1}, 
           fields=['name', 'total_cost'])
    if len(boms) > 0:
        return boms[0]['total_cost']
    else:
        return 0
    

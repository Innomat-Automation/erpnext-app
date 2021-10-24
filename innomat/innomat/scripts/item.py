
# Copyright (c) 2019-2021, asprotec ag and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from datetime import datetime, timedelta

"""
Update price list's
"""
@frappe.whitelist()
def set_price_list(sourcelist, destlist, itemgroup,margin, set_valuation_rate = True):
    item_prices = frappe.get_all('Item Price',filters={'price_list':str(sourcelist)},fields=['item_code','price_list_rate'])
    #item_prices = frappe.get_all("Item Price",filters={'price_list':'Standard-Kauf'},fields=['item_code','price_list_rate'])

    for item_price in item_prices:
        item = frappe.get_doc('Item',item_price.item_code)

        if item and item.item_group == itemgroup: 
            if set_valuation_rate: 
                item.valuation_rate = item_price.price_list_rate
                item.save()
            
            price = frappe.get_doc({'doctype' : 'Item Price',
                                    'item_code' : item_price.item_code,
                                    'price_list' : destlist,
                                    'price_list_rate' : float(item_price.price_list_rate) * float(margin),
                                    'valid_from': datetime.now().date()
            })
            price.insert()
    frappe.db.commit()
    return "Done"

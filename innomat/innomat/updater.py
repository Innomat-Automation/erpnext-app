# Copyright (c) 2019-2021, libracore and contributors
# For license information, please see license.txt

import frappe
from frappe import _

def cleanup_languages():
    # this function will remove languages after migrate
    print("Removing unnecessary languages...")
    lang = "'de', 'en-US', 'en', 'fr'"
    sql_query = """DELETE FROM `tabLanguage` WHERE `language_code` NOT IN ({lang});""".format(lang=lang)
    frappe.db.sql(sql_query, as_dict=1)
    return

# Copyright (c) 2019-2021, Asprotec AG and contributors
# For license information, please see license.txt
# functions for migration from old systems


import frappe
import pymssql
from frappe import _


# function to migrate projects from Timesafe
def migrate_projects_from_timesafe():
    con = get_connection();
    cursor = con.cursor(as_dict=True)
    cursor.execute('SELECT * From Projects')

    for row in cursor:
        key = row['strProjectNo']
        company_key = "IN"
        if(str(key).startswith('2') or str(key).startswith('3')):
            company_key = "AS"

        print("Check {0}P{1}".format(company_key, key))
        doc = frappe.db.exists("Project","{0}P{1}".format(company_key, key))
        if(doc == None):
            print("Create {0}P{1}".format(company_key, key))
            # create project 
            new_project = frappe.get_doc({
                "doctype": "Project",
                "project_key": key,
                "project_name": "{0}P{1}".format(company_key, key),
                "project_type": "Project",
                "is_active": "Yes",
                "status": "Open",
                "title": row['strProjectName']
            })
            new_project.insert()
        
    frappe.db.commit();
    con.close()
    

def get_connection():
    return pymssql.connect("192.168.80.25\Timesafe","sa","Websilas79","TimesafeBack")

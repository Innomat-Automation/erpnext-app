
import frappe
import json
from frappe import _



@frappe.whitelist()
def update_projects(data,invoice):
    jsondata = json.loads(data)
    
    project_list = []
    
    if "project" in jsondata.keys() and jsondata['project'] and jsondata['project'] != None:
        project = frappe.get_doc("Project", jsondata['project'])
        if project:
            project_list.append(jsondata['project'])
            frappe.db.sql("""UPDATE `tabPurchase Receipt Item` SET `project` = '{proj}' WHERE `parent` = '{name}' """.format(name=invoice, proj=jsondata['project']))
    
    for key,value in jsondata.items():
        if key == "project":
            continue
        if not value in project_list:
            project = frappe.get_doc("Project", value)
            if project:
                project_list.append(value)
            else:
                continue
       
        frappe.db.sql("""UPDATE `tabPurchase Receipt Item` SET `project` = '{proj}' WHERE `name` = '{name}' """.format(name=key, proj=value))
    
    for pro in project_list:
        project = frappe.get_doc("Project", pro)
        project.update_purchase_costing()
        project.db_update()
    
    return "Done"

@frappe.whitelist()
def delete_projects(invoice):
    project_list = frappe.db.sql("""SELECT project FROM `tabPurchase Receipt Item` WHERE `parent` = '{name}' AND NOT ISNULL(project)""".format(name=invoice),as_dict=1)
    
    frappe.db.sql("""UPDATE `tabPurchase Receipt Item` SET `project` = Null WHERE `parent` = '{name}' """.format(name=invoice))
    
    for pro in project_list:
        project = frappe.get_doc("Project", pro['project'])
        project.update_purchase_costing()
        project.db_update()
        
    return "Done"
    
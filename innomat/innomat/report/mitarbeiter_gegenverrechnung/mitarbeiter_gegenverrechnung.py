# Copyright (c) 2021, Innomat, Asprotec and libracore and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
import ast          # to parse str to dict (from JS calls)
from datetime import date

def execute(filters=None):
    columns = get_columns()
    data = get_data(filters)
    return columns, data

def get_columns():
    return [
        {"label": _("Emplyoee"), "fieldname": "employee", "fieldtype": "Link", "options": "Employee", "width": 80},
        {"label": _("Employee Name"), "fieldname": "employee_name", "width": 150},
        {"label": _("Company"), "fieldname": "company", "fieldtype": "Link", "options": "Company", "width": 100},
        {"label": _("Hours"), "fieldname": "hours", "fieldtype": "Float", "precision": 2, "width": 100}
    ]

@frappe.whitelist()
def get_data(filters):
    conditions = ""
    if type(filters) is str:
        filters = ast.literal_eval(filters)
    else:
        filters = dict(filters)
    
    sql_query = """
                SELECT 
                    `tabEmployee`.`name` AS `employee`,
                    `tabEmployee`.`employee_name` AS `employee_name`,
                    `tabProject`.`company` AS `company`,
                    SUM(`tabTimesheet Detail`.`hours`) AS `hours`,
                    CONCAT(`tabEmployee`.`name`, ":", `tabProject`.`company`) AS `key`
                FROM `tabEmployee`
                JOIN `tabTimesheet` ON `tabEmployee`.`name` = `tabTimesheet`.`employee`
                JOIN `tabTimesheet Detail` ON `tabTimesheet`.`name` =  `tabTimesheet Detail`.`parent`
                LEFT JOIN `tabProject` ON `tabTimesheet Detail`.`project` =  `tabProject`.`name`
                WHERE
                    `tabEmployee`.`company` = "{company}"
                    AND DATE(`tabTimesheet Detail`.`from_time`) >= "{from_date}"
                    AND DATE(`tabTimesheet Detail`.`from_time`) <= "{to_date}"
                    AND `tabTimesheet`.`docstatus` = 1
                    AND `tabTimesheet Detail`.`project` IS NOT NULL
                    AND `tabProject`.`company` != "{company}"
                GROUP BY `key`
                ;""".format(from_date=filters['from_date'], to_date=filters['to_date'], company=filters['company'])
    
    data = frappe.db.sql(sql_query, as_dict=True)
    
    # processing
    totals = {'hours': 0}
    for row in data:
        totals['hours'] += row['hours']
        
    data.append({
        'employee_name': "Total",
        'hours': totals['hours']
    })
        
    return data

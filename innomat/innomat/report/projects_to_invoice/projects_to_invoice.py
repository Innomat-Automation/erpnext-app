# Copyright (c) 2021, Innomat, Asprotec and libracore and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
import ast
from datetime import datetime, timedelta
from frappe.utils import cint

def execute(filters=None):
    columns = get_columns()
    data = get_data(filters)
    return columns, data

def get_columns():
    return [
        {"label": _("Project"), "fieldname": "project", "fieldtype": "Link", "options": "Project", "width": 120},

    ]

def get_data(filters):
    if type(filters) is str:
        filters = ast.literal_eval(filters)
    else:
        filters = dict(filters)
    # get additional conditions
    conditions = ""
    if 'company' in filters and filters['company']:
        conditions += """ AND `tabProject`.`company` = "{0}" """.format(filters['company'])
    
    # prepare query
    sql_query = """SELECT 
            `name` AS `project`
          FROM `tabProject`
          WHERE `tabProject`.`status` = 1
          {conditions}
        ORDER BY `tabProject`.`name` ASC;
      """.format(conditions=conditions)
    
    data = frappe.db.sql(sql_query, as_dict=True)

    return data

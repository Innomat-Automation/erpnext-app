# Copyright (c) 2021, Innomat, Asprotec and libracore and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
import ast
from datetime import datetime, timedelta
from frappe.utils import cint
from innomat.innomat.scripts.task import get_holidays

def execute(filters=None):
    # parse filters to a dict
    if type(filters) is str:
        filters = ast.literal_eval(filters)
    else:
        filters = dict(filters)
    # gather columns and data
    columns = get_columns(filters)
    data = get_data(filters)
    return columns, data

def get_columns(filters):
    # first column: user names
    columns = [
        {"label": _("User"), "fieldname": "user", "fieldtype": "Link", "options": "User", "width": 120}
    ]
    # further columns (pivot): dates
    date = datetime.strptime(filters['from_date'], "%Y-%m-%d")
    end_date = datetime.strptime(filters['to_date'], "%Y-%m-%d")
    company = frappe.defaults.get_global_default('company')
    holidays = get_holidays(company)
    while date <= end_date:
        if "{0}".format(date.date()) not in holidays:
            columns.append(
                {
                    "label": date.date(), 
                    "fieldname": ("{0}".format(date.date())).replace("-", "_"), 
                    "fieldtype": "Data", 
                    "width": 150 if "show_tasks" in filters and filters['show_tasks'] == 1 else 85
                }
            )
        date += timedelta(days=1)
        
    return columns

def get_data(filters):
    # get additional conditions
    conditions = ""
    if 'project' in filters and filters['project']:
        conditions += """ AND `tabTask`.`project` = "{0}" """.format(filters['project'])
    # date range
    date = datetime.strptime(filters['from_date'], "%Y-%m-%d")
    end_date = datetime.strptime(filters['to_date'], "%Y-%m-%d")
    
    # prepare users (all users who have a task in the selected period):
    users = frappe.db.sql("""
        SELECT `tabTask`.`completed_by` AS `user`
        FROM `tabTask`
        WHERE `tabTask`.`exp_end_date` >= "{start_date}"
          AND `tabTask`.`exp_start_date` <= "{end_date}"
          AND `tabTask`.`status` IN ("Open", "Working", "Overdue")
          {conditions}
        GROUP BY `tabTask`.`completed_by`
        ORDER BY `tabTask`.`completed_by`
    ;""".format(start_date=filters['from_date'], end_date=filters['to_date'], conditions=conditions), as_dict = True)
    
    data = []
    for user in users:
        user_planning = {'user': user['user']}
        
        # generate data per user (row)
        date = datetime.strptime(filters['from_date'], "%Y-%m-%d")
        while date <= end_date:
            if "show_tasks" in filters and filters['show_tasks'] == 1:
                # task view
                tasks = frappe.db.sql("""
                    SELECT IFNULL(GROUP_CONCAT(
                        CONCAT_WS(' ',
                            CONCAT('<a href=\"#Form/Project/',`tabTask`.`project`,'\" title=\"',`tabProject`.`title`,'\" data-doctype=\"Project\">',`tabTask`.`project`,'</a>') ,
                            CONCAT('<a href=\"#Form/Task/',`tabTask`.`name`,'\" title=\"',`tabTask`.`name`,'\" data-doctype=\"Task\">',`tabTask`.`subject`,'</a>')
                        ) 
                    SEPARATOR '<br/>'), "-") AS `task`
                    FROM `tabTask`
                    LEFT JOIN `tabProject` ON `tabProject`.project_name = `tabTask`.project
                    WHERE `tabTask`.`exp_end_date` >= "{date}"
                      AND `tabTask`.`exp_start_date` <= "{date}"
                      AND `tabTask`.`completed_by` = "{user}"
                      AND `tabTask`.`status` IN ("Open", "Working", "Overdue")
                      {conditions}
                ;""".format(date=date.date(), conditions=conditions, user= user['user']), as_dict = True)
                user_planning[("{0}".format(date.date())).replace("-", "_")] = tasks[0]['task']
            else:
                # load view
                load = frappe.db.sql("""
                    SELECT IFNULL(SUM(`tabTask`.`fte`), 0) AS `load`
                    FROM `tabTask`
                    WHERE `tabTask`.`exp_end_date` >= "{date}"
                      AND `tabTask`.`exp_start_date` <= "{date}"
                      AND `tabTask`.`completed_by` = "{user}"
                      AND `tabTask`.`status` IN ("Open", "Working", "Overdue")
                      {conditions}
                ;""".format(date=date.date(), conditions=conditions, user= user['user']), as_dict = True)
                color = "green"
                if load[0]['load'] == 0:
                    color = "blue"
                else:
                    if load[0]['load'] >= 0.8:
                        color = "orange"
                    if load[0]['load'] >= 1:
                        color = "red"
                content = """
                    <span style="color: {color}; ">
                    {load}
                    </span>
                """.format(load=round(load[0]['load'], 3), color=color)
                user_planning[("{0}".format(date.date())).replace("-", "_")] = content
            date += timedelta(days=1)
        # append new row
        data.append(user_planning)
    
    return data

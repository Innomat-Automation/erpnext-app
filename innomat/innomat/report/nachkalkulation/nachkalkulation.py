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
        {"label": _("Project"), "fieldname": "project", "fieldtype": "Link", "options": "Project", "width": 100},
        {"label": _("Project Name"), "fieldname": "project_name", "width": 200},
        {"label": _("Project manager name"), "fieldname": "project_manager_name", "fieldtype": "Data", "width": 100},
        {"label": _("Status Light"), "fieldname": "status_light", "fieldtype": "Data", "width": 100},
        {"label": _("Start Date"), "fieldname": "start_date", "fieldtype": "Date", "width": 80},
        {"label": _("End Date"), "fieldname": "end_date", "fieldtype": "Date", "width": 80},
        #{"label": _("Progress (time)"), "fieldname": "progress_time", "fieldtype": "Percent", "width": 100},   # only requried for project status
        #{"label": _("Progress (tasks)"), "fieldname": "progress_tasks", "fieldtype": "Percent", "width": 100}, # only requried for project status
        {"label": _("Material (plan)"), "fieldname": "planned_material_cost", "fieldtype": "Currency", "width": 100},
        {"label": _("Material (used)"), "fieldname": "actual_material_cost", "fieldtype": "Currency", "width": 100},
        {"label": _("Hours flat (plan)"), "fieldname": "planned_hours", "fieldtype": "Float", "width": 100},
        {"label": _("Hours flat (used)"), "fieldname": "hours_flat", "fieldtype": "Float", "width": 100},
        {"label": _("Hours by effort"), "fieldname": "hours_effective", "fieldtype": "Float", "width": 100},
        {"label": _("Hours budget"), "fieldname": "stundenbudget_plan", "fieldtype": "Currency", "width": 100},
        {"label": _("Hours consumed"), "fieldname": "stundenbudget_aktuell", "fieldtype": "Currency", "width": 100}
    ]

@frappe.whitelist()
def get_data(filters):
    conditions = ""
    if type(filters) is str:
        filters = ast.literal_eval(filters)
    else:
        filters = dict(filters)
    if 'project_manager' in filters:
        conditions += """ AND `tabProject`.`project_manager` = '{project_manager}'""".format(project_manager=filters['project_manager'])
    if 'project_manager_name' in filters:
        conditions += """ AND `tabProject`.`project_manager_name` LIKE '%{project_manager_name}%'""".format(project_manager_name=filters['project_manager_name'])
    if 'customer' in filters:
        conditions = """ AND `tabProject`.`customer` = '{customer}'""".format(customer=filters['customer'])
    
    sql_query = """SELECT 
                    `tabProject`.`name` AS `project`,
                    `tabProject`.`title` AS `project_name`,
                    `tabProject`.`project_manager` AS `project_manager`,
                    `tabProject`.`project_manager_name` AS `project_manager_name`,
                    `tabProject`.`finished` AS `finished`,
                    `tabProject`.`status_light` AS `status_light`,
                    `tabProject`.`expected_start_date` AS `start_date`,
                    `tabProject`.`expected_end_date` AS `end_date`,
                    (SELECT IFNULL(SUM(`tabTask`.`expected_time`) , 0)
                     FROM `tabTask` 
                     WHERE `tabTask`.`project` = `tabProject`.`name`) AS `project_expected_time`,
                    IFNULL(`tabProject`.`planned_material_cost`, 0) AS `planned_material_cost`,
                    IFNULL(`tabProject`.`actual_material_cost`, 0) AS `actual_material_cost`,
                    IFNULL(`tabProject`.`planned_hours`, 0) AS `planned_hours`,
                    (SELECT IFNULL(SUM(`tabTimesheet Detail`.`hours`), 0)
                     FROM `tabTimesheet Detail`
                     WHERE `tabTimesheet Detail`.`docstatus` = 1
                       AND `tabTimesheet Detail`.`project` = `tabProject`.`name`
                       AND `tabTimesheet Detail`. `by_effort` = 0) AS `hours_flat`,
                    (SELECT IFNULL(SUM(`tabTimesheet Detail`.`hours`), 0)
                     FROM `tabTimesheet Detail`
                     WHERE `tabTimesheet Detail`.`docstatus` = 1
                       AND `tabTimesheet Detail`.`project` = `tabProject`.`name`
                       AND `tabTimesheet Detail`. `by_effort` = 1) AS `hours_effective`,
                    `tabProject`.`stundenbudget_plan` AS `stundenbudget_plan`,
                    `tabProject`.`stundenbudget_aktuell` AS `stundenbudget_aktuell`
                FROM `tabProject`
                WHERE 
                  `tabProject`.`status` = "Open" 
                  {conditions}
                ;""".format(
              conditions=conditions)
    
    data = frappe.db.sql(sql_query, as_dict=True)
    
    # processing
    for row in data:
        if row['end_date'] and row['start_date']:
            duration_days = (row['end_date'] - row['start_date']).days
            if duration_days == 0:
                duration_days = 1
            expired_days = (date.today() - row['start_date']).days
            progress_time = 100 * expired_days / duration_days
            row['progress_time'] = progress_time
        if row['project_expected_time']:
            row['progress_tasks'] = 100 * (row['hours_flat'] or 0) / row['project_expected_time']
        
    return data

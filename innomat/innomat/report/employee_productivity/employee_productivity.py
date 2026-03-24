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
        {"label": _("Employee"), "fieldname": "employee", "fieldtype": "Link", "options": "Employee", "width": 200},
        {"label": _("Department"), "fieldname": "department", "fieldtype": "Link", "options": "Department", "width": 100},
        {"label": _("Total hours"), "fieldname": "total_hours", "fieldtype": "Float", "precision": 3, "width": 100},
        {"label": _("Project hours"), "fieldname": "project_hours", "fieldtype": "Float", "precision": 3, "width": 100},
        {"label": _("Productivity"), "fieldname": "productivity", "fieldtype": "Percent", "width": 100},
        {"label": _("Total hours YTD"), "fieldname": "total_hours_ytd", "fieldtype": "Float", "precision": 3, "width": 120},
        {"label": _("Project hours YTD"), "fieldname": "project_hours_ytd", "fieldtype": "Float", "precision": 3, "width": 140},
        {"label": _("Productivity YTD"), "fieldname": "productivity_ytd", "fieldtype": "Percent", "width": 120}
    ]

@frappe.whitelist()
def get_data(filters):
    filters = frappe._dict(filters or {})
    conditions = ""
    company = filters.company or '%'
    department = filters.department or '%'
    year = str(filters.to_date)[:4]
    default_projects = frappe.get_list("Cost Center", {'default_project'}, {'default_project':['is','set']})
    default_projects = [dp.default_project for dp in default_projects]

    sql_query = """
                SELECT
                    `details`.`employee` AS `employee`,
                    `details`.`employee_name` AS `employee_name`,
                    `details`.`department` AS `department`,
                    SUM(`details`.`hours`) AS `total_hours`,
                    SUM(`details`.`project_hours`) AS `project_hours`,
                    IFNULL((SELECT SUM(`TSD1`.`hours`)
                     FROM `tabTimesheet Detail` AS `TSD1`
                     INNER JOIN `tabTimesheet` AS `TS1` ON `TS1`.`name` = `TSD1`.`parent`
                     WHERE DATE(`TSD1`.`to_time`) >= "{year}-01-01"
                        AND DATE(`TSD1`.`to_time`) <= "{to_date}"
                        -- Timesheet company filter removed (MZ 2026-03-12) - this is about employee productivity and any work an employee does, also for third parties, should be included
                        -- AND `TS1`.`company` LIKE "{company}"
                        AND `TS1`.`docstatus` = 1
                        AND `TS1`.`employee` = `details`.`employee`), 0) AS `total_hours_ytd`,
                    IFNULL((SELECT SUM(`TSD2`.`hours`)
                     FROM `tabTimesheet Detail` AS `TSD2`
                     INNER JOIN `tabTimesheet` AS `TS2` ON `TS2`.`name` = `TSD2`.`parent`
                     WHERE DATE(`TSD2`.`to_time`) >= "{year}-01-01"
                        AND DATE(`TSD2`.`to_time`) <= "{to_date}"
                        -- Timesheet company filter removed (MZ 2026-03-12) - this is about employee productivity and any work an employee does, also for third parties, should be included
                        -- AND `TS2`.`company` LIKE "{company}"
                        AND `TS2`.`docstatus` = 1
                        AND `TS2`.`employee` = `details`.`employee`
                        AND `TSD2`.`project` IS NOT NULL
                        AND `TSD2`.`project` NOT IN {default_projects}), 0) AS `project_hours_ytd`
                FROM (
                   SELECT
                    `tabTimesheet`.`employee` AS `employee`,
                    `tabEmployee`.`employee_name` AS `employee_name`,
                    `tabEmployee`.`department` AS `department`,
                    `tabTimesheet Detail`.`hours` AS `hours`,
                    `tabTimesheet Detail`.`hours` * (IF(`tabTimesheet Detail`.`project` IS NULL OR `tabTimesheet Detail`.`project` IN {default_projects}, 0, 1)) AS `project_hours`
                   FROM `tabTimesheet Detail`
                   INNER JOIN `tabTimesheet` ON `tabTimesheet`.`name` = `tabTimesheet Detail`.`parent`
                   LEFT JOIN `tabEmployee` ON `tabTimesheet`.`employee` = `tabEmployee`.`name`
                   WHERE DATE(`tabTimesheet Detail`.`to_time`) >= "{from_date}"
                    AND DATE(`tabTimesheet Detail`.`to_time`) <= "{to_date}"
                    -- The employees are OK to be filtered by company/dept.
                    AND `tabTimesheet`.`company` LIKE "{company}"
                    AND `tabTimesheet`.`docstatus` = 1
                    AND `tabEmployee`.`department` LIKE "{department}"
                ) AS `details`
                GROUP BY `details`.`employee`
                ;""".format(from_date=filters.from_date, to_date=filters.to_date, company=company, department=department, year=year, default_projects=str(tuple(default_projects)))

    data = frappe.db.sql(sql_query, as_dict=True)

    # processing
    totals = {'hours': 0, 'project_hours': 0, 'hours_ytd': 0, 'project_hours_ytd': 0}
    for row in data:
        totals['hours'] += row['total_hours']
        totals['project_hours'] += row['project_hours']
        totals['hours_ytd'] += row['total_hours_ytd']
        totals['project_hours_ytd'] += row['project_hours_ytd']
        row['productivity'] = ((100 * row['project_hours']) / row['total_hours']) if row['total_hours'] != 0 else 0
        row['productivity_ytd'] = ((100 * row['project_hours_ytd']) / row['total_hours_ytd']) if row['total_hours_ytd'] != 0 else 0

    data.append({
        'employee_name': "Total",
        'total_hours': totals['hours'],
        'project_hours': totals['project_hours'],
        'productivity': ((100 * totals['project_hours']) / totals['hours']) if totals['hours'] != 0 else 0,
        'total_hours_ytd': totals['hours_ytd'],
        'project_hours_ytd': totals['project_hours_ytd'],
        'productivity_ytd': ((100 * totals['project_hours_ytd']) / totals['hours_ytd']) if totals['hours_ytd'] != 0 else 0
    })

    return data

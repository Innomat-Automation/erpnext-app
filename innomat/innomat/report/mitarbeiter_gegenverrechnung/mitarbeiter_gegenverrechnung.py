# Copyright (c) 2021, Innomat, Asprotec and libracore and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from datetime import date
from innomat.innomat.scripts.project import get_fallback_cost_supplements

def get_columns():
    columns = [
        {"label": _("Mitarbeiter"), "fieldname": "employee", "fieldtype": "Link", "options": "Employee", "width": 220},
        {"label": _("Abteilung"), "fieldname": "department", "fieldtype": "Link", "options": "Department", "width": 100},
        {"label": _("Int. Stundensatz MA"), "fieldname": "internal_rate_per_hour", "fieldtype": "Currency", "width": 150},
        {"label": _("ILV-Satz des MA"), "fieldname": "ilv_rate", "fieldtype": "Currency", "width": 120},
    ]
    return columns

def execute(filters=None):
    filters = frappe._dict(filters or {})
    columns = get_columns()
    fallback_gk, fallback_vvgk = get_fallback_cost_supplements(None, filters.company)
    data = []
    # NOTE - We could filter by status='Active' here, but we really should not.
    #        We want to show all relevant work time in the selected time period, irrespective of whether the employees who did the work are still in the company or not.
    employees = frappe.get_all("Employee", {'name AS employee','employee_name','internal_rate_per_hour','department'}, {'company':filters.company}, order_by='employee_name')
    totals = {'employee_name': _("Total")}
    for e in employees:
        e.ilv_rate = e.internal_rate_per_hour * (1 + 0.01 * fallback_gk) * (1 + 0.01 * fallback_vvgk)
        if e.department:
            employee_cc = frappe.get_value("Department", e.department, "default_cost_center")
        else:
            employe_cc = ""
        employee_rows = frappe.db.sql("""
                    SELECT
                        SUM(`tabTimesheet Detail`.`hours`) AS `hours`,
                        SUM( `tabTimesheet Detail`.`hours` * IFNULL(NULLIF(`tabTimesheet`.`internal_rate_per_hour`, 0), {fallback_rate}) *
                         (1.0 + 0.01 * IFNULL(NULLIF(`tabTimesheet`.`cost_supplement_gk`, 0), {fallback_gk})) *
                         (1.0 + 0.01 * IFNULL(NULLIF(`tabTimesheet`.`cost_supplement_vvgk`, 0), {fallback_vvgk})) ) AS `hours_ilv`,
                        CONCAT(`tabProject`.`company`, " - ", IFNULL(SUBSTRING_INDEX(`tabTimesheet Detail`.`cost_center`,' - ', 1), 'Ohne KS')) AS `key`
                    FROM `tabTimesheet`
                    INNER JOIN `tabTimesheet Detail` ON `tabTimesheet`.`name` =  `tabTimesheet Detail`.`parent`
                    LEFT JOIN `tabCost Center` ON `tabTimesheet Detail`.`cost_center` = `tabCost Center`.`name`
                    LEFT JOIN `tabProject` ON `tabTimesheet Detail`.`project` =  `tabProject`.`name`
                    WHERE
                        `tabTimesheet`.`employee` = "{employee}"
                        AND DATE(`tabTimesheet Detail`.`from_time`) >= "{from_date}"
                        AND DATE(`tabTimesheet Detail`.`from_time`) <= "{to_date}"
                        AND `tabTimesheet`.`docstatus` = 1
                        AND `tabTimesheet Detail`.`project` IS NOT NULL
                        AND (`tabProject`.`company` != "{company}" OR IFNULL(`tabTimesheet Detail`.`cost_center`, "{cost_center}") != "{cost_center}")
                    GROUP BY `key`
                    ;""".format(from_date=filters.from_date, to_date=filters.to_date, employee=e.employee, company=filters.company, cost_center=employee_cc, fallback_rate=e.internal_rate_per_hour, fallback_gk=fallback_gk, fallback_vvgk=fallback_vvgk), as_dict=True)
        if len(employee_rows) > 0:
            for row in employee_rows:
                hours_key = row.key + ': '+_("Stunden")
                ilv_key = row.key + ': '+_("Betrag ILV")
                if row.hours > 0 and totals.get(hours_key) == None:
                    columns.extend([
                        {"label": hours_key.replace(" - ","<br>"), "fieldname": hours_key, "fieldtype": "Float", "width": 160},
                        {"label": ilv_key.replace(" - ","<br>"), "fieldname": ilv_key, "fieldtype": "Currency", "width": 160},
                    ])
                e[hours_key] = row.hours
                e[ilv_key] = row.hours_ilv
                totals[hours_key] = totals.get(hours_key, 0) + row.hours
                totals[ilv_key] = totals.get(ilv_key, 0) + row.hours_ilv
            data.append(e)

    data.append(totals)

    return columns, data

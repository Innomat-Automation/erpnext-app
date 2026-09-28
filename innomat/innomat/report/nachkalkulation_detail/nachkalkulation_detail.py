# Copyright (c) 2026, Innomat, Asprotec and libracore and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
import ast
from innomat.innomat.scripts.project import get_project_material_cost, get_project_service_cost, get_expense_claims_cost


def execute(filters=None):
    columns = get_columns()
    data = get_data(filters)
    return columns, data


def get_columns():
    return [
        {"label": _("Projekt"), "fieldname": "project", "fieldtype": "Link", "options": "Project", "width": 90},
        {"label": _("Projekt / Mitarbeiter"), "fieldname": "description", "fieldtype": "Data", "width": 240},
        {"label": _("Abrechnungsart"), "fieldname": "billing_type", "fieldtype": "Data", "width": 100},
        {"label": _("Stunden"), "fieldname": "hours", "fieldtype": "Float", "width": 90},
        {"label": _("Stunden Budget"), "fieldname": "hours_budget", "fieldtype": "Float", "width": 100},
        {"label": _("Personalkosten (DK)"), "fieldname": "labor_cost", "fieldtype": "Currency", "width": 130},
        {"label": _("Materialkosten"), "fieldname": "material_cost", "fieldtype": "Currency", "width": 110},
        {"label": _("Materialkosten Budget"), "fieldname": "material_cost_budget", "fieldtype": "Currency", "width": 130},
        {"label": _("Fremdleistungen"), "fieldname": "third_party_services", "fieldtype": "Currency", "width": 120},
        {"label": _("Spesen"), "fieldname": "expenses", "fieldtype": "Currency", "width": 100},
        {"label": _("Direktkosten Total"), "fieldname": "total_direct_cost", "fieldtype": "Currency", "width": 130},
        {"label": _("Ertrag (Rechnungen, netto)"), "fieldname": "revenue", "fieldtype": "Currency", "width": 140},
        {"label": _("Ergebnis (Ertrag - Direktkosten)"), "fieldname": "result", "fieldtype": "Currency", "width": 160},
    ]


@frappe.whitelist()
def get_data(filters):
    if isinstance(filters, str):
        filters = ast.literal_eval(filters)
    else:
        filters = dict(filters or {})

    projects = filters.get('projects') or []
    if isinstance(projects, str):
        # comes in as a comma separated string when passed as a URL parameter
        projects = [p.strip() for p in projects.split(',') if p.strip()]

    output = []
    for project in projects:
        project_info = frappe.db.get_value("Project", project,
            ["title", "status", "planned_material_cost", "planned_hours", "planned_hours_by_effort"], as_dict=True)
        if not project_info:
            continue

        material_cost = get_project_material_cost(project) or 0
        thirdparty_cost = get_project_service_cost(project) or 0
        expense_cost = get_expense_claims_cost(project) or 0
        employee_rows = get_employee_labor_costs(project)

        total_hours = sum(row['hours'] or 0 for row in employee_rows)
        total_labor_cost = sum(row['direct_cost'] or 0 for row in employee_rows)
        hours_budget = (project_info['planned_hours'] or 0) + (project_info['planned_hours_by_effort'] or 0)
        material_cost_budget = project_info['planned_material_cost'] or 0
        revenue = get_project_revenue(project) or 0
        total_direct_cost = material_cost + thirdparty_cost + expense_cost + total_labor_cost

        output.append({
            "project": project,
            "description": "{0} ({1})".format(project_info['title'], _(project_info['status'])),
            "billing_type": '',
            "hours": total_hours,
            "hours_budget": hours_budget,
            "labor_cost": total_labor_cost,
            "material_cost": material_cost,
            "material_cost_budget": material_cost_budget,
            "third_party_services": thirdparty_cost,
            "expenses": expense_cost,
            "total_direct_cost": total_direct_cost,
            "revenue": revenue,
            "result": revenue - total_direct_cost,
            "indent": 0
        })

        for row in employee_rows:
            output.append({
                "project": '',
                "description": row['employee_name'] or row['employee'] or _("Ohne Mitarbeiter"),
                "billing_type": _("Nach Aufwand") if row['by_effort'] else _("Pauschal"),
                "hours": row['hours'],
                "hours_budget": '',
                "labor_cost": row['direct_cost'],
                "material_cost": '',
                "material_cost_budget": '',
                "third_party_services": '',
                "expenses": '',
                "total_direct_cost": '',
                "revenue": '',
                "result": '',
                "indent": 1
            })

    return output


# Verrechneter Ertrag (netto, ohne MwSt.) aus submitteten Sales Invoices - identisch zur Berechnung von Project.total_billed_amount
def get_project_revenue(project):
    return frappe.db.sql("""SELECT IFNULL(SUM(`base_net_total`), 0) AS `revenue`
            FROM `tabSales Invoice`
            WHERE `tabSales Invoice`.`docstatus` = 1
              AND `tabSales Invoice`.`project` = %(project)s
        ;""", {"project": project}, as_dict=True)[0]['revenue']


# Personalkosten (Direktkosten) gruppiert nach Mitarbeiter und Abrechnungsart, nur aus submitteten Timesheets
def get_employee_labor_costs(project):
    return frappe.db.sql("""SELECT
                `tabEmployee`.`name` AS `employee`,
                `tabEmployee`.`employee_name` AS `employee_name`,
                `tabTimesheet Detail`.`by_effort` AS `by_effort`,
                SUM(`tabTimesheet Detail`.`hours`) AS `hours`,
                SUM(`tabTimesheet Detail`.`hours` * IFNULL(NULLIF(`tabTimesheet`.`internal_rate_per_hour`, 0), `tabEmployee`.`internal_rate_per_hour`)) AS `direct_cost`
            FROM `tabTimesheet Detail`
            LEFT JOIN `tabTimesheet` ON `tabTimesheet`.`name` = `tabTimesheet Detail`.`parent`
            LEFT JOIN `tabEmployee` ON `tabEmployee`.`name` = `tabTimesheet`.`employee`
            WHERE `tabTimesheet`.`docstatus` = 1
              AND `tabTimesheet Detail`.`project` = %(project)s
            GROUP BY `tabEmployee`.`name`, `tabTimesheet Detail`.`by_effort`
            ORDER BY `tabEmployee`.`employee_name`, `tabTimesheet Detail`.`by_effort`
        ;""", {"project": project}, as_dict=True)

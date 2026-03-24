# Copyright (c) 2021, Innomat, Asprotec and libracore and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
import ast          # to parse str to dict (from JS calls)
from datetime import date
from innomat.innomat_reporting.kpi import get_project_kpis

def execute(filters=None):
    columns = get_columns()
    data = get_data(filters)
    return columns, data

def get_columns():
    return [
        {"label": _("Projekt"), "fieldname": "project", "fieldtype": "Link", "options": "Project", "width": 80},
        {"label": _("Projektname / Status"), "fieldname": "project_name", "width": 260},
        {"label": _("Projektleiter"), "fieldname": "project_manager_name", "fieldtype": "Data", "width": 100},
        {"label": _("Ampel"), "fieldname": "status_light", "fieldtype": "Data", "width": 60},
        {"label": _("Startdatum"), "fieldname": "start_date", "fieldtype": "Date", "width": 90},
        {"label": _("Enddatum"), "fieldname": "end_date", "fieldtype": "Date", "width": 80},
        {"label": _("Werte"), "fieldname": "budget_vs_actual", "fieldtype": "Data", "width": 80},
        {"label": _("Materialkosten"), "fieldname": "material_cost", "fieldtype": "Currency", "width": 110},
        {"label": _("Fremdleistungen"), "fieldname": "third_party_services", "fieldtype": "Currency", "width": 120},
        {"label": _("Spesen"), "fieldname": "expenses", "fieldtype": "Currency", "width": 120},
        {"label": _("Std pauschal"), "fieldname": "hours_flat", "fieldtype": "Float", "width": 100},
        {"label": _("Std n.Aufwand"), "fieldname": "hours_by_effort", "fieldtype": "Float", "width": 110},
        {"label": _("Personalaufwand (DK)"), "fieldname": "labor_cost", "fieldtype": "Currency", "width": 150},
        {"label": _("Direktkosten"), "fieldname": "direct_cost", "fieldtype": "Currency", "width": 100},
        {"label": _("Selbstkosten"), "fieldname": "prime_cost", "fieldtype": "Currency", "width": 100},
        {"label": _("Ertrag"), "fieldname": "revenue", "fieldtype": "Currency", "width": 100},
        {"label": _("EBIT"), "fieldname": "ebit", "fieldtype": "Currency", "width": 100},
        {"label": _("EBIT ΔFC-BU"), "fieldname": "ebit_delta", "fieldtype": "Currency", "width": 100},
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
        conditions += """ AND `tabProject`.`customer` = '{customer}'""".format(customer=filters['customer'])
    if 'status' in filters:
        conditions += """ AND `tabProject`.`status` = '{status}'""".format(status=filters['status'])
    if 'status_light' in filters and filters['status_light'] != '⚪':
        # For some reason the SQL comparison doesn't compare all bytes of the emoji, so use base64 as workaround
        # (Perhaps the issue is that the collation of the connection and/or tables is utf8_general_ci instead of utf8mb4_unicode_ci - in any case this appears to work.)
        conditions += """ AND TO_BASE64(`tabProject`.`status_light`) = TO_BASE64('{status}')""".format(status=filters['status_light'])
    if 'year' in filters:
        conditions += """AND (YEAR(expected_start_date) = '{year}' OR YEAR(expected_end_date) = '{year}' OR (YEAR(expected_end_date) = ('{year}' - 1) AND status !='Completed'))""".format(year=filters['year'])

    sql_query = """SELECT
                    `tabProject`.`name` AS `project`,
                    `tabProject`.`title` AS `project_name`,
                    `tabProject`.`project_manager` AS `project_manager`,
                    `tabProject`.`project_manager_name` AS `project_manager_name`,
                    `tabProject`.`status` AS `status`,
                    `tabProject`.`status_light` AS `status_light`,
                    `tabProject`.`expected_start_date` AS `start_date`,
                    `tabProject`.`expected_end_date` AS `end_date`
                FROM `tabProject`
                WHERE
                  1
                  {conditions}
                ORDER BY
                  `tabProject`.`name`
                ;""".format(
              conditions=conditions)

    data = frappe.db.sql(sql_query, as_dict=True)

    # processing
    output = []
    for row in data:
        kpi = get_project_kpis(row['project'])
        forecast_row = {
            "project": row['project'],
            "project_name": row['project_name'][10:],
            "project_manager_name": row['project_manager_name'],
            "status_light": row['status_light'],
            "start_date": row['start_date'],
            "end_date": row['end_date'],
            "budget_vs_actual": _("FORECAST"),
            "material_cost": kpi.material_forecast(),
            "third_party_services": kpi.thirdparty_forecast(),
            "expenses": kpi.expenses_forecast(),
            "hours_flat": kpi.total_hours_forecast(),
            "hours_by_effort": kpi.total_hours_by_effort_forecast(),
            "labor_cost": kpi.labor_direct_cost_forecast() + kpi.labor_direct_cost_by_effort_forecast(),
            "direct_cost": kpi.direct_cost_forecast(),
            "prime_cost": kpi.prime_cost_forecast(),
            "revenue": kpi.revenue_forecast(),
            "ebit": kpi.ebit_forecast(),
            "ebit_delta": kpi.ebit_forecast() - kpi.ebit_budget(),
        }
        actual_row = {
            "project": '',
            "project_name": _(row['status']),
            "project_manager_name": '',
            "status_light": '',
            "start_date": '',
            "end_date": '',
            "budget_vs_actual": _("IST"),
            "material_cost": kpi.material_current(),
            "third_party_services": kpi.thirdparty_current(),
            "expenses": kpi.expenses_current(),
            "hours_flat": kpi.total_hours_current(),
            "hours_by_effort": kpi.total_hours_by_effort_current(),
            "labor_cost": kpi.labor_direct_cost_current() + kpi.labor_direct_cost_by_effort_current(),
            "direct_cost": kpi.direct_cost_current(),
            "prime_cost": kpi.prime_cost_current(),
            "revenue": kpi.revenue_current(),
            "ebit": kpi.ebit_current(),
            "ebit_delta": '',
        }
        budget_row = {
            "project": '',
            "project_name": '',
            "project_manager_name": '',
            "status_light": '',
            "start_date": '',
            "end_date": '',
            "budget_vs_actual": _("BUDGET"),
            "material_cost": kpi.material_budget(),
            "third_party_services": kpi.thirdparty_budget(),
            "expenses": kpi.expenses_budget() or '',
            "hours_flat": kpi.total_hours_budget(),
            "hours_by_effort": kpi.total_hours_by_effort_budget(),
            "labor_cost": kpi.labor_direct_cost_budget() + kpi.labor_direct_cost_by_effort_budget(),
            "direct_cost": kpi.direct_cost_budget(),
            "prime_cost": kpi.prime_cost_budget(),
            "revenue": kpi.revenue_budget(),
            "ebit": kpi.ebit_budget(),
            "ebit_delta": '',
        }
        output.append(forecast_row)
        output.append(actual_row)
        output.append(budget_row)

    return output

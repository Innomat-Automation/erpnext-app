# Copyright (c) 2013, Innomat, Asprotec and libracore and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.utils import add_years
import datetime
from innomat.innomat_reporting.report.auftragseingang.auftragseingang import get_sales_total_and_count
from innomat.innomat.scripts.project import get_fallback_cost_supplements
from innomat.innomat_reporting.kpi import get_project_kpis

#WORK_HOURS_PER_YEAR = 41 * 52 * 0.83
#WORK_HOURS_PER_MONTH = WORK_HOURS_PER_YEAR / 12

def get_columns():
    return [
        {"label": _("Kostenstelle"), "fieldname": "name", "fieldtype": "Data", "width": 120},
        {"label": _("Auftragssumme / Erlös Plan"), "fieldname": "revenue", "fieldtype": "Currency", "width": 200},
        {"label": _("Selbstkosten Ist"), "fieldname": "prime_cost", "fieldtype": "Currency", "width": 150},
        {"label": _("Arbeitsvorrat CHF"), "fieldname": "backlog_chf", "fieldtype": "Currency", "width": 150},
        {"label": _("Arbeitsvorrat Monate"), "fieldname": "backlog_mon", "fieldtype": "Float", "width": 150},
    ]

# NOTE - Dieser Bericht funktioniert nicht rückwirkend und hat deshalb auch keinen variablen Datumsfilter
#        (Zu einem Stichdatum zu ermitteln, welche Projekte dann unfertig waren und was die Selbstkosten "IST" aller Projekte zu diesem Datum waren, wäre viel aufwändiger und bedingt insbesondere ein Feld "completion date" auf dem Projekt)

def execute(filters=None):
    columns = get_columns()
    company = filters.company
    # We cannot support a date filter at this time as we don't have project prime cost data available for past dates
    date = datetime.date.today()
    one_year_ago = add_years(date, -1)
    fallback_gk, fallback_vvgk = get_fallback_cost_supplements(None, company)

    cost_centers = frappe.get_all("Cost Center", filters={'company': company, 'parent_cost_center': ['is','set']}, order_by='name')
    overall = {}
    for cc in cost_centers:
        past_year_sales, dummy = get_sales_total_and_count(cc['name'], one_year_ago, date)
        cc['avg_monthly_sales'] = past_year_sales / 12

        open_projects = frappe.get_all("Project", filters={'cost_center': cc['name'], 'company': company, 'status': ['NOT IN', ['Completed','Cancelled']]})
        cc['revenue'] = 0
        cc['prime_cost'] = 0
        cc['backlog_chf'] = 0
        for p in open_projects:
            kpi = get_project_kpis(p['name'])
            cc['revenue'] += kpi.revenue_budget()
            cc['prime_cost'] += kpi.prime_cost_flat_current()
            cc['backlog_chf'] += kpi.backlog()
        # Calculate months from average monthly sales rather than via hours as it's less reliable and more complicated to calculate monthly total work hours across a cost center's employees
        cc['backlog_mon'] = cc['backlog_chf'] / cc['avg_monthly_sales'] if cc['avg_monthly_sales'] != 0 else 0
    overall = { col: sum(cc[col] for cc in cost_centers) for col in ['revenue', 'prime_cost', 'backlog_chf', 'avg_monthly_sales'] }
    overall['name'] = _("Total")
    overall['backlog_mon'] = overall['backlog_chf'] / overall['avg_monthly_sales']
    cost_centers.append(overall)

    return columns, cost_centers
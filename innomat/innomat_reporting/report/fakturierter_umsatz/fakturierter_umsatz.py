# Copyright (c) 2025, Innomat, libracore and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from datetime import date, datetime

def execute(filters=None):
    if not filters:
        filters = {}

    # Parse selected date, default to today
    reference_date = filters.get("reference_date")
    if reference_date:
        reference_date = datetime.strptime(reference_date, "%Y-%m-%d").date()
    else:
        reference_date = date.today()

    columns = get_columns()
    data = get_data(filters, reference_date)

    return columns, data


def get_columns():
    return [
        {"label": _("Cost Center / Project Type"), "fieldname": "group_label", "fieldtype": "Data", "width": 300},
        {"label": _("Current Month Amount"), "fieldname": "current_month_amount", "fieldtype": "Currency", "width": 180},
        {"label": _("YTD Amount"), "fieldname": "ytd_amount", "fieldtype": "Currency", "width": 180},
        {"label": _("Prev Year (To Date) Amount"), "fieldname": "prev_ytd_amount", "fieldtype": "Currency", "width": 200},
        {"label": _("Prev Full Year Amount"), "fieldname": "prev_full_year_amount", "fieldtype": "Currency", "width": 200},
    ]


def get_data(filters, reference_date):
    today = reference_date
    first_of_month = today.replace(day=1)
    first_of_year = today.replace(month=1, day=1)

    last_year = today.year - 1
    same_day_last_year = today.replace(year=last_year)
    first_of_prev_year = same_day_last_year.replace(month=1, day=1)
    end_of_prev_year = date(last_year, 12, 31)

    cost_centers = frappe.get_all("Cost Center", fields=["name"])
    data = []

    for cc in cost_centers:
        # Cost Center total
        totals = get_invoice_totals(cc.name, None, first_of_month, first_of_year, first_of_prev_year,
                                    same_day_last_year, end_of_prev_year)

        if filters.get("hide_zero_rows") and totals['ytd_amount'] == 0:
            continue

        cost_center_row = {"group_label": cc.name}
        cost_center_row.update(totals)
        data.append(cost_center_row)

        # Add subtotals for each project type (prefix)
        project_rows = get_project_type_rows(cc.name, first_of_month, first_of_year, first_of_prev_year,
                                             same_day_last_year, end_of_prev_year, filters)
        data.extend(project_rows)

    if data:
        total_row = {"group_label": _("Total")}
        for key in [
            "current_month_amount",
            "ytd_amount",
            "prev_ytd_amount",
            "prev_full_year_amount",
        ]:
            total_row[key] = sum(d.get(key, 0) for d in data if not d.get("indent"))
        data.append(total_row)

    # Add summary by third letter of project prefix (*P, *S)
    suffix_summaries = get_suffix_summaries(data)
    data.extend(suffix_summaries)

    return data


def get_invoice_totals(cost_center, project_prefix, first_of_month, first_of_year,
                       first_of_prev_year, same_day_last_year, end_of_prev_year):
    """Return a dict of totals for the given cost center (and optional project prefix)."""

    base_conditions = "si.docstatus = 1 AND si.cost_center = %s"
    params = [cost_center]

    if project_prefix == "zzz":
        base_conditions += " AND (si.project IS NULL OR si.project = '')"
    elif project_prefix:
        base_conditions += " AND LEFT(si.project, 3) = %s"
        params.append(project_prefix)

    # Helper: sum between two dates
    def period_total(from_date, to_date):
        return frappe.db.sql("""
            SELECT IFNULL(SUM(si.base_net_total), 0)
            FROM `tabSales Invoice` si
            WHERE {conds} AND si.posting_date BETWEEN %s AND %s
        """.format(conds=base_conditions), params + [from_date, to_date])[0][0] or 0

    cm_amt = period_total(first_of_month, date.today())
    ytd_amt = period_total(first_of_year, date.today())
    prev_ytd_amt = period_total(first_of_prev_year, same_day_last_year)
    prev_full_amt = period_total(first_of_prev_year, end_of_prev_year)

    return {
        "current_month_amount": cm_amt,
        "ytd_amount": ytd_amt,
        "prev_ytd_amount": prev_ytd_amt,
        "prev_full_year_amount": prev_full_amt,
    }


def get_project_type_rows(cost_center, first_of_month, first_of_year,
                          first_of_prev_year, same_day_last_year, end_of_prev_year, filters):
    """Return rows grouped by project type prefix (first 3 letters)."""

    project_prefixes = frappe.db.sql("""
        SELECT DISTINCT
            CASE WHEN project IS NULL OR project = '' THEN 'zzz'
                 ELSE LEFT(project, 3)
            END AS prefix
        FROM `tabSales Invoice`
        WHERE docstatus = 1
          AND cost_center = %s
        ORDER BY prefix
    """, (cost_center,))

    prefix_legend = {
        'P': _('Kundenprojekte'),
        'S': _('Service & Wartung'),
    }

    rows = []
    for prefix_row in project_prefixes:
        prefix = prefix_row[0]
        totals = get_invoice_totals(cost_center, prefix, first_of_month, first_of_year,
                                    first_of_prev_year, same_day_last_year, end_of_prev_year)

        if filters.get("hide_zero_rows") and all(v == 0 for v in totals.values()):
            continue

        group_label = _("No Project") if prefix == 'zzz' else prefix
        if legend != prefix_legend.get(prefix[2]):
            group_label = "{p} ({l})".format(p=prefix, l=legend)
        elif prefix == 'zzz':
            group_label = _("Kein Projekt")
        else:
            group_label = prefix
        row = {"group_label": group_label, "indent": 1}
        row.update(totals)
        rows.append(row)

    return rows


def get_suffix_summaries(data):
    """Aggregate sums by project type (third letter of project ID, eg. *P, *S)."""

    suffix_totals = {}
    for row in data:
        label = row.get("group_label", "").strip() #.replace("↳", "")
        if len(label) == 3:
            last_char = label[-1]
            key = "*" + last_char
            if not suffix_totals.get(key):
                suffix_totals[key] = {"current_month_amount": 0, "ytd_amount": 0, "prev_ytd_amount": 0, "prev_full_year_amount": 0}
            for field in suffix_totals[key].keys():
                suffix_totals[key][field] += row.get(field, 0)

    summary_rows = []
    for key in suffix_totals:
        summary = {"group_label": key, "indent": 1}
        summary.update(suffix_totals[key])
        summary_rows.append(summary)

    return summary_rows

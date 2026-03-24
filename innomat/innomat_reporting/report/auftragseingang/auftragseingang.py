# Copyright (c) 2025, Innomat, libracore and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from datetime import datetime, date, timedelta

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

        {"label": _("Cost Center"), "fieldname": "cost_center", "fieldtype": "Data", "width": 120},

        {"label": _("Current Month: Amount"), "fieldname": "current_month_amount", "fieldtype": "Currency", "width": 160},
        {"label": _("Orders"), "fieldname": "current_month_count", "fieldtype": "Int", "width": 60},

        {"label": _("YTD: Amount"), "fieldname": "ytd_amount", "fieldtype": "Currency", "width": 120},
        {"label": _("Orders"), "fieldname": "ytd_count", "fieldtype": "Int", "width": 60},

        {"label": _("Prev Year (To Date): Amount"), "fieldname": "prev_ytd_amount", "fieldtype": "Currency", "width": 200},
        {"label": _("Orders"), "fieldname": "prev_ytd_count", "fieldtype": "Int", "width": 60},

        {"label": _("Prev Full Year: Amount"), "fieldname": "prev_full_year_amount", "fieldtype": "Currency", "width": 160},
        {"label": _("Orders"), "fieldname": "prev_full_year_count", "fieldtype": "Int", "width": 60},
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
        current_month_amount, current_month_count = get_sales_total_and_count(cc.name, first_of_month, today)
        ytd_amount, ytd_count = get_sales_total_and_count(cc.name, first_of_year, today)
        prev_ytd_amount, prev_ytd_count = get_sales_total_and_count(cc.name, first_of_prev_year, same_day_last_year)
        prev_full_year_amount, prev_full_year_count = get_sales_total_and_count(cc.name, first_of_prev_year, end_of_prev_year)

        row = {
            "cost_center": cc.name,
            "current_month_amount": current_month_amount,
            "current_month_count": current_month_count,
            "ytd_amount": ytd_amount,
            "ytd_count": ytd_count,
            "prev_ytd_amount": prev_ytd_amount,
            "prev_ytd_count": prev_ytd_count,
            "prev_full_year_amount": prev_full_year_amount,
            "prev_full_year_count": prev_full_year_count
        }

        # Skip zero rows if filter is active
        if filters.get("hide_zero_rows"):
            if row['ytd_amount'] == 0:
                continue

        data.append(row)

    return data


def get_sales_total_and_count(cost_center, from_date, to_date):
    result = frappe.db.sql("""
        SELECT SUM(base_net_total), COUNT(name)
        FROM `tabSales Order`
        WHERE docstatus = 1
          AND transaction_date BETWEEN %s AND %s
          AND cost_center = %s
    """, (from_date, to_date, cost_center))

    total = result[0][0] or 0
    count = result[0][1] or 0

    return total, count

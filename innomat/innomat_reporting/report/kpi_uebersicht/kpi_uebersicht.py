# Copyright (c) 2025, Innomat, Asprotec and libracore and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from datetime import datetime, date


# ======================================================
# Base KPI class
# ======================================================
class KPI:
    name = None
    unit = None

    def compute(self, company, cost_center, from_date, to_date):
        """Override this in subclasses. Returns numeric value for the given date range."""
        return 0.0


# ======================================================
# --- SALES KPIs ---
# ======================================================

# Auftragseingang = Summe der erfassten Aufträge
# (sanity checked MZ)
class OrderVolume(KPI):
    name = "Order Volume"
    unit = "Currency"

    def compute(self, company, cost_center, from_date, to_date):
        query, params = make_conditions("tabSales Order", "transaction_date", company, cost_center, from_date, to_date)
        return frappe.db.sql(f"SELECT IFNULL(SUM(base_net_total), 0) FROM {query}", params)[0][0] or 0

# Auftragseingang-Wachstum = (Auftragsvol. - Auftragsvol. Vorjahr) / Auftragsvol. Vorjahr
# (sanity checked MZ)
class OrderVolumeGrowth(KPI):
    name = "Order Volume Growth (YoY)"
    unit = "Percent"

    def compute(self, company, cost_center, from_date, to_date):
        current = OrderVolume().compute(company, cost_center, from_date, to_date)
        # last year same period
        last_year_from = from_date.replace(year=from_date.year - 1)
        last_year_to = to_date.replace(year=to_date.year - 1)
        previous = OrderVolume().compute(company, cost_center, last_year_from, last_year_to)
        return ((current - previous) / previous * 100) if previous else 0

# Book-to-Bill Ratio = Auftragseingang / Umsatz
# => TODO, laut Excelsheet: Sales und nicht BilledSales verwenden?! Name ist dann aber irreführend.
class BookToBillRatio(KPI):
    name = "Book-to-Bill Ratio"
    unit = "Ratio"

    def compute(self, company, cost_center, from_date, to_date):
        orders = OrderVolume().compute(company, cost_center, from_date, to_date)
        billed = BilledSales().compute(company, cost_center, from_date, to_date)
        return (orders / billed) if billed else 0

# Auftragseingang Top-5-Kunden
# => TODO, indent = 2, mehrere Zeilen ausgeben...
class OrderVolumeTop5Share(KPI):
    name = "Order Volume % of Top-5 Customers"
    unit = "Percent"

    def compute(self, company, cost_center, from_date, to_date):
        query, params = make_conditions("tabSales Order", "transaction_date", company, cost_center, from_date, to_date)
        total = frappe.db.sql(f"SELECT IFNULL(SUM(base_net_total), 0) FROM {query}", params)[0][0] or 0
        top5 = frappe.db.sql(f"""
            SELECT IFNULL(SUM(base_net_total), 0)
            FROM (
                SELECT customer, SUM(base_net_total) AS base_net_total
                FROM {query}
                GROUP BY customer
                ORDER BY SUM(base_net_total) DESC
                LIMIT 5
            ) t
        """, params)[0][0] or 0
        return (top5 / total * 100) if total else 0


# ======================================================
# --- FULFILLMENT KPIs ---
# ======================================================

class BilledSales(KPI):
    name = "Billed Sales"
    unit = "Currency"

    def compute(self, company, cost_center, from_date, to_date):
        query, params = make_conditions("tabSales Invoice", "posting_date", company, cost_center, from_date, to_date)
        return frappe.db.sql(f"SELECT IFNULL(SUM(base_net_total), 0) FROM {query}", params)[0][0] or 0


class BillingRatio(KPI):
    name = "Billing Ratio"
    unit = "Percent"

    def compute(self, company, cost_center, from_date, to_date):
        billed = BilledSales().compute(company, cost_center, from_date, to_date)
        ordered = OrderVolume().compute(company, cost_center, from_date, to_date)
        return (billed / ordered * 100) if ordered else 0


class GrossMargin(KPI):
    name = "Gross Margin"
    unit = "Percent"

    def compute(self, company, cost_center, from_date, to_date):
        query, params = make_conditions("tabSales Invoice", "posting_date", company, cost_center, from_date, to_date)
        totals = frappe.db.sql(f"SELECT IFNULL(SUM(base_net_total),0), IFNULL(SUM(total_cost),0) FROM {query}", params)[0]
        sales, cost = totals
        return ((sales - cost) / sales * 100) if sales else 0


class GrossMarginGrowth(KPI):
    name = "Gross Margin Growth (YoY)"
    unit = "Percent"

    def compute(self, company, cost_center, from_date, to_date):
        current = GrossMargin().compute(company, cost_center, from_date, to_date)
        last_year_from = from_date.replace(year=from_date.year - 1)
        last_year_to = to_date.replace(year=to_date.year - 1)
        previous = GrossMargin().compute(company, cost_center, last_year_from, last_year_to)
        return current - previous


class Backlog(KPI):
    name = "Backlog"
    unit = "Currency"

    def compute(self, company, cost_center, from_date, to_date):
        ordered = OrderVolume().compute(company, cost_center, from_date, to_date)
        billed = BilledSales().compute(company, cost_center, from_date, to_date)
        return ordered - billed


class PostCalcDeviation(KPI):
    name = "Post-Calculation Deviation"
    unit = "Percent"

    def compute(self, company, cost_center, from_date, to_date):
        return 0.0  # placeholder


# ======================================================
# --- FINANCE KPIs ---
# ======================================================

#TODO, kann ERPNext keinen effektiven Umsatz ermitteln?
class Sales(KPI):
    name = "Sales"
    unit = "Currency"

    def compute(self, company, cost_center, from_date, to_date):
        return BilledSales().compute(company, cost_center, from_date, to_date)


class SalesGrowth(KPI):
    name = "Sales Growth (YoY)"
    unit = "Percent"

    def compute(self, company, cost_center, from_date, to_date):
        current = Sales().compute(company, cost_center, from_date, to_date)
        last_year_from = from_date.replace(year=from_date.year - 1)
        last_year_to = to_date.replace(year=to_date.year - 1)
        previous = Sales().compute(company, cost_center, last_year_from, last_year_to)
        return ((current - previous) / previous * 100) if previous else 0


class SalesVsBudget(KPI):
    name = "Sales % of Budget"
    unit = "Percent"

    def compute(self, company, cost_center, from_date, to_date):
        return 0.0  # placeholder


class EBITDA(KPI):
    name = "EBITDA"
    unit = "Currency"

    def compute(self, company, cost_center, from_date, to_date):
        return 0.0  # placeholder


class EBITDAMargin(KPI):
    name = "EBITDA Margin"
    unit = "Percent"

    def compute(self, company, cost_center, from_date, to_date):
        ebitda = EBITDA().compute(company, cost_center, from_date, to_date)
        sales = Sales().compute(company, cost_center, from_date, to_date)
        return (ebitda / sales * 100) if sales else 0


class OperatingProfit(KPI):
    name = "Operating Profit (OP)"
    unit = "Currency"

    def compute(self, company, cost_center, from_date, to_date):
        return 0.0  # placeholder


class OperatingProfitDue(KPI):
    name = "Operating Profit Due"
    unit = "Currency"

    def compute(self, company, cost_center, from_date, to_date):
        return 0.0  # placeholder


class Stock(KPI):
    name = "Stock"
    unit = "Currency"

    def compute(self, company, cost_center, from_date, to_date):
        val = frappe.db.sql("""
            SELECT IFNULL(SUM(actual_qty * valuation_rate), 0)
            FROM `tabBin`
        """)[0][0]
#TODO            WHERE company = %s
#(company,)
        return val or 0


class ROCE(KPI):
    name = "ROCE"
    unit = "Percent"

    def compute(self, company, cost_center, from_date, to_date):
        return 0.0  # placeholder


# ======================================================
# --- EMPLOYEE KPIs ---
# ======================================================

class Productivity(KPI):
    name = "Productivity"
    unit = "Ratio"

    def compute(self, company, cost_center, from_date, to_date):
        return 0.0


class OvertimeBalance(KPI):
    name = "Overtime Balance"
    unit = "Hours"

    def compute(self, company, cost_center, from_date, to_date):
        return 0.0


class VacationBalance(KPI):
    name = "Vacation Balance"
    unit = "Days"

    def compute(self, company, cost_center, from_date, to_date):
        return 0.0


# ======================================================
# --- UTILITY FUNCTIONS ---
# ======================================================

def make_conditions(doctype, date_field, company, cost_center, from_date, to_date):
    """Return a formatted FROM/WHERE fragment and params list."""
    conds = [f"{date_field} BETWEEN %s AND %s", "company = %s", "docstatus = 1"]
    params = [from_date, to_date, company]
    if cost_center:
        conds.append("cost_center = %s")
        params.append(cost_center)
    where = "WHERE " + " AND ".join(conds)
    return f"`{doctype}` {where}", params

# --------------------------------------------
# Helper functions
# --------------------------------------------

def get_ytd_range(reference_date):
    """Return the start and end date of the current year up to the reference date."""
    start_of_year = date(reference_date.year, 1, 1)
    return start_of_year, reference_date

def get_cost_centers(company):
    """Fetch cost centers belonging to the given company."""
    return frappe.get_all(
        "Cost Center",
        filters={"company": company, "is_group": 0},
        fields=["name"],
        order_by="name"
    )


# --------------------------------------------
# Report execution
# --------------------------------------------

def execute(filters=None):
    if not filters:
        filters = {}

    # Company filter (default = system default company)
    company = filters.get("company") or frappe.defaults.get_user_default("Company")
    if not company:
        frappe.throw(_("Please select a company."))

    # Date filters
    from_date = datetime.strptime(filters.get("from_date"), "%Y-%m-%d").date()
    to_date = datetime.strptime(filters.get("to_date"), "%Y-%m-%d").date()

    columns = get_columns(company)
    data = get_data(company, from_date, to_date)

    return columns, data


def get_columns(company):
    """
    Generates columns for the report: Company + each cost center, each with YTD/Period subcolumns.
    """
    cols = [{"label": _("KPI"), "fieldname": "kpi_label", "fieldtype": "Data", "width": 260}]
    entities = [company] + [cc.name for cc in get_cost_centers(company)]

    for entity in entities:
        base = entity.lower().replace(" ", "_")
        cols.append({"label": _(f"{entity} YTD"), "fieldname": f"{base}_ytd", "fieldtype": "Float", "width": 130})
        cols.append({"label": _(f"{entity} Period"), "fieldname": f"{base}_period", "fieldtype": "Float", "width": 130})

    return cols


def get_data(company, from_date, to_date):
    """
    Compute KPI rows for YTD and Period columns.
    Uses all KPI classes defined previously.
    """
    # KPI classes grouped by section
    kpis = {
        "Sales": [OrderVolume(), OrderVolumeGrowth(), BookToBillRatio(), OrderVolumeTop5Share()],
#        "Fulfillment": [BilledSales(), BillingRatio(), GrossMargin(), GrossMarginGrowth(), Backlog(), PostCalcDeviation()],
        "Fulfillment": [BilledSales(), BillingRatio(), Backlog(), PostCalcDeviation()],
        "Finance": [Sales(), SalesGrowth(), SalesVsBudget(), EBITDA(), EBITDAMargin(),
                    OperatingProfit(), OperatingProfitDue(), Stock(), ROCE()],
        "Employees": [Productivity(), OvertimeBalance(), VacationBalance()],
    }

    # Precompute YTD range based on to_date
    ytd_from, ytd_to = get_ytd_range(to_date)

    # Cost centers of the company
    cost_centers = [None] + [cc.name for cc in get_cost_centers(company)]

    data = []

    for section, kpi_list in kpis.items():
        # Section header row
        data.append({"kpi_label": section, "indent": 0})

        for kpi in kpi_list:
            row = {"kpi_label": kpi.name, "indent": 1}

            for cc in cost_centers:
                base = (company if cc is None else cc).lower().replace(" ", "_")

                # YTD column
                row[f"{base}_ytd"] = kpi.compute(company, cc, ytd_from, ytd_to)

                # Period column (from filters)
                row[f"{base}_period"] = kpi.compute(company, cc, from_date, to_date)

            data.append(row)

    return data

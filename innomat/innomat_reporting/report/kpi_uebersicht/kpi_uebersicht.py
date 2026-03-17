# Copyright (c) 2025, Innomat, Asprotec and libracore and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
import frappe.desk.query_report
from frappe import _
from datetime import datetime, date
from frappe.utils import add_years
from innomat.innomat.report.employee_productivity.employee_productivity import get_data as get_employee_productivity_data


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
# [OK-MZ]
class OrderVolume(KPI):
    name = "Order Volume"
    unit = "Currency"

    def compute(self, company, cost_center, from_date, to_date):
        query, params = make_conditions("tabSales Order", "transaction_date", company, cost_center, from_date, to_date)
        return frappe.db.sql(f"SELECT IFNULL(SUM(base_net_total), 0) FROM {query}", params)[0][0] or 0


# Auftragseingang-Wachstum = (Auftragsvol. - Auftragsvol. Vorjahr) / Auftragsvol. Vorjahr
# [OK-MZ]
class OrderVolumeGrowth(KPI):
    name = "Order Volume Growth (YoY)"
    unit = "Percent"

    def compute(self, company, cost_center, from_date, to_date):
        current = OrderVolume().compute(company, cost_center, from_date, to_date)
        # last year same period
        last_year_from = add_years(from_date, -1)
        last_year_to = add_years(to_date, -1)
        previous = OrderVolume().compute(company, cost_center, last_year_from, last_year_to)
        return ((current - previous) / previous * 100) if previous else 0


# Book-to-Bill Ratio = Auftragseingang / Umsatz
# => Umsatz und nicht Billed Sales verwenden!
# [OK-MZ]
class BookToBillRatio(KPI):
    name = "Book-to-Bill Ratio"
    unit = "Ratio"

    def compute(self, company, cost_center, from_date, to_date):
        orders = OrderVolume().compute(company, cost_center, from_date, to_date)
        sales = Sales().compute(company, cost_center, from_date, to_date)
        return (orders / sales) if sales else 0


# Auftragseingang pro Kunde (Top-5-Kunden): Anteil der 5 grössten Kunden am AE [%]
# [OK-MZ]
class OrderVolumeTop5Share(KPI):
    name = "Order Volume % of Top-5 Customers"
    unit = "Percent"
    multiline = True

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
        """, params, as_dict=True)
        result = []
        for t in top5:
            result[t['customer']] = 100 * t['base_net_total'] / total if total else 0
        return result


# ======================================================
# --- FULFILLMENT KPIs ---
# ======================================================

# Fakturierter Umsatz
# [OK-MZ]
class BilledSales(KPI):
    name = "Billed Sales"
    unit = "Currency"

    def compute(self, company, cost_center, from_date, to_date):
        query, params = make_conditions("tabSales Invoice", "posting_date", company, cost_center, from_date, to_date)
        return frappe.db.sql(f"SELECT IFNULL(SUM(base_net_total), 0) FROM {query}", params)[0][0] or 0


# Fakturierungsgrad = fakt. Umsatz / Selbstkosten
# Der Einfachheit halber auf Projektebene umgesetzt
# [OK-MZ]
class BillingRatio(KPI):
    name = "Billing Ratio"
    unit = "Percent"

    # Datumsbereich: Alle Projekte berücksichtigen, die im ang. Zeitraum irgendwann aktiv waren, d.h.
    # Startdatum <= to_date sowie
    # Enddatum >= from_date
    # (Nicht begonnene Projekte werden nicht berücksichtigt)
    def compute(self, company, cost_center, from_date, to_date):
        args = locals()
        query = """SELECT SUM(total_billed_amount) AS billed, SUM(actual_material_cost + sum_services + sum_expense_claim + labor_as_prime_cost + labor_by_effort_as_prime_cost) AS prime_cost
            FROM `tabProject`
            WHERE `company` = %(company)s
            AND `actual_start_date` <= %(to_date)s
            AND `actual_end_date` >= %(from_date)s
            """
        if cost_center:
            query += " AND cost_center = %(cost_center)s"
        data = frappe.db.sql(query, args, as_dict=True)
        if data and len(data) > 0 and data[0].prime_cost > 0:
            return 100 * data[0].billed / data[0].prime_cost
        else:
            return 0


# Bruttomarge = (Fakturierter Umsatz - Herstellungskosten) / Umsatz
# Der Einfachheit halber auf Projektebene umgesetzt
# [OK-MZ]
class GrossMargin(KPI):
    name = "Gross Margin"
    unit = "Percent"

    # Datumsbereich: Alle Projekte berücksichtigen, die im ang. Zeitraum irgendwann aktiv waren, d.h.
    # Startdatum <= to_date sowie
    # Enddatum >= from_date
    # (Nicht begonnene Projekte werden nicht berücksichtigt)
    def compute(self, company, cost_center, from_date, to_date):
        args = locals()
        query = """SELECT SUM(total_billed_amount) AS billed,
                          SUM(actual_material_cost + sum_services + sum_expense_claim + labor_as_production_cost + labor_by_effort_as_production_cost) AS prod_cost,
                          SUM(planned_revenue + planned_revenue_by_effort) AS revenue
            FROM `tabProject`
            WHERE `company` = %(company)s
            AND `actual_start_date` <= %(to_date)s
            AND `actual_end_date` >= %(from_date)s
            """
        if cost_center:
            query += " AND cost_center = %(cost_center)s"
        data = frappe.db.sql(query, args, as_dict=True)
        if data and len(data) > 0 and data[0].revenue > 0:
            return 100 * (data[0].billed - data[0].prod_cost) / data[0].revenue
        else:
            return 0


# Bruttomarge Wachstum (YoY) = Differenz zu Vorjahr in %
# [OK-MZ]
class GrossMarginGrowth(KPI):
    name = "Gross Margin Growth (YoY)"
    unit = "Percent"

    def compute(self, company, cost_center, from_date, to_date):
        current = GrossMargin().compute(company, cost_center, from_date, to_date)
        # last year same period
        last_year_from = add_years(from_date, -1)
        last_year_to = add_years(to_date, -1)
        previous = GrossMargin().compute(company, cost_center, last_year_from, last_year_to)
        return ((current - previous) / previous * 100) if previous else 0


# Arbeitsvorrat = noch nicht bearbeitetes Auftragsvolumen [CHF]
# Der Einfachheit halber auf Projektebene umgesetzt, mit Arb.vorrat = Projektumsatz minus bisherige Selbstkosten
# TODO - Die aktuelle Umsetzung ignoriert den Datumsfilter komplett.
#        Evtl. ist bei Umsetzung auf Buchhaltungsebene eine sinnvolle Filterung möglich
class Backlog(KPI):
    name = "Backlog"
    unit = "Currency"

    def compute(self, company, cost_center, dummy, dummy2):
        args = locals()
        query = """SELECT SUM(planned_revenue + planned_revenue_by_effort - actual_material_cost - sum_services - sum_expense_claim - labor_as_prime_cost - labor_by_effort_as_prime_cost) AS backlog_amount
            FROM `tabProject`
            WHERE `company` = %(company)s
            AND `status` NOT IN ('Completed','Cancelled')
            """
        if cost_center:
            query += " AND cost_center = %(cost_center)s"
        data = frappe.db.sql(query, args, as_dict=True)
        if data and len(data) > 0:
            return data[0].backlog_amount
        else:
            return 0


#TODO
class PostCalcDeviation(KPI):
    name = "Post-Calculation Deviation"
    unit = "Percent"

    def compute(self, company, cost_center, from_date, to_date):
        return 0.0  # placeholder


# ======================================================
# --- FINANCE KPIs ---
# ======================================================

# Umsatz
# [OK-MZ]
class Sales(KPI):
    name = "Sales"
    unit = "Currency"

    def compute(self, company, cost_center, from_date, to_date):
        args = locals()
        query = """
            SELECT SUM(gle.credit - gle.debit) AS total_sales
            FROM `tabGL Entry` AS gle
            WHERE LEFT(gle.account, 4) IN ('3000', '3200', '3400')
            AND gle.company = %(company)s
            AND gle.posting_date BETWEEN %(from_date)s AND %(to_date)s
            AND gle.docstatus = 1
            """
        if cost_center:
            query += " AND gle.cost_center = %(cost_center)s"
        total_sales = frappe.db.sql(query, args)
        return total_sales[0][0] if total_sales else 0


# Umsatzwachstum (YoY) = (Umsatz – Vorjahr) / Vorjahr
# [OK-MZ]
class SalesGrowth(KPI):
    name = "Sales Growth (YoY)"
    unit = "Percent"

    def compute(self, company, cost_center, from_date, to_date):
        current = Sales().compute(company, cost_center, from_date, to_date)
        # last year same period
        last_year_from = add_years(from_date, -1)
        last_year_to = add_years(to_date, -1)
        previous = Sales().compute(company, cost_center, last_year_from, last_year_to)
        return ((current - previous) / previous * 100) if previous else 0


# Umsatz in % zum Budget
# [OK-MZ]
# (NOTE - aktuell wird budget_prefix = "Budget" angenommen und sonst einfach das erstbeste Innomat-Budget verwendet)
class SalesVsBudget(KPI):
    name = "Sales % of Budget"
    unit = "Percent"

    def compute(self, company, cost_center, from_date, to_date):
        sales = Sales().compute(company, cost_center, from_date, to_date)
        # `budget_01`+`budget_02`+...
        budget_months = "+".join(["`budget_%02d`" % x for x in range(from_date.month,to_date.month+1)])
        budget_filters = {
            "name_prefix": "Budget",
            "company": filters.company,
            "fiscal_year": filters.fiscal_year
        }
        if cost_center:
            budget_filters['cost_center'] = cost_center
        budget_name = frappe.db.exists("Innomat Budget", budget_filters)
        if not budget_name:
            del budget_filters['name_prefix']
            budget_name = frappe.db.exists("Innomat Budget", budget_filters)
        if not budget_name:
            return 0

        query = """
            SELECT SUM({budget_months}) AS `sales_budget`,
            FROM `tabInnomat Budget Account`
            LEFT JOIN `tabAccount` ON `tabInnomat Budget Account`.`account` = `tabAccount`.`name`
            WHERE `tabInnomat Budget Account`.`parent` = '{budget_name}' AND `tabInnomat Budget Account`.`root_type`= 'Income'
            AND LEFT(`tabInnomat Budget`.`account`, 4) IN ('3000', '3200', '3400')
            """.format(budget_months=budget_months, budget_name=budget_name)
        data = frappe.db.sql(query, as_dict=True)
        if data and len(data) > 0 and data[0].sales_budget > 0:
            return 100 * sales / data[0].sales_budget
        else
            return 0


# EBITDA = Earnings before Interest, Taxes, Depreciation and Amortization
# [OK-MZ]
class EBITDA(KPI):
    name = "EBITDA"
    unit = "Currency"

    def compute(self, company, cost_center, from_date, to_date):
        return EBIT().compute(company, cost_center, from_date, to_date, True)


# EBIT = Earnings before Interest and Taxes
# EBITDA = Earnings before Interest, Taxes, Depreciation and Amortization
# => Sum of all accounts where report_type = "Profit and Loss", except:
#    - Accounts where account=type = "Expense Account" and expense_account_classification in [Interest, Tax]
#    - In case of EBITDA: Accounts where account_type = "Depreciation"
# Apparently we should also exclude Period Closing Vouchers, otherwise we get 0 for past periods.
# [OK-MZ]
class EBIT(KPI):
    name = "EBIT"
    unit = "Currency"

    def compute(self, company, cost_center, from_date, to_date, da=False):
        args = locals()
        da_condition = ' AND account_type != "Depreciation" ' if da else ''
        query = """
            SELECT SUM(gle.credit - gle.debit) AS ebit_da
            FROM `tabGL Entry` gle
            INNER JOIN `tabAccount` acc ON gle.account = acc.name
            WHERE gle.account IN (
                SELECT name FROM `tabAccount`
                WHERE report_type = "Profit and Loss"
                {da_condition}
                AND (account_type != "Expense Account" OR expense_account_classification NOT IN ('Interest', 'Tax'))
                AND company = %(company)s
            )
            AND gle.voucher_type != "Period Closing Voucher"
            AND gle.company = %(company)s
            AND gle.posting_date BETWEEN %(from_date)s AND %(to_date)s
            AND gle.docstatus = 1
            """.format(da_condition)
        if cost_center:
            query += " AND gle.cost_center = %(cost_center)s"
        data = frappe.db.sql(query, args, as_dict=True)
        if data and len(data) > 0:
            return data[0]['ebit_da']
        else:
            return 0


# EBITDA-Marge = EBITDA / Umsatz
# [OK-MZ]
class EBITDAMargin(KPI):
    name = "EBITDA Margin"
    unit = "Percent"

    def compute(self, company, cost_center, from_date, to_date):
        ebitda = EBITDA().compute(company, cost_center, from_date, to_date)
        sales = Sales().compute(company, cost_center, from_date, to_date)
        return (ebitda / sales * 100) if sales else 0


# Offene Posten (OP)
# [OK-MZ]
class OpenPositions(KPI):
    name = "Open Positions (OP)"
    unit = "Currency"

    def compute(self, company, cost_center, from_date, to_date):
        rep = frappe.desk.query_report.run("Accounts Receivable Summary", {"company": company, "ageing_based_on": "Due Date", "report_date": to_date, "range1":30, "range2":60, "range3":90, "range4":120})
        totals = rep['result'][-1]
        total_op = totals[6]
        return total_op


# Fällige OP
# [OK-MZ]
class OpenPositionsDue(KPI):
    name = "Open Positions Due"
    unit = "Currency"

    def compute(self, company, cost_center, from_date, to_date):
        rep = frappe.desk.query_report.run("Accounts Receivable Summary", {"company": company, "ageing_based_on": "Due Date", "report_date": to_date, "range1":30, "range2":60, "range3":90, "range4":120})
        totals = rep['result'][-1]
        total_op_due = totals[7]+totals[8]+totals[9]+totals[10]+totals[11]
        return total_op_due


# Wert des Lagers zum Ende der Periode
# (ignoriert from_date)
# [OK-MZ]
class Stock(KPI):
    name = "Stock"
    unit = "Currency"

    def compute(self, company, cost_center, dummy, to_date):
        args = locals()
        query = """
            SELECT  SUM(gle.debit - gle.credit) FROM `tabGL Entry` gle
            INNER JOIN `tabAccount` acc ON gle.account = acc.name
            WHERE gle.account LIKE '1200%'
            AND gle.company = %(company)s
            AND gle.voucher_type != "Period Closing Voucher"
            AND gle.posting_date < %(to_date)s
            AND gle.docstatus = 1
            """
        if cost_center:
            query += " AND gle.cost_center = %(cost_center)s"
        val = frappe.db.sql(query, args)
        if val and len(val)>0:
            return val[0][0]
        else:
            return 0


# ROCE = EBIT / Capital Employed
# [OK-MZ]
class ROCE(KPI):
    name = "ROCE"
    unit = "Percent"

    def compute(self, company, cost_center, from_date, to_date):
        ebit = EBIT().compute(company, cost_center, from_date, to_date)
        ce = CapitalEmployed().compute(company, cost_center, 0, to_date)
        return ebit / ce if ce else 0


# Gebundenes Kapital = Eigenkapital + verz. FK - Cash = Summe(240) + Summe(2b = 280+290) - Summe(100) im Kontenplan
# [OK-MZ]
class CapitalEmployed(KPI):
    name = "Capital Employed"
    unit = "Currency"

    def compute(self, company, cost_center, dummy, to_date):
        args = locals()
        # Sign: For 100, Debit - Credit is positive. For 2xx accounts, Credit - Debit is positive. To get 2xx - 100, just do sum(Credit-Debit)
        query = """
            SELECT SUM(gle.credit - gle.debit) AS ce
            FROM `tabGL Entry` gle
            INNER JOIN `tabAccount` acc ON gle.account = acc.name
            WHERE gle.account IN (
                SELECT name FROM `tabAccount`
                WHERE (parent_account LIKE '100 -%' OR parent_account LIKE '240 -%' OR parent_account LIKE '280 -%' OR parent_account LIKE '290 -%')
                AND company = %(company)s
            )
            AND gle.voucher_type != "Period Closing Voucher"
            AND gle.company = %(company)s
            AND gle.posting_date <= %(to_date)s
            AND gle.docstatus = 1
            """.format(da_condition)
        if cost_center:
            query += " AND gle.cost_center = %(cost_center)s"
        data = frappe.db.sql(query, args, as_dict=True)
        if data and len(data) > 0:
            return data[0]['ce']
        else:
            return 0

# ======================================================
# --- EMPLOYEE KPIs ---
# ======================================================

# Produktivität = Produktive Stunden / Anwesende Stunden [%]
# [OK-MZ]
class Productivity(KPI):
    name = "Productivity"
    unit = "Percent"

    def compute(self, company, cost_center, from_date, to_date):
        params = {"from_date": from_date, "to_date": to_date, "company": company}
        if cost_center:
            department = frappe.db.exists("Department", {"default_cost_center": cost_center})
            if department:
                params["department"] = department
            else:
                return 0
        data = get_employee_productivity_data(params)
        return data[-1]['productivity']

# Überzeit in Stunden pro Mitarbeiter
# TODO - Keine Daten verfügbar, da nicht alle MA das Timesheet ausfüllen
class OvertimeBalance(KPI):
    name = "Overtime Balance"
    unit = "Hours"

    def compute(self, company, cost_center, from_date, to_date):
        return 0.0

# Feriensaldo in Tagen pro Mitarbeiter
# NOTE - wird am Stichtag to_date berechnet, from_date wird ignoriert.
# [OK-MZ]
class VacationBalance(KPI):
    name = "Vacation Balance"
    unit = "Days"

    def compute(self, company, cost_center, from_date, to_date):
        employee_cond = {"status": "Active", "company": company}
        if cost_center:
            department = frappe.db.exists("Department", {"default_cost_center": cost_center})
            if department:
                employee_cond['department'] = department
            else:
                return 0
        employees = frappe.get_all("Employee", employee_cond)
        balance = 0
        for e in employees:
            # 2099-12-31 here means we ignore the expiry of vacation day allocations
            balance += get_leave_balance_on(e.name,"Urlaub",to_date,"2099-12-31")
        return balance


# ======================================================
# --- UTILITY FUNCTIONS ---
# ======================================================

def make_conditions(doctype, date_field, company, cost_center, from_date, to_date):
    """Return a formatted FROM/WHERE fragment and params list."""
    params = {"from_date": from_date, "to_date": to_date, "company": company, "cost_center": cost_center}
    conds = [f"{date_field} BETWEEN %(from_date)s AND %(to_date)s", "company = %(company)s", "docstatus = 1"]
    if cost_center:
        conds.append("cost_center = %(cost_center)s")
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
                    OpenPositions(), OpenPositionsDue(), Stock(), ROCE()],
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

            if kpi.get("multiline"):
                for cc in cost_centers:
                    base = (company if cc is None else cc).lower().replace(" ", "_")

                    # YTD column
                    ytd_data = kpi.compute(company, cc, ytd_from, ytd_to)
                    period_data = kpi.compute(company, cc, from_date, to_date)

                    row[f"{base}_ytd"] = 0
                    row[f"{base}_period"] = 0
                    sub_data = []
                    for d in ytd_data:
                        sub_row = {"kpi_label": name, "indent": 2, f"{base}_ytd": ytd_data[d], f"{base}_period": period_data.get(d)}
                        row[f"{base}_ytd"] += ytd_data[d]
                        row[f"{base}_period"] += period_data.get(d, 0)
                        sub_data.append(sub_row)

                    data.append(row)
                    data.extend(sub_data)
            else:
                for cc in cost_centers:
                    base = (company if cc is None else cc).lower().replace(" ", "_")

                    # YTD column
                    row[f"{base}_ytd"] = kpi.compute(company, cc, ytd_from, ytd_to)

                    # Period column (from filters)
                    row[f"{base}_period"] = kpi.compute(company, cc, from_date, to_date)

                data.append(row)

    return data

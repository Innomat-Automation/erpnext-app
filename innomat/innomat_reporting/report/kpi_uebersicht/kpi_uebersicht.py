# Copyright (c) 2025, Innomat, Asprotec and libracore and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
import frappe.desk.query_report
from frappe import _
from datetime import datetime, date
from frappe.utils import add_years
from innomat.innomat.report.employee_productivity.employee_productivity import get_data as get_employee_productivity_data
from erpnext.hr.doctype.leave_application.leave_application import get_leave_balance_on

# ======================================================
# Base KPI class
# ======================================================
class KPI:
    name = None
    unit = None
    multiline = False

    def compute(self, company, cost_center, from_date, to_date):
        """Override this in subclasses. Returns numeric value for the given date range."""
        return 0.0


# ======================================================
# --- SALES KPIs ---
# ======================================================

# Auftragseingang = Summe der erfassten Aufträge
# [OK-MZ]
class OrderVolume(KPI):
    name = "Auftragseingang"
    unit = "CHF"

    def compute(self, company, cost_center, from_date, to_date):
        query, params = make_conditions("tabSales Order", "transaction_date", company, cost_center, from_date, to_date)
        return frappe.db.sql(f"SELECT IFNULL(SUM(base_net_total), 0) FROM {query}", params)[0][0] or 0


# Auftragseingang-Wachstum = (Auftragsvol. - Auftragsvol. Vorjahr) / Auftragsvol. Vorjahr
# [OK-MZ]
class OrderVolumeGrowth(KPI):
    name = "Auftragseingang-Wachstum (YoY)"
    unit = "%"

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
    name = "Anteil der 5 grössten Kunden am AE"
    unit = "%"
    multiline = True

    def compute(self, company, cost_center, from_date, to_date):
        query, params = make_conditions("tabSales Order", "transaction_date", company, cost_center, from_date, to_date)
        total = frappe.db.sql(f"SELECT IFNULL(SUM(base_net_total), 0) FROM {query}", params)[0][0] or 0
        top5 = frappe.db.sql(f"""
            SELECT customer, customer_name, SUM(base_net_total) AS base_net_total
            FROM {query}
            GROUP BY customer
            ORDER BY SUM(base_net_total) DESC
            LIMIT 5
        """, params, as_dict=True)
        result = {}
        cust_cnt = 1
        for t in top5:
            # Use a neutral row title "Customer 1 .. Customer 5" as other cost centers will have different Top5 customers!
            result[_("Customer") + f" {cust_cnt}"] = 100 * t['base_net_total'] / total if total else 0
            cust_cnt += 1
        return result


# ======================================================
# --- FULFILLMENT KPIs ---
# ======================================================

# Fakturierter Umsatz
# [OK-MZ]
class BilledSales(KPI):
    name = "Fakturierter Umsatz"
    unit = "CHF"

    def compute(self, company, cost_center, from_date, to_date):
        query, params = make_conditions("tabSales Invoice", "posting_date", company, cost_center, from_date, to_date)
        return frappe.db.sql(f"SELECT IFNULL(SUM(base_net_total), 0) FROM {query}", params)[0][0] or 0


# Fakturierungsgrad = fakt. Umsatz / Selbstkosten
# Der Einfachheit halber auf Projektebene umgesetzt
# [OK-MZ]
class BillingRatio(KPI):
    name = "Fakturierungsgrad"
    unit = "%"

    # Datumsbereich: Alle Projekte berücksichtigen, die im ang. Zeitraum irgendwann aktiv waren, d.h.
    # Startdatum <= to_date sowie
    # Enddatum >= from_date
    # (Nicht begonnene Projekte werden nicht berücksichtigt)
    def compute(self, company, cost_center, from_date, to_date):
        args = locals()
        del args['self']
        query = """SELECT SUM(total_billed_amount) AS billed, SUM(actual_material_cost + sum_services + sum_expense_claim + actual_labor_as_prime_cost + labor_by_effort_as_prime_cost) AS prime_cost
            FROM `tabProject`
            WHERE `company` = %(company)s
            AND `actual_start_date` <= %(to_date)s
            AND `actual_end_date` >= %(from_date)s
            """
        if cost_center:
            query += " AND cost_center = %(cost_center)s"
        data = frappe.db.sql(query, args, as_dict=True)
        if data[0].prime_cost:
            return 100 * data[0].billed / data[0].prime_cost
        else:
            return 0


# Bruttomarge = (Fakturierter Umsatz - Herstellungskosten) / Umsatz
# Der Einfachheit halber auf Projektebene umgesetzt
# [OK-MZ]
class GrossMargin(KPI):
    name = "Bruttomarge"
    unit = "%"

    # Datumsbereich: Alle Projekte berücksichtigen, die im ang. Zeitraum irgendwann aktiv waren, d.h.
    # Startdatum <= to_date sowie
    # Enddatum >= from_date
    # (Nicht begonnene Projekte werden nicht berücksichtigt)
    def compute(self, company, cost_center, from_date, to_date):
        args = locals()
        del args['self']
        query = """SELECT SUM(total_billed_amount) AS billed,
                          SUM(actual_material_cost + sum_services + sum_expense_claim + actual_labor_as_production_cost + labor_by_effort_as_production_cost) AS prod_cost,
                          SUM(planned_revenue + planned_revenue_by_effort) AS revenue
            FROM `tabProject`
            WHERE `company` = %(company)s
            AND `actual_start_date` <= %(to_date)s
            AND `actual_end_date` >= %(from_date)s
            """
        if cost_center:
            query += " AND cost_center = %(cost_center)s"
        data = frappe.db.sql(query, args, as_dict=True)
        if data[0].revenue:
            return 100 * (data[0].billed - data[0].prod_cost) / data[0].revenue
        else:
            return 0


# Bruttomarge Wachstum (YoY) = Differenz zu Vorjahr in %
# [OK-MZ]
class GrossMarginGrowth(KPI):
    name = "Bruttomarge Wachstum (YoY)"
    unit = "%"

    def compute(self, company, cost_center, from_date, to_date):
        current = GrossMargin().compute(company, cost_center, from_date, to_date)
        # last year same period
        last_year_from = add_years(from_date, -1)
        last_year_to = add_years(to_date, -1)
        previous = GrossMargin().compute(company, cost_center, last_year_from, last_year_to)
        return ((current - previous) / previous * 100) if previous else 0


# Arbeitsvorrat = noch nicht bearbeitetes Auftragsvolumen [CHF] = Auftragsvolumen - Selbstkosten über alle laufenden Projekte
# Der Einfachheit halber wird effektiv erbrachte Arbeit hier ignoriert, es wird nur das verrechnete Volumen berücksichtigt.
# Zu einem beliebigen Stichtag die aktuellen Selbstkosten aller Projekte zu ermitteln, ist leider kaum realistisch.
# (TODO - eher unbefriedigende Lösung, zudem wird hier nur nach Belegdaten abgegrenzt, daher kann der KPI negativ werden, wenn in der Periode mehr verrechnet als neu bestellt wurde)
class Backlog(KPI):
    name = "Arbeitsvorrat"
    unit = "CHF"

    def compute(self, company, cost_center, from_date, to_date):
        ordered = OrderVolume().compute(company, cost_center, from_date, to_date)
        billed = BilledSales().compute(company, cost_center, from_date, to_date)
        return ordered - billed


# Nachkalkulationsabweichung = (Istkosten – Budgetkosten) / Budgetkosten
# Der Einfachheit halber auf Projektebene umgesetzt
# (Stunden basieren hier auf Selbstkosten, nicht Direktkosten)
# [OK-MZ]
class PostCalcDeviation(KPI):
    name = "Nachkalkulationsabweichung"
    unit = "%"

    # Datumsbereich: Alle ABGESCHLOSSENEN Projekte berücksichtigen, die im ang. Zeitraum irgendwann aktiv waren, d.h.
    # Startdatum <= to_date sowie
    # Enddatum >= from_date
    # (Nicht begonnene Projekte werden nicht berücksichtigt)
    def compute(self, company, cost_center, from_date, to_date):
        args = locals()
        del args['self']
        # NOTE - sum_expense_claim sowie Arbeit nach Aufwand hier ignorieren, da für Nachkalkulation irrelevant
        query = """SELECT SUM(actual_material_cost + sum_services + actual_labor_as_prime_cost) AS prime_cost_final,
                          SUM(planned_material_cost + services_offered + planned_hours_ilv) AS prime_cost_budget
            FROM `tabProject`
            WHERE `company` = %(company)s
            AND `status` = 'Completed'
            AND `actual_start_date` <= %(to_date)s
            AND `actual_end_date` >= %(from_date)s
            """
        if cost_center:
            query += " AND cost_center = %(cost_center)s"
        data = frappe.db.sql(query, args, as_dict=True)
        if data[0].prime_cost_budget:
            return 100 * (data[0].prime_cost_final - data[0].prime_cost_budget) / data[0].prime_cost_budget
        else:
            return 0
    #    return self.material_budget() + self.thirdparty_budget() + self.expenses_budget() + self.labor_direct_cost_budget() + self.labor_direct_cost_by_effort_budget()


# ======================================================
# --- FINANCE KPIs ---
# ======================================================

# Umsatz
# [OK-MZ]
class Sales(KPI):
    name = "Umsatz"
    unit = "CHF"

    def compute(self, company, cost_center, from_date, to_date):
        args = locals()
        del args['self']
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
        return total_sales[0][0] or 0


# Umsatzwachstum (YoY) = (Umsatz – Vorjahr) / Vorjahr
# [OK-MZ]
class SalesGrowth(KPI):
    name = "Umsatzwachstum (YoY)"
    unit = "%"

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
    name = "Umsatz in % zum Budget"
    unit = "%"

    def compute(self, company, cost_center, from_date, to_date):
        sales = Sales().compute(company, cost_center, from_date, to_date)
        # `budget_01`+`budget_02`+...
        budget_months = "+".join(["`budget_%02d`" % x for x in range(from_date.month,to_date.month+1)])
        budget_filters = {
            "name_prefix": "Budget",
            "company": company,
            "fiscal_year": from_date.year
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
            SELECT SUM({budget_months}) AS `sales_budget`
            FROM `tabInnomat Budget Account`
            LEFT JOIN `tabAccount` ON `tabInnomat Budget Account`.`account` = `tabAccount`.`name`
            WHERE `tabInnomat Budget Account`.`parent` = '{budget_name}' AND `tabInnomat Budget Account`.`root_type`= 'Income'
            AND LEFT(`tabInnomat Budget Account`.`account`, 4) IN ('3000', '3200', '3400')
            """.format(budget_months=budget_months, budget_name=budget_name)
        data = frappe.db.sql(query, as_dict=True)
        if data[0].sales_budget:
            return 100 * sales / data[0].sales_budget
        else:
            return 0


# EBITDA = Earnings before Interest, Taxes, Depreciation and Amortization
# [OK-MZ]
class EBITDA(KPI):
    name = "EBITDA"
    unit = "CHF"

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
    unit = "CHF"

    def compute(self, company, cost_center, from_date, to_date, da=False):
        da_condition = " AND account_type != 'Depreciation' " if da else ''
        query = """
            SELECT SUM(gle.credit - gle.debit) AS ebit_da
            FROM `tabGL Entry` gle
            INNER JOIN `tabAccount` acc ON gle.account = acc.name
            WHERE gle.account IN (
                SELECT name FROM `tabAccount`
                WHERE report_type = 'Profit and Loss'
                {da_condition}
                AND (account_type != 'Expense Account' OR expense_account_classification NOT IN ('Interest', 'Tax'))
                AND company = '{company}'
            )
            AND gle.voucher_type != 'Period Closing Voucher'
            AND gle.company = '{company}'
            AND gle.posting_date BETWEEN '{from_date}' AND '{to_date}'
            AND gle.docstatus = 1
            """.format(da_condition=da_condition, company=company, from_date=from_date, to_date=to_date)
        if cost_center:
            query += " AND gle.cost_center = '{cost_center}'".format(cost_center=cost_center)
        data = frappe.db.sql(query, as_dict=True)
        return data[0].ebit_da or 0


# EBITDA-Marge = EBITDA / Umsatz
# [OK-MZ]
class EBITDAMargin(KPI):
    name = "EBITDA-Marge"
    unit = "%"

    def compute(self, company, cost_center, from_date, to_date):
        ebitda = EBITDA().compute(company, cost_center, from_date, to_date)
        sales = Sales().compute(company, cost_center, from_date, to_date)
        return (ebitda / sales * 100) if sales else 0


# Offene Posten (OP)
# [OK-MZ]
class OpenPositions(KPI):
    name = "Offene Posten (OP)"
    unit = "CHF"

    def compute(self, company, cost_center, from_date, to_date):
        params = {"company": company, "ageing_based_on": "Due Date", "report_date": to_date, "range1":30, "range2":60, "range3":90, "range4":120}
        if cost_center:
            params['cost_center'] = cost_center # TODO - The cost center filter in this report seems to be broken: Fix it!
        rep = frappe.desk.query_report.run("Accounts Receivable Summary", params)
        totals = rep['result'][-1]
        total_op = totals[6]
        return total_op


# Fällige OP
# [OK-MZ]
class OpenPositionsDue(KPI):
    name = "Fällige Offene Posten"
    unit = "CHF"

    def compute(self, company, cost_center, from_date, to_date):
        params = {"company": company, "ageing_based_on": "Due Date", "report_date": to_date, "range1":30, "range2":60, "range3":90, "range4":120}
        if cost_center:
            params['cost_center'] = cost_center
        rep = frappe.desk.query_report.run("Accounts Receivable Summary", params)
        totals = rep['result'][-1]
        total_op_due = 0
        for i in range(7,12): #col 7,8,9,10: range1 to range4; col 11: the rest
            total_op_due += totals[i] or 0
        return total_op_due


# Wert des Lagers zum Ende der Periode
# (ignoriert from_date)
# [OK-MZ]
class Stock(KPI):
    name = "Wert des Lagers zum Ende der Periode"
    unit = "CHF"

    def compute(self, company, cost_center, dummy, to_date):
        query = """
            SELECT SUM(gle.debit - gle.credit) FROM `tabGL Entry` gle
            INNER JOIN `tabAccount` acc ON gle.account = acc.name
            WHERE gle.account LIKE '1200%'
            AND gle.company = '{company}'
            AND gle.voucher_type != 'Period Closing Voucher'
            AND gle.posting_date < '{to_date}'
            AND gle.docstatus = 1
            """.format(company=company, to_date=to_date)
        if cost_center:
            query += " AND gle.cost_center = '{cost_center}'".format(cost_center=cost_center)
        val = frappe.db.sql(query)
        return val[0][0] or 0


# ROCE = EBIT / Capital Employed
# [OK-MZ]
class ROCE(KPI):
    name = "ROCE"
    unit = "%"

    def compute(self, company, cost_center, from_date, to_date):
        ebit = EBIT().compute(company, cost_center, from_date, to_date)
        ce = CapitalEmployed().compute(company, cost_center, 0, to_date)
        return ebit / ce if ce else 0


# Gebundenes Kapital = Eigenkapital + verz. FK - Cash = Summe(240) + Summe(2b = 280+290) - Summe(100) im Kontenplan
# [OK-MZ]
class CapitalEmployed(KPI):
    name = "Gebundenes Kapital"
    unit = "CHF"

    def compute(self, company, cost_center, dummy, to_date):
        # Sign: For 100, Debit - Credit is positive. For 2xx accounts, Credit - Debit is positive. To get 2xx - 100, just do sum(Credit-Debit)
        query = """
            SELECT SUM(gle.credit - gle.debit) AS ce
            FROM `tabGL Entry` gle
            INNER JOIN `tabAccount` acc ON gle.account = acc.name
            WHERE gle.account IN (
                SELECT name FROM `tabAccount`
                WHERE (parent_account LIKE '100 -%' OR parent_account LIKE '240 -%' OR parent_account LIKE '280 -%' OR parent_account LIKE '290 -%')
                AND company = '{company}'
            )
            AND gle.voucher_type != "Period Closing Voucher"
            AND gle.company = '{company}'
            AND gle.posting_date <= '{to_date}'
            AND gle.docstatus = 1
            """.format(company=company,to_date=to_date)
        if cost_center:
            query += " AND gle.cost_center = '{cost_center}'".format(cost_center=cost_center)
        data = frappe.db.sql(query, as_dict=True)
        return data[0].ce or 0


# ======================================================
# --- EMPLOYEE KPIs ---
# ======================================================

# Produktivität = Produktive Stunden / Anwesende Stunden [%]
# [OK-MZ]
class Productivity(KPI):
    name = "Produktivität"
    unit = "%"

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
    name = "Überzeit pro Mitarbeiter"
    unit = "h"

    def compute(self, company, cost_center, from_date, to_date):
        return 0.0

# Feriensaldo in Tagen pro Mitarbeiter
# NOTE - wird am Stichtag to_date berechnet, from_date wird ignoriert.
# [OK-MZ]
class VacationBalance(KPI):
    name = "Feriensaldo pro Mitarbeiter"
    unit = "d"

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
        return balance / len(employees)


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
    cols = [{"label": _("KPI"), "fieldname": "kpi_label", "fieldtype": "Data", "width": 260},{"label": _("Unit"), "fieldname": "unit", "fieldtype": "Data", "width": 50}]
    entities = [company] + [cc.name for cc in get_cost_centers(company)]

    for entity in entities:
        base = entity.lower().replace(" ", "_")
        cols.append({"label": f"{entity}<br>"+_("YTD"), "fieldname": f"{base}_ytd", "fieldtype": "Float", "width": 160, "precision": 2})
        cols.append({"label": f"{entity}<br>"+_("Period"), "fieldname": f"{base}_period", "fieldtype": "Float", "width": 160, "precision": 2})

    return cols


def get_data(company, from_date, to_date):
    """
    Compute KPI rows for YTD and Period columns.
    Uses all KPI classes defined previously.
    """

    # Year must be the same for both dates (eg. due to budget comparisons taking place)
    if from_date.year != to_date.year:
        return []

    # KPI classes grouped by section
    kpis = {
        "Verkauf": [OrderVolume(), OrderVolumeGrowth(), BookToBillRatio(), OrderVolumeTop5Share()],
        "Abwicklung": [BilledSales(), BillingRatio(), GrossMargin(), GrossMarginGrowth(), Backlog(), PostCalcDeviation()],
        "Finanzen": [Sales(), SalesGrowth(), SalesVsBudget(), EBITDA(), EBITDAMargin(),
                    OpenPositions(), OpenPositionsDue(), Stock(), ROCE()],
        "Mitarbeitende": [Productivity(), VacationBalance()], #OvertimeBalance()
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
            row = {"kpi_label": kpi.name, "unit": kpi.unit, "indent": 1}

            if kpi.multiline:
                # Special KPIs such as Top5 customers, with several lines returned as dict
                # NOTE - the line titles must be the same across cost centers as only the first ones are shown!!
                sub_data = []
                first_cc = True
                for cc in cost_centers:
                    base = (company if cc is None else cc).lower().replace(" ", "_")

                    ytd_data = kpi.compute(company, cc, ytd_from, ytd_to)
                    period_data = kpi.compute(company, cc, from_date, to_date)

                    row[f"{base}_ytd"] = 0
                    row[f"{base}_period"] = 0
                    row_cnt = 0

                    for d in ytd_data:
                        if first_cc:
                            sub_data.append({"kpi_label": d, "indent": 2})
                        sub_data[row_cnt][f"{base}_ytd"] = ytd_data[d]
                        sub_data[row_cnt][f"{base}_period"] = period_data.get(d)
                        row[f"{base}_ytd"] += ytd_data[d]
                        row[f"{base}_period"] += period_data.get(d, 0)
                        row_cnt += 1

                    first_cc = False
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

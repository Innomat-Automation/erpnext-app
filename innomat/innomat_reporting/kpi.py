# Copyright (c) 2026, Innomat-Automation AG, libracore AG and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from innomat.innomat.scripts.project import update_project, get_fallback_ilv_rate

# Verwendete Übersetzungen:
# ist = current, Direktkosten = direct cost, Herstellkosten = production cost, Selbstkosten = prime cost

def get_project_kpis(project):
    return ProjectKPI(project)

class ProjectKPI:
    def __init__(self, project):
        self.project_name = project
        self.project_doc = frappe.get_doc("Project", project)
        sales_order = self.project_doc.get('sales_order')
        # Update project parameters (this is also done by a daily background job)
        update_project({'name': self.project_name, 'sales_order': sales_order})
        # Reload project doc after update
        self.project_doc = frappe.get_doc("Project", project)
        # Link other docs, if any
        if self.project_doc.company:
            self.company_doc = frappe.get_doc("Company", self.project_doc.company)
        if sales_order:
            self.sales_order_doc = frappe.get_doc("Sales Order", sales_order)
            # Quotation is currently not required
            #if self.sales_order_doc.items and self.sales_order_doc.items[0].prevdoc_docname:
            #    self.quotation_doc = frappe.get_doc("Quotation", self.sales_order_doc.items[0].prevdoc_docname)
        # Preload task details, needed by several KPI functions
        self.details_by_role = self._load_role_details_from_tasks()

    # Fortschritt Cost-to-cost = Kosten IST / Kosten FC (Basis: SK)
    def cost_to_cost_progress(self):
        fc = self.prime_cost_forecast()
        if fc > 0:
            return self.prime_cost_current() / fc
        return 1 # Forecast 0 = der Fortschritt beträgt von Anfang an 100%

    # Verrechnungsgrad Selbstkosten = verrechneter Betrag / SK
    def billed_prime_cost(self):
        prime_cost = self.prime_cost_current()
        if prime_cost > 0:
            return self.project_doc.total_billed_amount / prime_cost
        return 1 # Keine Selbstkosten = die Selbstkosten sind zu 100% verrechnet

    # Gesamtkosten IST, DK
    def direct_cost_current(self):
        return self.material_current() + self.thirdparty_current() + self.expenses_current() + self.labor_direct_cost_current() + self.labor_direct_cost_by_effort_current()

    # Gesamtkosten IST, HK
    def production_cost_current(self):
        return self.material_current() + self.thirdparty_current() + self.expenses_current() + self.labor_production_cost_current() + self.labor_production_cost_by_effort_current()

    # Gesamtkosten IST, SK
    def prime_cost_current(self):
        return self.material_current() + self.thirdparty_current() + self.expenses_current() + self.labor_prime_cost_current() + self.labor_prime_cost_by_effort_current()

    # Materialkosten IST
    def material_current(self):
        return self.project_doc.actual_material_cost # TODO, double-check this is correct (item selection and valuation rates used)

    # Dienstleistungen Dritter, IST
    def thirdparty_current(self):
        return self.project_doc.sum_services # TODO, double-check this is correct (item selection and valuation rates used)

    # Spesen IST
    def expenses_current(self):
        return self.project_doc.sum_expense_claim

    # Personalkosten IST, DK
    def labor_direct_cost_current(self):
        return self.project_doc.actual_labor_as_direct_cost

    # Personalkosten "nach Aufwand" IST, DK
    def labor_direct_cost_by_effort_current(self):
        return self.project_doc.labor_by_effort_as_direct_cost

    # Personalkosten IST, HK
    def labor_production_cost_current(self):
        return self.project_doc.actual_labor_as_production_cost

    # Personalkosten "nach Aufwand" IST, HK
    def labor_production_cost_by_effort_current(self):
        return self.project_doc.labor_by_effort_as_production_cost

    # Personalkosten IST, SK
    def labor_prime_cost_current(self):
        return self.project_doc.actual_labor_as_prime_cost

    # Personalkosten "nach Aufwand" IST, SK
    def labor_prime_cost_by_effort_current(self):
        return self.project_doc.labor_by_effort_as_prime_cost

    # Gesamtkosten BUDGET, DK
    def direct_cost_budget(self):
        return self.material_budget() + self.thirdparty_budget() + self.labor_direct_cost_budget() + self.labor_direct_cost_by_effort_budget()

    # Gesamtkosten BUDGET, HK
    def production_cost_budget(self):
        return self.material_budget() + self.thirdparty_budget() + self.labor_production_cost_budget() + self.labor_production_cost_by_effort_budget()

    # Gesamtkosten BUDGET, SK
    def prime_cost_budget(self):
        return self.material_budget() + self.thirdparty_budget() + self.labor_prime_cost_budget() + self.labor_prime_cost_by_effort_budget()

    # Materialkosten BUDGET
    def material_budget(self):
        return self.project_doc.planned_material_cost

    # Dienstleistungen Dritter, BUDGET
    def thirdparty_budget(self):
        return self.project_doc.services_offered # TODO, double-check this is correct (item selection and valuation rates used)

    # Personalkosten BUDGET (DK, indirekt anhand ILV)
    def labor_direct_cost_budget(self):
        return self.prime_cost_to_direct_cost(self.project_doc.planned_hours_ilv)

    # Personalkosten "nach Aufwand" BUDGET (DK, indirekt anhand ILV)
    def labor_direct_cost_by_effort_budget(self):
        return self.prime_cost_to_direct_cost(self.project_doc.planned_hours_by_effort_ilv)

    # Personalkosten BUDGET (HK, indirekt anhand ILV)
    def labor_production_cost_budget(self):
        return self.prime_cost_to_production_cost(self.project_doc.planned_hours_ilv)

    # Personalkosten "nach Aufwand" BUDGET (HK, indirekt anhand ILV)
    def labor_production_cost_by_effort_budget(self):
        return self.prime_cost_to_production_cost(self.project_doc.planned_hours_by_effort_ilv)

    # Personalkosten BUDGET (ILV, entspricht SK)
    def labor_prime_cost_budget(self):
        return self.project_doc.planned_hours_ilv

    # Personalkosten "nach Aufwand" BUDGET (ILV, entspricht SK)
    def labor_prime_cost_by_effort_budget(self):
        return self.project_doc.planned_hours_by_effort_ilv

    # Gesamtkosten FORECAST, DK
    def direct_cost_forecast(self):
        return self.material_forecast() + self.thirdparty_forecast() + self.labor_direct_cost_forecast() + self.labor_direct_cost_by_effort_forecast()

    # Gesamtkosten FORECAST, HK
    def production_cost_forecast(self):
        return self.material_forecast() + self.thirdparty_forecast() + self.labor_production_cost_forecast() + self.labor_production_cost_by_effort_forecast()

    # Gesamtkosten FORECAST, SK
    def prime_cost_forecast(self):
        return self.material_forecast() + self.thirdparty_forecast() + self.labor_prime_cost_forecast() + self.labor_prime_cost_by_effort_forecast()

    # Dienstleistungen FORECAST - wir haben kein Matching zwischen Budget- und Istpositionen, daher Forecast = max(Budget, Ist)
    def thirdparty_forecast(self):
        return max(self.thirdparty_budget(), self.thirdparty_current())

    # Materialkosten FORECAST - wir haben kein Matching zwischen Budget- und Istpositionen, daher Forecast = max(Budget, Ist)
    def material_forecast(self):
        return max(self.material_budget(), self.material_current())

    # Personalkosten FORECAST, DK
    def labor_direct_cost_forecast(self):
        # Die Forecasts anhand verbleibender Task-Stunden und deren durchschnittlichen Kostensätzen werden jetzt in project.py vorberechnet
        return self.project_doc.forecast_labor_as_direct_cost
        #return sum(map(lambda role: role['forecast_direct_cost'], self.details_by_role))

    # Personalkosten "nach Aufwand" FORECAST, DK
    def labor_direct_cost_by_effort_forecast(self):
        return self.project_doc.forecast_labor_by_effort_as_direct_cost
        #return max(self.labor_direct_cost_by_effort_current(), self.labor_direct_cost_by_effort_budget())

    # Personalkosten FORECAST, HK
    def labor_production_cost_forecast(self):
        return self.project_doc.forecast_labor_as_production_cost
        #return sum(map(lambda role: role['forecast_production_cost'], self.details_by_role))

    # Personalkosten "nach Aufwand" FORECAST, HK
    def labor_production_cost_by_effort_forecast(self):
        return self.project_doc.forecast_labor_by_effort_as_production_cost
        #return max(self.labor_production_cost_by_effort_current(), self.labor_production_cost_by_effort_budget())

    # Personalkosten FORECAST, SK
    def labor_prime_cost_forecast(self):
        return self.project_doc.forecast_labor_as_prime_cost
        #return sum(map(lambda role: role['forecast_prime_cost'], self.details_by_role))

    # Personalkosten "nach Aufwand" FORECAST, SK
    def labor_prime_cost_by_effort_forecast(self):
        return self.project_doc.forecast_labor_by_effort_as_prime_cost
        #return max(self.labor_prime_cost_by_effort_current(), self.labor_prime_cost_by_effort_budget())

    # EBIT IST = "Mögliche Anzahlungen" = Ertrag IST - Total Selbstkosten IST
    def ebit_current(self):
        return self.revenue_current() - self.prime_cost_current()

    # EBIT BUDGET = Ertrag BUDGET - Total Selbstkosten BUDGET
    def ebit_budget(self):
        return self.revenue_budget() - self.prime_cost_budget()

    # EBIT FORECAST = Ertrag FORECAST - Total Selbstkosten FORECAST
    def ebit_forecast(self):
        return self.revenue_forecast() - self.prime_cost_forecast()

    # Ertrag IST = verrechnet
    def revenue_current(self):
        return self.project_doc.total_billed_amount
        #return frappe.db.get_value("Sales Invoice", {"project": self.project_name, "docstatus": 1},"sum(base_net_total)") or 0

    # Ertrag BUDGET = Bestellbetrag (= Verkaufspreis, Auftragsvolumen, ...)
    def revenue_budget(self):
        return self.project_doc.planned_revenue + self.project_doc.planned_revenue_by_effort
        #return self.project_doc.total_sales_amount - sollte dasselbe zurückgeben

    # Ertrag FORECAST
    # Dies berücksichtigt verrechenbare Stunden "nach Aufwand"
    # TODO - evtl. noch Gutschriften, zusätzliche Salesorders (Nachkalkulation) etc. berücksichtigen...
    def revenue_forecast(self):
        return self.project_doc.forecast_revenue + self.project_doc.forecast_revenue_by_effort

    # Ausstehender Rechnungsbetrag (OP Debitoren)
    def outstanding_amount(self):
        outstanding = frappe.db.get_value("Sales Invoice", {"project": self.project_name, "docstatus": 1},"sum(outstanding_amount)") or 0
        return outstanding

    # Zuschlag Gemeinkosten in Prozent (Berechnungsgrundlage für Budgetwerte)
    def supplement_gk(self):
        gk = 0
        if self.sales_order_doc and self.sales_order_doc.cost_supplement_gk:
            gk = self.sales_order_doc.cost_supplement_gk
        elif self.company_doc and self.company_doc.cost_supplement_gk:
            gk = self.company_doc.cost_supplement_gk
        return gk

    # Zuschlag Verwaltungs- und Vertriebskosten in Prozent (Berechnungsgrundlage für Budgetwerte)
    def supplement_vvgk(self):
        vvgk = 0
        if self.sales_order_doc and self.sales_order_doc.cost_supplement_vvgk:
            vvgk = self.sales_order_doc.cost_supplement_vvgk
        elif self.company_doc and self.company_doc.cost_supplement_vvgk:
            vvgk = self.company_doc.cost_supplement_vvgk
        return vvgk

    # Umrechnung Selbstkosten zu Herstellkosten (nur für Budgetwerte)
    def prime_cost_to_production_cost(self, value):
        return value / (1 + 0.01 * self.supplement_vvgk())

    # Umrechnung Selbstkosten zu Direktkosten (nur für Budgetwerte)
    def prime_cost_to_direct_cost(self, value):
        return self.prime_cost_to_production_cost(value) / (1 + 0.01 * self.supplement_gk())

    # Umrechnung Direktkosten zu Selbstkosten (nur für Budgetwerte)
    def direct_cost_to_prime_cost(self, value):
        return value * (1 + 0.01 * self.supplement_gk()) * (1 + 0.01 * self.supplement_vvgk())

    # Summarische Darstellung der Tasks gruppiert nach Artikel = Rolle (wird durch Funktion _load_role_details_from_tasks vorberechnet)
    def hours_and_costs_by_role(self):
        return self.details_by_role

    # Total Arbeitsstunden über alle Rollen IST
    def total_hours_current(self):
        return self.project_doc.actual_labor_hours

    # Total Arbeitsstunden "nach Aufwand" über alle Rollen IST
    def total_hours_by_effort_current(self):
        return self.project_doc.labor_by_effort_hours

    # Total Arbeitsstunden über alle Rollen BUDGET
    def total_hours_budget(self):
        return self.project_doc.planned_hours
        #return sum(map(lambda role: role['budget_hours'] if not role['by_effort'] else 0, self.details_by_role))

    # Total Arbeitsstunden "nach Aufwand" über alle Rollen BUDGET
    def total_hours_by_effort_budget(self):
        return self.project_doc.planned_hours_by_effort

    # Total Arbeitsstunden über alle Rollen FORECAST
    def total_hours_forecast(self):
        return self.project_doc.forecast_hours
        #return sum(map(lambda role: role['forecast_hours'], self.details_by_role))

    # Total Arbeitsstunden "nach Aufwand" über alle Rollen FORECAST
    def total_hours_by_effort_forecast(self):
        return self.project_doc.forecast_hours_by_effort
        #return max(self.total_hours_by_effort_current(), self.total_hours_by_effort_budget())
        #return sum(map(lambda role: role['forecast_hours'], self.details_by_role))

    def _load_role_details_from_tasks(self):
        # Das Stundenbudget sowie die Istwerte für Stunden und Kosten sind auf dem Task bereits vorhanden.
        # Tasks mit gleichem Dienstleistungsartikel (Rolle) werden zusammengruppiert und die Werte aufsummiert.
        # Der ILV-Satz zur Berechnung des Kostenbudgets wird aus dem Artikelstamm gezogen, falls er im Task fehlt.
        # Die Fertigstellung wird summarisch betrachtet - alle Tasks einer Gruppe müssen abgeschlossen oder abgebrochen sein.
        fallback_ilv_rate = get_fallback_ilv_rate()
        details_by_role = frappe.db.sql("""SELECT
        `tabItem`.`item_name` AS `role`,
        `tabTask`.`by_effort` AS `by_effort`,
        SUM(`tabTask`.`expected_time`) AS `budget_hours`,
        SUM(`tabTask`.`actual_time`) AS `actual_hours`,
        SUM(IF(`tabTask`.`status` IN ('Cancelled', 'Completed'), `tabTask`.`actual_time`, GREATEST(`tabTask`.`expected_time`,`tabTask`.`actual_time`))) AS `forecast_hours`,
        SUM(`tabTask`.`expected_time` * IFNULL(NULLIF(IFNULL(NULLIF(`tabTask`.`ilv_rate`, 0), `tabItem`.`ilv_rate`), 0), {fallback_ilv_rate})) AS `budget_prime_cost`,
        SUM(`tabTask`.`actual_labor_as_prime_cost`) AS `actual_prime_cost`,
        SUM(`tabTask`.`actual_labor_as_production_cost`) AS `actual_production_cost`,
        SUM(`tabTask`.`actual_labor_as_direct_cost`) AS `actual_direct_cost`,
        IF(SUM(IF(`tabTask`.`status` NOT IN ('Cancelled','Completed'), 1, 0))>0, 0, 1) AS `all_completed`
        FROM
        `tabTask`
        LEFT JOIN `tabItem` ON `tabTask`.`item_code` = `tabItem`.`item_code`
        WHERE `tabTask`.`project` = '{project}'
        GROUP BY `tabTask`.`item_code`, `tabTask`.`by_effort`
        """.format(project=self.project_name, fallback_ilv_rate=fallback_ilv_rate), as_dict=True)
        total_role_hours = 0
        total_role_costs_prime = 0
        total_role_costs_prod = 0
        total_role_costs_direct = 0
        # Forecast-Werte für offene Tasks berechnen
        for line in details_by_role:
            line['budget_production_cost'] = self.prime_cost_to_production_cost(line['budget_prime_cost'])
            line['budget_direct_cost'] = self.prime_cost_to_direct_cost(line['budget_prime_cost'])
            #
            # NOTE - Der folgende Code lässt bei Tasks nach Aufwand das Budget mitwachsen, wenn der Aufwand das Budget übersteigt
            #        Somit wäre das ausgewiesene Budget immer identisch mit dem Forecast und niemals überschritten
            #        Das wird jetzt aber nicht so gemacht, stattdessen wird die Überschreitung als solche ausgewiesen und dafür einnahmenseitig die zusätzlichen Stunden ebenfalls.
            #
            #if line['by_effort']:
            #    if line['actual_hours'] > line['budget_hours'] or line['all_completed']:
            #        line['budget_hours'] = line['actual_hours']
            #    if line['actual_prime_cost'] > line['budget_prime_cost'] or line['all_completed']:
            #        line['budget_prime_cost'] = line['actual_prime_cost']
            #    if line['actual_production_cost'] > line['budget_production_cost'] or line['all_completed']:
            #        line['budget_production_cost'] = line['actual_production_cost']
            #    if line['actual_direct_cost'] > line['budget_direct_cost'] or line['all_completed']:
            #        line['budget_direct_cost'] = line['actual_direct_cost']
            if line['all_completed']:
                line['forecast_prime_cost'] = line['actual_prime_cost']
                line['forecast_production_cost'] = line['actual_production_cost']
                line['forecast_direct_cost'] = line['actual_direct_cost']
            else:
                prime_fc_rate = 0
                prod_fc_rate = 0
                direct_fc_rate = 0
                if line['actual_hours'] > 0:
                    prime_fc_rate = line['actual_prime_cost'] / line['actual_hours']
                    prod_fc_rate = line['actual_production_cost'] / line['actual_hours']
                    direct_fc_rate = line['actual_direct_cost'] / line['actual_hours']
                elif line['budget_hours'] > 0:
                    prime_fc_rate = line['budget_prime_cost'] / line['budget_hours']
                    prod_fc_rate = self.prime_cost_to_production_cost(prime_fc_rate)
                    direct_fc_rate = self.prime_cost_to_direct_cost(prime_fc_rate)
                delta_hours = line['forecast_hours'] - line['actual_hours']
                line['forecast_prime_cost'] = line['actual_prime_cost'] + delta_hours * prime_fc_rate
                line['forecast_production_cost'] = line['actual_production_cost'] + delta_hours * prod_fc_rate
                line['forecast_direct_cost'] = line['actual_direct_cost'] + delta_hours * direct_fc_rate
            total_role_hours += line['actual_hours']
            total_role_costs_prime += line['actual_prime_cost']
            total_role_costs_prod += line['actual_production_cost']
            total_role_costs_direct += line['actual_direct_cost']
        # Allfällige Arbeit ohne Task (nur bei internen Projekten erlaubt) als "Sonstige" aufführen
        # TODO - da ist jetzt "by effort" mit drin. Auf Projektebene läuft dies separat. Passt das so??
        other_hours = self.project_doc.actual_time - total_role_hours
        other_costs_prime = self.project_doc.actual_labor_as_prime_cost + self.project_doc.labor_by_effort_as_prime_cost - total_role_costs_prime
        other_costs_prod = self.project_doc.actual_labor_as_production_cost + self.project_doc.labor_by_effort_as_production_cost - total_role_costs_prod
        other_costs_direct = self.project_doc.actual_labor_as_direct_cost + self.project_doc.labor_by_effort_as_direct_cost - total_role_costs_direct
        if other_hours != 0 or other_costs_prime != 0 or other_costs_direct != 0:
            other_line = {'role': 'Sonstige', 'budget_hours': 0, 'budget_prime_cost': 0, 'budget_production_cost': 0, 'budget_direct_cost': 0, 'actual_hours': other_hours, 'actual_prime_cost': other_costs_prime, 'actual_production_cost': other_costs_prod, 'actual_direct_cost': other_costs_direct, 'forecast_hours': other_hours, 'forecast_prime_cost': other_costs_prime, 'forecast_production_cost': other_costs_prod, 'forecast_direct_cost': other_costs_direct, 'all_completed': 1, 'by_effort': 0}
            details_by_role.append(other_line)
        print(details_by_role)
        return details_by_role
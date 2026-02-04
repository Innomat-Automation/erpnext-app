# Copyright (c) 2026, Innomat-Automation AG, libracore AG and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from innomat.innomat.scripts.project import update_project

# Verwendete Übersetzungen:
# ist = current, Direktkosten = direct cost, Herstellkosten = production cost, Selbstkosten = prime cost

def get_project_kpis(project):
    return ProjectKPI(project)

class ProjectKPI:
    def __init__(self, project):
        self.project_name = project
        self.project_doc = frappe.get_doc("Project", project)
        # Update project parameters (this is also done by a daily background job)
        sales_order = self.project_doc.get('sales_order')
        update_project({'name': self.project_name, 'sales_order': sales_order})
        # Link other docs, if any
        if self.project_doc.company:
            self.company_doc = frappe.get_doc("Company", self.project_doc.company)
        if sales_order:
            self.sales_order_doc = frappe.get_doc("Sales Order", sales_order)
            # Quotation is currently not required
            #if self.sales_order_doc.items and self.sales_order_doc.items[0].prevdoc_docname:
            #    self.quotation_doc = frappe.get_doc("Quotation", self.sales_order_doc.items[0].prevdoc_docname)
        # Preload task details, needed by several KPI functions
        self.task_details = self._load_task_durations_and_costs()

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
            return self.invoiced_amount() / prime_cost
        return 1 # Keine Selbstkosten = die Selbstkosten sind zu 100% verrechnet

    # Gesamtkosten IST, DK
    def direct_cost_current(self):
        return self.material_current() + self.thirdparty_current() + self.expenses_current() + self.labor_direct_cost_current()

    # Gesamtkosten IST, HK
    def production_cost_current(self):
        return self.material_current() + self.thirdparty_current() + self.expenses_current() + self.labor_production_cost_current()

    # Gesamtkosten IST, SK
    def prime_cost_current(self):
        return self.material_current() + self.thirdparty_current() + self.expenses_current() + self.labor_prime_cost_current()

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

    # Personalkosten IST, HK
    def labor_prod_cost_current(self):
        return self.project_doc.actual_labor_as_production_cost

    # Personalkosten IST, SK
    def labor_prime_cost_current(self):
        return self.project_doc.actual_labor_as_prime_cost

    # Gesamtkosten BUDGET, DK
    def direct_cost_budget(self):
        return self.material_budget() + self.thirdparty_budget() + self.prime_cost_to_direct_cost(self.labor_prime_cost_budget())

    # Gesamtkosten BUDGET, HK
    def production_cost_budget(self):
        return self.material_budget() + self.thirdparty_budget() + self.prime_cost_to_production_cost(self.labor_prime_cost_budget())

    # Gesamtkosten BUDGET, SK
    def prime_cost_budget(self):
        return self.material_budget() + self.thirdparty_budget() + self.labor_prime_cost_budget()

    # Materialkosten BUDGET
    def material_budget(self):
        return self.project_doc.planned_material_cost

    # Dienstleistungen Dritter, BUDGET
    def thirdparty_budget(self):
        return self.project_doc.services_offered # TODO, double-check this is correct (item selection and valuation rates used)

    # Personalkosten BUDGET (DK, indirekt anhand ILV)
    def labor_direct_cost_budget(self):
        return self.prime_cost_to_direct_cost(self.project_doc.planned_hours_ilv)

    # Personalkosten BUDGET (ILV, entspricht SK)
    def labor_prime_cost_budget(self):
        return self.project_doc.planned_hours_ilv

    # Gesamtkosten FORECAST, DK
    def direct_cost_forecast(self):
        return self.material_forecast() + self.thirdparty_forecast() + self.labor_direct_cost_forecast()

    # Gesamtkosten FORECAST, SK
    def prime_cost_forecast(self):
        return self.material_forecast() + self.thirdparty_forecast() + self.labor_prime_cost_forecast()

    # Dienstleistungen FORECAST - wir haben kein Matching zwischen Budget- und Istpositionen, daher Forecast = max(Budget, Ist)
    def thirdparty_forecast(self):
        return max(self.thirdparty_budget(), self.thirdparty_current())

    # Materialkosten FORECAST - wir haben kein Matching zwischen Budget- und Istpositionen, daher Forecast = max(Budget, Ist)
    def material_forecast(self):
        return max(self.material_budget(), self.material_current())

    # Personalkosten FORECAST, DK
    def labor_direct_cost_forecast(self):
        # Für eine präzise Kostenschätzung basiert dieser Forecast auf den Tasks (verbleibende Stunden werden so mit realistischen Kostensätzen geschätzt)
        # Projektstunden ohne Task werden dennoch berücksichtigt, da self.task_details ggf. eine Zeile "Sonstige" enthält.
        forecast_hours = sum(map(lambda task: task['forecast_direct_cost'], self.task_details))
        return forecast_hours

    # Personalkosten FORECAST, SK
    def labor_prime_cost_forecast(self):
        # Für eine präzise Kostenschätzung basiert dieser Forecast auf den Tasks (verbleibende Stunden werden so mit realistischen Kostensätzen geschätzt)
        # Projektstunden ohne Task werden dennoch berücksichtigt, da self.task_details ggf. eine Zeile "Sonstige" enthält.
        forecast_hours = sum(map(lambda task: task['forecast_prime_cost'], self.task_details))
        return forecast_hours

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
        return self.invoiced_amount()

    # Ertrag BUDGET = Bestellbetrag (= Verkaufspreis, Auftragsvolumen, ...)
    def revenue_budget(self):
        return self.project_doc.total_sales_amount

    # Ertrag FORECAST
    # TODO - evtl. abweichend von Budget (Gutschrift auf Salesorder? / Zusatz-Salesorder für Nachkalkulation? etc.)
    def revenue_forecast(self):
        return self.revenue_budget()

    # Verrechneter Betrag
    # TODO - Gutschriften berücksichtigen
    def invoiced_amount(self):
        invoiced = frappe.db.get_value("Sales Invoice", {"project": self.project_name, "docstatus": 1},"sum(base_net_total)") or 0
        return invoiced

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

    # Summarische Darstellung der Tasks gruppiert nach Artikel (wird durch Funktion _load_task_details vorberechnet)
    def task_durations_and_costs(self):
        return self.task_details

    def _load_task_durations_and_costs(self):
        # Das Stundenbudget sowie die Istwerte für Stunden und Kosten sind auf dem Task bereits vorhanden.
        # Tasks mit gleichem Dienstleistungsartikel werden zusammengruppiert und die Werte aufsummiert.
        # Der ILV-Satz zur Berechnung des Kostenbudgets wird aus dem Artikelstamm gezogen, falls er im Task fehlt.
        # Die Fertigstellung wird summarisch betrachtet - alle Tasks einer Gruppe müssen abgeschlossen oder abgebrochen sein.
        task_details = frappe.db.sql("""SELECT
        `tabItem`.`item_name` AS `activity`,
        SUM(`tabTask`.`expected_time`) AS `budget_hours`,
        SUM(`tabTask`.`expected_time` * IFNULL(NULLIF(`tabTask`.`ilv_rate`, 0), `tabItem`.`ilv_rate`)) AS `budget_prime_cost`,
        SUM(`tabTask`.`actual_time`) AS `actual_hours`,
        SUM(`tabTask`.`actual_labor_as_prime_cost`) AS `actual_prime_cost`,
        SUM(`tabTask`.`actual_labor_as_direct_cost`) AS `actual_direct_cost`,
        IF(SUM(IF(`tabTask`.`status` NOT IN ('Cancelled','Completed'), 1, 0))>0, 0, 1) AS `all_completed`
        FROM
        `tabTask`
        LEFT JOIN `tabItem` ON `tabTask`.`item_code` = `tabItem`.`item_code`
        WHERE `tabTask`.`project` = '{project}'
        GROUP BY `tabTask`.`item_code`
        """.format(project=self.project_name), as_dict=True)
        total_task_hours = 0
        total_task_costs_p = 0
        total_task_costs_d = 0
        # Forecast-Werte für offene Tasks berechnen
        for line in task_details:
            if line['all_completed']:
                line['forecast_hours'] = line['actual_hours']
                line['forecast_prime_cost'] = line['actual_prime_cost']
                line['forecast_direct_cost'] = line['actual_direct_cost']
            else:
                prime_fc_rate = 0
                direct_fc_rate = 0
                if line['budget_hours'] > 0:
                    prime_fc_rate = line['budget_prime_cost'] / line['budget_hours']
                    direct_fc_rate = self.prime_cost_to_direct_cost(prime_fc_rate)
                if line['actual_hours'] > 0:
                    prime_fc_rate = line['actual_prime_cost'] / line['actual_hours']
                    direct_fc_rate = line['actual_direct_cost'] / line['actual_hours']
                line['forecast_hours'] = max(line['budget_hours'], line['actual_hours'])
                delta_hours = line['forecast_hours'] - line['actual_hours']
                line['forecast_prime_cost'] = line['actual_prime_cost'] + delta_hours * prime_fc_rate
                line['forecast_direct_cost'] = line['actual_direct_cost'] + delta_hours * direct_fc_rate
            total_task_hours += line['actual_hours']
            total_task_costs_p += line['actual_prime_cost']
            total_task_costs_d += line['actual_direct_cost']
        # Allfällige Arbeit ohne Task (nur bei internen Projekten erlaubt) als "Sonstige" aufführen
        other_hours = self.project_doc.actual_time - total_task_hours
        other_costs_p = self.project_doc.actual_labor_as_prime_cost - total_task_costs_p
        other_costs_d = self.project_doc.actual_labor_as_direct_cost - total_task_costs_d
        if other_hours != 0 or other_costs_p != 0 or other_costs_d != 0:
            other_line = {'activity': 'Sonstige', 'budget_hours': 0, 'budget_prime_cost': 0, 'actual_hours': other_hours, 'actual_prime_cost': other_costs_p, 'actual_direct_cost': other_costs_d, 'forecast_hours': other_hours, 'forecast_prime_cost': other_costs_p, 'forecast_direct_cost': other_costs_d, 'all_completed': 1}
            task_details.append(other_line)

        return task_details
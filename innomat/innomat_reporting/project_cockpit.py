# -*- coding: utf-8 -*-
# Copyright (c) 2025, Innomat-Automation AG
# Projekt-Cockpit Berechnungen

import frappe
from frappe import _

# Konstanten (später aus Einstellungen laden)
OVERHEAD_RATE = 0.26  # 26% Gemeinkosten auf Personalkosten
ADMIN_RATE = 0.12     # 12% Verwaltungs- und Vertriebskosten


def get_project_cockpit_data(project_name):
    """
    Hauptfunktion: Berechnet alle KPIs für das Projekt-Cockpit

    Returns:
        dict: Alle berechneten Werte für das Cockpit
    """
    project = frappe.get_doc("Project", project_name)

    # Budget aus BOM berechnen
    budget = calculate_budget_from_bom(project)

    # Ist-Kosten aus Projekt-Feldern holen
    actual = get_actual_costs(project)

    # Fortschritt über Earned Value berechnen
    progress = calculate_progress(project, budget)

    # Forecast berechnen
    forecast = calculate_forecast(actual, progress, budget)

    # EBIT berechnen
    ebit = calculate_ebit(project, budget, forecast)

    # Fakturierung und OP
    billing = calculate_billing_metrics(project)

    return {
        "budget": budget,
        "actual": actual,
        "progress": progress,
        "forecast": forecast,
        "ebit": ebit,
        "billing": billing
    }


def calculate_budget_from_bom(project):
    """
    Berechnet Budget aus den BOM der Sales Order Items

    Returns:
        dict: Budget-Werte nach Kategorie
    """
    budget = {
        "hours_by_item": {},      # {item_code: qty in Stunden}
        "cost_by_item": {},       # {item_code: amount in CHF}
        "hours_cost": 0,          # Gesamte Personalkosten
        "material_cost": 0,       # Materialkosten
        "services_cost": 0,       # Fremdleistungen
        "direct_cost": 0,         # Direktkosten gesamt
        "overhead": 0,            # Gemeinkosten
        "hk": 0                   # Herstellungskosten
    }

    if not project.sales_order:
        # Fallback auf Custom Fields
        budget["hours_cost"] = project.stundenbudget_plan or 0
        budget["material_cost"] = project.planned_material_cost or 0
        budget["services_cost"] = project.services_offered or 0
    else:
        # BOM Items aus Sales Order holen
        so_items = frappe.get_all("Sales Order Item",
            filters={"parent": project.sales_order, "docstatus": 1},
            fields=["from_bom", "item_name"])

        for so_item in so_items:
            if not so_item.from_bom:
                continue

            bom_items = frappe.get_all("BOM Item",
                filters={"parent": so_item.from_bom},
                fields=["item_code", "qty", "amount", "uom"])

            for bom_item in bom_items:
                if bom_item.uom == "h":
                    # Stunden-Budget
                    budget["hours_by_item"][bom_item.item_code] = bom_item.qty
                    budget["cost_by_item"][bom_item.item_code] = bom_item.amount
                    budget["hours_cost"] += bom_item.amount
                else:
                    # Material-Budget
                    budget["material_cost"] += bom_item.amount

    # Berechnungen
    budget["direct_cost"] = budget["hours_cost"] + budget["material_cost"] + budget["services_cost"]
    budget["overhead"] = budget["hours_cost"] * OVERHEAD_RATE
    budget["hk"] = budget["direct_cost"] + budget["overhead"]

    return budget


def get_actual_costs(project):
    """
    Holt Ist-Kosten aus den Projekt-Feldern

    Returns:
        dict: Ist-Kosten nach Kategorie
    """
    actual = {
        "hours_cost": project.stundenbudget_aktuell or 0,
        "material_cost": project.actual_material_cost or 0,
        "services_cost": project.sum_services or 0,
        "expense_claims": project.sum_expense_claim or 0,
        "direct_cost": 0,
        "overhead": 0,
        "hk": 0
    }

    # Berechnungen
    actual["direct_cost"] = (actual["hours_cost"] + actual["material_cost"] +
                            actual["services_cost"] + actual["expense_claims"])
    actual["overhead"] = actual["hours_cost"] * OVERHEAD_RATE
    actual["hk"] = actual["direct_cost"] + actual["overhead"]

    return actual


def calculate_progress(project, budget):
    """
    Berechnet Fortschritt über Earned Value Method (abgeschlossene Tasks)

    Returns:
        dict: Fortschritts-Metriken
    """
    # Abgeschlossene Tasks holen
    completed_tasks = frappe.get_all("Task",
        filters={"project": project.name, "status": "Completed"},
        fields=["item_code"])

    # Earned Value berechnen
    earned_value = 0
    for task in completed_tasks:
        if task.item_code and task.item_code in budget["cost_by_item"]:
            earned_value += budget["cost_by_item"][task.item_code]

    # Fortschritt berechnen
    progress_pct = (earned_value / budget["hk"] * 100) if budget["hk"] > 0 else 0

    return {
        "earned_value": earned_value,
        "percent": progress_pct,
        "decimal": progress_pct / 100
    }


def calculate_forecast(actual, progress, budget):
    """
    Berechnet Forecast basierend auf Ist-Kosten und Fortschritt

    Returns:
        dict: Forecast-Werte
    """
    forecast = {
        "hk": 0,
        "etc": 0,  # Estimate to Complete (Restkosten)
        "vac": 0,  # Variance at Completion (Abweichung)
        "eac_classic": 0,  # Klassischer EVM-Forecast
        "hours_cost": 0,
        "material_cost": 0,
        "services_cost": 0,
        "direct_cost": 0,
        "overhead": 0
    }

    progress_decimal = progress["decimal"]

    # Forecast berechnen
    if progress_decimal > 0 and progress_decimal < 1:
        forecast["hk"] = actual["hk"] / progress_decimal
        # Forecast für Einzelpositionen
        forecast["hours_cost"] = actual["hours_cost"] / progress_decimal
        forecast["material_cost"] = actual["material_cost"] / progress_decimal
        forecast["services_cost"] = actual["services_cost"] / progress_decimal
    elif progress_decimal >= 1:
        forecast["hk"] = actual["hk"]
        forecast["hours_cost"] = actual["hours_cost"]
        forecast["material_cost"] = actual["material_cost"]
        forecast["services_cost"] = actual["services_cost"]
    else:
        # Kein Fortschritt: Forecast = Budget
        forecast["hk"] = budget["hk"]
        forecast["hours_cost"] = budget["hours_cost"]
        forecast["material_cost"] = budget["material_cost"]
        forecast["services_cost"] = budget["services_cost"]

    # Direkt- und Gemeinkosten berechnen
    forecast["direct_cost"] = (forecast["hours_cost"] + forecast["material_cost"] +
                               forecast["services_cost"])
    forecast["overhead"] = forecast["hours_cost"] * OVERHEAD_RATE

    # Restkosten
    forecast["etc"] = forecast["hk"] - actual["hk"]

    # Abweichung zum Budget
    forecast["vac"] = budget["hk"] - forecast["hk"]

    # Klassischer EVM-Forecast
    cpi = progress["earned_value"] / actual["hk"] if actual["hk"] > 0 else 1
    forecast["eac_classic"] = budget["hk"] / cpi if cpi > 0 else budget["hk"]
    forecast["vac_classic"] = budget["hk"] - forecast["eac_classic"]

    return forecast


def calculate_ebit(project, budget, forecast):
    """
    Berechnet EBIT (Budget und Forecast)

    Returns:
        dict: EBIT-Werte
    """
    revenue = project.total_sales_amount or 0

    ebit = {
        "revenue": revenue,
        "budget": revenue - budget["hk"],
        "budget_pct": ((revenue - budget["hk"]) / revenue * 100) if revenue > 0 else 0,
        "forecast": revenue - forecast["hk"],
        "forecast_pct": ((revenue - forecast["hk"]) / revenue * 100) if revenue > 0 else 0
    }

    return ebit


def calculate_billing_metrics(project):
    """
    Berechnet Fakturierungs- und OP-Kennzahlen

    Returns:
        dict: Billing-Metriken
    """
    # Fakturierungsgrad
    invoiced = frappe.db.get_value("Sales Invoice",
        {"project": project.name, "docstatus": 1},
        "sum(base_net_total)") or 0

    total_sales = project.total_sales_amount or 1
    billing_rate = (invoiced / total_sales * 100)

    # OP Debitoren
    outstanding = frappe.db.get_value("Sales Invoice",
        {"project": project.name, "docstatus": 1},
        "sum(outstanding_amount)") or 0

    return {
        "invoiced": invoiced,
        "billing_rate": billing_rate,
        "outstanding": outstanding
    }


def calculate_cost_to_cost_progress(actual, forecast):
    """
    Berechnet Cost-to-Cost Fortschritt (für Header)

    Returns:
        float: Fortschritt in Prozent
    """
    if forecast["hk"] > 0:
        return (actual["hk"] / forecast["hk"] * 100)
    return 0


# Hilfsfunktion für Jinja-Template
@frappe.whitelist()
def get_cockpit_data_for_print(project_name):
    """
    Wrapper für Druckformat-Zugriff
    """
    return get_project_cockpit_data(project_name)


def get_project_overview_data(project_name):
    """
    Berechnet Daten für die Projektübersicht (Kompakt)

    Returns:
        dict: Zusammenfassung, Kostenstruktur und Rollen-Details
    """
    project = frappe.get_doc("Project", project_name)

    # Budget und Forecast berechnen
    budget = calculate_budget_from_bom(project)
    actual = get_actual_costs(project)
    progress = calculate_progress(project, budget)
    forecast = calculate_forecast(actual, progress, budget)

    # Zusammenfassung
    summary = {
        "fc": forecast["hk"],
        "bu": budget["hk"],
        "ist": actual["hk"],
        "delta_chf": budget["hk"] - forecast["hk"],
        "delta_pct": ((budget["hk"] - forecast["hk"]) / budget["hk"] * 100) if budget["hk"] > 0 else 0,
        "etc": forecast["etc"],
        "revenue": project.total_sales_amount or 0,
        "margin_fc": (project.total_sales_amount or 0) - forecast["hk"],
        "margin_fc_pct": (((project.total_sales_amount or 0) - forecast["hk"]) / (project.total_sales_amount or 1) * 100),
        "budget_usage": (actual["hk"] / budget["hk"] * 100) if budget["hk"] > 0 else 0
    }

    # Kostenstruktur berechnen
    costs = calculate_cost_structure(budget, forecast, actual)

    # Rollen-Details berechnen
    roles = calculate_role_details(project, budget)

    return {
        "summary": summary,
        "costs": costs,
        "roles": roles
    }


def calculate_cost_structure(budget, forecast, actual):
    """
    Berechnet Kostenstruktur FC vs. BU
    """
    # Forecast-Werte für Direktkosten proportional hochrechnen
    if actual["hk"] > 0:
        fc_factor = forecast["hk"] / actual["hk"]
    else:
        fc_factor = 1

    fc_material = actual["material_cost"] * fc_factor
    fc_services = actual["services_cost"] * fc_factor
    fc_personnel = actual["hours_cost"] * fc_factor
    fc_overhead = fc_personnel * OVERHEAD_RATE

    costs = {
        "material": {
            "fc": fc_material,
            "bu": budget["material_cost"],
            "delta_chf": budget["material_cost"] - fc_material,
            "delta_pct": ((budget["material_cost"] - fc_material) / budget["material_cost"] * 100) if budget["material_cost"] > 0 else None
        },
        "services": {
            "fc": fc_services,
            "bu": budget["services_cost"],
            "delta_chf": budget["services_cost"] - fc_services,
            "delta_pct": ((budget["services_cost"] - fc_services) / budget["services_cost"] * 100) if budget["services_cost"] > 0 else None
        },
        "personnel": {
            "fc": fc_personnel,
            "bu": budget["hours_cost"],
            "delta_chf": budget["hours_cost"] - fc_personnel,
            "delta_pct": ((budget["hours_cost"] - fc_personnel) / budget["hours_cost"] * 100) if budget["hours_cost"] > 0 else None
        },
        "overhead": {
            "fc": fc_overhead,
            "bu": budget["overhead"],
            "delta_chf": budget["overhead"] - fc_overhead,
            "delta_pct": ((budget["overhead"] - fc_overhead) / budget["overhead"] * 100) if budget["overhead"] > 0 else None
        }
    }

    return costs


def calculate_role_details(project, budget):
    """
    Berechnet Stunden und Kosten pro Rolle (FC, BU, Ist)

    Returns:
        list: Liste mit Rollen-Details
    """
    roles = []

    # Alle Items aus Budget holen
    for item_code, bu_hours in budget["hours_by_item"].items():
        # Item-Details holen
        item = frappe.get_doc("Item", item_code)

        # Budget-Daten
        bu_cost = budget["cost_by_item"].get(item_code, 0)

        # Ist-Stunden aus Timesheets holen
        ist_hours = get_actual_hours_for_item(project.name, item_code)
        ist_cost = ist_hours * (item.valuation_rate or 0)

        # Forecast berechnen (proportional zum Gesamtfortschritt)
        progress = calculate_progress(project, budget)
        if progress["decimal"] > 0 and progress["decimal"] < 1:
            fc_hours = ist_hours / progress["decimal"]
            fc_cost = ist_cost / progress["decimal"]
        elif progress["decimal"] >= 1:
            fc_hours = ist_hours
            fc_cost = ist_cost
        else:
            fc_hours = bu_hours
            fc_cost = bu_cost

        # Delta berechnen
        delta_hours = bu_hours - fc_hours
        delta_cost = bu_cost - fc_cost

        roles.append({
            "name": f"Stunden {item.item_name}",
            "item_code": item_code,
            "fc_hours": fc_hours,
            "bu_hours": bu_hours,
            "ist_hours": ist_hours,
            "delta_hours": delta_hours,
            "fc_cost": fc_cost,
            "bu_cost": bu_cost,
            "ist_cost": ist_cost,
            "delta_cost": delta_cost
        })

    return roles


def get_actual_hours_for_item(project_name, item_code):
    """
    Holt Ist-Stunden für einen bestimmten Item Code aus Timesheets
    """
    # Tasks mit diesem Item Code finden
    tasks = frappe.get_all("Task",
        filters={"project": project_name, "item_code": item_code},
        fields=["name"])

    if not tasks:
        return 0

    task_names = [t.name for t in tasks]

    # Timesheets zu diesen Tasks finden
    total_hours = frappe.db.get_value("Timesheet Detail",
        {"task": ["in", task_names], "docstatus": 1},
        "sum(hours)") or 0

    return total_hours
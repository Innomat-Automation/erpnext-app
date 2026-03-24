from __future__ import unicode_literals
from frappe import _

def get_data():
    return[
		{
			"label": _("Berichte"),
			"items": [
				{
					"type": "report",
					"name": "KPI-Uebersicht",
					"label": _("KPI-Übersicht"),
					"is_query_report": True,
				},
				{
					"type": "report",
					"name": "Auftragseingang",
					"label": _("Auftragseingang"),
					"doctype": "Sales Order",
					"is_query_report": True
				},
				{
					"type": "report",
					"name": "Fakturierter Umsatz",
					"label": _("Fakturierter Umsatz"),
					"is_query_report": True,
					"doctype": "Sales Invoice"
				},
				{
					"type": "report",
					"name": "Arbeitsvorrat",
					"label": _("Arbeitsvorrat"),
					"is_query_report": True,
					"doctype": "Sales Order"
				},
				{
					"type": "report",
					"name": "Nachkalkulation",
					"label": _("Nachkalkulation"),
					"is_query_report": True,
					"doctype": "Sales Order"
				},
				{
					"type": "report",
					"name": "Projektstatus",
					"label": _("Projektstatus"),
					"is_query_report": True,
					"doctype": "Sales Order"
				},
				{
					"type": "report",
					"name": "Akonto Forecast",
					"label": _("Akonto Forecast"),
					"is_query_report": True,
				},
				{
					"type": "report",
					"name": "Mitarbeiter Gegenverrechnung",
					"label": _("Mitarbeiter Gegenverrechnung"),
					"is_query_report": True,
					"doctype": "Sales Order"
				},
			]
		},
		{
			"label": _("Finanzen"),
			"items": [
				{
					"type": "report",
					"name": "Erfolgsrechnung nach Kostenstellen",
					"label": _("Erfolgsrechnung nach Kostenstellen"),
					"doctype": "GL Entry",
					"is_query_report": True
				},
				{
					"type": "report",
					"name": "Deckungsbeitragsrechnung nach Kostenstellen",
					"label": _("Deckungsbeitragsrechnung nach Kostenstellen"),
					"doctype": "GL Entry",
					"is_query_report": True
				},
				{
					"type": "report",
					"name": "Abgeschlossene Projekte",
					"label": _("Abgeschlossene Projekte"),
					"doctype": "Project",
					"is_query_report": True
				},
			]
		},
		{
			"label": _("Liquidität"),
			"items": [
				{
					"type": "report",
					"name": "Accounts Receivable",
					"label": _("OP nach Fälligkeit"),
					"is_query_report": True,
					"doctype": "Sales Invoice",
				},
				{
					"type": "report",
					"name": "Liquiditaetspositionen",
					"label": _("Liquiditätspositionen"),
					"is_query_report": True,
				},
			]
		},
		{
			"label": _("HR"),
			"items": [
				{
					"type": "report",
					"name": "Employee Productivity",
					"label": _("Mitarbeiter-Produktivität"),
					"is_query_report": True,
				},
				{
					"type": "report",
					"name": "Worktime Overview",
					"label": _("GLZ und Ferien"),
					"is_query_report": True,
				},
			]
		},
		{
			"label": _("Budget"),
			"items": [
				{
					"type": "doctype",
					"name": "Innomat Budget",
					"description": _("Monatsweises Budget")
				},
			]
		},
    ]

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
					#"doctype": "tbd"
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
					"name": "Auftraege in Arbeit",
					"label": _("Aufträge in Arbeit"),
					"is_query_report": True,
					"doctype": "Sales Order"
				},
				{
					"type": "report",
					"name": "Arbeitsvorrat",
					"label": _("Arbeitsvorrat"),
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
					"name": "Erfolgsrechnung",
					"label": _("Erfolgsrechnung"),
					"doctype": "GL Entry",
					"is_query_report": True
				},
				{
					"type": "report",
					"name": "Deckungsbeitragsrechnung",
					"label": _("Deckungsbeitragsrechnung"),
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
					"name": "OP nach Faelligkeit",
					"label": _("OP nach Fälligkeit"),
					"is_query_report": True,
					"doctype": "Sales Invoice",
				},
				{
					"type": "report",
					"name": "Liquiditaet",
					"label": _("Liquidität"),
					"is_query_report": True,
					#"doctype": "tbd"
				},
			]
		},
		{
			"label": _("HR"),
			"items": [
				{
					"type": "report",
					"name": "Produktivitaet",
					"label": _("Produktivität"),
					"is_query_report": True,
					#"doctype": "tbd"
				},
				{
					"type": "report",
					"name": "GLZ und Ferien",
					"label": _("GLZ und Ferien"),
					"is_query_report": True,
					#"doctype": "tbd"
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

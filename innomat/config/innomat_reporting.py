from __future__ import unicode_literals
from frappe import _

def get_data():
    return[
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

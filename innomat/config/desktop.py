# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from frappe import _

def get_data():
	return [
		{
			"module_name": "Innomat",
			"color": "grey",
			"icon": "octicon octicon-briefcase",
			"type": "module",
			"label": _("Innomat")
		},
		{
			"module_name": "innomat_accounting",
			"color": "grey",
			"icon": "icon accounting-blue",
			"type": "module",
			"label": _("Innomat Accounting")
		}
	]

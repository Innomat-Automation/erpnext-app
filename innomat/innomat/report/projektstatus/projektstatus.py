# Copyright (c) 2021, Innomat, Asprotec and libracore and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
import ast          # to parse str to dict (from JS calls)
from datetime import date
from innomat.innomat.report.nachkalkulation.nachkalkulation import get_data

def execute(filters=None):
    columns = get_columns()
    data = get_data(filters)
    return columns, data

def get_columns():
    return [
        {"label": _("Project"), "fieldname": "project", "fieldtype": "Link", "options": "Project", "width": 100},
        {"label": _("Project Name"), "fieldname": "project_name", "width": 200},
        {"label": _("Project manager name"), "fieldname": "project_manager_name", "fieldtype": "Data", "width": 100},
        {"label": _("Status Light"), "fieldname": "status_light", "fieldtype": "Data", "width": 100},
        {"label": _("Start Date"), "fieldname": "start_date", "fieldtype": "Date", "width": 80},
        {"label": _("End Date"), "fieldname": "end_date", "fieldtype": "Date", "width": 80},
        {"label": _("Progress (time)"), "fieldname": "progress_time", "fieldtype": "Percent", "width": 100},
        {"label": _("Progress (tasks)"), "fieldname": "progress_tasks", "fieldtype": "Percent", "width": 100},
        {"label": _("Hours flat (plan)"), "fieldname": "planned_hours", "fieldtype": "Float", "width": 100},
        {"label": _("Hours flat (used)"), "fieldname": "hours_flat", "fieldtype": "Float", "width": 100},
        {"label": _("Hours by effort"), "fieldname": "hours_effective", "fieldtype": "Float", "width": 100}
    ]

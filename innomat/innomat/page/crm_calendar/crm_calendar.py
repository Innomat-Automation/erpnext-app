# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import frappe
import json
from frappe import _
from six import string_types


@frappe.whitelist()
def get_events(start, end, include_completed=0):
    """Return communication rows for the requested calendar range."""
    frappe.has_permission("Lead", "read", throw=True)

    completed_condition = ""
    if not int(include_completed or 0):
        completed_condition = " AND IFNULL(k.`completed`, 0) = 0"

    return frappe.db.sql("""
        SELECT
            k.`name` AS `name`,
            k.`parent` AS `lead`,
            k.`communication_type` AS `communication_type`,
            k.`completed` AS `completed`,
            k.`date` AS `date`,
            k.`time` AS `time`,
            k.`duration` AS `duration`,
            k.`user` AS `user`,
            k.`preparation` AS `preparation`,
            k.`note` AS `note`,
            l.`lead_name` AS `lead_name`,
            l.`company_name` AS `company_name`
        FROM `tabLead Kommunikation` AS k
        LEFT JOIN `tabLead` AS l ON l.`name` = k.`parent`
        WHERE k.`parenttype` = 'Lead'
          AND k.`date` >= %(start)s
          AND k.`date` < %(end)s
          {completed_condition}
        ORDER BY k.`date` ASC, k.`time` ASC
    """.format(completed_condition=completed_condition),
        {"start": start, "end": end}, as_dict=True)


@frappe.whitelist()
def update_event(name, values):
    """Save calendar date, time and duration changes on the parent Lead."""
    if isinstance(values, string_types):
        values = json.loads(values)

    parent = frappe.db.get_value("Lead Kommunikation", name, "parent")
    if not parent:
        frappe.throw(_("Eintrag nicht gefunden"))

    lead = frappe.get_doc("Lead", parent)
    lead.check_permission("write")
    for communication in lead.verlauf:
        if communication.name == name:
            communication.date = values.get("date")
            communication.time = values.get("time")
            communication.duration = max(float(values.get("duration") or 1), 0.25)
            lead.save()
            frappe.db.commit()
            return name

    frappe.throw(_("Eintrag nicht gefunden"))

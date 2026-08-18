# -*- coding: utf-8 -*-
# Copyright (c) 2026, Innomat, Asprotec and libracore and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
import json
from frappe import _
from six import string_types
from frappe.utils import getdate, nowdate

EDITABLE_FIELDS = ["communication_type", "completed", "date", "time",
                   "user", "preparation", "note", "follow_up"]


@frappe.whitelist()
def get_upcoming(user=None, limit=25):
    """Return the open (not completed) communication entries per type."""
    frappe.has_permission("Lead", "read", throw=True)
    complete_past_entries()

    limit = min(int(limit or 25), 100)
    conditions = ""
    values = {"limit": limit}
    if user:
        conditions = " AND k.`user` = %(user)s"
        values["user"] = user

    data = {}
    for communication_type in ["Telefonat", "Besprechung"]:
        values["communication_type"] = communication_type
        data[communication_type] = frappe.db.sql("""
            SELECT
                k.`name` AS `name`,
                k.`parent` AS `lead`,
                k.`communication_type` AS `communication_type`,
                k.`date` AS `date`,
                k.`time` AS `time`,
                k.`user` AS `user`,
                k.`preparation` AS `preparation`,
                k.`note` AS `note`,
                k.`follow_up` AS `follow_up`,
                l.`lead_name` AS `lead_name`,
                l.`company_name` AS `company_name`
            FROM `tabLead Kommunikation` AS k
            LEFT JOIN `tabLead` AS l ON l.`name` = k.`parent`
            WHERE k.`parenttype` = 'Lead'
              AND k.`communication_type` = %(communication_type)s
              AND IFNULL(k.`completed`, 0) = 0
              {conditions}
            ORDER BY k.`date` ASC, k.`time` ASC
            LIMIT %(limit)s
        """.format(conditions=conditions), values, as_dict=True)

    return data


def complete_past_entries():
    """Complete open communication rows dated before today."""
    rows = frappe.db.sql("""
        SELECT k.`name`, k.`parent`
        FROM `tabLead Kommunikation` AS k
        WHERE k.`parenttype` = 'Lead'
          AND IFNULL(k.`completed`, 0) = 0
          AND k.`date` < CURDATE()
    """, as_dict=True)

    rows_by_lead = {}
    for row in rows:
        rows_by_lead.setdefault(row.parent, set()).add(row.name)

    completed = 0
    for parent, row_names in rows_by_lead.items():
        lead = frappe.get_doc("Lead", parent)
        lead.check_permission("write")
        for communication in lead.verlauf:
            if communication.name in row_names and not communication.completed:
                communication.completed = 1
                completed += 1
        if lead.contact_date and getdate(lead.contact_date) < getdate(nowdate()):
            lead.contact_date = None
        lead.save()

    if completed:
        frappe.db.commit()
    return completed


@frappe.whitelist()
def update_entry(name, values):
    """Update a single Lead Kommunikation row through its parent Lead."""
    if isinstance(values, string_types):
        values = json.loads(values)

    parent = frappe.db.get_value("Lead Kommunikation", name, "parent")
    if not parent:
        frappe.throw(_("Eintrag nicht gefunden"))

    lead = frappe.get_doc("Lead", parent)
    lead.check_permission("write")

    for row in lead.verlauf:
        if row.name == name:
            for field in EDITABLE_FIELDS:
                if field in values:
                    row.set(field, values.get(field))
            break
    else:
        frappe.throw(_("Eintrag nicht gefunden"))

    lead.save()
    frappe.db.commit()
    return name


@frappe.whitelist()
def complete_all(user=None):
    """Mark all visible open communication rows as completed."""
    frappe.has_permission("Lead", "read", throw=True)

    user_condition = ""
    values = {}
    if user:
        user_condition = " AND k.`user` = %(user)s"
        values["user"] = user

    rows = frappe.db.sql("""
        SELECT k.`name`, k.`parent`
        FROM `tabLead Kommunikation` AS k
        WHERE k.`parenttype` = 'Lead'
          AND IFNULL(k.`completed`, 0) = 0
          {user_condition}
    """.format(user_condition=user_condition), values, as_dict=True)

    rows_by_lead = {}
    for row in rows:
        rows_by_lead.setdefault(row.parent, set()).add(row.name)

    completed = 0
    for parent, row_names in rows_by_lead.items():
        lead = frappe.get_doc("Lead", parent)
        lead.check_permission("write")
        for communication in lead.verlauf:
            if communication.name in row_names and not communication.completed:
                communication.completed = 1
                completed += 1
        lead.save()

    frappe.db.commit()
    return completed


@frappe.whitelist()
def create_entry(values):
    """Create a communication row on an existing or newly created Lead."""
    if isinstance(values, string_types):
        values = json.loads(values)

    lead_name = values.get("lead")
    new_lead_name = (values.get("new_lead_name") or "").strip()
    if lead_name:
        lead = frappe.get_doc("Lead", lead_name)
        lead.check_permission("write")
    elif new_lead_name:
        frappe.has_permission("Lead", "create", throw=True)
        lead = frappe.get_doc({
            "doctype": "Lead",
            "lead_name": new_lead_name
        })
    else:
        frappe.throw(_("Bitte einen bestehenden Lead auswählen oder einen neuen Namen eingeben"))

    communication = {
        "doctype": "Lead Kommunikation",
        "communication_type": values.get("communication_type") or "Telefonat",
        "completed": 0,
        "date": values.get("date"),
        "time": values.get("time"),
        "user": values.get("user"),
        "preparation": values.get("preparation"),
        "note": values.get("note"),
        "follow_up": values.get("follow_up")
    }
    lead.append("verlauf", communication)
    lead.save()
    frappe.db.commit()
    return lead.name

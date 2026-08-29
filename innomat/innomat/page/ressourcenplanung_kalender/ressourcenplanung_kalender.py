# -*- coding: utf-8 -*-
# Copyright (c) 2026, Innomat and contributors
# For license information, please see license.txt
from __future__ import unicode_literals

import frappe
from frappe import _
from frappe.utils import today


OPEN_STATUSES = ["Open", "Working", "Pending Review", "Overdue"]


def get_employee_for_user(user):
    return frappe.db.get_value("Employee", {"user_id": user}, "name")


@frappe.whitelist()
def get_scheduled_tasks(user, start, end):
    """Tasks assigned to `user` with a start/end date overlapping the given range."""
    frappe.has_permission("Task", "read", throw=True)

    return frappe.db.sql("""
        SELECT
            `tabTask`.`name` AS `name`,
            `tabTask`.`subject` AS `subject`,
            `tabTask`.`project` AS `project`,
            `tabTask`.`status` AS `status`,
            `tabTask`.`priority` AS `priority`,
            `tabTask`.`exp_start_date` AS `exp_start_date`,
            `tabTask`.`exp_end_date` AS `exp_end_date`,
            `tabTask`.`color` AS `color`,
            `tabProject`.`project_name` AS `project_name`
        FROM `tabTask`
        LEFT JOIN `tabProject` ON `tabProject`.`name` = `tabTask`.`project`
        WHERE `tabTask`.`completed_by` = %(user)s
          AND `tabTask`.`exp_start_date` IS NOT NULL
          AND `tabTask`.`exp_end_date` IS NOT NULL
          AND `tabTask`.`exp_end_date` >= %(start)s
          AND `tabTask`.`exp_start_date` <= %(end)s
          AND `tabTask`.`status` IN %(statuses)s
        ORDER BY `tabTask`.`project` ASC, `tabTask`.`exp_start_date` ASC
    """, {"user": user, "start": start, "end": end, "statuses": OPEN_STATUSES}, as_dict=True)


@frappe.whitelist()
def get_unscheduled_tasks(user):
    """Tasks assigned to `user` that are missing a start and/or end date."""
    frappe.has_permission("Task", "read", throw=True)

    return frappe.db.sql("""
        SELECT
            `tabTask`.`name` AS `name`,
            `tabTask`.`subject` AS `subject`,
            `tabTask`.`project` AS `project`,
            `tabTask`.`status` AS `status`,
            `tabTask`.`priority` AS `priority`,
            `tabProject`.`project_name` AS `project_name`
        FROM `tabTask`
        LEFT JOIN `tabProject` ON `tabProject`.`name` = `tabTask`.`project`
        WHERE `tabTask`.`completed_by` = %(user)s
          AND (`tabTask`.`exp_start_date` IS NULL OR `tabTask`.`exp_end_date` IS NULL)
          AND `tabTask`.`status` IN %(statuses)s
          AND `tabProject`.`status` = 'Open'
        ORDER BY `tabTask`.`subject` ASC
    """, {"user": user, "statuses": OPEN_STATUSES}, as_dict=True)


@frappe.whitelist()
def get_overdue_tasks(user):
    """Tasks assigned to `user` whose expected end date is in the past and are not yet completed."""
    frappe.has_permission("Task", "read", throw=True)

    return frappe.db.sql("""
        SELECT
            `tabTask`.`name` AS `name`,
            `tabTask`.`subject` AS `subject`,
            `tabTask`.`project` AS `project`,
            `tabTask`.`status` AS `status`,
            `tabTask`.`priority` AS `priority`,
            `tabTask`.`exp_start_date` AS `exp_start_date`,
            `tabTask`.`exp_end_date` AS `exp_end_date`,
            `tabProject`.`project_name` AS `project_name`
        FROM `tabTask`
        LEFT JOIN `tabProject` ON `tabProject`.`name` = `tabTask`.`project`
        WHERE `tabTask`.`completed_by` = %(user)s
          AND `tabTask`.`exp_end_date` IS NOT NULL
          AND `tabTask`.`exp_end_date` < %(today)s
          AND `tabTask`.`status` IN %(statuses)s
          AND `tabProject`.`status` = 'Open'
        ORDER BY `tabTask`.`exp_end_date` ASC
    """, {"user": user, "today": today(), "statuses": OPEN_STATUSES}, as_dict=True)


@frappe.whitelist()
def get_unassigned_pm_tasks(user):
    """Unassigned tasks that belong to a project where `user` is the project manager."""
    frappe.has_permission("Task", "read", throw=True)

    employee = get_employee_for_user(user)
    if not employee:
        return []

    return frappe.db.sql("""
        SELECT
            `tabTask`.`name` AS `name`,
            `tabTask`.`subject` AS `subject`,
            `tabTask`.`project` AS `project`,
            `tabTask`.`status` AS `status`,
            `tabTask`.`priority` AS `priority`,
            `tabProject`.`project_name` AS `project_name`
        FROM `tabTask`
        INNER JOIN `tabProject` ON `tabProject`.`name` = `tabTask`.`project`
        WHERE `tabProject`.`project_manager` = %(employee)s
          AND IFNULL(`tabTask`.`completed_by`, '') = ''
          AND `tabTask`.`status` IN %(statuses)s
          AND `tabProject`.`status` = 'Open'
        ORDER BY IFNULL(`tabTask`.`exp_end_date`, `tabTask`.`creation`) ASC
    """, {"employee": employee, "statuses": OPEN_STATUSES}, as_dict=True)


@frappe.whitelist()
def schedule_task(task, start_date, end_date=None, assign_user=None):
    """Set/move the expected start & end date of a task, optionally assigning it to a user."""
    doc = frappe.get_doc("Task", task)
    doc.check_permission("write")

    doc.exp_start_date = start_date
    doc.exp_end_date = end_date or start_date

    if assign_user:
        if doc.completed_by and doc.completed_by != assign_user:
            frappe.throw(_("Diese Aufgabe ist bereits einem anderen Benutzer zugewiesen."))
        doc.completed_by = assign_user

    doc.save()
    return {
        "name": doc.name,
        "exp_start_date": doc.exp_start_date,
        "exp_end_date": doc.exp_end_date,
        "completed_by": doc.completed_by
    }


EDITABLE_FIELDS = ["subject", "status", "priority", "exp_start_date", "exp_end_date", "description", "completed_by", "color"]


@frappe.whitelist()
def get_task_details(task):
    """Fetch the fields shown/edited in the calendar popup."""
    doc = frappe.get_doc("Task", task)
    doc.check_permission("read")

    return {
        "name": doc.name,
        "subject": doc.subject,
        "project": doc.project,
        "project_name": frappe.db.get_value("Project", doc.project, "project_name") if doc.project else None,
        "status": doc.status,
        "priority": doc.priority,
        "exp_start_date": doc.exp_start_date,
        "exp_end_date": doc.exp_end_date,
        "description": doc.description,
        "completed_by": doc.completed_by,
        "color": doc.color
    }


@frappe.whitelist()
def update_task(task, values):
    """Save calendar popup edits (subject, status, priority, dates, description)."""
    if isinstance(values, str):
        values = frappe.parse_json(values)

    doc = frappe.get_doc("Task", task)
    doc.check_permission("write")

    for fieldname in EDITABLE_FIELDS:
        if fieldname in values:
            doc.set(fieldname, values.get(fieldname))

    doc.save()
    return get_task_details(task)

// Copyright (c) 2021, Innomat, Asprotec and libracore and contributors
// For license information, please see license.txt
/* eslint-disable */

frappe.query_reports["Nachkalkulation"] = {
    "filters": [
        {
            fieldname: "project_manager",
            label: __("Projektleiter"),
            fieldtype: "Link",
            options: "Employee"
        },
        {
            fieldname: "project_manager_name",
            label: __("Name Projektleiter"),
            fieldtype: "Data"
        },
        {
            fieldname: "customer",
            label: __("Kunde"),
            fieldtype: "Link",
            options: "Customer"
        },
        {
            fieldname: "status",
            label: __("Status"),
            fieldtype: "Select",
            options: "\nOpen\nCompleted\nCancelled"
        },
        {
            fieldname: "status_light",
            label: __("Status-Ampel"),
            fieldtype: "Select",
            options: "⚪\n🟢\n🟡\n🔴"
        },
        {
            fieldname: "year",
            label: __("Jahr"),
            fieldtype: "Link",
            options: "Fiscal Year",
            default: new Date().getFullYear()
        }
    ]
};

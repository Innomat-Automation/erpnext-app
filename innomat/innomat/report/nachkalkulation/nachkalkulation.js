// Copyright (c) 2021, Innomat, Asprotec and libracore and contributors
// For license information, please see license.txt
/* eslint-disable */

frappe.query_reports["Nachkalkulation"] = {
    "filters": [
        {
            fieldname: "project_manager",
            label: __("Project manager"),
            fieldtype: "Link",
            options: "Employee"
        },
        {
            fieldname: "project_manager_name",
            label: __("Project manager name"),
            fieldtype: "Data"
        },
        {
            fieldname: "customer",
            label: __("Customer"),
            fieldtype: "Link",
            options: "Customer"
        }
    ]
};

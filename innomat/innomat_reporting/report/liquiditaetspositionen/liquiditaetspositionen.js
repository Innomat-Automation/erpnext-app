// Copyright (c) 2016, Innomat, Asprotec and libracore and contributors
// For license information, please see license.txt
/* eslint-disable */

frappe.query_reports["Liquiditaetspositionen"] = {
    "filters": [
        {
            "fieldname": "company",
            "label": "Company",
            "fieldtype": "Link",
            "options": "Company",
            "reqd": 1,
            "default": frappe.defaults.get_user_default("Company"),
        },
        {
            "fieldname": "date",
            "label": "Date",
            "fieldtype": "Date",
            "default": frappe.datetime.get_today(),
            "reqd": 1
        }
    ]
};
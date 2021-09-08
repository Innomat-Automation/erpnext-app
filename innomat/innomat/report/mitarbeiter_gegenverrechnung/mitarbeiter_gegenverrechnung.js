// Copyright (c) 2021, Innomat, Asprotec and libracore and contributors
// For license information, please see license.txt
/* eslint-disable */

frappe.query_reports["Mitarbeiter Gegenverrechnung"] = {
    "filters": [
        {
            'fieldname':"from_date",
            'label': __("From Date"),
            'fieldtype': "Date",
            'default': new Date(new Date().getFullYear(), 0, 1),
            'reqd': 1
        },
        {
            'fieldname':"to_date",
            'label': __("To Date"),
            'fieldtype': "Date",
            'default': frappe.datetime.get_today(),
            'reqd': 1
        },
        {
            'fieldname': "company",
            'label': __("Company"),
            'fieldtype': "Link",
            'options': "Company",
            'default': frappe.defaults.get_default("Company"),
            'reqd': 1
        }
    ]
};

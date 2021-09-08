// Copyright (c) 2016, Innomat, Asprotec and libracore and contributors
// For license information, please see license.txt
/* eslint-disable */

frappe.query_reports["Kennzahlen"] = {
    "filters": [
        {
            'fieldname':"date",
            'label': __("Date"),
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

// Copyright (c) 2025, Innomat, libracore and contributors
// For license information, please see license.txt
/* eslint-disable */

frappe.query_reports["Auftragseingang"] = {
    filters: [
        {
            fieldname: "reference_date",
            label: __("Reference Date"),
            fieldtype: "Date",
            default: frappe.datetime.get_today()
        },
        {
            fieldname: "hide_zero_rows",
            label: __("Kostenstellen ohne YTD-Umsatz ausblenden"),
            fieldtype: "Check",
            default: 1
        }
    ]
};

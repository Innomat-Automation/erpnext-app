// Copyright (c) 2025, Innomat, Asprotec and libracore and contributors
// For license information, please see license.txt
/* eslint-disable */

frappe.query_reports["KPI-Uebersicht"] = {
    filters: [
        {
            fieldname: "company",
            label: __("Company"),
            fieldtype: "Link",
            options: "Company",
            reqd: 1,
            default: frappe.defaults.get_user_default("Company")
        },
        {
            fieldname: "from_date",
            label: __("From Date"),
            fieldtype: "Date",
            reqd: 1,
            default: frappe.datetime.add_months(frappe.datetime.get_today(), -1),
        },
        {
            fieldname: "to_date",
            label: __("To Date"),
            fieldtype: "Date",
            reqd: 1,
            default: frappe.datetime.get_today(),
        }
    ],

    "after_datatable_render": function() {
        $("div.dt-row-header").css("height","50px");
    }
};

// Copyright (c) 2016, Innomat, Asprotec and libracore and contributors
// For license information, please see license.txt
/* eslint-disable */

frappe.query_reports["Deckungsbeitragsrechnung nach Kostenstellen"] = {
    "filters": [
        {
            fieldname: "company",
            label: __("Unternehmen"),
            fieldtype: "Link",
            options: "Company",
            default: frappe.defaults.get_user_default("Company"),
            reqd: 1
        },
        {
            fieldname: "fiscal_year",
            label: __("Geschäftsjahr"),
            fieldtype: "Link",
            options: "Fiscal Year",
            default: new Date().getFullYear(),
            reqd: 1
        },
        {
            fieldname: "month_from",
            label: __("Monat von"),
            fieldtype: "Select",
            options: "Jan\nFeb\nMar\nApr\nMay\nJun\nJul\nAug\nSep\nOct\nNov\nDec",
            default: "Jan",
            reqd: 1
        },
        {
            fieldname: "month_to",
            label: __("Monat bis"),
            fieldtype: "Select",
            options: "Jan\nFeb\nMar\nApr\nMay\nJun\nJul\nAug\nSep\nOct\nNov\nDec",
            default: new Date().toLocaleString('en-US', { month: 'short' }),
            reqd: 1
        },
        {
            fieldname: "budget_prefix",
            label: __("Budget-Präfix"),
            fieldtype: "Select",
            options: "tbd",
            default: "tbd",
            reqd: 1
        }
    ],

    "onload": function(report) {
        frappe.db.get_list("Innomat Budget", {fields: 'name_prefix', group_by: 'name_prefix'}).then(data => {
            if(data) {
                data = data.map(e => e.name_prefix);
                filter = frappe.query_report.get_filter("budget_prefix");
                filter.df.options = data.join("\n");
                filter.options = filter.df.options;
                filter.value = data[0];
                filter.refresh();
            }
        });
    },

    "initial_depth": 0
};
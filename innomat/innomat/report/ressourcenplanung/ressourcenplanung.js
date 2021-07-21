// Copyright (c) 2021, Innomat, Asprotec and libracore and contributors
// For license information, please see license.txt
/* eslint-disable */

frappe.query_reports["Ressourcenplanung"] = {
    "filters": [
        {
            "fieldname":"from_date",
            "label": __("From Date"),
            "fieldtype": "Date",
            "default": frappe.datetime.get_today(),
            "reqd": 1
        },
        {
            "fieldname":"to_date",
            "label": __("To Date"),
            "fieldtype": "Date",
            "default": frappe.datetime.add_months(frappe.datetime.get_today(), +1),
            "reqd": 1
        },
        {
            "fieldname":"project",
            "label": __("Project"),
            "fieldtype": "Link",
            "options": "Project"
        },
        {
            "fieldname":"show_tasks",
            "label": __("Show Tasks"),
            "fieldtype": "Check",
            "default": true
        }
    ],
	get_datatable_options(options) {
		return Object.assign(options, {
            checkboxColumn : true
        })
    },

    after_datatable_render: function(datatable_obj) {
        datatable_obj.style.setStyle(".dt-scrollable",{ width : 'auto !important', height: 'auto !important'});
        datatable_obj.style.setStyle(".dt-row",{ position : 'relative !important', top: 'auto !important', height: 'auto !important'});
    }
};



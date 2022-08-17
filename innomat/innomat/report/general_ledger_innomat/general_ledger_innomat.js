// Copyright (c) 2016, Innomat, Asprotec and libracore and contributors
// For license information, please see license.txt
/* eslint-disable */

frappe.query_reports["General Ledger Innomat"] = {
		"filters": [
			{
				"fieldname":"company",
				"label": __("Company"),
				"fieldtype": "Link",
				"options": "Company",
				"default": frappe.defaults.get_user_default("Company"),
				"reqd": 1
			},
			{
				"fieldname":"from_date",
				"label": __("From Date"),
				"fieldtype": "Date",
				"default": (new Date(new Date().getFullYear(), 0, 1)), /* use first day of current year */
				"reqd": 1,
				"width": "60px"
			},
			{
				"fieldname":"to_date",
				"label": __("To Date"),
				"fieldtype": "Date",
				"default": frappe.datetime.get_today(),
				"reqd": 1,
				"width": "60px"
			},
			{
				"fieldname":"account",
				"label": __("Account"),
				"fieldtype": "Link",
				"options": "Account",
				"get_query": function() {
					var company = frappe.query_report.get_filter_value('company');
					return {
						"doctype": "Account",
						"filters": {
							"company": company,
						}
					}
				}
			},
			{
				"fieldname":"voucher_no",
				"label": __("Voucher No"),
				"fieldtype": "Data",
				on_change: function() {
					frappe.query_report.set_filter_value('group_by', "");
				}
			},
			{
				"fieldname":"group_by",
				"label": __("Group by"),
				"fieldtype": "Select",
				"options": ["", __("Group by Voucher"), __("Group by Voucher (Consolidated)"),
					__("Group by Account"), __("Group by Party")],
				"default": __("Group by Voucher (Consolidated)")
			},
			{
				"fieldname":"tax_id",
				"label": __("Tax Id"),
				"fieldtype": "Data",
				"hidden":1
			},
			{
				"fieldname": "presentation_currency",
				"label": __("Currency"),
				"fieldtype": "Select",
				"options": erpnext.get_presentation_currency_list()
			},
			{
				"fieldname":"project",
				"label": __("Project"),
				"fieldtype": "MultiSelectList",
				get_data: function(txt) {
					return frappe.db.get_link_options('Project', txt);
				}
			},
			{
				"fieldname": "show_opening_entries",
				"label": __("Show Opening Entries"),
				"fieldtype": "Check"
			},
			{
				"fieldname": "include_default_book_entries",
				"label": __("Include Default Book Entries"),
				"fieldtype": "Check"
			}
		]
	}
	
	erpnext.dimension_filters.forEach((dimension) => {
		frappe.query_reports["General Ledger Innomat"].filters.splice(15, 0 ,{
			"fieldname": dimension["fieldname"],
			"label": __(dimension["label"]),
			"fieldtype": "Link",
			"options": dimension["document_type"]
		});
	});
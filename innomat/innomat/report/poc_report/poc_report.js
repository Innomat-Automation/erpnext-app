// Copyright (c) 2016, Innomat, Asprotec and libracore and contributors
// For license information, please see license.txt
/* eslint-disable */

frappe.query_reports["POC Report"] = {
	"filters": [
        {
            'fieldname': "company",
            'label': __("Company"),
            'fieldtype': "Link",
            'options': "Company",
            'default': frappe.defaults.get_default("Company"),
            'reqd': 1
        },
		{
            'fieldname': "to_date",
            'label': __("To Date"),
            'fieldtype': "Date",
			'default': date.get_today(),
            'reqd': 1
        }
	]
};

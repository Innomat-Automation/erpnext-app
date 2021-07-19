// Copyright (c) 2021, Innomat, Asprotec and libracore and contributors
// For license information, please see license.txt
/* eslint-disable */

frappe.query_reports["Projects to invoice"] = {
    "filters": [
        {
            "fieldname":"company",
            "label": __("Company"),
            "fieldtype": "Link",
            "options": "Company"
        }
    ]
};

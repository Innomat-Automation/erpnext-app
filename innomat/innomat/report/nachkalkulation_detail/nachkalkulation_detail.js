// Copyright (c) 2026, Innomat, Asprotec and libracore and contributors
// For license information, please see license.txt
/* eslint-disable */

frappe.query_reports["Nachkalkulation Detail"] = {
    "filters": [
        {
            fieldname: "projects",
            label: __("Projekte"),
            fieldtype: "MultiSelectList",
            reqd: 1,
            get_data: function(txt) {
                return frappe.db.get_list("Project", {
                    or_filters: [
                        ["name", "like", "%" + (txt || "") + "%"],
                        ["title", "like", "%" + (txt || "") + "%"]
                    ],
                    fields: ["name as value", "title as description"],
                    limit: 20,
                    order_by: "modified desc"
                }).then(results => results.map(r => ({
                    value: r.value,
                    label: r.value,
                    description: r.description
                })));
            }
        }
    ]
};

// Copyright (c) 2026, Innomat and contributors
// For license information, please see license.txt

frappe.query_reports["Jahresergebnis Projekte Mitarbeiter"] = {
    filters: [
        {
            fieldname: "company", label: __("Unternehmen"), fieldtype: "Link",
            options: "Company", default: frappe.defaults.get_user_default("Company"), reqd: 1
        },
        {
            fieldname: "fiscal_year", label: __("Geschäftsjahr"), fieldtype: "Link",
            options: "Fiscal Year", default: String(new Date().getFullYear()), reqd: 1
        },
        {
            fieldname: "view", label: __("Ansicht"), fieldtype: "Select",
            options: "Finanzbuchhaltung\nProjekte\nMitarbeiter", default: "Finanzbuchhaltung", reqd: 1
        }
    ]
};
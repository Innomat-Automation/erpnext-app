frappe.listview_settings['Task'] = {
    onload: function(listview) {
        // default filter settings (ignore when first load from project)
        if (!("project" in frappe.route_options)) {
            frappe.route_options = {
                "completed_by": frappe.session.user,
                "status": "Open"
            };
        }
    }
}

frappe.listview_settings['Task'] = {
    onload: function(listview) {
        // default filter settings
        frappe.route_options = {
            "completed_by": frappe.session.user,
            "status": "Open"
        };
    }
}

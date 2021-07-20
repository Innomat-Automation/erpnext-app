// extend dashboard
cur_frm.dashboard.add_transactions([
    {
        'items': [
            'Settings'
        ],
        'label': __('Persistent Session Default')
    }
]);

frappe.ui.form.on('User', {
    refresh(frm) {
        // button to create sales invoice
        if (!frm.doc.__islocal) {
            frm.add_custom_button(__("Session Defaults"), function() {
                frappe.set_route("List", "Persistent Session Setting", {"user": frm.doc.name});
            });
        }
    }
});

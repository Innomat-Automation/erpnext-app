// Copyright (c) 2022, Innomat, Asprotec and libracore and contributors
// For license information, please see license.txt

frappe.ui.form.on('Service Contract', {
	refresh: function(frm) {
        if (frappe.user.has_role("Accounts User")) {
            // button to create sales invoice
            frm.add_custom_button(__("Create Invoice"), function() {
                create_sinv(frm);
            });
		}
	}
});


function create_sinv(frm) {
    frappe.call({
        'method': "innomat.innomat.scripts.service_contract.create_sinv_from_service_contract",
        'args': {
            'contract': frm.doc.name
        },
        'callback': function(response) {
			frm.reload_doc();
            frappe.show_alert( response.message );
        }
    })
}
// Copyright (c) 2022, Innomat, Asprotec and libracore and contributors
// For license information, please see license.txt

frappe.ui.form.on('Remote Access', {
	// refresh: function(frm) {

	// }
});


frappe.ui.form.on('Remote Access Point', {
    copy_password(frm, cdt, cdn) {
        frappe.call({
            "method": "innomat.innomat.scripts.remote_access.decrypt_access_password",
            "args": {
                "cdn": cdn
            },
            "callback": function(response) {
                navigator.clipboard.writeText(response.message).then(function() {
                    frappe.show_alert( __("Copied") );
                  }, function() {
                     frappe.show_alert( __("No access") );
                });
            }
        });
    }
});
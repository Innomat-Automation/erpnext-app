/*
 * Form handlers for custom automation
 * (also refer to Custom Scripts section in system configuration)
 */
frappe.ui.form.on('Payment Entry', {
    paid_amount: function(frm) {
        if ((frm.doc.ignore_camt === 0) && (frm.doc.camt_amount) && (frm.doc.paid_amount != frm.doc.camt_amount)) {
            frm.set_value("paid_amount", frm.doc.camt_amount);
        }
    },
    on_submit: function(frm) {
        // check if any of the references is against a sales order, if so, match against akonto
        for (var i = 0; i < frm.doc.references.length; i++) {
            if (frm.doc.references[i].reference_doctype === "Sales Order") {
                frappe.call({
                    method:"innomat.innomat.utils.add_akonto_payment_reference",
                    args: {
                        'sales_order': frm.doc.references[i].reference_name,
                        'payment_entry': frm.doc.name
                    },
                    callback: function(r) {
                        frappe.show_alert( __("Updated") + " " + frm.doc.references[i].reference_name);
                    }
                });
            }
        }
    }
});

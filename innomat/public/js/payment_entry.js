/*
 * Form handlers for custom automation
 * (also refer to Custom Scripts section in system configuration)
 */
frappe.ui.form.on('Payment Entry', {
    paid_amount: function(frm) {
        if ((frm.doc.ignore_camt === 0) && (frm.doc.camt_amount) && (frm.doc.paid_amount != frm.doc.camt_amount)) {
            frm.set_value("paid_amount", frm.doc.camt_amount);
        }
    }
});

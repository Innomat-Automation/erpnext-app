frappe.ui.form.on('Quotation', {
    refresh(frm) {
        if (!frm.doc.__islocal) {
            // capture price changes (see innomat_common)
            check_rates(frm);
        }
    }
});

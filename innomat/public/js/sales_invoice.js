frappe.ui.form.on('Sales Invoice', {
    refresh(frm) {
        
    },
    customer(frm) {
        fetch_tax_rule(frm);
    },
    company(frm) {
        fetch_tax_rule(frm);
    }
});

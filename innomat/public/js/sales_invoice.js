frappe.ui.form.on('Sales Invoice', {
    refresh(frm) {
        
    },
    customer(frm) {
        fetch_tax_rule(frm);
    },
    company(frm) {
        fetch_tax_rule(frm);
    },
    delete_contact(frm){
        frm.set_value("contact_display",'');
        frm.set_value("contact_person",null)
    }
});
frappe.ui.form.on('Sales Invoice', {
    refresh(frm) {
        if ((frm.doc.__islocal) && (frm.doc.is_akonto === 1)) {
            // this is a new akonto invoice: insert akonto item
            frappe.call({
                'method': 'innomat.innomat.utils.get_akonto_item',
                'callback': function(r) {
                    if (r.message) {
                        // render links into html string
                        var child = cur_frm.add_child('items');
                        frappe.model.set_value(child.doctype, child.name, 'item_code', r.message);
                        frappe.model.set_value(child.doctype, child.name, 'qty', 1);
                        cur_frm.refresh_field('items');
                        cur_frm.clear_table("sales_item_groups");
                    }
                }
            });
        }
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

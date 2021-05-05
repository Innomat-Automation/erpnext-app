frappe.ui.form.on('Task', {
    before_save(frm) {
       // assure service projects are always invoiced by effort
       if ((frm.doc.project_type === "Service") && (!frm.doc.by_effort)) {
           cur_frm.set_value("by_effort", 1);
           frappe.show_alert( __("Service projects are invoiced by effort") );
       } 
    },
    validate(frm) {
        // make sure that there is an invoiceing item for an invoicable time
        if ((frm.doc.by_effort) && (!frm.doc.item_code)) {
            frappe.msgprint( __("Please select an item for invoicing"), __("Validation") );
            frappe.validated=false;
        }
    }
});

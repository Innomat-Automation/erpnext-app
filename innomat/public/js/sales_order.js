frappe.ui.form.on('Sales Order', {
    refresh(frm) {
        // create project button
        if (frm.doc.docstatus === 1) {
            frm.add_custom_button(__('Create project'), function() {
                frappe.call({
                    method:"innomat.innomat.utils.create_project",
                    args: {
                        'sales_order': frm.doc.name
                    },
                    callback: function(r) {
                        frappe.set_route("Form", "Project", r.message);
                    }
                })
            }).addClass("btn-primary");
        }
    }
});

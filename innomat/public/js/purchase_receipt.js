


frappe.ui.form.on('Purchase Receipt', {
    refresh(frm) {
        if (frm.doc.docstatus === 1) {
            frm.add_custom_button(__("Update Project Link"), function() {
                var field = new Array();
                
                field.push({label : __("Project"), fieldname : "project", fieldtype: 'Link', "options": "Project"})
                frm.doc.items.forEach(e => field.push({label : e.idx + ':' + e.item_code, fieldname : e.name, fieldtype: 'Link', "options": "Project", default: e.project}))

                let d = new frappe.ui.Dialog({
                    title: 'Items',
                    fields: field,
                    primary_action_label: 'Submit',
                    primary_action(values) {
                        d.hide();
                        frappe.call({
                            "method": "innomat.innomat.scripts.purchase_receipt.update_projects",
                            "args": {
                                "data": values,
                                "invoice" : frm.doc.name
                            },
                            "callback": function(response) {
                                var data = response.message;
                                console.log(data);
                                frm.reload_doc();
                            }
                        });
                    }
                });
                d.show();
            });
            frm.add_custom_button(__("Delete all Project Link"), function() {
                frappe.confirm(__("Delete all Project links"),
                () => {
                    frappe.call({
                        "method": "innomat.innomat.scripts.purchase_receipt.delete_projects",
                        "args": {
                            "invoice" : frm.doc.name
                        },
                        "callback": function(response) {
                            var data = response.message;
                            console.log(data);
                            frm.reload_doc();
                        }
                    });
                },
                () => {});
            });
        }
    }
});


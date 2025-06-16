frappe.ui.form.on("Purchase Invoice", {
    "bill_no": function(frm) {
        if(!frm.doc.bill_no.match("^[ A-Za-z0-9\+\?\/\\-\:\(\)\.\,\']+$"))
            {
                frappe.msgprint("Nur alphanumerische Zeichen und +?/-:/()., erlaubt");
            }

    },
    "validate": function(frm) {
        if(!frm.doc.bill_no.match("^[ A-Za-z0-9\+\?\/\\-\:\(\)\.\,\']+$"))
            {
                frappe.msgprint("Nur alphanumerische Zeichen und +?/-:/()., erlaubt");
                frappe.validate = false;
            }

    },
    "refresh": function(frm) {
        // prepare filters
        cur_frm.fields_dict['cost_center'].get_query = function(doc) {
            return {
                filters: {
                    "company": frm.doc.company
                }
            }
        };
        
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
                            "method": "innomat.innomat.scripts.purchase_invoice.update_projects",
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
                        "method": "innomat.innomat.scripts.purchase_invoice.delete_projects",
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

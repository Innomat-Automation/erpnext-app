
{% include "erpnext/public/js/controllers/taxes_and_totals.js" %}


frappe.ui.form.on('Sales Invoice', {
    refresh(frm) {
        // prepare filters
        cur_frm.fields_dict['cost_center'].get_query = function(doc) {
            return {
                filters: {
                    "company": frm.doc.company
                }
            }
        };
	    
        if ((frm.doc.__islocal) && (frm.doc.is_akonto === 1) && (frm.doc.items.length == 0)) {
            // this is a new akonto invoice: insert akonto item
            frappe.call({
                'method': 'innomat.innomat.utils.get_akonto_item',
                "args": {
                    "project": frm.doc.project
                },
                'callback': function(r) {
                    if (r.message) {
                        // render links into html string
                        var child = cur_frm.add_child('items');
                        frappe.model.set_value(child.doctype, child.name, 'item_code', r.message["item"]);
                        cur_frm.refresh_field('items');

                        setTimeout(function() {
                            frappe.model.set_value(child.doctype, child.name, 'qty', 1);
                            frappe.model.set_value(child.doctype, child.name, 'rate', r.message["amount"]);
                            frappe.model.set_value(child.doctype, child.name, 'description', r.message["text"]);
                            cur_frm.refresh_field('items');
                            cur_frm.clear_table("sales_item_groups");
                        }, 1000);
                    }
                }
            });
        }
        if ((frm.doc.docstatus == 0) && (!frm.doc.is_akonto)) {
            frm.add_custom_button(__("Get Akonto"), function() {
                fetch_akonto(frm);
            });
        }
        if (frm.doc.__islocal && frm.doc.additional_discount_percentage_akonto == 0 && frm.doc.additional_discount_percentage > 0) {
            frm.doc.additional_discount_percentage_akonto = frm.doc.additional_discount_percentage;
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
    },
    before_save(frm) {
        apply_discount_from_akonto(frm);

	apply_cost_center(frm);
    },
    additional_discount_percentage_akonto(frm){
        frm.doc.additional_discount_amount_akonto = flt(frm.doc.total * flt(frm.doc.additional_discount_percentage_akonto) / 100, precision("additional_discount_amount_akonto"));
        apply_discount_from_akonto(frm);
		frm.refresh();
    },
    on_submit(frm) {
        frappe.call({
            'method': 'innomat.innomat.scripts.invoices.set_akonto',
            "args": {
                "project": frm.doc.project,
                "sales_invoice": frm.doc.name
            },
            'callback': function(r) {
                frappe.msgprint({
                    title: __('Notification'),
                    indicator: 'green',
                    message: r.message
                });
            }
        });
    },
    before_cancel(frm) {
        frappe.call({
            'method': 'innomat.innomat.scripts.invoices.del_akonto',
            "args": {
                "project": frm.doc.project,
                "sales_invoice": frm.doc.name
            },
            'callback': function(r) {
                if (r.message) {
                    frappe.msgprint({
                        title: __('Notification'),
                        indicator: 'green',
                        message: r.message
                    });
                }
            }
        });
    }

});

frappe.ui.form.on('Sales Invoice Akonto Reference', {
    akonto_references_remove: function(frm) {
        apply_discount_from_akonto(frm);
    }
});
   
// get all un-used akonto invoices from the same sales order
function fetch_akonto(frm) {
    var sales_order = null;
    for (var i = 0; i < frm.doc.items.length; i++) {
        if (frm.doc.items[i].sales_order) {
            sales_order = frm.doc.items[i].sales_order;
            break;
        }
    }
    
    frappe.call({
        "method": "innomat.innomat.utils.fetch_akonto",
        "args": {
            "sales_order": sales_order
        },
        "callback": function(response) {
            if (response.message) {
                for (var a = 0; a < response.message.length; a++) {
                    var child = cur_frm.add_child('akonto_references');
                    frappe.model.set_value(child.doctype, child.name, 'date', response.message[a].date);
                    frappe.model.set_value(child.doctype, child.name, 'sales_invoice', response.message[a].sales_invoice);
                    frappe.model.set_value(child.doctype, child.name, 'net_amount', response.message[a].net_amount);
                    frappe.model.set_value(child.doctype, child.name, 'tax_amount', response.message[a].tax_amount);
                }
                cur_frm.refresh_field('akonto_references');
                apply_discount_from_akonto(frm);
                frappe.show_alert( __("Akonto inserted") );
            }
        }
    });

}

// use the sum of the akonto invoices as discount
function apply_discount_from_akonto(frm) {
    var akonto_discount = 0;
    if (frm.doc.akonto_references) {
        for (var a = 0; a < frm.doc.akonto_references.length; a++) {
            akonto_discount += frm.doc.akonto_references[a].net_amount;
        }
    } 
    akonto_discount += frm.doc.additional_discount_amount_akonto
    cur_frm.set_value("akonto_amount", akonto_discount);
    cur_frm.set_value("apply_discount_on", "Net Total");
    cur_frm.set_value("discount_amount", akonto_discount);
}

function apply_cost_center(frm) {
    if (frm.doc.items) {
        for (let i = 0; i < frm.doc.items.length; i++) {
	    frappe.model.set_value(frm.doc.items[i].doctype, frm.doc.items[i].name, 'cost_center', frm.doc.cost_center);
	}
    }
}

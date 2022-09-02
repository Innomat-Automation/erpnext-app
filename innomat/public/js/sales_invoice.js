
{% include "erpnext/public/js/controllers/taxes_and_totals.js" %}


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
        if ((frm.doc.docstatus == 0) && (!frm.doc.is_akonto)) {
            frm.add_custom_button(__("Get Akonto"), function() {
                fetch_akonto(frm);
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
    },
    before_save(frm) {
        apply_discount_from_akonto(frm);
    },
    additional_discount_percentage_akonto(frm){
        frm.doc.additional_discount_amount_akonto = flt(frm.doc.total * flt(frm.doc.additional_discount_percentage_akonto) / 100, precision("additional_discount_amount_akonto"));
        apply_discount_from_akonto(frm);
		frm.refresh();
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

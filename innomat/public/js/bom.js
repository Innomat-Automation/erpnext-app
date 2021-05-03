frappe.ui.form.on('BOM', {
    refresh(frm) {
        if (frm.doc.docstatus == 0) {
            // button to create sales invoice
            frm.add_custom_button(__("Bulk Import"), function() {
                bulk_import(frm);
            });
        }
    },
    before_save(frm) {
        // update total hours
        var total_hours = 0;
        for (var i = 0; i < frm.doc.items.length; i++) {
            if ((frm.doc.items[i].uom === "h") || (frm.doc.items[i].uom === "h res")) {
                total_hours += frm.doc.items[i].qty;
            }
        }
        cur_frm.set_value("total_hours", total_hours);
    }
});

function bulk_import(frm) {
    var d = new frappe.ui.Dialog({
        'fields': [
            {'fieldname': 'raw', 
             'fieldtype': 'Long Text', 
             'label': __('Code'), 
             'reqd': 1, 
             'description': __("Enter semi-colon separated items, one per line") 
            }
        ],
        primary_action: function() {
            d.hide();
            var values = d.get_values();
            var lines = values.raw.split("\n");
            for (var i = 0; i < lines.length; i++) {
                var fields = [];
                try {
                    fields = lines[i].split(";");
                } catch {
                    console.log("failed to parse field");
                    fields = ["", "0"];
                }
                var child = cur_frm.add_child('items');
                console.log(fields[0]);
                frappe.model.set_value(child.doctype, child.name, 'item_code', fields[0]);
                frappe.model.set_value(child.doctype, child.name, 'qty', fields[1]);
            }
            cur_frm.refresh_field('items');
        },
        primary_action_label: __('OK'),
        title: __('Bulk Import')
    });
    d.show();
}

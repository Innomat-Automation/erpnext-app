frappe.ui.form.on('BOM', {
    refresh(frm) {
        if (frm.doc.docstatus == 0) {
            // button to create sales invoice
            frm.add_custom_button(__("Bulk Import"), function() {
                bulk_import(frm);
            });
            frm.add_custom_button(__("BOM Template"), function() {
                import_template_bom(frm);
            });
        }
        // button to create sales invoice
        frm.add_custom_button(__("Bulk Export"), function() {
            bulk_export(frm);
        });

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


frappe.ui.form.on('BOM Item', {
    item_code(frm, cdt, cdn) {
        // fetch need_task
        var row = locals[cdt][cdn];
        if (row.task) {
            frappe.call({
                'method': "frappe.client.get",
                'args': {
                    'doctype': "Item",
                    'name': row.item_code
                },
                'callback': function (response) {
                    var item = response.message;
                    frappe.model.set_value(cdt, cdn, 'need_task', item.need_task);
                }
            });
        }
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
                    var child = cur_frm.add_child('items');
                    frappe.model.set_value(child.doctype, child.name, 'item_code', fields[0]);
                    frappe.model.set_value(child.doctype, child.name, 'qty', fields[1]);
                } catch {
                    console.log("failed to parse field");
                }

            }
            cur_frm.refresh_field('items');
            // clean up uom and rates
            for (var i = 0; i < frm.doc.items.length; i++) {
                if (!frm.doc.items[i].uom) {
                    frappe.call({
                        "method": "frappe.client.get",
                        "args": {
                            "doctype": "Item",
                            "name": frm.doc.items[i].item_code
                        },
                        "async": false,
                        "callback": function(response) {
                            var item = response.message;
                            frappe.model.set_value(frm.doc.items[i].doctype, frm.doc.items[i].name, 'uom', item.stock_uom);
                        }
                    });
                }
            }
            cur_frm.refresh_field('items');
        },
        primary_action_label: __('OK'),
        title: __('Bulk Import')
    });
    d.show();
}


function bulk_export(frm) {
    var d = new frappe.ui.Dialog({
        'fields': [
            {'fieldname': 'raw', 
             'fieldtype': 'Long Text', 
             'label': __('Code'), 
             'reqd': 1, 
             'description': __("Data to copy"),
             'default': get_items(frm)
            }
        ],
        primary_action: function() {
            d.hide();
        },
        primary_action_label: __('OK'),
        title: __('Bulk Export')
    });
    d.show();
}

function get_items(frm)
{
    var data = []
    for(var i = 0;frm.doc.exploded_items.length > i;i++){
        data.push(frm.doc.exploded_items[i].item_code + ";" + cur_frm.doc.exploded_items[i].qty_consumed_per_unit + ";" + frm.doc.exploded_items[i].item_name)
    }
    return data.join("\n");
}


function import_template_bom(frm) {
    var d = new frappe.ui.Dialog({
        'fields': [
            {'fieldname': 'BOM_Template', 'fieldtype': 'Link', 'label': __('BOM Template'), 'options': 'BOM Template', 'reqd': 1}
        ],
        primary_action: function() {
            d.hide();
            var values = d.get_values();
            frappe.call({
                url: "/api/resource/BOM Template/" + values["BOM_Template"],
                type: "GET",
                callback: function(response) {
                    console.log(response.data.items);
                    if(response.data.items != null && response.data.items.length > 0){
                        for (var i = 0; i < response.data.items.length; i++) {
                            var child = cur_frm.add_child('items');
                            frappe.model.set_value(child.doctype, child.name, 'item_code', response.data.items[i].item_code);
                            frappe.model.set_value(child.doctype, child.name, 'qty', response.data.items[i].qty);
                            console.log("Add item " + response.data.items[i].item_code);
                        }
                    }else{
                        console.log("no items found");
                    }
                    cur_frm.refresh_field('items');
                    // clean up uom and rates
                    for (var i = 0; i < frm.doc.items.length; i++) {
                        if (!frm.doc.items[i].uom) {
                            frappe.call({
                                "method": "frappe.client.get",
                                "args": {
                                    "doctype": "Item",
                                    "name": frm.doc.items[i].item_code
                                },
                                "async": false,
                                "callback": function(response) {
                                    var item = response.message;
                                    frappe.model.set_value(frm.doc.items[i].doctype, frm.doc.items[i].name, 'uom', item.stock_uom);
                                }
                            });
                        }
                    }
                    cur_frm.refresh_field('items');
        
                }
            });
        },
        primary_action_label: __('OK'),
        title: __('BOM Template Import')
        });
    d.show();
}
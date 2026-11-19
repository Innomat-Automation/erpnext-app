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
    },
    update_cost(frm) {
        // override of the standard "Update Cost" handler
        if (frm.doc.docstatus === 1) {
            // submitted BOMs: rate/amount are not allowed to change after
            // submission, so they can only be persisted server-side.
            // Show a read-only preview (old vs. new rates) first; nothing is
            // written until the user confirms. Cancelling keeps the old data.
            return frappe.call({
                'method': "innomat.innomat.scripts.bom.preview_update_cost",
                'args': {'bom': frm.doc.name},
                'freeze': true,
                'callback': function(r) {
                    if (r.exc || !r.message) { return; }
                    show_update_cost_preview(frm, r.message);
                }
            });
        }
        // draft BOMs: only fetch the new rates (save: false) so the user can
        // review them; mark the form as changed so it can be saved manually
        // (the standard handler leaves the form "clean" and unsaveable)
        return frappe.call({
            'doc': frm.doc,
            'method': "update_cost",
            'freeze': true,
            'args': {
                'update_parent': true,
                'from_child_bom': false,
                'save': false
            },
            'callback': function(r) {
                if (!r.exc) {
                    frm.refresh();                      // rebind synced doc with new rates
                    erpnext.bom.update_cost(frm.doc);   // recalculate amounts/totals client-side
                    frm.dirty();                        // enable manual save
                }
            }
        });
    }
});

function show_update_cost_preview(frm, rows) {
    var currency = frm.doc.currency;
    var old_total = 0;
    var new_total = 0;
    var changed = 0;
    var body = "";
    for (var i = 0; i < rows.length; i++) {
        var row = rows[i];
        var old_amount = flt(row.old_rate) * flt(row.qty);
        var new_amount = flt(row.new_rate) * flt(row.qty);
        old_total += old_amount;
        new_total += new_amount;
        var is_changed = Math.abs(flt(row.new_rate) - flt(row.old_rate)) > 0.005;
        if (is_changed) { changed++; }
        body += "<tr" + (is_changed ? " style='font-weight: bold;'" : "") + ">"
            + "<td>" + frappe.utils.escape_html(row.item_code || "") + "</td>"
            + "<td class='text-right'>" + flt(row.qty) + " " + frappe.utils.escape_html(row.uom || "") + "</td>"
            + "<td class='text-right'>" + format_currency(row.old_rate, currency) + "</td>"
            + "<td class='text-right'>" + format_currency(row.new_rate, currency) + "</td>"
            + "</tr>";
    }
    var html = "<table class='table table-bordered small'>"
        + "<thead><tr>"
        + "<th>" + __("Item") + "</th>"
        + "<th class='text-right'>" + __("Qty") + "</th>"
        + "<th class='text-right'>" + __("Current Rate") + "</th>"
        + "<th class='text-right'>" + __("New Rate") + "</th>"
        + "</tr></thead><tbody>" + body + "</tbody>"
        + "<tfoot><tr style='font-weight: bold;'>"
        + "<td colspan='2'>" + __("Raw Material Cost") + "</td>"
        + "<td class='text-right'>" + format_currency(old_total, currency) + "</td>"
        + "<td class='text-right'>" + format_currency(new_total, currency) + "</td>"
        + "</tr></tfoot></table>";
    if (changed === 0) {
        html = "<p>" + __("No price changes") + "</p>" + html;
    }
    var d = new frappe.ui.Dialog({
        'title': __("Update Cost"),
        'fields': [
            {'fieldname': 'preview', 'fieldtype': 'HTML'}
        ],
        'primary_action_label': __("Save"),
        primary_action: function() {
            d.hide();
            frappe.call({
                'doc': frm.doc,
                'method': "update_cost",
                'freeze': true,
                'args': {
                    'update_parent': true,
                    'from_child_bom': false,
                    'save': true
                },
                'callback': function(r) {
                    if (!r.exc) {
                        frm.reload_doc();
                    }
                }
            });
        }
    });
    d.fields_dict.preview.$wrapper.html(html);
    d.show();
}


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
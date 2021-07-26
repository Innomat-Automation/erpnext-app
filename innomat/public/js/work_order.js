
frappe.ui.form.on('Work Order', {
    refresh(frm) {
        // button to create sales invoice
            frm.add_custom_button(__("Bulk Export"), function() {
                bulk_export(frm);
            });
    }
});


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
    for(var i = 0;frm.doc.required_items.length > i;i++){
        data.push(frm.doc.required_items[i].item_code + ";" + cur_frm.doc.required_items[i].required_qty + ";" + cur_frm.doc.required_items[i].item_name)
    }
    return data.join("\n");
}
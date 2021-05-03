frappe.ui.form.on('Sales Order', {
    refresh(frm) {
        if (frm.doc.docstatus === 1) {
            // create project button
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
            
            // create part delivery
            frm.add_custom_button(__('Create part delivery'), function() {
                create_part_delivery(frm);
            }).addClass("btn-primary");
        }
    }
});

function create_part_delivery(frm) {
    var total_qty = 0;
    var delivered_qty = 0;
    for (var i=0; i < frm.doc.items.length; i++) {
        total_qty += frm.doc.items[i].qty;
        delivered_qty += frm.doc.items[i].delivered_qty;
    }
    console.log(total_qty);
    console.log(delivered_qty);
    frappe.prompt([
        {'fieldname': 'deliver_part', 'fieldtype': 'Percent', 'label': __('Deliver part'), 'reqd': 1, 'default': 40}  
    ],
    function(values){
        frappe.call({
            method:"innomat.innomat.utils.create_part_delivery",
            args: {
                'sales_order': frm.doc.name,
                'percentage': values.deliver_part
            },
            callback: function(r) {
                frappe.set_route("Form", "Delivery Note", r.message);
            }
        })
    },
    __('Deliver part') + " (" + Math.round(100 * delivered_qty / total_qty) + __("% delivered)"),
    __('Create')
    )

}

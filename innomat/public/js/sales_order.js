frappe.ui.form.on('Sales Order', {
    refresh(frm) {
        if (frm.doc.docstatus === 1) {
            // create project button if there is no linked project yet
            frappe.call({
                'method': "frappe.client.get_list",
                'args': {
                    'doctype': "Project",
                    'filters': [
                        ["sales_order","=", frm.doc.name]
                    ],
                    'fields': ["name"]
                },
                'callback': function(r) {
                    if ((r.message) && (r.message.length === 0)) {
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
            
            // create part delivery (deprecated 2021-07-20, process no longer used)
            /* frm.add_custom_button(__('Create part delivery'), function() {
                create_part_delivery(frm);
            }).addClass("btn-primary"); */ 
            // create akonto
            frm.add_custom_button(__('Create akonto'), function() {
                create_akonto(frm);
            }).addClass("btn-primary");
        }
        if (!frm.doc.__islocal) {
            // capture price changes (see innomat_common)
            check_rates(frm);
        }
    },
    before_save(frm) {
        // update akonto table
        var net_amount = get_effective_net_amount(frm);
        var tax_rate = get_tax_rate(frm);
        if (frm.doc.akonto) {
            for (var a = 0; a < frm.doc.akonto.length; a++) {
                recalculate_akonto(frm, frm.doc.akonto[a].doctype, frm.doc.akonto[a].name);
            }
        }
    },
    customer(frm) {
        fetch_tax_rule(frm);
    },
    company(frm) {
        fetch_tax_rule(frm);
    }
});

frappe.ui.form.on('Sales Order Akonto', {
    amount(frm, cdt, cdn) {
        // amount set, compute percentage
        var akonto = locals[cdt][cdn];
        var net_amount = get_effective_net_amount(frm);
        var tax_rate = get_tax_rate(frm);
        var percent = (akonto / (net_amount * tax_rate)) * 100;
        frappe.model.set_value(cdt, cdn, 'percent', percent);
    },
    percent(frm, cdt, cdn) {
        recalculate_akonto(frm, cdt, cdn);
    }
});

function recalculate_akonto(frm, cdt, cdn) {
    var akonto = locals[cdt][cdn];
    var fraction  = frappe.model.get_value(cdt, cdn, 'percent') / 100;
    var gross_amount = net_amount * tax_rate * fraction;
    if (abs(gross_amount - akonto.amount) >= 1) {
        // only update amount if it is more than CHF 1 different from actual value (compensate for rounding)
        frappe.model.set_value(frm.doc.akonto[a].doctype, frm.doc.akonto[a].name, 'amount', gross_amount);
    }
}

function get_tax_rate(frm) {
    var tax_rate = 1;
    if ((frm.doc.taxes) && (frm.doc.taxes.length > 0)) {
        tax_rate = 1 + (frm.doc.taxes[0].rate / 100);
    }
    return tax_rate;
}

function get_effective_net_amount(frm) {
    var net_amount = 0;
    for (var i = 0; i < frm.doc.items.length; i++) {
        if (frm.doc.items[i].by_effort === 0) {
            net_amount += frm.doc.items[i].amount;
        }
    }
    return net_amount;
}

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
            });
        },
        __('Deliver part') + " (" + Math.round(100 * delivered_qty / total_qty) + __("% delivered)"),
        __('Create')
    );
}

function create_akonto(frm) {
    frappe.call({
        method:"innomat.innomat.utils.create_akonto",
        args: {
            'sales_order': frm.doc.name
        },
        callback: function(r) {
            cur_frm.reload_doc();
        }
    });
}

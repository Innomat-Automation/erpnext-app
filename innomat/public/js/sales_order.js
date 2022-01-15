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
                            var d = new frappe.ui.Dialog({
                                'fields': [
                                    {'fieldname': 'combine_bom', 
                                     'fieldtype': 'Check', 
                                     'label': __('Combine Task per Bom'), 
                                     'default': 0
                                    }
                                ],
                                primary_action: function() {
                                    var values = d.get_values();
                                    frappe.call({
                                        method:"innomat.innomat.scripts.sales_order.create_project",
                                        args: {
                                            'sales_order': frm.doc.name,
                                            'combine_bom': values.combine_bom
                                        },
                                        callback: function(r) {
                                            frappe.set_route("Form", "Project", r.message);
                                        }
                                    })
                                    d.hide();
                                },
                                primary_action_label: __('OK'),
                                title: __('Create Project')
                            });
                            d.show();
                        }).addClass("btn-primary");
                    }
                }
            });
            
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
    form_render : function(frm, cdt, cdn) {
        var akonto = locals[cdt][cdn];
        if(akonto.file === undefined) {
            frm.fields_dict.akonto.grid.grid_rows[akonto.idx -1].toggle_editable("date",true);
            frm.fields_dict.akonto.grid.grid_rows[akonto.idx -1].toggle_editable("percent",true);
            frm.fields_dict.akonto.grid.grid_rows[akonto.idx -1].toggle_editable("netto",true);
            frm.fields_dict.akonto.grid.grid_rows[akonto.idx -1].toggle_editable("remarks",true);
            frm.fields_dict.akonto.grid.grid_rows[akonto.idx -1].toggle_editable("print_total_and_percent",true);
        }else{
            frm.fields_dict.akonto.grid.grid_rows[akonto.idx -1].toggle_editable("date",false);
            frm.fields_dict.akonto.grid.grid_rows[akonto.idx -1].toggle_editable("percent",false);
            frm.fields_dict.akonto.grid.grid_rows[akonto.idx -1].toggle_editable("netto",false);
            frm.fields_dict.akonto.grid.grid_rows[akonto.idx -1].toggle_editable("remarks",false);
            frm.fields_dict.akonto.grid.grid_rows[akonto.idx -1].toggle_editable("print_total_and_percent",false);
        }
    },
    netto(frm, cdt, cdn) {
        var akonto = locals[cdt][cdn];
        var net_amount = get_effective_net_amount(frm);
        var percent = (akonto.netto / net_amount) * 100;
        frappe.model.set_value(cdt, cdn, 'percent', percent);
        var tax_rate = get_tax_rate(frm);
        frappe.model.set_value(cdt, cdn, 'amount', akonto.netto * tax_rate);
    },
    percent(frm, cdt, cdn) {
        recalculate_akonto(frm, cdt, cdn);
    },
    date(frm, cdt, cdn) {
        recalculate_akonto(frm, cdt, cdn);
    }
});

function recalculate_akonto(frm, cdt, cdn) {
    var akonto = locals[cdt][cdn];
    var fraction  = frappe.model.get_value(cdt, cdn, 'percent') / 100;
    var net_amount = get_effective_net_amount(frm);
    var tax_rate = get_tax_rate(frm);
    var gross_amount = net_amount * fraction;
    if ((Math.abs(gross_amount - (akonto.amount || 0)) >= 1) || (!akonto.amount)) {
        // only update amount if it is more than CHF 1 different from actual value (compensate for rounding)
        frappe.model.set_value(cdt, cdn, 'netto', gross_amount);
        frappe.model.set_value(cdt, cdn, 'amount', akonto.netto * tax_rate);
        cur_frm.refresh_field('akonto');
    }frappe
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
            net_amount += frm.doc.items[i].net_amount;
        }
    }
    if (net_amount === 0) {
        net_amount = 0.01;      // in case of all by effort positions to prevent division by 0
    }
    return net_amount;
}

function create_akonto(frm) {
    frappe.call({
        method:"innomat.innomat.scripts.sales_order.create_akonto",
        args: {
            'sales_order': frm.doc.name
        },
        callback: function(r) {
            cur_frm.reload_doc();
        }
    });
}


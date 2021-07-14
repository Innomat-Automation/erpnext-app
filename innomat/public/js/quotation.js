frappe.ui.form.on('Quotation', {
    refresh(frm) {
        if (!frm.doc.__islocal) {
            // capture price changes (see innomat_common)
            check_rates(frm);
        }
    },
    party_name(frm) {
        fetch_tax_rule_qtn(frm);
    },
    company(frm) {
        fetch_tax_rule_qtn(frm);
    }
});

/*
 * This function will correctly load the tax template for sales documents
 */
function fetch_tax_rule_qtn(frm) {
    if ((frm.doc.party_name) && (frm.doc.company)) {
        frappe.call({
            'method': 'innomat.innomat.utils.get_sales_tax_rule',
            'args': {
                'customer': frm.doc.party_name,
                'company': frm.doc.company
            },
            "callback": function(response) {
                // delay callback so that the customer selling controller is overridden (otherwise, link field is wrong)
                setTimeout(function() {
                    cur_frm.set_value("taxes_and_charges", response.message);
                }, 1000);
            }
        });
    }
}

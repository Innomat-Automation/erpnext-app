frappe.listview_settings['Purchase Invoice'] = {
    onload: function(listview) {
        listview.page.add_menu_item( __("Quick Invoice"), function() {
            quick_invoice();
        });
    }
}

function quick_invoice() {
    frappe.prompt([
            {'fieldname': 'company', 'fieldtype': 'Link', 'label': __("Company"), 'options': 'Company', 'reqd': 1},
            {'fieldname': 'date', 'fieldtype': 'Date', 'label': __("Date"), 'reqd': 1},
            {'fieldname': 'amount', 'fieldtype': 'Currency', 'label': __("Amount"), 'reqd': 1},
            {'fieldname': 'expense_account', 'fieldtype': 'Link', 'label': __("Expense account"), 'options': 'Account', 'reqd': 1},
            {'fieldname': 'taxes', 'fieldtype': 'Link', 'label': __("Taxes"), 'options': 'Purchase Taxes and Charges Template', 'reqd': 1},
            {'fieldname': 'supplier', 'fieldtype': 'Link', 'label': __("Supplier"), 'options': 'Supplier', 'reqd': 1},
            {'fieldname': 'remarks', 'fieldtype': 'Data', 'label': __("Remarks"), 'reqd': 1}
        ],
        function(values){
            frappe.call({
                'method': 'innomat.innomat.utils.quick_pinv',
                'args': {
                    'date': values.date,
                    'gross_amount': values.amount,
                    'supplier': values.supplier,
                    'expense_account': values.expense_account,
                    'purchase_taxes': values.taxes,
                    'remarks': values.remarks,
                    'company': values.company
                },
                callback: function(r) {
                    frappe.show_alert(r.message);
                    // loop to create the next
                    quick_invoice();
                }
            });
        },
        __("Quick purchase invoice"),
        __("Create")
    )
}

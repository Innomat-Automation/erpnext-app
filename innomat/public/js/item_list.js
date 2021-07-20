frappe.listview_settings['Item'] = {
    onload: function(listview) {
        listview.page.add_menu_item( __("Set Prices"), function() {
            set_prices();
        });
    }
}


function set_prices() {
    frappe.prompt([
            {'fieldname': 'sourcelist', 'fieldtype': 'Link', 'label': __('Source Price List'), 'reqd': 1,'options': 'Price List'},
            {'fieldname': 'destlist', 'fieldtype': 'Link', 'label': __('Destination Price List'), 'reqd': 1,'options': 'Price List'},
            {'fieldname': 'itemgroup', 'fieldtype': 'Link', 'label': __('Item Group'), 'reqd': 1,'options': 'Item Group'},
            {'fieldname': 'margin', 'fieldtype': 'Float', 'label': __('Margin'), 'reqd': 1},
            {'fieldname': 'set_valuation_rate', 'fieldtype': 'Check', 'label': __('Set Valuation Rate'), 'reqd': 1},
        ],
        function(values){
            frappe.call({
                "method": "innomat.innomat.utils.set_price_list",
                "args": {
                    "sourcelist" : values.sourcelist,
                    "destlist" : values.destlist,
                    "itemgroup" : values.itemgroup,
                    "margin" : values.margin,
                    "set_valuation_rate" : values.set_valuation_rate
                },
                "callback": function(response) {
                    frappe.show_alert( response.message );
                }
            });
        },
        __('Create Prices'),
        __('Create')
    );
}
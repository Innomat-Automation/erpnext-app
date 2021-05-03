frappe.listview_settings['Project'] = {
    onload: function(listview) {
        listview.page.add_menu_item( __("Create Service Invoices"), function() {
            create_service_sales_invoices();
        });
    }
}

function create_service_sales_invoices() {
    frappe.prompt([
            {'fieldname': 'from_date', 'fieldtype': 'Date', 'label': __('From Date'), 'reqd': 1, 'default': get_start_last_quarter()},
            {'fieldname': 'to_date', 'fieldtype': 'Date', 'label': __('To Date'), 'reqd': 1, 'default': get_end_last_quarter()}
        ],
        function(values){
            frappe.call({
                "method": "innomat.innomat.utils.create_sinvs_for_date_range",
                "args": {
                    "from_date": values.from_date,
                    "to_date": values.to_date
                },
                "callback": function(response) {
                    frappe.show_alert( response.message );
                }
            });
        },
        __('Create Service Invoices'),
        __('Create')
    );
}

function get_start_last_quarter() {
    var today = new Date(frappe.datetime.get_today());
    var act_month = today.getMonth();
    var fullyear = today.getFullYear();
    if ([0, 1, 2].includes(act_month)) {
        fullyear = fullyear - 1;
        var start = new Date(String(fullyear) + "-10-01");
    }
    if ([3, 4, 5].includes(act_month)) {
        var start = new Date(String(fullyear) + "-01-01");
    }
    if ([6, 7, 8].includes(act_month)) {
        var start = new Date(String(fullyear) + "-04-01");
    }
    if ([9, 10, 11].includes(act_month)) {
        var start = new Date(String(fullyear) + "-07-01");
    }
    return start;
}

function get_end_last_quarter() {
    var today = new Date(frappe.datetime.get_today());
    var act_month = today.getMonth();
    var fullyear = today.getFullYear();
    if ([0, 1, 2].includes(act_month)) {
        fullyear = fullyear - 1;
        var end = new Date(String(fullyear) + "-12-31");
    }
    if ([3, 4, 5].includes(act_month)) {
        var end = new Date(String(fullyear) + "-03-31");
    }
    if ([6, 7, 8].includes(act_month)) {
        var end = new Date(String(fullyear) + "-06-30");
    }
    if ([9, 10, 11].includes(act_month)) {
        var end = new Date(String(fullyear) + "-09-30");
    }
    
    return end;
}

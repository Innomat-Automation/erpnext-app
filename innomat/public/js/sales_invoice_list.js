frappe.listview_settings['Sales Invoice'] = {
    onload: function(listview) {
        listview.page.add_menu_item( __("Get Invoices"), function() {
            get_sales_invoices();
        });
        listview.page.add_menu_item( __("Get Akontos"), function() {
            get_sales_akonto();
        });
    },
    get_indicator: function(doc) {
		var status_color = {
			"Draft": "grey",
			"Unpaid": "orange",
			"Paid": "green",
			"Return": "darkgrey",
			"Credit Note Issued": "darkgrey",
			"Unpaid and Discounted": "orange",
			"Overdue and Discounted": "red",
			"Overdue": "red"

		};
		return [__(doc.status), status_color[doc.status], "status,=,"+doc.status];
	}
}


function get_sales_invoices() {
    frappe.prompt([
        {'fieldname': 'company', 'fieldtype': 'Link', 'label': __("Company"), 'options': 'Company', 'reqd': 1},
        {'fieldname': 'fromdate', 'fieldtype': 'Date', 'label': __("From Date"), 'reqd': 1},
        {'fieldname': 'todate', 'fieldtype': 'Date', 'label': __("To Date"), 'reqd': 1}
    ],
    function(values){
        window.open('/api/method/innomat.innomat.scripts.invoices.get_sales_invoices?' +
								'&company=' + encodeURIComponent(values.company) + '&fromdate=' + encodeURIComponent(values.fromdate) + '&todate=' + encodeURIComponent(values.todate));
    },
    __("Quick purchase invoice"),
    __("Create")
)
}

function get_sales_akonto() {
    frappe.prompt([
        {'fieldname': 'company', 'fieldtype': 'Link', 'label': __("Company"), 'options': 'Company', 'reqd': 1},
        {'fieldname': 'fromdate', 'fieldtype': 'Date', 'label': __("From Date"), 'reqd': 1},
        {'fieldname': 'todate', 'fieldtype': 'Date', 'label': __("To Date"), 'reqd': 1}
    ],
    function(values){
        window.open('/api/method/innomat.innomat.scripts.invoices.get_sales_akonto?' +
								'&company=' + encodeURIComponent(values.company) + '&fromdate=' + encodeURIComponent(values.fromdate) + '&todate=' + encodeURIComponent(values.todate));
    },
    __("Quick purchase invoice"),
    __("Create")
)
}

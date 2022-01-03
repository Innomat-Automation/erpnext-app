


frappe.listview_settings['Expense Claim'] = {
	onload: function(listview) {
        listview.page.add_menu_item( __("Get Expens Claims"), function() {
            get_expense_claim_attachement();
        });
    },
	add_fields: ["total_claimed_amount", "docstatus"],
	get_indicator: function(doc) {
		if(doc.status == "Paid") {
			return [__("Paid"), "green", "status,=,'Paid'"];
		}else if(doc.status == "Unpaid") {
			return [__("Unpaid"), "orange"];
		} else if(doc.status == "Rejected") {
			return [__("Rejected"), "grey"];
		}
	}
};


function get_expense_claim_attachement() {
    frappe.prompt([
        {'fieldname': 'company', 'fieldtype': 'Link', 'label': __("Company"), 'options': 'Company', 'reqd': 1},
        {'fieldname': 'fromdate', 'fieldtype': 'Date', 'label': __("Date"), 'reqd': 1},
        {'fieldname': 'todate', 'fieldtype': 'Date', 'label': __("Date"), 'reqd': 1}
    ],
    function(values){
        window.open('/api/method/innomat.innomat.scripts.expense_claim.get_expense_claim_attachement?' +
								'&company=' + encodeURIComponent(values.company) + '&fromdate=' + encodeURIComponent(values.fromdate) + '&todate=' + encodeURIComponent(values.todate));
    },
    __("Quick expense claim"),
    __("Create")
)
}


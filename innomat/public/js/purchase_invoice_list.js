frappe.listview_settings['Purchase Invoice'] = {
    onload: function(listview) {
        listview.page.add_menu_item( __("Get Invoices"), function() {
            get_invoices();
        });
    },
    add_fields: ["supplier", "supplier_name", "base_grand_total", "outstanding_amount", "due_date", "company",
      "currency", "is_return", "release_date", "on_hold"],
    get_indicator: function(doc) {
        if(flt(doc.outstanding_amount) < 0 && doc.docstatus == 1) {
         return [__("Debit Note Issued"), "darkgrey", "outstanding_amount,<,0"]
        } else if(flt(doc.outstanding_amount) > 0 && doc.docstatus==1) {
         if(cint(doc.on_hold) && !doc.release_date) {
            return [__("On Hold"), "darkgrey"];
         } else if(cint(doc.on_hold) && doc.release_date && frappe.datetime.get_diff(doc.release_date, frappe.datetime.nowdate()) > 0) {
            return [__("Temporarily on Hold"), "darkgrey"];
         } else if(frappe.datetime.get_diff(doc.due_date) < 0) {
            return [__("Overdue"), "red", "outstanding_amount,>,0|due_date,<,Today"];
         } else {
            return [__("Unpaid"), "orange", "outstanding_amount,>,0|due,>=,Today"];
         }
        } else if(cint(doc.is_return)) {
         return [__("Return"), "darkgrey", "is_return,=,Yes"];
        } else if(flt(doc.outstanding_amount)==0 && doc.docstatus==1) {
         return [__("Paid"), "green", "outstanding_amount,=,0"];
        }
    }
}

function get_invoices() {
    frappe.prompt([
        {'fieldname': 'company', 'fieldtype': 'Link', 'label': __("Company"), 'options': 'Company', 'reqd': 1},
        {'fieldname': 'fromdate', 'fieldtype': 'Date', 'label': __("Date"), 'reqd': 1},
        {'fieldname': 'todate', 'fieldtype': 'Date', 'label': __("Date"), 'reqd': 1}
    ],
    function(values){
        window.open('/api/method/innomat.innomat.scripts.invoices.get_invoices?' +
								'&company=' + encodeURIComponent(values.company) + '&fromdate=' + encodeURIComponent(values.fromdate) + '&todate=' + encodeURIComponent(values.todate));
    },
    __("Quick purchase invoice"),
    __("Create")
)
}
// Copyright (c) 2022, Innomat, Asprotec and libracore and contributors
// For license information, please see license.txt

frappe.ui.form.on('Acceptance Report', {
	refresh(frm) {
        frm.add_custom_button(__("Get Timesheets"),  function() {
            get_timesheets(frm);

        }, __("Tools"));
		frm.add_custom_button(__("Get Delivery Notes"),  function() {
            get_deliverynotes(frm);

        }, __("Tools"));
    },
});


function get_timesheets(frm)
{
    frappe.call({
        'method': "innomat.innomat.scripts.acceptance_report.get_timesheet_entrys",
        'args': {
            'project': frm.doc.project,
			'employee': frm.doc.employee
            },
            'callback': function(response) {
				console.log(response);
				var data = response.message;
				if (data) {
					for (var i = 0; i < data.length; i++) {
						var child = cur_frm.add_child('timesheets');
						frappe.model.set_value(child.doctype, child.name, 'activity_type', data[i].activity_type);
						frappe.model.set_value(child.doctype, child.name, 'from_time', (data[i].from_time));
						frappe.model.set_value(child.doctype, child.name, 'to_time', (data[i].to_time));
						frappe.model.set_value(child.doctype, child.name, 'hours', (data[i].hours));
						frappe.model.set_value(child.doctype, child.name, 'remarks', (data[i].external_remarks));
						frappe.model.set_value(child.doctype, child.name, 'ts', (data[i].timesheet));
						frappe.model.set_value(child.doctype, child.name, 'ts_detail', (data[i].ts_detail));
					}
					cur_frm.refresh_field('timesheets');
					frappe.show_alert(__("Updated"));
				} 
            }
    });
}

function get_deliverynotes(frm)
{
    frappe.call({
        'method': "innomat.innomat.scripts.acceptance_report.get_delivery_notes",
        'args': {
            'project': frm.doc.project
            },
            'callback': function(response) {
				console.log(response);
				var data = response.message;
				if (data) {
					for (var i = 0; i < data.length; i++) {
						var child = cur_frm.add_child('delivery');
						frappe.model.set_value(child.doctype, child.name, 'item_code', data[i].item_code);
						frappe.model.set_value(child.doctype, child.name, 'description', (data[i].description));
						frappe.model.set_value(child.doctype, child.name, 'qty', (data[i].qty));
						frappe.model.set_value(child.doctype, child.name, 'dn', (data[i].dn));
						frappe.model.set_value(child.doctype, child.name, 'dn_entry', (data[i].dn_entry));
					}
					cur_frm.refresh_field('delivery');
					frappe.show_alert(__("Updated"));
				} 
            }
    });
}
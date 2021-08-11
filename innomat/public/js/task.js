frappe.ui.form.on('Task', {
    "by_effort": function(frm) {
        frappe.msgprint("Um bestehende Timesheets zu aktualisieren auf Timesheet aktualisieren drücken!");
    },
    refresh(frm) {
        frm.add_custom_button(__("Update Timesheets"), function() {
                update_timesheets(frm);
        });
    },
    before_save(frm) {
       // assure service projects are always invoiced by effort
       if ((frm.doc.project_type === "Service") && (!frm.doc.by_effort)) {
           cur_frm.set_value("by_effort", 1);
           frappe.show_alert( __("Service projects are invoiced by effort") );
       } 
       // compute fte of this task
       if ((frm.doc.expected_time) && (frm.doc.exp_start_date) && (frm.doc.exp_end_date) && (frm.doc.completed_by)) {
            frappe.call({
                'method': 'innomat.innomat.utils.get_fte',
                'async': false,
                'args': {
                    'user': frm.doc.completed_by,
                    'start_date': frm.doc.exp_start_date, 
                    'end_date': frm.doc.exp_end_date,
                    'hours': frm.doc.expected_time
                },
                'callback': function(r) {
                    cur_frm.set_value('fte', r.message);
                }
            });
       }
    },
    validate(frm) {
        // make sure that there is an invoiceing item for an invoicable time
        if ((frm.doc.by_effort) && (!frm.doc.item_code)) {
            frappe.msgprint( __("Please select an item for invoicing"), __("Validation") );
            frappe.validated=false;
        }
    }
});

function update_timesheets(frm) {
    frappe.call({
        'method': 'innomat.innomat.utils.update_timesheets',
        'async': false,
        'args': {
            'task': frm.doc.name,
            'by_effort': frm.doc.by_effort
        },
        'callback': function(r) {
            console.log(r);
            console.log(r.message.count);
            frappe.msgprint("Aktualisiert Einträge: " + r.message.count);
        }
    });
}
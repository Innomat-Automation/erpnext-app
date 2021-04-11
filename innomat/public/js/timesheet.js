frappe.ui.form.on('Timesheet', {
    refresh(frm) {
        // filter projects by employee (team member)
        frm.fields_dict.time_logs.grid.get_field('project').get_query =   
            function(doc, cdt, cdn) {    
                return {
                    filters: {'employee': frm.doc.employee},
                    query: "innomat.innomat.filters.projects_for_employee"
                };
        };
        // button to create delivery notes
        if (frm.doc.docstatus === 0) {
            frm.add_custom_button(__("Delivered Material"), function() {
                create_dn(frm);
            });
        }
    },
    validate(frm) {
        // get lock date
        var lock_date = new Date('2000-01-01T00:00:00');
        frappe.call({
            "method": "innomat.innomat.utils.get_timesheet_lock_date",
            "async": false,
            "callback": function(response) {
                lock_date = response.message;
            }
        });
        // validate booking entries
        for (var i = 0; i < frm.doc.time_logs.length; i++) {
            // check that booking is after lock date
            if (frm.doc.time_logs[i].from_time <= lock_date) {
                frappe.msgprint( __("Row {0} is before lock date").replace("{0}", (i+1)), __("Validation") );
                frappe.validated=false;
            }
            // check that projects are set (and only) for activities with project
            if ((frm.doc.time_logs[i].with_project === 1) && (!frm.doc.time_logs[i].project)) {
                frappe.msgprint( __("Project required for {0} in row {1}").replace("{0}", frm.doc.time_logs[i].activity_type).replace("{1}", (i+1)), __("Validation") );
                frappe.validated=false;
            } else if ((frm.doc.time_logs[i].with_project === 0) && (frm.doc.time_logs[i].project)) {
                frm.doc.time_logs[i].project = null;
            }
            // check that if project type is "Project", task is selected
            if ((frm.doc.time_logs[i].project_type === "Project") && (!frm.doc.time_logs[i].task)) {
                frappe.msgprint( __("Task required for {0} in row {1}").replace("{0}", frm.doc.time_logs[i].project).replace("{1}", (i+1)), __("Validation") );
                frappe.validated=false;
            }
            // check if a template was used that it was changed
            if ((frm.doc.time_logs[i].template_character_count) && (frm.doc.time_logs[i].template_character_count === frm.doc.time_logs[i].external_remarks.length)) {
                frappe.msgprint( __("Please edit the external remarks in row {0}").replace("{0}", (i+1)), __("Validation") );
                frappe.validated=false;
            }
        }
    }
});

frappe.ui.form.on('Timesheet Detail', {
    button_template(frm, cdt, cdn) {
        // ask for template
        pull_external_text_from_template(frm, cdt, cdn);
    },
    activity_type(frm, cdt, cdn) {
        pull_external_text_from_activity(frm, cdt, cdn);
    },
    time_logs_add(frm, cdt, cdn) {
        var row_idx = frappe.model.get_value(cdt, cdn, 'idx');
        if (row_idx > 1) {
            var last_time = frm.doc.time_logs[row_idx - 2].to_time;
            if (last_time) {
                frappe.model.set_value(cdt, cdn, 'from_time', last_time);
            }
        }
    }
});

function pull_external_text_from_activity(frm, cdt, cdn) {
    // check if there is a matching template
    var row = locals[cdt][cdn];
    frappe.call({
        method: 'frappe.client.get_list',
        args: {
            doctype: 'Textkonserve',
            filters: {'name': row.activity_type},
            fields: ['name', 'text']
        },
        "callback": function(response) {
            var templates = response.message;

            if ((templates) && (templates.length > 0)) {
                frappe.model.set_value(cdt, cdn, "external_remarks", templates[0].text);
                frappe.model.set_value(cdt, cdn, "template_character_count", templates[0].text.length);
            }
        }
    });
}

function pull_external_text_from_template(frm, cdt, cdn) {
    // get all templates
    frappe.call({
        method: 'frappe.client.get_list',
        args: {
            doctype: 'Textkonserve',
            fields: ['name', 'text']
        },
        callback: function(response) {
            // check which template should be filled
            if ((response.message) && (response.message.length > 0)) {
                var templates = [];
                for (var i = 0; i < response.message.length; i++) {
                    templates.push(response.message[i].name);
                }
                frappe.prompt([
                        {
                            'fieldname': 'template', 
                            'fieldtype': 'Select', 
                            'label': __('Template'), 
                            'options': templates.join('\n'),
                            'default': templates[0],
                            'reqd': 1
                        } 
                    ],
                    function(values){
                        var text = "";
                        for (var j = 0; j < response.message.length; j++) {
                            if (response.message[j].name === values.template) {
                                text = response.message[j].text;
                                break;
                            }
                        } 
                        frappe.model.set_value(cdt, cdn, "external_remarks", text);
                        frappe.model.set_value(cdt, cdn, "template_character_count", text.length);
                    },
                    __('Templates'),
                    __('Select')
                )
            } else {
                frappe.msgprint( __("No templates found") );
            }
        }
    });
}

function create_dn(frm) {
    var d = new frappe.ui.Dialog({
        'fields': [
            {'fieldname': 'project', 'fieldtype': 'Link', 'label': 'Project', 'options': 'Project', 'reqd': 1},
            {'fieldname': 'item', 'fieldtype': 'Link', 'label': 'Item', 'options': 'Item', 'reqd': 1},
            {'fieldname': 'qty', 'fieldtype': 'Float', 'label': 'Qty', 'reqd': 1, 'default': 1}
        ],
        primary_action: function(){
            d.hide();
            var values = d.get_values();
            frappe.call({
                method: 'innomat.innomat.utils.create_dn',
                args: {
                    project: values.project,
                    item: values.item,
                    qty: values.qty
                },
                "callback": function(response) {
                    frappe.show_alert( response.message );
                }
            });
        },
        primary_action_label: __('OK'),
        title: __('Delivered Material')
    });
    d.fields_dict['project'].get_query =   
        function(doc) {    
            return {
                filters: {'employee': frm.doc.employee},
                query: "innomat.innomat.filters.projects_for_employee"
            };
        };
    d.show();
}

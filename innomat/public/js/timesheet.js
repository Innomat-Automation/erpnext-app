const travel_key = "Reisetätigkeit";
         
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
        // filter activity types by prio
        frm.fields_dict.time_logs.grid.get_field('activity_type').get_query = function(doc, cdt, cdn) {
            return {
                filters:{'disabled': 0},
                order_by: 'prio'
            }
        }
        if (!frm.doc.__islocal) {
            // button to create delivery notes
            if (frm.doc.docstatus === 0) {
                frm.add_custom_button(__("Delivered Material"), function() {
                    create_dn(frm);
                });
            }
            // button to add on call fees
            if (frm.doc.docstatus === 0) {
                frm.add_custom_button(__("On Call Fee"), function() {
                    create_on_call_fee(frm);
                });
            }
            // button to add on call fees
            if (frm.doc.docstatus === 0) {
                frm.add_custom_button(__("Service Report"), function() {
                    create_service_report(frm);
                });
            }
        }
        // hide salary buttons
        $('button[data-label="Create%20Salary%20Slip"]').hide();
        $('button[data-label="Gehaltsabrechnung%20erstellen"]').hide(); 
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
        var projects = [];
        for (var i = 0; i < frm.doc.time_logs.length; i++) {
            // compile list of all projects
            if ((frm.doc.time_logs[i].project) && (!(projects.includes(frm.doc.time_logs[i].project)))) {
                projects.push(frm.doc.time_logs[i].project);
            }
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
                frappe.model.set_value(frm.doc.time_logs[i].doctype, frm.doc.time_logs[i].name, "project", null);
                frappe.model.set_value(frm.doc.time_logs[i].doctype, frm.doc.time_logs[i].name, "project_title", null);
                frappe.model.set_value(frm.doc.time_logs[i].doctype, frm.doc.time_logs[i].name, "project_type", null);
                frappe.model.set_value(frm.doc.time_logs[i].doctype, frm.doc.time_logs[i].name, "task", null);
                frappe.model.set_value(frm.doc.time_logs[i].doctype, frm.doc.time_logs[i].name, "task_name", null);
                continue;
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
            // check if a this is a travel expense and mileage or fees are recorded
            if (frm.doc.time_logs[i].activity_type === travel_key) {
                if ((frm.doc.time_logs[i].travel_type.indexOf("wagen") >= 0) && (!(frm.doc.time_logs[i].kilometers > 0))) {
                    frappe.msgprint( __("Please set mileage in row {0}").replace("{0}", (i+1)), __("Validation") );
                    frappe.validated=false;
                } else if ((frm.doc.time_logs[i].travel_type === "ÖV") && (!(frm.doc.time_logs[i].travel_fee > 0))) {
                    frappe.msgprint( __("Please set travel fee in row {0}").replace("{0}", (i+1)), __("Validation") );
                    frappe.validated=false;
                }
            }
        }
        // validate that all projects are open
        var project_str = "\"" + projects.join("\", \"") + "\"";
        frappe.call({
            'method': "innomat.innomat.utils.check_projects_open",
            'args': {
                'projects': project_str
            },
            'sync': false,
            'callback': function(response) {
                if (response.message) {
                    frappe.msgprint( __("Only open projects can be booked ({0})").replace("{0}", response.message), __("Validation") );
                    frappe.validated=false;
                }
            }
        });
    },
    on_submit(frm) {
        create_travel_notes(frm);
        
        close_completed_tasks(frm);
    },
    after_cancel(frm) {
        unclose_completed_tasks(frm);
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
    },
    task(frm, cdt, cdn) {
        // fetch by effort
        var row = locals[cdt][cdn];
        if (row.task) {
            frappe.call({
               'method': "frappe.client.get",
               'args': {
                    'doctype': "Task",
                    'name': row.task
               },
               'callback': function(response) {
                    var task = response.message;
                    frappe.model.set_value(cdt, cdn, 'by_effort', task.by_effort);
               }
            });
        }
    }
});

function pull_external_text_from_activity(frm, cdt, cdn) {
    // check if there is a matching template
    var row = locals[cdt][cdn];
    frappe.call({
        'method': 'frappe.client.get_list',
        'args': {
            'doctype': 'Textkonserve',
            'filters': {'name': row.activity_type},
            'fields': ['name', 'text']
        },
        'callback': function(response) {
            var templates = response.message;

            if ((templates) && (templates.length > 0)) {
                frappe.model.set_value(cdt, cdn, "external_remarks", templates[0].text);
                frappe.model.set_value(cdt, cdn, "template_character_count", templates[0].text.length);
            } else {
                frappe.model.set_value(cdt, cdn, "external_remarks", null);
                frappe.model.set_value(cdt, cdn, "template_character_count", null);
            }
        }
    });
}

function pull_external_text_from_template(frm, cdt, cdn) {
    // get all templates
    frappe.call({
        'method': 'frappe.client.get_list',
        'args': {
            'doctype': 'Textkonserve',
            'fields': ['name', 'text']
        },
        'callback': function(response) {
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
            {'fieldname': 'project', 'fieldtype': 'Link', 'label': __('Project'), 'options': 'Project', 'reqd': 1},
            {'fieldname': 'item', 'fieldtype': 'Link', 'label': __('Item'), 'options': 'Item', 'reqd': 1},
            {'fieldname': 'qty', 'fieldtype': 'Float', 'label': __('Qty'), 'reqd': 1, 'default': 1},
            {'fieldname': 'description', 'fieldtype': 'Data', 'label': __('Description')}
        ],
        primary_action: function(){
            d.hide();
            var values = d.get_values();
            frappe.call({
                'method': 'innomat.innomat.utils.create_dn',
                'args': {
                    'project': values.project,
                    'item': values.item,
                    'qty': values.qty,
                    'description': (values.description || ""),
                    'timesheet': frm.doc.name
                },
                'callback': function(response) {
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

function create_on_call_fee(frm) {
    var d = new frappe.ui.Dialog({
        'fields': [
            {'fieldname': 'project', 'fieldtype': 'Link', 'label': __('Project'), 'options': 'Project', 'reqd': 1},
            {'fieldname': 'date', 'fieldtype': 'Date', 'label': __('Date'), 'default': new Date(), 'reqd': 1}
        ],
        primary_action: function(){
            d.hide();
            var values = d.get_values();
            frappe.call({
                'method': 'innomat.innomat.utils.create_on_call_fee',
                'args': {
                    'project': values.project,
                    'date': values.date,
                    'timesheet': frm.doc.name
                },
                'callback': function(response) {
                    frappe.show_alert( response.message );
                }
            });
        },
        primary_action_label: __('OK'),
        title: __('On Call Fee')
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

function create_travel_notes(frm) {
    frappe.call({
        'method': 'innomat.innomat.utils.create_travel_notes',
        'args': {
            'timesheet': frm.doc.name,
            'travel_key': travel_key
        },
        "callback": function(response) {
            frappe.show_alert( response.message );
        }
    });
}

function create_service_report(frm) {
    var projects = [];
    for (var i = 0; i < frm.doc.time_logs.length; i++) {
        if ((frm.doc.time_logs[i].project) && (!projects.includes(frm.doc.time_logs[i].project))) {
            projects.push(frm.doc.time_logs[i].project);
        }
    } 
    frappe.prompt([
            {'fieldname': 'project', 'fieldtype': 'Select', 'label': __('Project'), 'reqd': 1, 'options': projects.join("\n")},
            {'fieldname': 'contact', 'fieldtype': 'Data', 'label': __('Contact person'), 'reqd': 1}
        ],
        function(values){
            frappe.call({
                'method': "innomat.innomat.utils.create_service_report",
                'args': {
                    'contact': values.contact,
                    'timesheet': frm.doc.name,
                    'project': values.project
                },
                'callback': function(response) {
                    frappe.show_alert( response.message );
                    window.open("/private/files/" + response.message, '_blank').focus();
                }
            });
        },
        __('Service Report'),
        __('Create')
    );
}

function close_completed_tasks(frm) {
    frappe.call({
        'method': 'innomat.innomat.utils.close_completed_tasks',
        'args': {
            'timesheet': frm.doc.name
        }
    });
}

function unclose_completed_tasks(frm) {
    frappe.call({
        'method': 'innomat.innomat.utils.close_completed_tasks',
        'args': {
            'timesheet': frm.doc.name,
            'close': 0
        }
    });
}

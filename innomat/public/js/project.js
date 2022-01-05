// extend dashboard
cur_frm.dashboard.add_transactions([
    {
        'items': [
            'Equipment'
        ],
        'label': __('Equipment')
    }
]);

/*
 * Form handlers for custom automation
 * (also refer to Custom Scripts section in system configuration)
 */
frappe.ui.form.on('Project', {
    refresh(frm) {
        // restricted area for account users (elevated)
        if (frappe.user.has_role("Accounts User")) {
            // button to create sales invoice
            frm.add_custom_button(__("Create Invoice"), function() {
                create_sinv(frm);
            });
            // draft notification area
            if (!frm.doc.__islocal) {
                frappe.call({
                    'method': 'innomat.innomat.scripts.project.find_drafts',
                    'args': {
                        'project': frm.doc.name
                    },
                    'callback': function(r) {
                        if ((r.message) && (r.message.has_drafts === 1)) {
                            // render links into html string
                            var html = r.message.urls.join(", ");
                            cur_frm.dashboard.add_comment( __('This project has drafts: {0}', [html]), 'yellow', true);
                        }
                    }
                });
            }
            
        }
    },
    before_save(frm) {
        if (frm.doc.__islocal) {
            get_project_key(frm);
        }
        set_project_manager(frm);
    }
});

/*
 * This function will generate the unique project key
 */
function get_project_key(frm) {
    frappe.call({
        'method': 'innomat.innomat.utils.get_project_key',
        'async': false,
        'callback': function(r) {
            cur_frm.set_value('project_key', r.message);
            var company_key = "IN";
            if (frm.doc.company.indexOf('Asprotec') >= 0) {
                company_key = "AS";
            }
            cur_frm.set_value('project_name', company_key + frm.doc.project_type.charAt(0) + r.message);
            cur_frm.set_value('title', frm.doc.project_name + " " + (frm.doc.title || ""));s
        }
    });
}

/*
 * This function will set the project manager field from the child table
 */
function set_project_manager(frm) {
    if ((frm.doc.project_team) && (frm.doc.project_team.length > 0)) {
        for (var i=0; i < frm.doc.project_team.length; i++) {
            if (frm.doc.project_team[i].project_manager === 1) {
                cur_frm.set_value("project_manager", frm.doc.project_team[i].employee);
                cur_frm.set_value("project_manager_name", frm.doc.project_team[i].full_name);
                break
            }
        }
    }
}

function create_sinv(frm) {
    frappe.call({
        'method': "innomat.innomat.scripts.project.create_sinv_from_project",
        'args': {
            'project': frm.doc.name,
            'sales_item_group': frm.doc.project_type
        },
        'callback': function(response) {
            frappe.show_alert( response.message );
            if (frm.doc.status === "Completed") {
                cur_frm.set_value("is_invoiced", 1);
                cur_frm.set_value("is_active", "No");
            }
        }
    })
}

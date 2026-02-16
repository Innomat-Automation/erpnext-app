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
        frm.add_custom_button(__("Projektcockpit"), function() {
            frm.print_preview.refresh_print_options();
            frm.print_preview.print_sel.val("Projektcockpit");
            frm.page.set_view("print");
            frm.print_preview.set_user_lang();
            frm.print_preview.set_default_print_language();
            frm.print_preview.preview();
        });
        frm.add_custom_button(__("Projektübersicht"), function() {
            frm.print_preview.refresh_print_options();
            frm.print_preview.print_sel.val("Projektübersicht");
            frm.page.set_view("print");
            frm.print_preview.set_user_lang();
            frm.print_preview.set_default_print_language();
            frm.print_preview.preview();
        });
        set_department_filter(frm);
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
        if(frm.doc.company.startsWith("Innomat") && !frm.doc.department && frm.doc.name.substr(3,2) != "00") {
            // (Project number starting with 00: Special projects for general operating costs. Can exist without a department.)
            frappe.msgprint(__("Bei Innomat-Projekten bitte die Abteilung (Standort) angeben."));
            frm.scroll_to_field('department');
            frappe.validated=false;
            return;
        }
        set_cost_center(frm);
        if (frm.doc.__islocal) {
            get_project_key(frm);
        }
        set_project_manager(frm);
    },
    company(frm) {
        set_department_filter(frm);
    }
});

/*
 * This function will generate the unique project key and assign the cost center
 */
function get_project_key(frm) {
    frappe.call({
        'method': 'innomat.innomat.utils.get_project_key',
        'async': false,
        'callback': function(r) {
            cur_frm.set_value('project_key', r.message);
            let company_key = "XX";
            if (frm.doc.department) {
                if(frm.doc.department.includes('Frauenfeld')) {
                    company_key = "AS";
                } else if(frm.doc.department.includes('Herisau')) {
                    company_key = "IN";
                }
            }
            else if(frm.doc.company) {
                company_key = frm.doc.company.substr(0,2).toUpperCase();
            }
            cur_frm.set_value('project_name', company_key + frm.doc.project_type.charAt(0) + r.message);
            cur_frm.set_value('title', frm.doc.project_name + " " + (frm.doc.title || ""));
        }
    });
}


/**
  * Set cost center from company and/or department
  */
function set_cost_center(frm) {
    if (frm.doc.department) {
        if(frm.doc.project_type == 'Intern' && frm.doc.company.startsWith("Innomat") && frm.doc.name.substr(3,2) != "00") {
            // Cost center for internal development projects
            frm.set_value("cost_center", "Entwicklung - I");
            // (Project number starting with 00: Special projects for general operating costs rather than development. Set cost center based on department.)
        } else {
            frappe.db.get_value("Department", frm.doc.department, "default_cost_center").then(r => {
                if(r.message && r.message.default_cost_center) {
                    frm.set_value("cost_center", r.message.default_cost_center);
                } else {
                    frappe.msgprint(__("Für die Abteilung '{0}' ist keine Standard-Kostenstelle definiert", [frm.doc.department]), __("Fehler beim Ermitteln der Kostenstelle"));
                    frappe.validated = false;
                }
            });
        }
    } else {
        frappe.db.get_value("Company", frm.doc.company, "cost_center").then(r => {
            if(r.message && r.message.cost_center) {
                frm.set_value("cost_center", r.message.cost_center);
            } else {
                frappe.msgprint(__("Für das Unternehmen '{0}' ist keine Standard-Kostenstelle definiert", [frm.doc.company]), __("Fehler beim Ermitteln der Kostenstelle"));
                frappe.validated = false;
            }
        });
    }
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

function set_department_filter(frm) {
    frm.fields_dict.department.get_query = function(doc, cdt, cdn) {
        return {
            filters: {'company': frm.doc.company},
        };
    };
}

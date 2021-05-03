/*
 * Form handlers for custom automation
 * (also refer to Custom Scripts section in system configuration)
 */
frappe.ui.form.on('Project', {
    before_save(frm) {
        if (frm.doc.__islocal) {
            get_project_key(frm);
        }
        set_project_manager(frm);
        
        // invoice completed project
        if ((frm.doc.project_type === "Service") && (frm.doc.status === "Completed") && (frm.doc.is_invoiced === 0)) {
            frappe.call({
                method: "innomat.innomat.utils.create_sinv_from_project",
                args: {
                    'project': frm.doc.name
                },
                callback: function(response) {
                    frappe.show_alert( response.message );
                    cur_frm.set_value("is_invoiced", 1);
                }
            })
        }
    }
});

/*
 * This function will generate the unique project key
 */
function get_project_key(frm) {
    frappe.call({
        method: 'innomat.innomat.utils.get_project_key',
        async: false,
        callback: function(r) {
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
    for (var i=0; i < frm.doc.project_team.length; i++) {
        if (frm.doc.project_team[i].project_manager === 1) {
            cur_frm.set_value("project_manager", frm.doc.project_team[i].employee);
            cur_frm.set_value("project_manager_name", frm.doc.project_team[i].full_name);
            break
        }
    }
}

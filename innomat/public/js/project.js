frappe.ui.form.on('Project', {
    before_save(frm) {
        if ((frm.doc.__islocal) && (!frm.doc.project_key)) {
            get_project_key(frm);
        }
    }
});

function get_project_key(frm) {
    frappe.call({
        method: 'innomat.innomat.utils.get_project_key',
        async: false,
        callback: function(r) {
            cur_frm.set_value('project_key', r.message);
            var company_key = "IN";
            if (frm.doc.company.indexOf('Asprotec') >= 0) {
                company_key = "AS"
            }
            cur_frm.set_value('project_name', company_key + frm.doc.project_type.charAt(0) + r.message);
            cur_frm.set_value('title', frm.doc.project_name + " " + (frm.doc.title || ""));
            console.log("done");
        }
    });
}

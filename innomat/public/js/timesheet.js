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
    }
});

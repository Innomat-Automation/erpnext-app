frappe.ui.form.on('Expense Claim', {
    refresh(frm) {
        // filter projects by employee (team member)
        frm.fields_dict.expenses.grid.get_field('project').get_query =   
            function(doc, cdt, cdn) {    
                return {
                    filters: {'employee': frm.doc.employee},
                    query: "innomat.innomat.filters.projects_for_employee"
                };
        };
    }
});

frappe.ui.form.on('Expense Claim Detail', {
    qty(frm, cdt, cdn) {
        set_amount_from_qty(frm, cdt, cdn);
    },
    internal_rate(frm, cdt, cdn) {
        set_amount_from_qty(frm, cdt, cdn);
    },
    amount(frm, cdt, cdn) {
        var child = locals[cdt][cdn]
        frappe.model.set_value(cdt, cdn, 'sanctioned_amount', child.amount);
    }
});

function set_amount_from_qty(frm, cdt, cdn) {
    var child = locals[cdt][cdn]
    var new_amount = child.qty * child.internal_rate;
    if (new_amount > 0) {
        frappe.model.set_value(cdt, cdn, 'amount', (child.qty * child.internal_rate));
    }
}

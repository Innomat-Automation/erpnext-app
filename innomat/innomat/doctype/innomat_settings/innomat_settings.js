// Copyright (c) 2021, Innomat, Asprotec and libracore and contributors
// For license information, please see license.txt

frappe.ui.form.on('Innomat Settings', {
    refresh: function(frm) {
        frm.fields_dict.akonto_accounts.grid.get_field('akonto_account').get_query =   
            function(frm, cdt, cdn) {                                                                      
                var v = locals[cdt][cdn];
                return {
                        filters: {
                            "company": v.company
                            }
                }
            };
    }
});

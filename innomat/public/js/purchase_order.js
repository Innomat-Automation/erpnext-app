frappe.ui.form.on('Purchase Order', {
    before_save(frm) {
       // assure each item has a project assigned
       if (frm.doc.project) {
           for (var i = 0; i < frm.doc.items.length; i++) {
               if (!frm.doc.items[i].project) {
                   frappe.model.set_value(frm.doc.items[i].doctype, frm.doc.items[i].name, "project", frm.doc.project);
               }
           }
       } 
    }
});

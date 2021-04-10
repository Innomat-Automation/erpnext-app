frappe.ui.form.on('BOM', {
    before_save(frm) {
        // update total hours
        var total_hours = 0;
        for (var i = 0; i < frm.doc.items.length; i++) {
            if ((frm.doc.items[i].uom === "h") || (frm.doc.items[i].uom === "h res")) {
                total_hours += frm.doc.items[i].qty;
            }
        }
        cur_frm.set_value("total_hours", total_hours);
    }
});

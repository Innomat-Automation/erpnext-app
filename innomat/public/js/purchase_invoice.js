

frappe.ui.form.on("Purchase Invoice", {
    "bill_no": function(frm) {
        if(!frm.doc.bill_no.match("^[ A-Za-z0-9\+\?\/\-\:\(\)\.\,\']+$"))
            {
                frappe.msgprint("Nur alphanumerische Zeichen und +?/-:/()., erlaubt");
            }

    }
});
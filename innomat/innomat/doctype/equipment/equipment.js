// Copyright (c) 2021, Innomat, Asprotec and libracore and contributors
// For license information, please see license.txt

frappe.ui.form.on('Equipment', {
    refresh(frm) {
        // filter projects only for customer
        cur_frm.fields_dict['project'].get_query = function(doc) {
            return {
                filters: {
                    "customer": frm.doc.customer
                }
            }
        }
        // filter addresses by end customer
        cur_frm.fields_dict['location'].get_query = function(doc) {
            return {
                query: "frappe.contacts.doctype.address.address.address_query",
                filters: {
                    "link_doctype": "Customer",
                    "link_name": frm.doc.end_customer
                }
            }
        }
    },
    project(frm) {
        if ((!frm.doc.customer) && (frm.doc.project)) {
            frappe.call({
                "method": "frappe.client.get",
                "args": {
                    "doctype": "Project",
                    "name": frm.doc.project
                },
                "callback": function(response) {
                    var project = response.message;
                    cur_frm.set_value("customer", project.customer);
                    cur_frm.set_value("customer_name", project.customer_name);
                }
            });
        }
        if ((!frm.doc.title) && (frm.doc.project)) {
            cur_frm.set_value("title", frm.doc.project);
        }
    },
    location(frm) {
        if (frm.doc.location) {
            frappe.call({
                "method": "frappe.client.get",
                "args": {
                    "doctype": "Address",
                    "name": frm.doc.location
                },
                "callback": function(response) {
                    var address = response.message;
                    var html = address.address_line1;
                    if (address.address_line2) {
                        html += "<br>" + address.address_line2;
                    }
                    html += "<br>" + address.pincode + " " + address.city;
                    html += "<br>" + address.country;
                    cur_frm.set_value("location_display", html);
                }
            });
        } else {
            cur_frm.set_value("location_display", null);
        }
    }
});



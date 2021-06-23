// Innomat script global script inserts

// mark navbar in specific colour
window.onload = function () {
        setTimeout(function() {
                var navbars = document.getElementsByClassName("navbar");
                if (navbars.length > 0) {
                        if (window.location.hostname.includes("srv-erp-test")) {
                                navbars[0].style.backgroundColor = "#d68080";
                        }
                }
        }, 500);
}

function aggregate_groups(frm) {
    // find all groups and their amount
    var groups = {};
    (frm.doc.items || []).forEach(function (item) {
        var this_group = item.sales_item_group;
        if (this_group === undefined) {
            this_group  = "empty";
        }
        if (groups[this_group] === undefined) {
            // first occurence
            groups[this_group] = item.amount;
        } else {
            // add amount
            groups[this_group] = groups[this_group ] + item.amount;
        }
    });
    // update child table groups (to keep manual changes)
    (frm.doc.sales_item_groups || []).forEach(function (group) {
        frappe.model.set_value(group.doctype, group.name, "total_amount", 0);
    });
    for (var key in groups) {
        var match = false;
        var amount = groups[key];
        if (frm.doc.sales_item_groups) {
            for (var g = (frm.doc.sales_item_groups.length - 1); g >= 0; g--) {
                if (frm.doc.sales_item_groups[g].group === key) {
                    if (match === true) {
                        // this is a duplicate, remove
                        cur_frm.get_field("sales_item_groups").grid.grid_rows[g].remove();
                        cur_frm.refresh();
                    } else {
                        match = true;
                        frappe.model.set_value(frm.doc.sales_item_groups[g].doctype, frm.doc.sales_item_groups[g].name, "total_amount", amount);
                    }
                }
            }
        }
        if (match === false) {
            // add new row
            var child = cur_frm.add_child('sales_item_groups');
            frappe.model.set_value(child.doctype, child.name, 'group', key);
            frappe.model.set_value(child.doctype, child.name, 'title', key);
            frappe.model.set_value(child.doctype, child.name, 'sum_caption', 'Summe ' + key);
            frappe.model.set_value(child.doctype, child.name, 'total_amount', amount);
        }
    }
}

/* this function will check if there are rate changes and write them to the html_price_info */
function check_rates(frm) {
    frappe.call({
        method: "innomat.innomat.utils.check_rates",
        args: {
            'doctype': frm.doc.doctype,
            'docname': frm.doc.name
        },
        callback: function(response) {
            var html = response.message.html || "";
            cur_frm.set_df_property('html_price_info', 'options', html);
        }
    })
}

/*
 * This is a new hook to detect post-login, in order to load persistent session defaults
 */
$(document).on('app_ready', function() {
    // app ready, let's rumble
    console.log("let's rumble");
    // get persistent session settings
    frappe.call({
        'method': "frappe.client.get_list",
        'args': {
            'doctype': "Persistent Session Setting",
            'filters': {'user': frappe.session.user},
            'fields': ["setting_key", "setting_value"]
        },
        'callback': function(response) {
            if (response.message) {
                response.message.forEach(function (setting) {
                    var key = setting.setting_key.toLowerCase().replaceAll(" ", "_");
                    frappe.defaults.set_user_default_local(key, setting.setting_value);
                });
            }
        }
    });
});

frappe.pages['crm_dashboard'].on_page_load = function(wrapper) {
    var page = frappe.ui.make_app_page({
        parent: wrapper,
        title: __("CRM Dashboard"),
        single_column: true
    });

    frappe.crm_dashboard.make(page);
    frappe.crm_dashboard.refresh();

    frappe.breadcrumbs.add("Innomat");
};

frappe.crm_dashboard = {
    page: null,
    body: null,
    entries: {},

    make: function(page) {
        var me = frappe.crm_dashboard;
        me.page = page;

        me.user_field = page.add_field({
            fieldname: 'user',
            label: __("Benutzer"),
            fieldtype: 'Link',
            options: 'User',
            change: function() { me.refresh(); }
        });

        page.set_primary_action(__("Neuer Eintrag"), function() { me.new_entry(); }, 'add');
        page.add_inner_button(__("Aktualisieren"), function() { me.refresh(); }, 'refresh');

        me.body = $('<div class="crm-dashboard"></div>').appendTo(page.main);
        me.body.on('click', '.crm-entry', function() {
            me.edit_entry($(this).attr('data-name'));
        });
        me.body.on('click', '.crm-open-lead', function(e) {
            e.stopPropagation();
            frappe.set_route("Form", "Lead", $(this).attr('data-lead'));
        });
    },

    refresh: function() {
        var me = frappe.crm_dashboard;
        frappe.call({
            method: 'innomat.innomat.page.crm_dashboard.crm_dashboard.get_upcoming',
            args: { user: me.user_field ? me.user_field.get_value() : null },
            callback: function(r) {
                if (!r.message) { return; }
                me.render(r.message);
            }
        });
    },

    render: function(data) {
        var me = frappe.crm_dashboard;
        me.entries = {};
        (["Telefonat", "Besprechung"]).forEach(function(type) {
            (data[type] || []).forEach(function(e) { me.entries[e.name] = e; });
        });
        var html = '<div class="row">'
            + '<div class="col-sm-6">' + me.render_section(__("Nächste Telefonate"), data["Telefonat"] || []) + '</div>'
            + '<div class="col-sm-6">' + me.render_section(__("Nächste Besprechungen"), data["Besprechung"] || []) + '</div>'
            + '</div>';
        me.body.html(html);
    },

    render_section: function(title, entries) {
        var html = '<h4>' + title + ' <span class="text-muted">(' + entries.length + ')</span></h4>';
        if (!entries.length) {
            return html + '<p class="text-muted">' + __("Keine offenen Einträge") + '</p>';
        }
        html += '<ul class="list-unstyled">';
        entries.forEach(function(e) {
            var subject = frappe.utils.escape_html(e.lead_name || e.company_name || e.lead || '');
            var when = frappe.datetime.str_to_user(e.date);
            if (e.time) { when += ' ' + e.time.substring(0, 5); }
            var overdue = e.date && e.date < frappe.datetime.get_today();
            html += '<li class="crm-entry" data-name="' + frappe.utils.escape_html(e.name) + '"'
                + ' style="cursor:pointer; border:1px solid #d1d8dd; border-radius:4px; padding:8px; margin-bottom:6px;">'
                + '<span class="' + (overdue ? 'text-danger' : 'text-muted') + '">' + when + '</span>'
                + ' &ndash; <b>' + subject + '</b>'
                + (e.user ? ' <span class="text-muted">(' + frappe.utils.escape_html(e.user) + ')</span>' : '')
                + ' <a class="crm-open-lead pull-right" data-lead="' + frappe.utils.escape_html(e.lead) + '">'
                + __("Lead") + '</a>'
                + (e.note ? '<div class="text-muted small">' + frappe.utils.escape_html(e.note) + '</div>' : '')
                + '</li>';
        });
        html += '</ul>';
        return html;
    },

    edit_entry: function(name) {
        var me = frappe.crm_dashboard;
        var doc = me.entries[name];
        if (!doc) { return; }
        var d = new frappe.ui.Dialog({
            title: __("Termin bearbeiten"),
            fields: [
                { fieldname: 'communication_type', label: __("Art"), fieldtype: 'Select',
                  options: "Telefonat\nBesprechung", reqd: 1, default: doc.communication_type },
                { fieldname: 'status', label: __("Status"), fieldtype: 'Select',
                  options: "Geplant\nErledigt", reqd: 1, default: doc.status },
                { fieldname: 'completed', label: __("Erledigt"), fieldtype: 'Check', default: 0 },
                { fieldname: 'cb', fieldtype: 'Column Break' },
                { fieldname: 'date', label: __("Datum"), fieldtype: 'Date', reqd: 1, default: doc.date },
                { fieldname: 'time', label: __("Zeit"), fieldtype: 'Time', default: doc.time },
                { fieldname: 'user', label: __("Benutzer"), fieldtype: 'Link', options: 'User', default: doc.user },
                { fieldname: 'sb', fieldtype: 'Section Break' },
                { fieldname: 'preparation', label: __("Vorbereitung"), fieldtype: 'Small Text', default: doc.preparation },
                { fieldname: 'note', label: __("Gesprächsnotiz"), fieldtype: 'Small Text', default: doc.note },
                { fieldname: 'follow_up', label: __("Nachbereitung"), fieldtype: 'Small Text', default: doc.follow_up }
            ],
            primary_action_label: __("Speichern"),
            primary_action: function(values) {
                frappe.call({
                    method: 'innomat.innomat.page.crm_dashboard.crm_dashboard.update_entry',
                    args: { name: name, values: values },
                    freeze: true,
                    callback: function(r) {
                        if (!r.exc) {
                            d.hide();
                            frappe.show_alert({ message: __("Gespeichert"), indicator: 'green' });
                            me.refresh();
                        }
                    }
                });
            }
        });
        d.show();
        },

        new_entry: function() {
                var me = frappe.crm_dashboard;
                var d = new frappe.ui.Dialog({
                        title: __("Neuer CRM-Eintrag"),
                        fields: [
                                { fieldname: 'communication_type', label: __("Art"), fieldtype: 'Select',
                                    options: "Telefonat\nBesprechung", reqd: 1, default: "Telefonat" },
                                { fieldname: 'lead', label: __("Bestehender Lead"), fieldtype: 'Link',
                                    options: 'Lead' },
                                { fieldname: 'new_lead_name', label: __("Neuer Lead"), fieldtype: 'Data',
                                    description: __("Nur ausfüllen, wenn kein bestehender Lead ausgewählt ist") },
                                { fieldname: 'cb', fieldtype: 'Column Break' },
                                { fieldname: 'date', label: __("Datum"), fieldtype: 'Date', reqd: 1,
                                    default: frappe.datetime.get_today() },
                                { fieldname: 'time', label: __("Zeit"), fieldtype: 'Time' },
                                { fieldname: 'user', label: __("Benutzer"), fieldtype: 'Link', options: 'User',
                                    default: frappe.session.user },
                                { fieldname: 'sb', fieldtype: 'Section Break' },
                                { fieldname: 'preparation', label: __("Vorbereitung"), fieldtype: 'Small Text' },
                                { fieldname: 'note', label: __("Gesprächsnotiz"), fieldtype: 'Small Text' },
                                { fieldname: 'follow_up', label: __("Nachbereitung"), fieldtype: 'Small Text' }
                        ],
                        primary_action_label: __("Anlegen"),
                        primary_action: function(values) {
                                if (!values.lead && !values.new_lead_name) {
                                        frappe.msgprint(__("Bitte einen bestehenden Lead auswählen oder einen neuen Namen eingeben"));
                                        return;
                                }
                                frappe.call({
                                        method: 'innomat.innomat.page.crm_dashboard.crm_dashboard.create_entry',
                                        args: { values: values },
                                        freeze: true,
                                        callback: function(r) {
                                                if (!r.exc) {
                                                        d.hide();
                                                        frappe.show_alert({ message: __("Eintrag angelegt"), indicator: 'green' });
                                                        me.refresh();
                                                }
                                        }
                                });
                        }
                });
                d.show();
    }
};

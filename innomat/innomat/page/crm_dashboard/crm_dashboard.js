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
        me.body.on('click', '.crm-entry', function(e) {
            if ($(e.target).closest('.crm-open-lead, .crm-create-follow-up').length) { return; }
            me.edit_entry($(this).attr('data-name'));
        });
        me.body.on('click', '.crm-open-lead', function(e) {
            e.preventDefault();
            e.stopPropagation();
            frappe.set_route("Form", "Lead", $(this).attr('data-lead'));
        });
        me.body.on('click', '.crm-create-follow-up', function(e) {
            e.preventDefault();
            e.stopPropagation();
            me.create_follow_up($(this).attr('data-name'));
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
        (["Telefon", "Remotebesprechung", "Vor Ort Besprechung"]).forEach(function(type) {
            (data[type] || []).forEach(function(e) { me.entries[e.name] = e; });
        });
        var html = '<div class="crm-dashboard-frame"><div class="row">'
            + '<div class="col-sm-4 crm-dashboard-column">' + me.render_section(__("Nächste Telefon"), data["Telefon"] || []) + '</div>'
            + '<div class="col-sm-4 crm-dashboard-column">' + me.render_section(__("Nächste Remotebesprechungen"), data["Remotebesprechung"] || []) + '</div>'
            + '<div class="col-sm-4 crm-dashboard-column">' + me.render_section(__("Nächste Vor Ort Besprechungen"), data["Vor Ort Besprechung"] || []) + '</div>'
            + '</div></div>';
        me.body.html(html);
    },

    render_section: function(title, entries) {
        var html = '<div class="crm-dashboard-section"><h4 class="crm-dashboard-section-title">' + title + ' <span class="text-muted">(' + entries.length + ')</span></h4>';
        if (!entries.length) {
            return html + '<p class="text-muted crm-empty-state">' + __("Keine offenen Einträge") + '</p></div>';
        }
        html += '<ul class="list-unstyled crm-entry-list">';
        entries.forEach(function(e) {
            var subject = frappe.utils.escape_html(e.lead_name || e.company_name || e.lead || '');
            var when = frappe.datetime.str_to_user(e.date);
            if (e.time) { when += ' ' + e.time.substring(0, 5); }
            var overdue = e.date && e.date < frappe.datetime.get_today();
            html += '<li class="crm-entry' + (overdue ? ' crm-entry-overdue' : '') + '" data-name="' + frappe.utils.escape_html(e.name) + '">'
                + '<div class="crm-entry-header"><span class="crm-entry-date">' + when + '</span>'
                + ' <b class="crm-entry-subject">' + subject + '</b></div>'
                + (e.user ? ' <span class="text-muted">(' + frappe.utils.escape_html(e.user) + ')</span>' : '')
                + '<div class="crm-entry-actions">'
                + '<a href="#" class="crm-open-lead" data-lead="' + frappe.utils.escape_html(e.lead) + '">'
                + __("Lead öffnen") + '</a>'
                + '<a href="#" class="crm-create-follow-up" data-name="' + frappe.utils.escape_html(e.name) + '">'
                + __("Neue Kommunikation") + '</a></div>'
                + (e.note ? '<div class="text-muted small">' + frappe.utils.escape_html(e.note) + '</div>' : '')
                + (e.preparation ? '<div class="crm-entry-preparation"><span class="crm-entry-label">' + __("Vorbereitung") + ':</span> ' + frappe.utils.escape_html(e.preparation) + '</div>' : '')
                + '</li>';
        });
        html += '</ul>';
        return html + '</div>';
    },

    edit_entry: function(name) {
        var me = frappe.crm_dashboard;
        var doc = me.entries[name];
        if (!doc) { return; }
        var d = new frappe.ui.Dialog({
            title: __("Termin bearbeiten"),
            fields: [
                { fieldname: 'communication_type', label: __("Art"), fieldtype: 'Select',
                  options: "Telefon\nRemotebesprechung\nVor Ort Besprechung", reqd: 1, default: doc.communication_type },
                { fieldname: 'completed', label: __("Erledigt"), fieldtype: 'Check', default: 0 },
                { fieldname: 'cb', fieldtype: 'Column Break' },
                { fieldname: 'date', label: __("Datum"), fieldtype: 'Date', reqd: 1, default: doc.date },
                { fieldname: 'time', label: __("Zeit"), fieldtype: 'Time', default: doc.time },
                                { fieldname: 'duration', label: __("Dauer (Stunden)"), fieldtype: 'Float',
                                    default: doc.duration || 1, min: 0.25, precision: 2 },
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

        create_follow_up: function(name) {
            var me = frappe.crm_dashboard;
            var doc = me.entries[name];
            if (!doc) { return; }
            var d = new frappe.ui.Dialog({
                title: __("Neue Kommunikation für {0}", [doc.lead_name || doc.company_name || doc.lead]),
                fields: [
                    { fieldname: 'communication_type', label: __("Art"), fieldtype: 'Select',
                        options: "Telefon\nRemotebesprechung\nVor Ort Besprechung", reqd: 1, default: doc.communication_type || "Telefon" },
                    { fieldname: 'date', label: __("Datum"), fieldtype: 'Date', reqd: 1,
                        default: frappe.datetime.get_today() },
                    { fieldname: 'time', label: __("Zeit"), fieldtype: 'Time' },
                    { fieldname: 'duration', label: __("Dauer (Stunden)"), fieldtype: 'Float',
                        default: doc.duration || 1, min: 0.25, precision: 2 },
                    { fieldname: 'user', label: __("Benutzer"), fieldtype: 'Link', options: 'User',
                        default: doc.user || frappe.session.user },
                    { fieldname: 'sb', fieldtype: 'Section Break' },
                    { fieldname: 'preparation', label: __("Vorbereitung"), fieldtype: 'Small Text' },
                    { fieldname: 'note', label: __("Gesprächsnotiz"), fieldtype: 'Small Text' },
                    { fieldname: 'follow_up', label: __("Nachbereitung"), fieldtype: 'Small Text' }
                ],
                primary_action_label: __("Anlegen"),
                primary_action: function(values) {
                    frappe.call({
                        method: 'innomat.innomat.page.crm_dashboard.crm_dashboard.create_follow_up_entry',
                        args: { name: name, values: values },
                        freeze: true,
                        callback: function(r) {
                            if (!r.exc) {
                                d.hide();
                                frappe.show_alert({ message: __("Eintrag angelegt und alter erledigt"), indicator: 'green' });
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
                                    options: "Telefon\nRemotebesprechung\nVor Ort Besprechung", reqd: 1, default: "Telefon" },
                                { fieldname: 'lead', label: __("Bestehender Lead"), fieldtype: 'Link',
                                    options: 'Lead' },
                                { fieldname: 'new_lead_name', label: __("Neuer Lead"), fieldtype: 'Data',
                                    description: __("Nur ausfüllen, wenn kein bestehender Lead ausgewählt ist") },
                                { fieldname: 'cb', fieldtype: 'Column Break' },
                                { fieldname: 'date', label: __("Datum"), fieldtype: 'Date', reqd: 1,
                                    default: frappe.datetime.get_today() },
                                { fieldname: 'time', label: __("Zeit"), fieldtype: 'Time' },
                                                                { fieldname: 'duration', label: __("Dauer (Stunden)"), fieldtype: 'Float',
                                                                    default: 1, min: 0.25, precision: 2 },
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

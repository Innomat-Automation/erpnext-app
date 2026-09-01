frappe.pages['crm_calendar'].on_page_load = function(wrapper) {
    frappe.require([
        'assets/frappe/js/lib/fullcalendar/fullcalendar.min.css',
        'assets/frappe/js/lib/fullcalendar/fullcalendar.min.js',
        'assets/frappe/js/lib/fullcalendar/locale-all.js'
    ], function() {
        frappe.crm_calendar.make(wrapper);
    });
};

frappe.crm_calendar = {
    page: null,
    calendar: null,
    include_completed: false,
    user_field: null,

    make: function(wrapper) {
        var me = frappe.crm_calendar;
        me.page = frappe.ui.make_app_page({
            parent: wrapper,
            title: __("CRM Kalender"),
            single_column: true
        });

        me.user_field = me.page.add_field({
            fieldname: 'user',
            label: __("Benutzer"),
            fieldtype: 'Link',
            options: 'User',
            reqd: 1,
            default: frappe.session.user,
            change: function() {
                me.refresh();
            }
        });

        me.include_completed_field = me.page.add_field({
            fieldname: 'include_completed',
            label: __("Erledigte anzeigen"),
            fieldtype: 'Check',
            change: function() {
                me.include_completed = !!me.include_completed_field.get_value();
                me.refresh();
            }
        });
        me.page.set_primary_action(__("Aktualisieren"), function() { me.refresh(); }, 'refresh');
        me.body = $('<div class="crm-calendar"></div>').appendTo(me.page.main);
        me.body.html(me.legend_html() + '<div class="crm-calendar-container"></div>');
        me.calendar = me.body.find('.crm-calendar-container');

        me.calendar.fullCalendar({
            locale: 'de',
            defaultView: 'month',
            header: {
                left: 'prev,next today',
                center: 'title',
                right: 'month,agendaWeek,agendaDay'
            },
            buttonText: {
                today: __("Heute"),
                month: __("Monat"),
                week: __("Woche"),
                day: __("Tag")
            },
            height: 'auto',
            eventLimit: true,
            editable: true,
            eventStartEditable: true,
            eventDurationEditable: true,
            events: function(start, end, timezone, callback) {
                me.load_events(start, end, callback);
            },
            eventDrop: function(event, delta, revertFunc) {
                me.save_event_change(event, revertFunc);
            },
            eventResize: function(event, delta, revertFunc) {
                me.save_event_change(event, revertFunc);
            },
            eventClick: function(event) {
                frappe.set_route("Form", "Lead", event.lead);
            },
            eventRender: function(event, element) {
                element.attr('title', event.tooltip || event.title);
            }
        });
    },

    legend_html: function() {
        return '<div class="crm-calendar-toolbar">'
            + '<span class="crm-calendar-legend-item"><span class="crm-calendar-swatch crm-calendar-phone"></span>' + __("Telefon") + '</span>'
            + '<span class="crm-calendar-legend-item"><span class="crm-calendar-swatch crm-calendar-remote"></span>' + __("Remotebesprechung") + '</span>'
            + '<span class="crm-calendar-legend-item"><span class="crm-calendar-swatch crm-calendar-onsite"></span>' + __("Vor Ort Besprechung") + '</span>'
            + '</div>';
    },

    load_events: function(start, end, callback) {
        var me = frappe.crm_calendar;
        var selected_user = (me.user_field && me.user_field.get_value()) || frappe.session.user;
        frappe.call({
            method: 'innomat.innomat.page.crm_calendar.crm_calendar.get_events',
            args: {
                start: start.format('YYYY-MM-DD'),
                end: end.format('YYYY-MM-DD'),
                include_completed: me.include_completed ? 1 : 0,
                user: selected_user || ''
            },
            callback: function(r) {
                if (r.exc || !r.message) {
                    callback([]);
                    return;
                }
                callback(r.message.map(function(row) {
                    var title = row.lead_name || row.company_name || row.lead;
                    var start_value = row.date + (row.time ? 'T' + row.time : '');
                    var start = moment(start_value);
                    var duration = parseFloat(row.duration) || 1;
                    return {
                        id: row.name,
                        title: title,
                        start: start_value,
                        end: row.time ? start.clone().add(duration, 'hours') : null,
                        allDay: !row.time,
                        lead: row.lead,
                        duration_hours: duration,
                        tooltip: title + ' - ' + row.communication_type
                            + ' (' + duration + ' h)'
                            + (row.user ? '\n' + __("Benutzer") + ': ' + row.user : '')
                            + (row.preparation ? '\n' + __("Vorbereitung") + ': ' + row.preparation : ''),
                        color: me.color_for(row.communication_type),
                        textColor: '#ffffff'
                    };
                }));
            }
        });
    },

    save_event_change: function(event, revertFunc) {
        var me = frappe.crm_calendar;
        var duration = event.end ? event.end.diff(event.start, 'minutes') / 60 : event.duration_hours;
        duration = Math.max(duration || 1, 0.25);
        frappe.call({
            method: 'innomat.innomat.page.crm_calendar.crm_calendar.update_event',
            args: {
                name: event.id,
                values: {
                    date: event.start.format('YYYY-MM-DD'),
                    time: event.allDay ? null : event.start.format('HH:mm:ss'),
                    duration: duration
                }
            },
            freeze: true,
            callback: function(r) {
                if (r.exc) {
                    revertFunc();
                    return;
                }
                event.duration_hours = duration;
                frappe.show_alert({ message: __("Termin aktualisiert"), indicator: 'green' });
            }
        });
    },

    color_for: function(type) {
        return {
            "Telefon": '#5e6b75',
            "Remotebesprechung": '#2490ef',
            "Vor Ort Besprechung": '#c58b28'
        }[type] || '#8a969f';
    },

    refresh: function() {
        if (this.calendar) {
            this.calendar.fullCalendar('refetchEvents');
        }
    }
};

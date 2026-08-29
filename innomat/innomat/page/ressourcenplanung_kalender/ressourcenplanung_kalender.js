frappe.pages['ressourcenplanung_kalender'].on_page_load = function(wrapper) {
    frappe.require([
        'assets/frappe/js/lib/fullcalendar/fullcalendar.min.css',
        'assets/frappe/js/lib/fullcalendar/fullcalendar.min.js',
        'assets/frappe/js/lib/fullcalendar/locale-all.js'
    ], function() {
        frappe.ressourcenplanung_kalender.make(wrapper);
    });
};

frappe.ressourcenplanung_kalender = {
    page: null,
    calendar: null,
    user: null,

    make: function(wrapper) {
        var me = frappe.ressourcenplanung_kalender;
        me.page = frappe.ui.make_app_page({
            parent: wrapper,
            title: __("Ressourcenplanung Kalender"),
            single_column: true
        });

        me.user = frappe.session.user;
        me.user_field = me.page.add_field({
            fieldname: 'user',
            label: __("Benutzer"),
            fieldtype: 'Link',
            options: 'User',
            default: me.user,
            change: function() {
                var value = me.user_field.get_value();
                if (value && value !== me.user) {
                    me.user = value;
                    me.refresh_all();
                }
            }
        });
        me.page.set_primary_action(__("Aktualisieren"), function() { me.refresh_all(); }, 'refresh');

        me.body = $('<div class="rpk-layout"></div>').appendTo(me.page.main);
        me.body.html(
            '<div class="rpk-sidebar">'
                + '<div class="rpk-panel" data-panel="unscheduled">'
                    + '<div class="rpk-panel-title">' + __("Nicht terminierte Aufgaben") + '</div>'
                    + '<div class="rpk-panel-hint">' + __("Ihnen zugewiesene Aufgaben ohne Start-/Enddatum") + '</div>'
                    + '<div class="rpk-panel-list" data-list="unscheduled"></div>'
                + '</div>'
                + '<div class="rpk-panel" data-panel="pm">'
                    + '<div class="rpk-panel-title">' + __("Nicht zugewiesene Projektleiter-Aufgaben") + '</div>'
                    + '<div class="rpk-panel-hint">' + __("Aufgaben in Ihren Projekten ohne zugewiesenen Benutzer") + '</div>'
                    + '<div class="rpk-panel-list" data-list="pm"></div>'
                + '</div>'
                + '<div class="rpk-panel" data-panel="overdue">'
                    + '<div class="rpk-panel-title">' + __("Überfällige Aufgaben") + '</div>'
                    + '<div class="rpk-panel-hint">' + __("Zugewiesene Aufgaben mit abgelaufenem Enddatum") + '</div>'
                    + '<div class="rpk-panel-list" data-list="overdue"></div>'
                + '</div>'
            + '</div>'
            + '<div class="rpk-calendar-container"></div>'
        );
        me.calendar_container = me.body.find('.rpk-calendar-container');

        me.calendar_container.fullCalendar({
            locale: 'de',
            defaultView: 'month',
            header: {
                left: 'prev,next today',
                center: 'title',
                right: 'month'
            },
            buttonText: {
                today: __("Heute"),
                month: __("Monat")
            },
            height: 850,
            eventLimit: 3,
            editable: true,
            eventStartEditable: true,
            eventDurationEditable: true,
            eventOrder: false,
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
                me.open_task_dialog(event.id);
            },
            eventRender: function(event, element) {
                element.attr('title', event.tooltip || event.title);
            }
        });

        me.setup_dropzone();
        me.refresh_all();
    },

    refresh_all: function() {
        var me = this;
        me.user_field.set_value(me.user);
        me.refresh();
        me.load_panel('unscheduled', 'innomat.innomat.page.ressourcenplanung_kalender.ressourcenplanung_kalender.get_unscheduled_tasks');
        me.load_panel('pm', 'innomat.innomat.page.ressourcenplanung_kalender.ressourcenplanung_kalender.get_unassigned_pm_tasks');
        me.load_panel('overdue', 'innomat.innomat.page.ressourcenplanung_kalender.ressourcenplanung_kalender.get_overdue_tasks');
    },

    refresh: function() {
        if (this.calendar_container) {
            this.calendar_container.fullCalendar('refetchEvents');
        }
    },

    load_events: function(start, end, callback) {
        var me = frappe.ressourcenplanung_kalender;
        if (!me.user) {
            callback([]);
            return;
        }
        frappe.call({
            method: 'innomat.innomat.page.ressourcenplanung_kalender.ressourcenplanung_kalender.get_scheduled_tasks',
            args: {
                user: me.user,
                start: start.format('YYYY-MM-DD'),
                end: end.format('YYYY-MM-DD')
            },
            callback: function(r) {
                if (r.exc || !r.message) {
                    callback([]);
                    return;
                }
                var rows = r.message.slice().sort(function(a, b) {
                    if (a.project !== b.project) return (a.project || '') < (b.project || '') ? -1 : 1;
                    return (a.exp_start_date || '') < (b.exp_start_date || '') ? -1 : 1;
                });
                callback(rows.map(me.to_event));
            }
        });
    },

    to_event: function(row) {
        var me = frappe.ressourcenplanung_kalender;
        var title = row.subject + (row.project_name ? ' (' + row.project_name + ')' : '');
        var display_title = row.project ? '[' + row.project + '] ' + row.subject : row.subject;
        return {
            id: row.name,
            title: display_title,
            project: row.project || '',
            start: row.exp_start_date,
            end: moment(row.exp_end_date).add(1, 'days').format('YYYY-MM-DD'),
            allDay: true,
            tooltip: title + ' - ' + __(row.status),
            color: row.color || me.color_for_project(row.project),
            borderColor: me.color_for_status(row.status),
            textColor: '#ffffff'
        };
    },

    PROJECT_COLORS: ['#2490ef', '#36b37e', '#c58b28', '#8e44ad', '#e24c4c', '#5e6b75', '#0b8793', '#c0392b', '#2e86ab', '#7d5ba6'],

    color_for_project: function(project) {
        var me = this;
        if (!project) return '#8a969f';
        var hash = 0;
        for (var i = 0; i < project.length; i++) {
            hash = (hash * 31 + project.charCodeAt(i)) >>> 0;
        }
        return me.PROJECT_COLORS[hash % me.PROJECT_COLORS.length];
    },

    color_for_status: function(status) {
        return {
            "Open": '#2490ef',
            "Working": '#c58b28',
            "Overdue": '#e24c4c',
            "Pending Review": '#8e44ad'
        }[status] || '#8a969f';
    },

    save_event_change: function(event, revertFunc) {
        var me = frappe.ressourcenplanung_kalender;
        var start = event.start.format('YYYY-MM-DD');
        var end = event.end ? event.end.clone().subtract(1, 'days').format('YYYY-MM-DD') : start;
        frappe.call({
            method: 'innomat.innomat.page.ressourcenplanung_kalender.ressourcenplanung_kalender.schedule_task',
            args: {
                task: event.id,
                start_date: start,
                end_date: end
            },
            freeze: true,
            callback: function(r) {
                if (r.exc) {
                    revertFunc();
                    return;
                }
                frappe.show_alert({ message: __("Aufgabe aktualisiert"), indicator: 'green' });
            }
        });
    },

    open_task_dialog: function(task) {
        var me = this;
        frappe.call({
            method: 'innomat.innomat.page.ressourcenplanung_kalender.ressourcenplanung_kalender.get_task_details',
            args: { task: task },
            freeze: true,
            callback: function(r) {
                if (r.exc || !r.message) return;
                me.render_task_dialog(r.message);
            }
        });
    },

    render_task_dialog: function(task) {
        var me = this;
        var dialog = new frappe.ui.Dialog({
            title: (task.project ? '[' + task.project + '] ' : '') + task.subject,
            fields: [
                { fieldname: 'subject', fieldtype: 'Data', label: __("Betreff"), reqd: 1, default: task.subject },
                { fieldname: 'project_name', fieldtype: 'Data', label: __("Projekt"), default: task.project_name || task.project, read_only: 1 },
                { fieldname: 'col_break_1', fieldtype: 'Column Break' },
                { fieldname: 'status', fieldtype: 'Select', label: __("Status"), options: 'Open\nWorking\nPending Review\nOverdue\nCompleted\nCancelled', default: task.status },
                { fieldname: 'priority', fieldtype: 'Select', label: __("Priorität"), options: 'Low\nMedium\nHigh\nUrgent', default: task.priority },
                { fieldname: 'completed_by', fieldtype: 'Link', options: 'User', label: __("Zugewiesener Mitarbeiter"), default: task.completed_by },
                { fieldname: 'color', fieldtype: 'Color', label: __("Farbe"), default: task.color },
                { fieldname: 'sb_dates', fieldtype: 'Section Break' },
                { fieldname: 'exp_start_date', fieldtype: 'Date', label: __("Start"), default: task.exp_start_date },
                { fieldname: 'col_break_2', fieldtype: 'Column Break' },
                { fieldname: 'exp_end_date', fieldtype: 'Date', label: __("Ende"), default: task.exp_end_date },
                { fieldname: 'sb_desc', fieldtype: 'Section Break' },
                { fieldname: 'description', fieldtype: 'Text Editor', label: __("Beschreibung"), default: task.description }
            ],
            primary_action_label: __("Speichern"),
            primary_action: function(values) {
                frappe.call({
                    method: 'innomat.innomat.page.ressourcenplanung_kalender.ressourcenplanung_kalender.update_task',
                    args: { task: task.name, values: values },
                    freeze: true,
                    callback: function(r) {
                        if (r.exc) return;
                        frappe.show_alert({ message: __("Aufgabe gespeichert"), indicator: 'green' });
                        dialog.hide();
                        me.refresh_all();
                    }
                });
            }
        });
        // secondary_action would also fire whenever the dialog is dismissed (X, Escape, backdrop),
        // so "open in form" is added as an independent header button instead of using it.
        $('<button type="button" class="btn btn-default btn-sm">' + __("In Formular öffnen") + '</button>')
            .insertBefore(dialog.header.find('.btn-primary'))
            .on('click', function() {
                dialog.hide();
                frappe.set_route("Form", "Task", task.name);
            });
        dialog.show();
    },

    load_panel: function(panel_name, method) {
        var me = this;
        var list_el = me.body.find('.rpk-panel-list[data-list="' + panel_name + '"]');
        frappe.call({
            method: method,
            args: { user: me.user },
            callback: function(r) {
                list_el.empty();
                var rows = r.message || [];
                if (!rows.length) {
                    list_el.append('<div class="rpk-panel-empty">' + __("Keine Aufgaben") + '</div>');
                    return;
                }
                rows.forEach(function(row) {
                    var subtitle = row.project_name || row.project || '';
                    var card = $(
                        '<div class="rpk-task-card" draggable="true" data-task="' + frappe.utils.escape_html(row.name) + '">'
                            + '<div class="rpk-task-subject">' + frappe.utils.escape_html(row.subject) + '</div>'
                            + (subtitle ? '<div class="rpk-task-project">' + frappe.utils.escape_html(subtitle) + '</div>' : '')
                        + '</div>'
                    );
                    card.on('dragstart', function(e) {
                        var dt = e.originalEvent.dataTransfer;
                        dt.effectAllowed = 'move';
                        dt.setData('text/plain', JSON.stringify({
                            task: row.name,
                            panel: panel_name
                        }));
                    });
                    card.on('click', function() {
                        frappe.set_route("Form", "Task", row.name);
                    });
                    list_el.append(card);
                });
            }
        });
    },

    setup_dropzone: function() {
        var me = this;
        var el = me.calendar_container.get(0);

        el.addEventListener('dragover', function(e) {
            var cell = e.target.closest('td.fc-day');
            if (!cell) return;
            e.preventDefault();
            e.dataTransfer.dropEffect = 'move';
        });

        el.addEventListener('drop', function(e) {
            var cell = e.target.closest('td.fc-day');
            if (!cell) return;
            e.preventDefault();
            var date = cell.getAttribute('data-date');
            if (!date) return;
            var raw = e.dataTransfer.getData('text/plain');
            if (!raw) return;
            var payload;
            try {
                payload = JSON.parse(raw);
            } catch (err) {
                return;
            }
            me.drop_task(payload.task, payload.panel, date);
        });
    },

    drop_task: function(task, panel_name, date) {
        var me = this;
        frappe.call({
            method: 'innomat.innomat.page.ressourcenplanung_kalender.ressourcenplanung_kalender.schedule_task',
            args: {
                task: task,
                start_date: date,
                end_date: date,
                assign_user: panel_name === 'pm' ? me.user : null
            },
            freeze: true,
            callback: function(r) {
                if (r.exc) return;
                frappe.show_alert({ message: __("Aufgabe eingeplant"), indicator: 'green' });
                me.refresh_all();
            }
        });
    }
};

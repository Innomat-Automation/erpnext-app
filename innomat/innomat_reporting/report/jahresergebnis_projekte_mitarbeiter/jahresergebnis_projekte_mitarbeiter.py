# Copyright (c) 2026, Innomat and contributors
# For license information, please see license.txt

from __future__ import unicode_literals

from collections import defaultdict

import frappe
from frappe import _
from frappe.utils import flt, getdate


def execute(filters=None):
    filters = frappe._dict(filters or {})
    company, fiscal_year = filters.get('company'), filters.get('fiscal_year')
    if not company or not fiscal_year:
        frappe.throw(_("Unternehmen und Geschäftsjahr sind erforderlich"))
    if not frappe.has_permission('Project', 'read'):
        frappe.throw(_("Keine Leseberechtigung für Projekte"), frappe.PermissionError)

    dates = frappe.db.get_value('Fiscal Year', fiscal_year, ['year_start_date', 'year_end_date'])
    if not dates:
        frappe.throw(_("Geschäftsjahr nicht gefunden"))
    start, end = map(getdate, dates)
    if start > end:
        frappe.throw(_("Ungültiges Geschäftsjahr"))

    view = filters.get('view') or 'Finanzbuchhaltung'
    if not frappe.has_permission('GL Entry', 'read'):
        frappe.throw(_("Keine Leseberechtigung für Buchungen"), frappe.PermissionError)
    if view in ('Projekte', 'Mitarbeiter') and not frappe.has_permission('Salary Slip', 'read'):
        frappe.throw(_("Keine Leseberechtigung für Lohnabrechnungen"), frappe.PermissionError)
    if view == 'Finanzbuchhaltung':
        return financial_columns(), financial_data(company, start, end), financial_note()
    if view == 'Projekte':
        return project_columns(), project_data(company, start, end), project_note()
    if view == 'Mitarbeiter':
        return employee_columns(), employee_data(company, start, end), employee_note()
    frappe.throw(_("Ungültige Ansicht"))


def financial_columns():
    return [
        column('category', 'Kategorie', 'Data', 200),
        column('account', 'Konto', 'Link', 260, 'Account'),
        column('amount', 'Betrag', 'Currency', 160),
    ]


def project_columns():
    return [
        column('project', 'Projekt', 'Link', 135, 'Project'),
        column('project_name', 'Projektname', 'Data', 210),
        column('revenue', 'Umsatz', 'Currency', 130),
        column('material', 'Material (DN)', 'Currency', 130),
        column('services', 'Fremdleistungen (PI)', 'Currency', 150),
        column('expenses', 'Spesen', 'Currency', 110),
        column('hours', 'Projektstunden', 'Float', 120),
        column('labor', 'Ist-Lohnkosten', 'Currency', 150),
        column('labor_hourly_rate', 'Ist-Lohn / Projektstd.', 'Currency', 160),
        column('overhead', 'Übriger Aufwand (Umlage)', 'Currency', 190),
        column('overhead_hourly_rate', 'Umlage / Projektstd.', 'Currency', 170),
        column('profit', 'Deckungsbeitrag', 'Currency', 145),
    ]


def employee_columns():
    return [
        column('employee', 'Mitarbeiter', 'Link', 155, 'Employee'),
        column('employee_name', 'Name', 'Data', 170),
        column('hours', 'Stunden gesamt', 'Float', 115),
        column('project_hours', 'Projektstunden', 'Float', 115),
        column('salary', 'Bruttolohn (Abrechnung)', 'Currency', 175),
        column('hourly_rate', 'Ist-Lohn / Stunde', 'Currency', 135),
        column('overhead', 'Übriger Aufwand (Umlage)', 'Currency', 190),
        column('overhead_hourly_rate', 'Umlage / Projektstd.', 'Currency', 170),
        column('revenue', 'Zugeordneter Umsatz', 'Currency', 170),
        column('other_costs', 'Projekt-Sachkostenanteil', 'Currency', 180),
        column('contribution', 'Beitrag nach Kosten', 'Currency', 180),
    ]


def column(fieldname, label, fieldtype, width, options=None):
    result = {'fieldname': fieldname, 'label': _(label), 'fieldtype': fieldtype, 'width': width}
    if options:
        result['options'] = options
    return result


def financial_data(company, start, end):
    # All income and expenses, including unassigned postings. No artificial mapping
    # from cost centre to employee or project is attempted here.
    entries = frappe.db.sql("""
        SELECT a.name AS account, a.account_number, a.root_type,
               IFNULL(a.contribution_margin_classification, '') AS classification,
               SUM(gl.credit - gl.debit) AS income,
               SUM(gl.debit - gl.credit) AS expense
        FROM `tabGL Entry` gl
        INNER JOIN `tabAccount` a ON a.name = gl.account
        WHERE gl.company = %(company)s AND gl.posting_date BETWEEN %(start)s AND %(end)s
                    AND IFNULL(gl.is_opening, 'No') != 'Yes'
                    AND IFNULL(gl.voucher_type, '') != 'Period Closing Voucher'
          AND a.root_type IN ('Income', 'Expense')
        GROUP BY a.name, a.account_number, a.root_type, a.contribution_margin_classification
        ORDER BY a.root_type, a.name
    """, {'company': company, 'start': start, 'end': end}, as_dict=True)
    data = []
    totals = defaultdict(float)
    categories = defaultdict(float)
    for entry in entries:
        if entry.root_type == 'Income':
            category, amount = _('Ertrag'), flt(entry.income)
            totals['income'] += amount
        else:
            if (entry.account_number or '').startswith('5'):
                category = _('Personalaufwand (Kontoklasse 5)')
            else:
                category = {
                    'Direct Cost': _('Einzelkosten'),
                    'Overhead Cost': _('Gemeinkosten'),
                }.get(entry.classification, _('Übrige Kosten'))
            amount = flt(entry.expense)
            totals['expense'] += amount
        categories[category] += amount
        data.append({'category': category, 'account': entry.account, 'amount': amount})
    for category in (_('Ertrag'), _('Personalaufwand (Kontoklasse 5)'),
                     _('Gemeinkosten'), _('Einzelkosten'), _('Übrige Kosten')):
        data.append({'category': _('Summe {0}').format(category), 'amount': categories[category]})
    data.append({'category': _('Ertrag gesamt'), 'amount': totals['income']})
    data.append({'category': _('Aufwand gesamt'), 'amount': totals['expense']})
    data.append({'category': _('Ergebnis'), 'amount': totals['income'] - totals['expense']})
    return data


def invoice_revenue(company, start, end):
    return frappe.db.sql("""
        SELECT si.project, SUM(si.base_net_total) AS revenue
        FROM `tabSales Invoice` si
        WHERE si.company = %(company)s AND si.docstatus = 1
          AND si.posting_date BETWEEN %(start)s AND %(end)s
          AND IFNULL(si.is_opening, 'No') != 'Yes'
          AND IFNULL(si.project, '') != ''
        GROUP BY si.project
    """, {'company': company, 'start': start, 'end': end}, as_dict=True)


def time_costs(company, start, end):
        # The denominator includes internal/non-project work. Only the hours are used:
        # configured ILV rates and GK/VVGK percentages are not actual costs.
    return frappe.db.sql("""
                 SELECT ts.employee,
                     CASE WHEN p.name IS NOT NULL AND NOT EXISTS (
                         SELECT 1 FROM `tabCost Center` cc
                         WHERE cc.default_project = p.name AND cc.company = %(company)s
                     ) THEN p.name END AS project,
                             SUM(td.hours) AS hours
        FROM `tabTimesheet Detail` td
        INNER JOIN `tabTimesheet` ts ON ts.name = td.parent
                LEFT JOIN `tabProject` p ON p.name = td.project AND p.company = %(company)s
                WHERE ts.docstatus = 1 AND ts.company = %(company)s
                    AND IFNULL(ts.employee, '') != '' AND td.hours > 0
          AND td.from_time >= %(start)s AND td.from_time < DATE_ADD(%(end)s, INTERVAL 1 DAY)
                GROUP BY ts.employee, project
    """, {'company': company, 'start': start, 'end': end}, as_dict=True)


def project_costs(company, start, end):
    params = {'company': company, 'start': start, 'end': end}
    # DN expense-side postings reflect stock valuation (not sales value).
    material = frappe.db.sql("""
        SELECT dn.project, SUM(gl.debit - gl.credit) AS amount
        FROM `tabGL Entry` gl
        INNER JOIN `tabDelivery Note` dn ON dn.name = gl.voucher_no
        INNER JOIN `tabAccount` a ON a.name = gl.account AND a.root_type = 'Expense'
        WHERE gl.voucher_type = 'Delivery Note' AND dn.docstatus = 1
          AND dn.company = %(company)s AND IFNULL(dn.project, '') != ''
                    AND gl.company = %(company)s
          AND gl.posting_date BETWEEN %(start)s AND %(end)s
        GROUP BY dn.project
    """, params, as_dict=True)
    services = frappe.db.sql("""
        SELECT pi_item.project, SUM(pi_item.base_net_amount) AS amount
        FROM `tabPurchase Invoice Item` pi_item
        INNER JOIN `tabPurchase Invoice` pi ON pi.name = pi_item.parent
        INNER JOIN `tabItem` item ON item.name = pi_item.item_code
        WHERE pi.docstatus = 1 AND pi.company = %(company)s
          AND pi.posting_date BETWEEN %(start)s AND %(end)s
          AND IFNULL(pi_item.project, '') != '' AND item.is_stock_item = 0
        GROUP BY pi_item.project
    """, params, as_dict=True)
    expenses = frappe.db.sql("""
        SELECT detail.project, SUM(detail.amount * detail.qty) AS amount
        FROM `tabExpense Claim Detail` detail
        INNER JOIN `tabExpense Claim` claim ON claim.name = detail.parent
        WHERE claim.docstatus = 1 AND claim.company = %(company)s
          AND claim.posting_date BETWEEN %(start)s AND %(end)s
          AND IFNULL(detail.project, '') != ''
        GROUP BY detail.project
    """, params, as_dict=True)
    return material, services, expenses


def salary_costs(company, start, end):
    return {r.employee: flt(r.salary) for r in frappe.db.sql("""
        SELECT employee, SUM(gross_pay) AS salary
        FROM `tabSalary Slip`
        WHERE docstatus = 1 AND company = %(company)s
          AND posting_date BETWEEN %(start)s AND %(end)s
        GROUP BY employee
    """, {'company': company, 'start': start, 'end': end}, as_dict=True)}


def gl_totals(company, start, end):
    entries = frappe.db.sql("""
        SELECT a.root_type, SUM(gl.debit - gl.credit) AS amount
        FROM `tabGL Entry` gl
        INNER JOIN `tabAccount` a ON a.name = gl.account
        WHERE gl.company = %(company)s AND gl.posting_date BETWEEN %(start)s AND %(end)s
          AND IFNULL(gl.is_opening, 'No') != 'Yes'
          AND IFNULL(gl.voucher_type, '') != 'Period Closing Voucher'
          AND a.root_type IN ('Income', 'Expense')
        GROUP BY a.root_type
    """, {'company': company, 'start': start, 'end': end}, as_dict=True)
    totals = {r.root_type: flt(r.amount) for r in entries}
    return -totals.get('Income', 0), totals.get('Expense', 0)


def allocate_by_hours(amount, hours):
    """Split one company-wide expense pool across recorded project hours."""
    total = sum(flt(value) for value in hours.values())
    return {key: flt(amount) * flt(value) / total for key, value in hours.items()} if total else {}


def actual_cost_basis(company, start, end):
    """One consistent expense basis for both views; no ILV or GK percentage."""
    salaries = salary_costs(company, start, end)
    times = time_costs(company, start, end)
    employee_hours = defaultdict(float)
    project_hours = defaultdict(float)
    employee_project_hours = defaultdict(float)
    for entry in times:
        employee_hours[entry.employee] += flt(entry.hours)
        if entry.project:
            project_hours[entry.project] += flt(entry.hours)
            employee_project_hours[entry.employee] += flt(entry.hours)

    salary_rates = {employee: salary / employee_hours[employee]
                    for employee, salary in salaries.items() if employee_hours[employee]}
    # Employees with no submitted slips have no verifiable payroll rate: zero,
    # never a silently invented cost based on the configured internal rate.
    labor_by_project = defaultdict(float)
    for entry in times:
        if entry.project:
            labor_by_project[entry.project] += flt(entry.hours) * salary_rates.get(entry.employee, 0)

    direct = {key: defaultdict(float) for key in ('material', 'services', 'expenses')}
    for key, entries in zip(('material', 'services', 'expenses'), project_costs(company, start, end)):
        for entry in entries:
            direct[key][entry.project] += flt(entry.amount)
    revenues = {entry.project: flt(entry.revenue) for entry in invoice_revenue(company, start, end)}
    gl_revenue, gl_expense = gl_totals(company, start, end)
    direct_total = sum(sum(values.values()) for values in direct.values())
    payroll_total = sum(salaries.values())
    labor_total = sum(labor_by_project.values())
    # Costs not covered by individual gross salaries or identifiable project
    # material/services/expenses, including employer contributions and other
    # personnel costs, remain in this signed GL reconciliation pool.
    remaining_expense = gl_expense - payroll_total - direct_total
    return {
        'salaries': salaries, 'salary_rates': salary_rates, 'times': times,
        'employee_hours': employee_hours, 'employee_project_hours': employee_project_hours,
        'project_hours': project_hours, 'labor_by_project': labor_by_project,
        'direct': direct, 'revenues': revenues,
        'gl_revenue': gl_revenue, 'gl_expense': gl_expense,
        'remaining_expense': remaining_expense,
        # Salary for internal/non-project time is an indirect project cost.
        'project_pool': remaining_expense + payroll_total - labor_total,
    }


def project_data(company, start, end):
    basis = actual_cost_basis(company, start, end)
    projects = set(basis['revenues']) | set(basis['project_hours'])
    for values in basis['direct'].values():
        projects.update(values)
    names = frappe.get_all('Project', filters={'name': ('in', list(projects)), 'company': company},
                           fields=['name', 'project_name']) if projects else []
    titles = {p.name: p.project_name for p in names}
    overhead = allocate_by_hours(basis['project_pool'], basis['project_hours'])
    data = []
    for project in sorted(projects):
        if project not in titles:
            continue
        entry = {'project': project, 'project_name': titles[project],
                 'revenue': basis['revenues'].get(project, 0),
                 'hours': basis['project_hours'].get(project, 0),
                 'labor': basis['labor_by_project'].get(project, 0),
                 'overhead': overhead.get(project, 0)}
        for key, values in basis['direct'].items():
            entry[key] = values.get(project, 0)
        if entry['hours']:
            entry['labor_hourly_rate'] = entry['labor'] / entry['hours']
            entry['overhead_hourly_rate'] = entry['overhead'] / entry['hours']
        entry['profit'] = entry['revenue'] - sum(entry[k] for k in
            ('material', 'services', 'expenses', 'labor', 'overhead'))
        data.append(entry)

    # A reconciliation line also exposes revenue not assigned on invoices and
    # expense not distributable when there are no project hours in the year.
    unmatched = {'project_name': _('Nicht zugeordnet / Abweichung zur Finanzbuchhaltung'),
                 'revenue': basis['gl_revenue'] - sum(r['revenue'] for r in data),
                 'hours': 0, 'labor': 0,
                 'overhead': basis['gl_expense'] - sum(sum(r[k] for k in
                     ('material', 'services', 'expenses', 'labor', 'overhead')) for r in data),
                 'material': 0, 'services': 0, 'expenses': 0}
    unmatched['profit'] = unmatched['revenue'] - unmatched['overhead']
    if unmatched['revenue'] or unmatched['overhead']:
        data.append(unmatched)
    return data


def allocate_revenue(amounts, times):
    """Split project amounts over employees by submitted project hours."""
    hours = defaultdict(float)
    for entry in times:
        if entry.project:
            hours[entry.project] += flt(entry.hours)
    allocated = defaultdict(float)
    for entry in times:
        if entry.project and hours[entry.project]:
            allocated[entry.employee] += (flt(amounts.get(entry.project)) *
                                          flt(entry.hours) / hours[entry.project])
    return allocated


def employee_data(company, start, end):
    basis = actual_cost_basis(company, start, end)
    times = basis['times']
    allocated = allocate_revenue(basis['revenues'], times)
    other_costs = defaultdict(float)
    for values in basis['direct'].values():
        for project, amount in values.items():
            other_costs[project] += amount
    allocated_costs = allocate_revenue(other_costs, times)
    allocated_overhead = allocate_by_hours(basis['remaining_expense'],
                                            basis['employee_project_hours'])
    employees = {}
    def row(employee):
        return employees.setdefault(employee, {'employee': employee, 'hours': 0,
                                               'project_hours': 0, 'salary': 0,
                                               'hourly_rate': 0, 'overhead': 0,
                                               'revenue': 0, 'other_costs': 0})

    for employee, amount in basis['salaries'].items():
        person = row(employee)
        person['salary'] = amount
        person['hourly_rate'] = basis['salary_rates'].get(employee, 0)
    for entry in times:
        person = row(entry.employee)
        person['hours'] += flt(entry.hours)
        if entry.project:
            person['project_hours'] += flt(entry.hours)
    for employee, amount in allocated_overhead.items():
        row(employee)['overhead'] = amount
    for employee, revenue in allocated.items():
        row(employee)['revenue'] = revenue
    for employee, amount in allocated_costs.items():
        row(employee)['other_costs'] = amount

    names = frappe.get_all('Employee', filters={'name': ('in', list(employees))},
                           fields=['name', 'employee_name']) if employees else []
    labels = {e.name: e.employee_name for e in names}
    data = []
    for employee in sorted(employees):
        if employee not in labels:
            continue
        person = employees[employee]
        person['employee_name'] = labels[employee]
        if person['project_hours']:
            person['overhead_hourly_rate'] = person['overhead'] / person['project_hours']
        person['contribution'] = (person['revenue'] - person['other_costs'] -
                                  person['salary'] - person['overhead'])
        data.append(person)
    unmatched = {'employee_name': _('Nicht zugeordnet / Abweichung zur Finanzbuchhaltung'),
                 'revenue': basis['gl_revenue'] - sum(p['revenue'] for p in data),
                 'other_costs': 0, 'salary': 0, 'hours': 0, 'project_hours': 0,
                 'hourly_rate': 0,
                 'overhead': basis['gl_expense'] - sum(sum(p[k] for k in
                     ('salary', 'other_costs', 'overhead')) for p in data)}
    unmatched['contribution'] = unmatched['revenue'] - unmatched['overhead']
    if unmatched['revenue'] or unmatched['overhead']:
        data.append(unmatched)
    return data


def financial_note():
    return _("Gebuchte Netto-Erträge und Aufwendungen gemäss Hauptbuch (inklusive nicht zugeordneter Buchungen). "
             "Personalaufwand umfasst Aufwandkonten mit Kontonummer 5* (inkl. Sozialaufwand); Gemeinkosten "
             "basieren auf der Kontoklassifikation 'Overhead Cost'. Fehlende Klassifikation erscheint unter "
             "'Übrige Kosten'. Konten ohne 5*-Nummer werden nicht automatisch als Lohnkonten erkannt.")


def project_note():
    return _("Ist-Lohn/Stunde = Bruttolohn eingereichter Lohnabrechnungen im Geschäftsjahr / alle erfassten "
             "Stunden des Mitarbeiters (auch interne Stunden). Projektlohn = Projektstunden × Ist-Lohn/Stunde. "
             "Übriger Aufwand = GL-Gesamtaufwand minus Bruttolöhne und direkt erfasste Projekt-Sachkosten, "
             "zuzüglich Lohnkosten für interne/nicht projektbezogene Stunden; Umlage proportional zu allen "
             "Projektstunden. Enthält auch Arbeitgeberkosten und buchhalterische Abweichungen (ggf. negativer Saldo). "
             "Direkte Sachkosten: Lieferschein-Aufwand, nicht lagergeführte Einkaufspositionen und Spesen. "
             "Nicht zuordenbare Beträge und die Abweichung zum gebuchten Ertrag stehen separat. "
             "Ohne Lohnabrechnung bzw. erfasste Stunden ist kein individueller Ist-Stundensatz bestimmbar.")


def employee_note():
    return _("Ist-Lohn/Stunde = gebuchter Bruttolohn aus eingereichten Lohnabrechnungen / alle erfassten "
             "Stunden des Mitarbeiters. Übriger Aufwand = GL-Gesamtaufwand minus Bruttolöhne und direkt "
             "zuordenbare Sachkosten (inkl. Arbeitgeberkosten und Differenzen), auf Mitarbeiter nach deren "
             "Projektstunden verteilt. Umsatz und direkte Sachkosten werden pro Projekt nach Stunden verteilt. "
             "Der Beitrag zieht den vollen Mitarbeiter-Bruttolohn ab, auch für interne Stunden. "
             "Nicht zuordenbare Beträge werden separat gezeigt. Eine negative Umlage zeigt eine "
             "Abweichung zwischen Belegen und Hauptbuch, keine negativen Gemeinkosten im engeren Sinn.")
# Copyright (c) 2026, Innomat, Asprotec and libracore and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.utils import flt
from erpnext.accounts.report.financial_statements import get_accounts, filter_accounts, get_appropriate_currency, get_additional_conditions, calculate_values, accumulate_values_into_parents, prepare_data, filter_out_zero_value_rows, add_total_row
from erpnext.accounts.utils import get_fiscal_year
from datetime import datetime
from frappe.utils import (flt, getdate, get_first_day, add_months, add_days, formatdate)

def execute(filters=None):
    filters = frappe._dict(filters or {})
    from_date = datetime.strptime(filters.month_from+' '+filters.fiscal_year, '%b %Y').date()
    to_date = datetime.strptime(filters.month_to+' '+filters.fiscal_year, '%b %Y').date()
    to_date = add_months(to_date, 1)
    to_date = add_days(to_date, -1) # Last day of selected month
    to_date_fy = get_fiscal_year(to_date, company=filters.company)[0]
    from_date_fy_start = get_fiscal_year(from_date, company=filters.company)[1]
    period_list = [frappe._dict({
        'from_date': from_date,
        'to_date': to_date,
        'to_date_fiscal_year': to_date_fy,
        'from_date_fiscal_year_start_date': from_date_fy_start,
        'key': 'myperiod',
        'label': filters.month_from+'-'+filters.month_to+from_date.strftime(' %y'),
        'year_start_date': datetime(int(filters.fiscal_year), 1, 1).date(),
        'year_end_date': datetime(int(filters.fiscal_year), 12, 31).date()
    })]

    cost_center_list = frappe.get_list("Cost Center", {'company':filters.company}, order_by='ISNULL(parent_cost_center), name')
    cost_center_list = [cc.name for cc in cost_center_list]
    op_income_merged = []
    direct_cost_merged = []
    overhead_cost_merged = []
    remaining_cost_merged = []

    for cc in cost_center_list:

        period_list[0].key = cc

        op_income_filters = frappe._dict({'company': filters.company, 'cost_center': cc, 'account_number': '3%'})
        op_income = get_data(filters.company, "Income", "Credit", period_list, filters=op_income_filters,
            accumulated_values=False, ignore_closing_entries=True, ignore_accumulated_values_for_fy= True)
        merge_data(op_income_merged, op_income, cc)

        direct_cost_filters = frappe._dict({'company': filters.company, 'cost_center': cc, 'contribution_margin_classification': 'Direct Cost'})
        direct_cost = get_data(filters.company, "Expense", "Debit", period_list, filters=direct_cost_filters,
            accumulated_values=False, ignore_closing_entries=True, ignore_accumulated_values_for_fy= True)
        merge_data(direct_cost_merged, direct_cost, cc)

        overhead_cost_filters = frappe._dict({'company': filters.company, 'cost_center': cc, 'contribution_margin_classification': 'Overhead Cost'})
        overhead_cost = get_data(filters.company, "Expense", "Debit", period_list, filters=overhead_cost_filters,
            accumulated_values=False, ignore_closing_entries=True, ignore_accumulated_values_for_fy= True)
        merge_data(overhead_cost_merged, overhead_cost, cc)

        remaining_cost_filters = frappe._dict({'company': filters.company, 'cost_center': cc, 'contribution_margin_classification': 'Other', 'expense_account_classification': 'Other'})
        remaining_cost = get_data(filters.company, "Expense", "Debit", period_list, filters=remaining_cost_filters,
            accumulated_values=False, ignore_closing_entries=True, ignore_accumulated_values_for_fy= True)
        merge_data(remaining_cost_merged, remaining_cost, cc)

    # `budget_01`+`budget_02`+...
    budget_months = "+".join(["`budget_%02d`" % x for x in range(from_date.month,to_date.month+1)])
    for cc in cost_center_list:
        budget_filters = {
            "name_prefix": filters.budget_prefix,
            "cost_center": cc,
            "company": filters.company,
            "fiscal_year": filters.fiscal_year
        }
        budget_name = frappe.db.exists("Innomat Budget", budget_filters)
        if not budget_name:
            continue

        op_income_budget = get_budget_data(budget_name, budget_months, cc, "Income", "`account_number` LIKE '3%'")
        merge_data(op_income_merged, op_income_budget, cc+' - BU')
        direct_cost_budget = get_budget_data(budget_name, budget_months, cc, "Expense", "`contribution_margin_classification` = 'Direct Cost'")
        merge_data(direct_cost_merged, direct_cost_budget, cc+' - BU')
        overhead_cost_budget = get_budget_data(budget_name, budget_months, cc, "Expense", "`contribution_margin_classification` = 'Overhead Cost'")
        merge_data(overhead_cost_merged, overhead_cost_budget, cc+' - BU')
        remaining_cost_budget = get_budget_data(budget_name, budget_months, cc, "Expense", "`contribution_margin_classification` = 'Other'")
        merge_data(remaining_cost_merged, remaining_cost_budget, cc+' - BU')

    data = [{'account': "'<b>"+_('Betriebsertrag')+"</b>'"}]
    op_income_merged[-1]['account'] = "'"+_('Total Betriebsertrag')+"'"
    data.extend(op_income_merged or [])
    data.extend([{},{'account': "'<b>"+_('Einzelkosten')+"</b>'"}])
    direct_cost_merged[-1]['account'] = "'"+_('Total Einzelkosten')+"'"
    data.extend(direct_cost_merged or [])
    data.extend([{}])
    db1 = get_difference_row("<b>"+_("DB1")+"</b>", op_income_merged, direct_cost_merged, cost_center_list, filters.company)
    data.extend(db1)
    data.extend([{},{'account': "'<b>"+_('Gemeinkosten')+"</b>'"}])
    overhead_cost_merged[-1]['account'] = "'"+_('Total Gemeinkosten')+"'"
    data.extend(overhead_cost_merged or [])
    data.extend([{}])
    db2 = get_difference_row("<b>"+_("DB2")+"</b>", db1, overhead_cost_merged, cost_center_list, filters.company)
    data.extend(db2)
    data.extend([{},{'account': "'<b>"+_('Übrige Kosten')+"</b>'"}])
    remaining_cost_merged[-1]['account'] = "'"+_('Total Übrige Kosten')+"'"
    data.extend(remaining_cost_merged or [])
    data.extend([{}])
    db3 = get_difference_row("<b>"+_("DB3 (EBIT)")+"</b>", db2, remaining_cost_merged, cost_center_list, filters.company)
    data.extend(db3)
    columns = get_columns(cost_center_list)

    return columns, data


def get_difference_row(title, income, expense, cost_center_list, company):
    difference_row = {
        "account_name": "'" + title + "'",
        "account": "'" + title + "'",
        "warn_if_negative": True,
        "currency": frappe.get_cached_value('Company',  company,  "default_currency")
    }

    has_value = False

    for cc in cost_center_list:
        total_income = flt(income[-1].get(cc), 3) if income else 0
        total_expense = flt(expense[-1].get(cc), 3) if expense else 0
        total_income_BU = flt(income[-1].get(cc+' - BU'), 3) if income else 0
        total_expense_BU = flt(expense[-1].get(cc+' - BU'), 3) if expense else 0

        difference_row[cc] = total_income - total_expense
        difference_row[cc+' - BU'] = total_income_BU - total_expense_BU

        if difference_row[cc] or difference_row[cc+' - BU']:
            has_value=True

    if has_value:
        return [difference_row]
    else:
        return []


def get_columns(cost_center_list):
    columns = [
        {
            "fieldname": "account",
            "label": _("Account"),
            "fieldtype": "Link",
            "options": "Account",
            "width": 300,
        },
        {
            "fieldname": "currency",
            "label": _("Currency"),
            "fieldtype": "Link",
            "options": "Currency"
        },
    ]
    for cc in cost_center_list:
        stripped_cc = cc[0:cc.find(' - ')]
        columns.append({
            "fieldname": cc,
            "label": stripped_cc+' - IST',
            "fieldtype": "Currency",
            "options": "currency",
            "width": 150
        })
        columns.append({
            "fieldname": cc+' - BU',
            "label": stripped_cc+' - BU',
            "fieldtype": "Currency",
            "options": "currency",
            "width": 150
        })

    # add blank column to make space for scrollbar
    columns.append({
                "fieldname": "scrollbar",
                "label": _(""),
                "fieldtype": "Data",
                "width": 20
            })
    return columns


# Merge two lists of dicts containing account information.
def merge_data(existing_data, more_data, key):
    search_pos = 0
    for new_item in more_data:
        if not 'account' in new_item:
            continue
        found_at = search_account_in_data(new_item['account'], existing_data, search_pos)
        if found_at != None:
            existing_data[found_at][key] = new_item[key]
            search_pos = found_at + 1
        else:
            tree_path = get_account_tree_path(new_item['account'])
            found_idx = -1
            found_pos = None
            # Go up the path, i.e. start at the end, and stop whenever a parent node is found
            for t in range(len(tree_path)-1, -1, -1):
                found_pos = search_account_in_data(tree_path[t], existing_data)
                if found_pos != None:
                    found_idx = t
                    break
            # Now go downward and insert all the missing nodes
            # (Note - this also works if no parent was found, in that case we start at t=0)
            pos = found_pos
            for t in range(found_idx + 1, len(tree_path)):
                pos = insert_account_into_data(tree_path[t], existing_data, pos)
            pos = insert_account_into_data(new_item['account'], existing_data, pos)
            existing_data[pos][key] = new_item[key]
            search_pos = pos + 1
    update_sums(existing_data, key)


# Update sums by going upward through the tree
def update_sums(data, key):
    prev_indent = 0
    sum = [0, 0, 0, 0, 0]
    for i in range(len(data)-1, -1, -1):
        if data[i]['account'].startswith("'Total"):
            continue
        indent = data[i]['indent']
        if indent == prev_indent:
            sum[indent] += data[i].get(key, 0)
        elif indent > prev_indent:
            sum[indent] = data[i].get(key, 0)
        else: # indent < prev_indent
            data[i][key] = sum[prev_indent] or ''
            sum[indent] += sum[prev_indent]
            sum[prev_indent] = 0
        prev_indent = indent
    if len(data)>0 and data[-1]['account'].startswith("'Total"):
        data[-1][key] = sum[0]
    else:
        data.append({'account': "'Total'", 'indent': 0, key: sum[0]})


# Returns a list of accounts, starting at the root of the account tree and ending at the given account's parent
def get_account_tree_path(account):
    path = []
    if not frappe.db.exists("Account", account):
        return path
    acc_doc = frappe.get_doc("Account", account)
    company = acc_doc.company
    while True:
        if acc_doc.parent_account == company or acc_doc.parent_account == None:
            break
        path.insert(0, acc_doc.parent_account)
        acc_doc = frappe.get_doc("Account", acc_doc.parent_account)
    return path


# Returns the position of the given account in the data, or None if not found.
# The search is started at the given position to speed things up (usually the data is in order)
def search_account_in_data(account, data, start_at=0):
    if len(data) == 0:
        return None
    start_at = min(start_at, len(data)-1)
    pos = start_at
    while True:
        if data[pos]['account'] == account:
            return pos
        pos += 1
        if pos >= len(data):
            pos = 0
        if pos == start_at:
            return None


def insert_account_into_data(account, data, parent_pos = None):
    if account.startswith("'Total"):
        return 0 # Do not merge total rows as they are managed by update_sums()
    comp_account = account.replace("'","")
    if parent_pos != None:
        parent = data[parent_pos]['account']
        my_indent = data[parent_pos]['indent'] + 1
        pos = parent_pos + 1
        # Remove single quotes when comparing names because 'Total Expense' and 'Total Credit' rows are quoted, and need to be without quotes to stay at the bottom ("'Total" < "1234" but "Total" > "1234")
        while pos < len(data) and (data[pos]['indent'] > my_indent or (data[pos]['indent'] == my_indent and comp_account > data[pos]['account'].replace("'",""))):
            pos += 1
        data.insert(pos, {'account': account, 'parent_account': parent, 'indent': my_indent})
    else:
        pos = 0
        while pos < len(data) and comp_account > data[pos]['account'].replace("'",""):
            pos += 1
        data.insert(pos, {'account': account, 'parent_account': None, 'indent': 0})
    return pos


def get_budget_data(budget_name, budget_months, cost_center, root_type, other_cond='1'):
    budget_column = cost_center+' - BU'
    budget_data = frappe.db.sql("""
    SELECT
      `tabInnomat Budget Account`.`account`,
      ({budget_months}) AS `{budget_column}`,
      `tabAccount`.`parent_account`
    FROM `tabInnomat Budget Account`
    LEFT JOIN `tabAccount` ON `tabInnomat Budget Account`.`account` = `tabAccount`.`name`
    WHERE `tabInnomat Budget Account`.`parent` = '{budget_name}' AND `tabInnomat Budget Account`.`root_type`= '{root_type}'
    AND {other_cond}
    ORDER BY `account`
    """.format(budget_months=budget_months, budget_column=budget_column, budget_name=budget_name, root_type=root_type, other_cond=other_cond), as_dict=True)
    return budget_data


# Identical copy of erpnext.accounts.report.financial_statements.get_data.
# Only difference: Since it has a different context, it uses the customized variant of set_gl_entries_by_account() as below.
# All other "dependencies" are imported from financial_statements.
def get_data(
        company, root_type, balance_must_be, period_list, filters=None,
        accumulated_values=1, only_current_fiscal_year=True, ignore_closing_entries=False,
        ignore_accumulated_values_for_fy=False , total = True):

    accounts = get_accounts(company, root_type)
    if not accounts:
        return None

    accounts, accounts_by_name, parent_children_map = filter_accounts(accounts)

    company_currency = get_appropriate_currency(company, filters)

    gl_entries_by_account = {}
    for root in frappe.db.sql("""select lft, rgt from tabAccount
            where root_type=%s and ifnull(parent_account, '') = ''""", root_type, as_dict=1):

        set_gl_entries_by_account(
            company,
            period_list[0]["year_start_date"] if only_current_fiscal_year else None,
            period_list[-1]["to_date"],
            root.lft, root.rgt, filters,
            gl_entries_by_account, ignore_closing_entries=ignore_closing_entries
        )

    calculate_values(
        accounts_by_name, gl_entries_by_account, period_list, accumulated_values, ignore_accumulated_values_for_fy)
    accumulate_values_into_parents(accounts, accounts_by_name, period_list, accumulated_values)
    out = prepare_data(accounts, balance_must_be, period_list, company_currency)
    out = filter_out_zero_value_rows(out, parent_children_map)

    if out and total:
        add_total_row(out, root_type, balance_must_be, period_list, company_currency)

    return out


# Modified version of erpnext.accounts.report.financial_statements.set_gl_entries_by_account
# Will accept filters by attributes from tabAccount: account_number, contribution_margin_classification, expense_account_classification
def set_gl_entries_by_account(
        company, from_date, to_date, root_lft, root_rgt, filters, gl_entries_by_account, ignore_closing_entries=False):
    """Returns a dict like { "account": [gl entries], ... }"""

    additional_conditions = get_additional_conditions(from_date, ignore_closing_entries, filters)

    accounts = frappe.db.sql_list("""select name from `tabAccount`
        where lft >= %s and rgt <= %s""", (root_lft, root_rgt))
    additional_conditions += " and account in ({})"\
        .format(", ".join([frappe.db.escape(d) for d in accounts]))
    if filters.get("account_number"):
        additional_conditions += " and account_number LIKE %(account_number)s"
    if filters.get("contribution_margin_classification"):
        additional_conditions += " and contribution_margin_classification = %(contribution_margin_classification)s"
    if filters.get("expense_account_classification"):
        additional_conditions += " and expense_account_classification = %(expense_account_classification)s"


    gl_filters = {
        "company": company,
        "from_date": from_date,
        "to_date": to_date,
        "finance_book": filters.get("finance_book")
    }

    if filters.get("include_default_book_entries"):
        gl_filters["company_fb"] = frappe.db.get_value("Company",
            company, 'default_finance_book')

    for key, value in filters.items():
        if value:
            gl_filters.update({
                key: value
            })

    sql_q = """select posting_date, account, debit, credit, is_opening, fiscal_year, debit_in_account_currency, credit_in_account_currency, `tabGL Entry`.`account_currency` from `tabGL Entry`
        inner join `tabAccount` on `tabGL Entry`.`account` = `tabAccount`.`name`
        where `tabGL Entry`.`company`=%(company)s
        {additional_conditions}
        and posting_date <= %(to_date)s
        order by account, posting_date""".format(additional_conditions=additional_conditions)
    print(sql_q)
    gl_entries = frappe.db.sql(sql_q, gl_filters, as_dict=True) #nosec

    if filters and filters.get('presentation_currency'):
        convert_to_presentation_currency(gl_entries, get_currency(filters))

    for entry in gl_entries:
        gl_entries_by_account.setdefault(entry.account, []).append(entry)

    return gl_entries_by_account
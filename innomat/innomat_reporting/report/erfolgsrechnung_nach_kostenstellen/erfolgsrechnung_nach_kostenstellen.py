# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.utils import flt
from erpnext.accounts.report.financial_statements import get_data
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

    cost_center_list = frappe.get_list("Cost Center", {'company':'Innomat-Automation AG'}, order_by='ISNULL(parent_cost_center), name')
    cost_center_list = [cc.name for cc in cost_center_list]
    income_merged = []
    expense_merged = []

    for cc in cost_center_list:

        data_filters = frappe._dict({'company': filters.company, 'cost_center': cc})
        period_list[0].key = cc

        income = get_data(filters.company, "Income", "Credit", period_list, filters=data_filters,
            accumulated_values=False, ignore_closing_entries=True, ignore_accumulated_values_for_fy= True)

        expense = get_data(filters.company, "Expense", "Debit", period_list, filters=data_filters,
            accumulated_values=False, ignore_closing_entries=True, ignore_accumulated_values_for_fy= True)

        merge_data(income_merged, income, cc)
        merge_data(expense_merged, expense, cc)

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

        income_budget = get_budget_data(budget_name, budget_months, cc, "Income")
        expense_budget = get_budget_data(budget_name, budget_months, cc, "Expense")
        merge_data(income_merged, income_budget, cc+' - BU')
        merge_data(expense_merged, expense_budget, cc+' - BU')

    data = []
    data.extend(income_merged or [])
    data.extend([{}])
    data.extend(expense_merged or [])
    data.extend([{}])

    net_profit_loss = get_net_profit_loss(income_merged, expense_merged, cost_center_list, filters.company)
    data.extend(net_profit_loss)
    columns = get_columns(cost_center_list)

    return columns, data


def get_net_profit_loss(income, expense, cost_center_list, company):
    net_profit_loss = {
        "account_name": "'" + _("Profit for the year") + "'",
        "account": "'" + _("Profit for the year") + "'",
        "warn_if_negative": True,
        "currency": frappe.get_cached_value('Company',  company,  "default_currency")
    }

    has_value = False

    for cc in cost_center_list:
        total_income = flt(income[-1].get(cc), 3) if income else 0
        total_expense = flt(expense[-1].get(cc), 3) if expense else 0
        total_income_BU = flt(income[-1].get(cc+' - BU'), 3) if income else 0
        total_expense_BU = flt(expense[-1].get(cc+' - BU'), 3) if expense else 0

        net_profit_loss[cc] = total_income - total_expense
        net_profit_loss[cc+' - BU'] = total_income_BU - total_expense_BU

        if net_profit_loss[cc] or net_profit_loss[cc+' - BU']:
            has_value=True

    if has_value:
        return [net_profit_loss]
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
# TODO Aktuell werden übergeordnete Konten von Budgetkonten nicht dargestellt und deren Budgets nicht aufsummiert!
#      Am besten analog Budget-Druckformat vorgehen - der Reihe nach gemäss Kontenplan - und die Summen so bilden.
#      Vermutlich ein "Pfad"-Dict führen, wo alle Parents aufgeführt sind, um deren Totale vorzu zu updaten.
# - fehlende "parent" Konten
def merge_data(existing_data, more_data, key):
    cnt = 0
    mcnt = 0
    while True:
        if mcnt == len(more_data):
            break
        if more_data[mcnt] == {}:
            mcnt += 1
            continue
        if cnt < len(existing_data):
            if existing_data[cnt] == {}:
                cnt += 1
                continue
            if existing_data[cnt]['account'] == more_data[mcnt]['account']:
                # Account matches
                existing_data[cnt][key] = more_data[mcnt][key]
                mcnt += 1
            elif (existing_data[cnt]['account'].replace("'","") > more_data[mcnt]['account'].replace("'","")):
                # Account is missing from existing_data and should be inserted here
                # NOTE: We assume that account numbers are in order, which usually works, because eg. '4' > '300' in Python.
                #       We remove single quotes because 'Total Expense' and 'Total Credit' rows are quoted, and need to be without quotes to end up in the right spot ("'Total" < "1234" but "Total" > "1234")

                if more_data[mcnt].get("indent") == None:
                    # Account data without 'indent', coming from budget: We need to figure out the correct indentation
                    for i in range(cnt,0,-1):
                        if existing_data[i]['account'] == more_data[mcnt]['parent_account'] and existing_data[i].get('indent') != None:
                            more_data[mcnt]['indent'] = existing_data[i]['indent'] + 1
                            break
                existing_data.insert(cnt, more_data[mcnt])
                mcnt += 1
            cnt += 1
        else:
            existing_data.append(more_data[mcnt])
            mcnt += 1


def get_budget_data(budget_name, budget_months, cost_center, root_type):
    budget_column = cost_center+' - BU'
    budget_data = frappe.db.sql("""
    SELECT
      `tabInnomat Budget Account`.`account`,
      ({budget_months}) AS `{budget_column}`,
      `tabAccount`.`parent_account`
    FROM `tabInnomat Budget Account`
    LEFT JOIN `tabAccount` ON `tabInnomat Budget Account`.`account` = `tabAccount`.`name`
    WHERE `tabInnomat Budget Account`.`parent` = '{budget_name}' AND `tabInnomat Budget Account`.`root_type`= '{root_type}'
    ORDER BY `account`
    """.format(budget_months=budget_months, budget_column=budget_column, budget_name=budget_name, root_type=root_type), as_dict=True)
    return budget_data

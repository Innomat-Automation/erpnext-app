# Copyright (c) 2013, Innomat, Asprotec and libracore and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
import ast          # to parse str to dict (from JS calls)
from datetime import date
from erpnext.accounts.report.financial_statements import (get_period_list, get_data)
from erpnext.accounts.utils import get_balance_on

def execute(filters=None):
    columns = get_columns()
    data = get_internal_data(filters)
    return columns, data

def get_columns():
    return [
        {"label": _("Description"), "fieldname": "description", "fieldtype": "Data", "width": 150},
        {"label": _("YTD [CHF]"), "fieldname": "ytd", "fieldtype": "Currency", "width": 120},
        {"label": _("PY [CHF]"), "fieldname": "py", "fieldtype": "Currency", "width": 120},
        {"label": _(""), "fieldname": "blank", "fieldtype": "Data", "width": 20}
    ]

@frappe.whitelist()
def get_internal_data(filters):
    # # conditions = ""
    # if type(filters) is str:
    #     filters = ast.literal_eval(filters)
    # else:
    #     filters = dict(filters)
    
    year = int(filters.date[:4])
    date = filters['date']
    previous_year = year - 1
    previous_date = "{0}{1}".format(previous_year, filters['date'][5:])
    
    data = []

    data.append({
        'description': _("Income"),
        'ytd': None,
        'py': None
    })
    
    period_list = get_period_list(year, year, "Yearly", False, filters.company)

    ytd_revenue = get_data(filters.company, "Income", "Credit", period_list, filters = filters,
		accumulated_values=False,
		ignore_closing_entries=True, ignore_accumulated_values_for_fy= True)

    py_period_list = get_period_list(previous_year, previous_year,
		"Yearly", False, filters.company)

    py_revenue = get_data(filters.company, "Income", "Credit", py_period_list, filters = filters,
		accumulated_values=False,
		ignore_closing_entries=True, ignore_accumulated_values_for_fy= True)

    if len(ytd_expenses) > 1 and len(py_revenue) > 1 and 'total' in ytd_revenue[1] and 'total' in py_revenue[1] :
        data.append({
            'description': _("Revenue"),
            'ytd': ytd_revenue[1].total,
            'py': py_revenue[1].total
        })

    if len(ytd_expenses) > 4 and len(py_revenue) > 4 and  'total' in ytd_revenue[4] and 'total' in py_revenue[4] :
        data.append({
            'description': _("from that Akonto Revenue"),
            'ytd': ytd_revenue[4].total,
            'py': py_revenue[4]['total']
        })
    
   
    # receivables
    ytd_receivables = frappe.db.sql("""
        SELECT IFNULL(SUM(`outstanding_amount` * IFNULL(`conversion_rate`, 1)), 0) AS `amount`
        FROM `tabSales Invoice`
        WHERE
            `tabSales Invoice`.`docstatus` = 1
            AND `tabSales Invoice`.`company` = "{company}"
            AND `tabSales Invoice`.`outstanding_amount` > 0;""".format(
        company=filters['company'], year=year, date=date), as_dict=True)[0]['amount']
    data.append({
        'description': _("from that Receivables"),
        'ytd': ytd_receivables,
        'py': None
    })
   
    # expected receivables
    ytd_expected_receivables = frappe.db.sql("""
        SELECT (`amount_volume` - `invoiced_akonto_volume` - `invoiced_volume`) AS `amount`
            FROM
            (SELECT
                (SELECT
                    IFNULL(SUM(`tabSales Order`.`base_net_total`), 0) 
                        FROM `tabSales Order`
                        WHERE `tabSales Order`.`docstatus` = 1
                        AND `tabSales Order`.`status` NOT IN ("Closed", "Completed")
                        AND `tabSales Order`.`company` = "{company}"
                        AND `tabSales Order`.`transaction_date` <= "{date}"
                ) AS `amount_volume`,
                (SELECT IFNULL(SUM(`tabSales Invoice`.`base_net_total`), 0)
                        FROM `tabSales Invoice`
                        LEFT JOIN `tabSales Order` ON `tabSales Order`.`name` = `tabSales Invoice`.sales_order
                        WHERE
                            `tabSales Invoice`.`docstatus` = 1
                            AND `tabSales Invoice`.`is_akonto` = 1
                            AND `tabSales Invoice`.`company` = "{company}"
                            AND `tabSales Order`.`docstatus` = 1
                            AND `tabSales Order`.`status` NOT IN ("Closed", "Completed")
                            AND `tabSales Order`.`transaction_date` <= "{date}"
                ) AS `invoiced_akonto_volume`,
                (SELECT IFNULL(SUM(`tabSales Invoice Item`.`amount`), 0)
                        FROM `tabSales Invoice Item`
                        LEFT JOIN `tabSales Order` ON `tabSales Order`.`name` = `tabSales Invoice Item`.sales_order
                        LEFT JOIN `tabSales Invoice` ON `tabSales Invoice`.`name` = `tabSales Invoice Item`.parent
                        WHERE
                            `tabSales Invoice`.`docstatus` = 1
                            AND `tabSales Invoice`.`is_akonto` = 0
                            AND `tabSales Invoice`.`company` = "{company}"
                            AND `tabSales Order`.`docstatus` = 1
                            AND `tabSales Order`.`status` NOT IN ("Closed", "Completed")
                            AND `tabSales Order`.`transaction_date` <= "{date}"
                ) AS `invoiced_volume`
            ) as `data`
        ;""".format(company=filters['company'], date=date), as_dict=True)[0]['amount']
   
    data.append({
        'description': _("Expected Receivables"),
        'ytd': ytd_expected_receivables,
        'py': None
    })


    data.append({
        'description': "-----------",
        'ytd': None,
        'py': None
    })

    data.append({
        'description': _("Expense"),
        'ytd': None,
        'py': None
    })

    ytd_expenses = get_data(filters.company, "Expense", "Debit", period_list, filters = filters,
		accumulated_values=False,
		ignore_closing_entries=True, ignore_accumulated_values_for_fy= True)

    py_expenses = get_data(filters.company, "Expense", "Debit", py_period_list, filters = filters,
		accumulated_values=False,
		ignore_closing_entries=True, ignore_accumulated_values_for_fy= True)

    if len(ytd_expenses) > 2 and len(py_revenue) > 2 and 'total' in ytd_revenue[-2] and 'total' in py_revenue[-2] :
        data.append({
            'description': _("Expenses"),
            'ytd': ytd_expenses[-2]['total'],
            'py': py_expenses[-2]['total']
        })
        
    # payables 
    ytd_payables = frappe.db.sql("""
        SELECT IFNULL((SUM(`debit`) - SUM(`credit`)), 0) AS `amount`
        FROM `tabGL Entry` 
        WHERE `account` IN (SELECT `name` FROM `tabAccount` WHERE `account_type` = "Payable")
          AND `posting_date` <= "{date}"
          AND `company` = "{company}"
        ;""".format(company=filters['company'], date=date), as_dict=True)[0]['amount']
    data.append({
        'description': _("from that Payables"),
        'ytd': ytd_payables * -1,
        'py': None
    })
    
    # expected payables
    ytd_expected_payables = frappe.db.sql("""
        SELECT
            (-1) * IFNULL(SUM(`tabPurchase Order Item`.`base_net_amount`), 0) AS `amount`
        FROM `tabPurchase Order Item`
        LEFT JOIN `tabPurchase Order` ON `tabPurchase Order`.`name` = `tabPurchase Order Item`.`parent`
        LEFT JOIN `tabPurchase Invoice Item` ON `tabPurchase Invoice Item`.`po_detail` = `tabPurchase Order Item`.`name`
        WHERE `tabPurchase Order`.`docstatus` = 1
          AND `tabPurchase Order`.`status` NOT IN ("Closed", "Completed")
          AND `tabPurchase Order`.`company` = "{company}"
          AND `tabPurchase Order`.`transaction_date` <= "{date}"
          AND `tabPurchase Invoice Item`.`name` IS NULL
        ;""".format(company=filters['company'], date=date), as_dict=True)[0]['amount']

    data.append({
        'description': _("Expected Payables"),
        'ytd': ytd_expected_payables * -1,
        'py': None
    })
    
    data.append({
        'description': "-----------",
        'ytd': None,
        'py': None
    })

    # open quotations
    ytd_open_quotations = frappe.db.sql("""
        SELECT
            IFNULL(SUM(`tabQuotation`.`base_net_total` * `tabQuotation`.`probability` / 100), 0) AS `amount`
        FROM `tabQuotation`
        WHERE `tabQuotation`.`docstatus` = 1
          AND `tabQuotation`.`status` IN ("Open")
          AND `tabQuotation`.`company` = "{company}"
        ;""".format(company=filters['company'], date=date), as_dict=True)[0]['amount']
    data.append({
        'description': _("Open Quotation Volume"),
        'ytd': ytd_open_quotations,
        'py': None
    })

    if filters['company'] == "Asprotec AG":
        stock = get_balance_on("1200 - Vorräte Handelswaren - A",date=date,party_type=None,company=filters['company'],in_account_currency=True)
    else:
        stock = get_balance_on("1200 - Vorräte Handelswaren - I",date=date,party_type=None,company=filters['company'],in_account_currency=True)

    data.append({
        'description': _("Stock"),
        'ytd': stock,
        'py': None
    })

    return data

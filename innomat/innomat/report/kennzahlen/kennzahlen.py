# Copyright (c) 2013, Innomat, Asprotec and libracore and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
import ast          # to parse str to dict (from JS calls)
from datetime import date

def execute(filters=None):
    columns = get_columns()
    data = get_data(filters)
    return columns, data

def get_columns():
    return [
        {"label": _("Description"), "fieldname": "description", "fieldtype": "Data", "width": 150},
        {"label": _("YTD [CHF]"), "fieldname": "ytd", "fieldtype": "Currency", "width": 120},
        {"label": _("PY [CHF]"), "fieldname": "py", "fieldtype": "Currency", "width": 120},
        {"label": _(""), "fieldname": "blank", "fieldtype": "Data", "width": 20}
    ]

@frappe.whitelist()
def get_data(filters):
    conditions = ""
    if type(filters) is str:
        filters = ast.literal_eval(filters)
    else:
        filters = dict(filters)
    
    year = int(filters['date'][:4])
    date = filters['date']
    previous_year = year - 1
    previous_date = "{0}{1}".format(previous_year, filters['date'][5:])
    
    data = []
    
    # revenue
    ytd_revenue = frappe.db.sql("""
        SELECT ((`invoice_volume` - `advance_volume` + `akonto_invoiced`) / 1.077) AS `amount`
        FROM
        (SELECT
            (SELECT IFNULL(SUM(`grand_total` * IFNULL(`conversion_rate`, 1)), 0)
                    FROM `tabSales Invoice`
                    WHERE
                        `tabSales Invoice`.`docstatus` = 1
                        AND `tabSales Invoice`.`company` = "{company}"
                        AND DATE(`tabSales Invoice`.`posting_date`) >= "{year}-01-01"
                        AND DATE(`tabSales Invoice`.`posting_date`) <= "{date}"
            ) AS `invoice_volume`,
            (SELECT IFNULL(SUM(`total_advance` * IFNULL(`conversion_rate`, 1)), 0)
                    FROM `tabSales Invoice`
                    WHERE
                        `tabSales Invoice`.`docstatus` = 1
                        AND `tabSales Invoice`.`company` = "{company}"
                        AND DATE(`tabSales Invoice`.`posting_date`) >= "{year}-01-01"
                        AND DATE(`tabSales Invoice`.`posting_date`) <= "{date}"
            ) AS `advance_volume`,
            (SELECT
                IFNULL(SUM(`tabSales Order Akonto`.`amount` * IFNULL(`tabSales Order`.`conversion_rate`, 1)), 0) AS `amount`
             FROM `tabSales Order Akonto`
             LEFT JOIN `tabSales Order` ON `tabSales Order`.`name` = `tabSales Order Akonto`.`parent`
             WHERE `tabSales Order`.`docstatus` = 1
               AND `tabSales Order`.`status` NOT IN ("Closed", "Completed")
               AND `tabSales Order`.`company` = "{company}"
               AND DATE(`tabSales Order Akonto`.`creation_date`) >= "{year}-01-01"
               AND DATE(`tabSales Order Akonto`.`creation_date`) <= "{date}"
               AND `tabSales Order Akonto`.`file` IS NOT NULL
            ) AS `akonto_invoiced`
        ) AS `data`;""".format(
        company=filters['company'], year=year, date=date), as_dict=True)[0]['amount']
    py_revenue = frappe.db.sql("""
        SELECT ((`invoice_volume` - `advance_volume` + `akonto_invoiced`) / 1.077) AS `amount`
        FROM
        (SELECT
            (SELECT IFNULL(SUM(`grand_total` * IFNULL(`conversion_rate`, 1)), 0)
                    FROM `tabSales Invoice`
                    WHERE
                        `tabSales Invoice`.`docstatus` = 1
                        AND `tabSales Invoice`.`company` = "{company}"
                        AND DATE(`tabSales Invoice`.`posting_date`) >= "{year}-01-01"
                        AND DATE(`tabSales Invoice`.`posting_date`) <= "{date}"
            ) AS `invoice_volume`,
            (SELECT IFNULL(SUM(`total_advance` * IFNULL(`conversion_rate`, 1)), 0)
                    FROM `tabSales Invoice`
                    WHERE
                        `tabSales Invoice`.`docstatus` = 1
                        AND `tabSales Invoice`.`company` = "{company}"
                        AND DATE(`tabSales Invoice`.`posting_date`) >= "{year}-01-01"
                        AND DATE(`tabSales Invoice`.`posting_date`) <= "{date}"
            ) AS `advance_volume`,
            (SELECT
                IFNULL(SUM(`tabSales Order Akonto`.`amount` * IFNULL(`tabSales Order`.`conversion_rate`, 1)), 0) AS `amount`
             FROM `tabSales Order Akonto`
             LEFT JOIN `tabSales Order` ON `tabSales Order`.`name` = `tabSales Order Akonto`.`parent`
             WHERE `tabSales Order`.`docstatus` = 1
               AND `tabSales Order`.`status` NOT IN ("Closed", "Completed")
               AND `tabSales Order`.`company` = "{company}"
               AND DATE(`tabSales Order Akonto`.`creation_date`) >= "{year}-01-01"
               AND DATE(`tabSales Order Akonto`.`creation_date`) <= "{date}"
               AND `tabSales Order Akonto`.`file` IS NOT NULL
            ) AS `akonto_invoiced`
        ) AS `data`;""".format(
        company=filters['company'], year=previous_year, date=previous_date), as_dict=True)[0]['amount']
    data.append({
        'description': _("Revenue"),
        'ytd': ytd_revenue,
        'py': py_revenue
    })
    
    # expenses
    ytd_expenses = frappe.db.sql("""
        SELECT 
          IFNULL(SUM(`tabGL Entry`.`debit`) - SUM(`tabGL Entry`.`credit`), 0) AS `amount`
        FROM `tabGL Entry`
        JOIN `tabAccount` ON `tabGL Entry`.`account` = `tabAccount`.`name`
        WHERE 
          `tabGL Entry`.`docstatus` = 1
          AND `tabGL Entry`.`company` = "{company}"
          AND `tabAccount`.`account_type` IN ('Expense Account', 'Stock Adjustment', 'Depreciation', 'Cost of Goods Sold')
          AND `tabGL Entry`.`posting_date` >= '{year}-01-01'
          AND `tabGL Entry`.`posting_date` <= '{date}'
          AND `tabGL Entry`.`voucher_type` != 'Period Closing Voucher';""".format(
        company=filters['company'], year=year, date=date), as_dict=True)[0]['amount']
    py_expenses = frappe.db.sql("""
        SELECT 
          IFNULL(SUM(`tabGL Entry`.`debit`) - SUM(`tabGL Entry`.`credit`), 0) AS `amount`
        FROM `tabGL Entry`
        JOIN `tabAccount` ON `tabGL Entry`.`account` = `tabAccount`.`name`
        WHERE 
          `tabGL Entry`.`docstatus` = 1
          AND `tabGL Entry`.`company` = "{company}"
          AND `tabAccount`.`account_type` IN ('Expense Account', 'Stock Adjustment', 'Cost of Goods Sold', 'Depreciation')
          AND `tabGL Entry`.`posting_date` >= '{year}-01-01'
          AND `tabGL Entry`.`posting_date` <= '{date}'
          AND `tabGL Entry`.`voucher_type` != 'Period Closing Voucher';""".format(
        company=filters['company'], year=previous_year, date=previous_date), as_dict=True)[0]['amount']
    data.append({
        'description': _("Expenses"),
        'ytd': ytd_expenses,
        'py': py_expenses
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
        'description': _("Receivables"),
        'ytd': ytd_receivables,
        'py': None
    })
    
    # akonto receivables
    ytd_akonto_receivables = frappe.db.sql("""
        SELECT IFNULL((SUM(`debit`) - SUM(`credit`)), 0) AS `amount`
        FROM `tabGL Entry` 
        WHERE `account` LIKE "1150%"
          AND `posting_date` <= "{date}"
          AND `company` = "{company}"
        ;""".format(company=filters['company'], date=date), as_dict=True)[0]['amount']
    data.append({
        'description': _("Akonto Receivables"),
        'ytd': ytd_akonto_receivables,
        'py': None
    })
    
    # expected receivables
    ytd_expected_receivables = frappe.db.sql("""
        SELECT
            IFNULL(SUM(`tabSales Order Item`.`base_net_amount`), 0) AS `amount`
        FROM `tabSales Order Item`
        LEFT JOIN `tabSales Order` ON `tabSales Order`.`name` = `tabSales Order Item`.`parent`
        LEFT JOIN `tabSales Invoice Item` ON `tabSales Invoice Item`.`so_detail` = `tabSales Order Item`.`name`
        WHERE `tabSales Order`.`docstatus` = 1
          AND `tabSales Order`.`status` NOT IN ("Closed", "Completed")
          AND `tabSales Order`.`company` = "{company}"
          AND `tabSales Order`.`transaction_date` <= "{date}"
          AND `tabSales Invoice Item`.`name` IS NULL
        ;""".format(company=filters['company'], date=date), as_dict=True)[0]['amount']
    akonto_invoiced = frappe.db.sql("""
        SELECT
            IFNULL(SUM(`tabSales Order Akonto`.`amount` * IFNULL(`tabSales Order`.`conversion_rate`, 1)), 0) AS `amount`
        FROM `tabSales Order Akonto`
        LEFT JOIN `tabSales Order` ON `tabSales Order`.`name` = `tabSales Order Akonto`.`parent`
        WHERE `tabSales Order`.`docstatus` = 1
          AND `tabSales Order`.`status` NOT IN ("Closed", "Completed")
          AND `tabSales Order`.`company` = "{company}"
          AND `tabSales Order`.`transaction_date` <= "{date}"
          AND `tabSales Order Akonto`.`file` IS NOT NULL
        ;""".format(company=filters['company'], date=date), as_dict=True)[0]['amount']
    data.append({
        'description': _("Expected Receivables"),
        'ytd': ytd_expected_receivables - akonto_invoiced,
        'py': None
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
        'description': _("Payables"),
        'ytd': ytd_payables,
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
        'ytd': ytd_expected_payables,
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
    
    # average quotation volume
    ytd_open_quotations = frappe.db.sql("""
        SELECT
            IFNULL((SUM(`tabQuotation`.`base_net_total`) / IFNULL(COUNT(`tabQuotation`.`base_net_total`), 1)), 0) AS `amount`
        FROM `tabQuotation`
        WHERE `tabQuotation`.`docstatus` = 1
          AND `tabQuotation`.`status` IN ("Open")
          AND `tabQuotation`.`company` = "{company}"
          AND `tabQuotation`.`transaction_date` >= '{year}-01-01'
          AND `tabQuotation`.`transaction_date` <= '{date}'
        ;""".format(company=filters['company'], date=date, year=year), as_dict=True)[0]['amount']
    py_open_quotations = frappe.db.sql("""
        SELECT
            IFNULL((SUM(`tabQuotation`.`base_net_total`) / IFNULL(COUNT(`tabQuotation`.`base_net_total`), 1)), 0) AS `amount`
        FROM `tabQuotation`
        WHERE `tabQuotation`.`docstatus` = 1
          AND `tabQuotation`.`status` IN ("Open")
          AND `tabQuotation`.`company` = "{company}"
          AND `tabQuotation`.`transaction_date` >= '{year}-01-01'
          AND `tabQuotation`.`transaction_date` <= '{date}'
        ;""".format(company=filters['company'], date=previous_date, year=previous_year), as_dict=True)[0]['amount']
    data.append({
        'description': _("Average Quotation Volume"),
        'ytd': ytd_open_quotations,
        'py': py_open_quotations
    })
    return data

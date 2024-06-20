# Copyright (c) 2024, Innomat, Asprotec and libracore and contributors
# For license information, please see license.txt

import frappe
from frappe import _


def execute(filters=None):
    columns = get_columns()
    data = get_data(filters)
    return columns, data


def get_columns():
    columns = [
        {"label": _("Tax Code"), "fieldname": "tax_code", "fieldtype": "Data", "width": 90},
        {"label": _("Income Account"), "fieldname": "income_account", "fieldtype": "Link", "options": "Account", "width": 125},
        {"label": _("Date"), "fieldname": "posting_date", "fieldtype": "Date", "width": 100},
        {"label": _("Document"), "fieldname": "name", "fieldtype": "Link", "options": "Sales Invoice", "width": 125},
        {"label": _("Net Amount"), "fieldname": "base_net_amount", "fieldtype": "Currency", "width": 100, 'options': 'currency'}
    ]
    return columns


def get_data(filters, short=False):
    sql_query = """
        SELECT
            `tabSales Taxes and Charges Template`.`tax_code`,
            `tabSales Invoice Item`.`income_account`,
            `tabSales Invoice`.`posting_date`,
            `tabSales Invoice`.`name`,
            SUM(`tabSales Invoice Item`.`base_net_amount`) AS `base_net_amount`,
            "CHF" AS `currency`
        FROM `tabSales Invoice Item`
        LEFT JOIN `tabSales Invoice` ON `tabSales Invoice`.`name` = `tabSales Invoice Item`.`parent`
        LEFT JOIN `tabSales Taxes and Charges Template` ON `tabSales Taxes and Charges Template`.`name` = `tabSales Invoice`.`taxes_and_charges`
        WHERE
            `tabSales Invoice`.`docstatus` = 1
            AND `tabSales Invoice`.`posting_date` BETWEEN "{from_date}" AND "{to_date}"
            AND `tabSales Invoice`.`company` = "{company}"
        GROUP BY CONCAT(`tabSales Invoice`.`name`, ":", `tabSales Invoice Item`.`income_account`)
        ORDER BY 
            `tabSales Taxes and Charges Template`.`tax_code` ASC, 
            `tabSales Invoice`.`posting_date` ASC, 
            `tabSales Invoice`.`name` ASC;
    """.format(from_date=filters.from_date, to_date=filters.to_date, company=filters.company)

    data = frappe.db.sql(sql_query, as_dict=True)

    return data

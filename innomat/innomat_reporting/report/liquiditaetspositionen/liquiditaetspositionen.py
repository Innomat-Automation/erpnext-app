# Copyright (c) 2026, Innomat, Asprotec and libracore and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.utils import flt
from erpnext.accounts.utils import get_balance_on

def execute(filters=None):
    columns = get_columns()
    data = get_data(filters)
    return columns, data


def get_columns():
    return [
        {"label": "Position", "fieldname": "position", "fieldtype": "Data", "width": 400},
        {"label": "Betrag", "fieldname": "amount", "fieldtype": "Currency", "width": 200}
    ]


def get_account_balance(account, company, date):
    return get_balance_on(
        account=account,
        date=date,
        company=company
    )
    return flt(balance)


def get_data(filters):
    company = filters.company
    date = filters.date

    cash = get_account_balance("100 - Flüssige Mittel - I", company, date)
    other_short_liab = get_account_balance(
        "220 - Andere kurzfristige Verbindlichkeiten - I", company, date
    )
    ap = get_account_balance(
        "200 - Kurzfristige Verbindlichkeiten aus Lieferungen und Leistungen - I",
        company,
        date
    )

    ar1 = get_account_balance(
        "1100 - Forderungen aus Lieferungen und Leistungen - I", company, date
    )
    ar2 = get_account_balance(
        "1102 - Forderungen aus Lieferungen und Leistungen EUR - I", company, date
    )
    ar = ar1 + ar2

    total_liq = cash + ap + other_short_liab + ar

    return [
        {"position": "Guthaben - Flüssige Mittel (100)", "amount": cash},
        {"position": "Ausgänge - Verbindlichkeiten aus L&L (200)", "amount": ap},
        {"position": "Ausgänge - Übrige kurzfristige Verbindlichkeiten (220)", "amount": other_short_liab},
        {"position": "Eingänge - Forderungen aus L&L (1100+1102)", "amount": ar},
        {},
        {"position": "Summe", "amount": total_liq},
    ]
# -*- coding: utf-8 -*-
# Copyright (c) 2025, Innomat, Asprotec and libracore and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.model.document import Document

class InnomatBudget(Document):

    def validate(self):
        seen_accounts = []
        for acc in self.accounts:
            acc_doc = frappe.get_doc("Account", acc.account)
            if acc_doc.company != self.company:
                frappe.throw(_("Zeile {0}: Konto gehört nicht zu Firma '{1}'").format(acc.idx, self.company))

            if acc.account in seen_accounts:
                frappe.throw(_("Zeile {0}: Konto '{1}' erscheint mehrfach im Budget").format(acc.idx, acc.account))
            else:
                seen_accounts.append(acc.account)

# Copyright (c) 2021, libracore and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe

# searches for supplier
def projects_for_employee(doctype, txt, searchfield, start, page_len, filters):
    return frappe.db.sql(
        """SELECT `tabProject`.`name`, 
                `tabProject`.`customer_name`,
                `tabProject`.`status`,
                `tabProject`.`priority`
           FROM `tabProject`
           LEFT JOIN `tabProject Member` ON `tabProject Member`.`parent` = `tabProject`.`name`
           WHERE `tabProject Member`.`employee` = "{e}"
             AND `tabProject`.`is_active` = "Yes";
        """.format(e=filters['employee']))

from __future__ import unicode_literals
from frappe import _

def get_data():
    return[
        {
            "label": _("Selling"),
            "icon": "fa fa-money",
            "items": [
                   {
                       "type": "doctype",
                       "name": "Item",
                       "label": _("Item"),
                       "description": _("Item")
                   },
                   {
                       "type": "doctype",
                       "name": "BOM",
                       "label": _("BOM"),
                       "description": _("BOM")
                   },
                   {
                       "type": "doctype",
                       "name": "Customer",
                       "label": _("Customer"),
                       "description": _("Customer")
                   },
                   {
                       "type": "doctype",
                       "name": "Quotation",
                       "label": _("Quotation"),
                       "description": _("Quotation")
                   },
                   {
                       "type": "doctype",
                       "name": "Sales Order",
                       "label": _("Sales Order"),
                       "description": _("Sales Order")
                   },
                   {
                       "type": "doctype",
                       "name": "Sales Invoice",
                       "label": _("Sales Invoice"),
                       "description": _("Sales Invoice")
                   }
            ]
        },
        {
            "label": _("Buying"),
            "icon": "fa fa-money",
            "items": [
                   {
                       "type": "doctype",
                       "name": "Item",
                       "label": _("Item"),
                       "description": _("Item")
                   },
                   {
                       "type": "doctype",
                       "name": "Supplier",
                       "label": _("Supplier"),
                       "description": _("Supplier")
                   },
                   {
                       "type": "doctype",
                       "name": "Supplier Quotation",
                       "label": _("Supplier Quotation"),
                       "description": _("Supplier Quotation")
                   },
                   {
                       "type": "doctype",
                       "name": "Purchase Order",
                       "label": _("Purchase Order"),
                       "description": _("Purchase Order")
                   },
                   {
                       "type": "doctype",
                       "name": "Purchase Invoice",
                       "label": _("Purchase Invoice"),
                       "description": _("Purchase Invoice")
                   }
            ]
        },
        {
            "label": _("Projects"),
            "icon": "fa fa-money",
            "items": [
                   {
                       "type": "doctype",
                       "name": "Project",
                       "label": _("Project"),
                       "description": _("Project")
                   },
                   {
                       "type": "doctype",
                       "name": "Task",
                       "label": _("Task"),
                       "description": _("Task")
                   },
                   {
                       "type": "doctype",
                       "name": "Timesheet",
                       "label": _("Timesheet"),
                       "description": _("Timesheet")
                   },
                   {
                       "type": "doctype",
                       "name": "Expense Claim",
                       "label": _("Expense Claim"),
                       "description": _("Expense Claim")
                   },
                   {
                       "type": "doctype",
                       "name": "Equipment",
                       "label": _("Equipment"),
                       "description": _("Equipment")
                   }
            ]
        },
        {
            "label": _("Accounting"),
            "icon": "fa fa-money",
            "items": [
                   {
                       "type": "page",
                       "name": "bank_wizard",
                       "label": _("Bank Wizard"),
                       "description": _("Bank Wizard")
                   },
                   {
                       "type": "doctype",
                       "name": "Payment Proposal",
                       "label": _("Payment Proposal"),
                       "description": _("Payment Proposal")
                   },
                   {
                       "type": "doctype",
                       "name": "Payment Reminder",
                       "label": _("Payment Reminder"),
                       "description": _("Payment Reminder")
                   }
            ]
        },
        {
            "label": _("Configuration"),
            "icon": "octicon octicon-file-submodule",
            "items": [
                   {
                       "type": "doctype",
                       "name": "Textkonserve",
                       "label": _("Textkonserve"),
                       "description": _("Textkonserve")                   
                   },
                   {
                       "type": "doctype",
                       "name": "Activity Type",
                       "label": _("Activity Type"),
                       "description": _("Activity Type")                   
                   },
                   {
                       "type": "doctype",
                       "name": "Item Group",
                       "label": _("Item Group"),
                       "description": _("Item Group")                   
                   },
                   {
                       "type": "doctype",
                       "name": "Innomat Settings",
                       "label": _("Innomat Settings"),
                       "description": _("Innomat Settings")                   
                   },
                   {
                       "type": "doctype",
                       "name": "Project Template",
                       "label": _("Project Template"),
                       "description": _("Project Template")                   
                   }
            ]
        }
    ]

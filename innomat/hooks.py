# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from . import __version__ as app_version

app_name = "innomat"
app_title = "Innomat"
app_publisher = "Innomat, Asprotec and libracore"
app_description = "Innomat ERPNext applications"
app_icon = "octicon octicon-briefcase"
app_color = "grey"
app_email = "info@libracore.com"
app_license = "AGPL"

# Includes in <head>
# ------------------

# include js, css files in header of desk.html
# app_include_css = "/assets/innomat/css/innomat.css"
# app_include_js = "/assets/innomat/js/innomat.js"
app_include_js = ["/assets/innomat/js/innomat_common.js"]

# include js, css files in header of web template
# web_include_css = "/assets/innomat/css/innomat.css"
web_include_js = "/assets/innomat/js/innomat_web.js"

# include js in page
# page_js = {"page" : "public/js/file.js"}

# include js in doctype views
# doctype_js = {"doctype" : "public/js/doctype.js"}
doctype_js = {
    "Project" : "public/js/project.js",
    "Timesheet" : "public/js/timesheet.js",
    "Task" : "public/js/task.js",
    "BOM" : "public/js/bom.js",
    "Sales Order" : "public/js/sales_order.js",
    "Expense Claim" : "public/js/expense_claim.js",
    "Sales Invoice" : "public/js/sales_invoice.js",
    "Purchase Order" : "public/js/purchase_order.js",
    "Payment Entry" : "public/js/payment_entry.js",
    "Quotation" : "public/js/quotation.js",
    "User" : "public/js/user.js"
}
# doctype_list_js = {"doctype" : "public/js/doctype_list.js"}
doctype_list_js = {
    "Project" : "public/js/project_list.js",
    "Task": "public/js/task_list.js",
    "Purchase Invoice": "public/js/purchase_invoice_list.js",
    "Item": "public/js/item_list.js"
}
# doctype_tree_js = {"doctype" : "public/js/doctype_tree.js"}
# doctype_calendar_js = {"doctype" : "public/js/doctype_calendar.js"}

# Home Pages
# ----------

# application home page (will override Website Settings)
# home_page = "login"

# website user home page (by Role)
# role_home_page = {
#	"Role": "home_page"
# }

# Website user home page (by function)
# get_website_user_home_page = "innomat.utils.get_home_page"

# Generators
# ----------

# automatically create page for each record of this doctype
# website_generators = ["Web Page"]

# Installation
# ------------

# before_install = "innomat.install.before_install"
# after_install = "innomat.install.after_install"

# Desk Notifications
# ------------------
# See frappe.core.notifications.get_notification_config

# notification_config = "innomat.notifications.get_notification_config"

# Permissions
# -----------
# Permissions evaluated in scripted ways

# permission_query_conditions = {
# 	"Event": "frappe.desk.doctype.event.event.get_permission_query_conditions",
# }
#
# has_permission = {
# 	"Event": "frappe.desk.doctype.event.event.has_permission",
# }

# Document Events
# ---------------
# Hook on document methods and events

# doc_events = {
# 	"*": {
# 		"on_update": "method",
# 		"on_cancel": "method",
# 		"on_trash": "method"
#	}
# }

# Scheduled Tasks
# ---------------

# scheduler_events = {
# 	"all": [
# 		"innomat.tasks.all"
# 	],
# 	"daily": [
# 		"innomat.tasks.daily"
# 	],
# 	"hourly": [
# 		"innomat.tasks.hourly"
# 	],
# 	"weekly": [
# 		"innomat.tasks.weekly"
# 	]
# 	"monthly": [
# 		"innomat.tasks.monthly"
# 	]
# }
scheduler_events = {
    "daily": [
        "innomat.innomat.utils.update_project_costs"
    ]
}

# Testing
# -------

# before_tests = "innomat.install.before_tests"

# Overriding Methods
# ------------------------------
#
# override_whitelisted_methods = {
# 	"frappe.desk.doctype.event.event.get_events": "innomat.event.get_events"
# }
#
# each overriding function accepts a `data` argument;
# generated from the base implementation of the doctype dashboard,
# along with any modifications made in other Frappe apps
# override_doctype_dashboards = {
# 	"Task": "innomat.task.get_dashboard_data"
# }

# hook for migrate cleanup tasks
after_migrate = [
    'innomat.innomat.updater.cleanup_languages'
]

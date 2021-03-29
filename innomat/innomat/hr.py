# -*- coding: utf-8 -*-
# Copyright (c) 2018-2021, libracore (https://www.libracore.com) and contributors
# For license information, please see license.txt
import frappe
from frappe import _
from datetime import datetime, timedelta
from erpnextswiss.erpnextswiss.hr import get_working_days_between_dates

def get_working_hours_ytd(employee):
    employee = frappe.get_doc("Employee", employee)
    company = frappe.get_doc("Company", employee.company)
    holiday_list = company.default_holiday_list
    start_date = datetime(datetime.now().year, 1, 1).date()
    h_per_day = 0
    hours = 0
    # go through part-time blocks
    for pt in employee.part_time:
        if pt.from_date > datetime.now().date():
            days = get_working_days_between_dates(holiday_list, start_date, datetime.now().date())
            #print("{0} days from last date until today at {1}".format(days, h_per_day))
            hours += h_per_day * days
        elif pt.from_date > start_date:
            days = get_working_days_between_dates(holiday_list, start_date, (pt.from_date + timedelta(days=-1)))
            #print("{0} days from last date until new percentage {1}".format(days, h_per_day))
            hours += h_per_day * days
            start_date = pt.from_date
        # keep last h per day
        h_per_day = pt.hours_per_day
    if start_date < datetime.now().date():
        days = get_working_days_between_dates(holiday_list, start_date, datetime.now().date())
        #print("{0} days with last percentage {1}".format(days, h_per_day))
        hours += h_per_day * days
    return hours

def get_actual_hours_ytd(employee, activity="%"):
    sql_query = """SELECT SUM(`hours`) AS `h`
                   FROM `tabTimesheet Detail`
                   LEFT JOIN `tabTimesheet` ON `tabTimesheet`.`name` = `tabTimesheet Detail`.`parent`
                   WHERE `tabTimesheet`.`employee` = "{e}"
                     AND `tabTimesheet`.`docstatus` = 1
                     AND DATE(`tabTimesheet Detail`.`from_time`) >= CONCAT(YEAR(CURDATE()), "-01-01")
                     AND DATE(`tabTimesheet Detail`.`to_time`
                     AND `tabTimesheet Detail`.`activity_type` LIKE "{a}") <= CURDATE();""".format(e=employee, a=activity)
    data = frappe.db.sql(sql_query, as_dict=True)
    if len(data) > 0:
        return data[0]['h']
    else:
        return 0

@frappe.whitelist()
def get_employee_overview(employee):
    data = {
        'target_h': get_working_hours_ytd(employee),
        'actual_h': get_actual_hours_ytd(employee)
    }
    return data

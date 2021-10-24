
# Copyright (c) 2019-2021, asprotec ag and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from datetime import datetime, timedelta
from erpnextswiss.erpnextswiss.doctype.worktime_settings.worktime_settings import get_daily_working_hours, get_default_working_hours

"""
Calculates the planned resource consumption in full-time equivalent
"""
@frappe.whitelist()
def get_fte(user, start_date, end_date, hours):
    # get working hours for employee
    employees = frappe.get_all("Employee", filters={'user_id': user}, fields=['name', 'company'])
    if employees and len(employees) > 0:
        employee = employees[0]['name']
        company = employees[0]['company']
        working_hours = get_daily_working_hours(company, employee)
    else:
        company = frappe.defaults.get_global_default('company')
        working_hours = get_default_working_hours()
    # get number of working days
    working_days = get_working_days(start_date, end_date, company)
    # available time
    available_hours = working_days * working_hours
    # fte
    fte = float(hours) / available_hours
    return fte
    
""" 
Get number of working days between two dates (including the two dates)
"""
def get_working_days(from_date, to_date, company):
    holidays = get_holidays(company)
    date = datetime.strptime(from_date, "%Y-%m-%d")
    end_date = datetime.strptime(to_date, "%Y-%m-%d")
    days = 0
    while date <= end_date:
        if "{0}".format(date.date()) not in holidays:
            days += 1
        date += timedelta(days=1)
    return days

       
"""
Gets a list of all days off
"""
def get_holidays(company):
    holiday_list = frappe.get_value("Company", company, "default_holiday_list")
    sql_query = """SELECT `holiday_date` FROM `tabHoliday` WHERE `parent` = "{h}";""".format(h=holiday_list)
    data = frappe.db.sql(sql_query, as_dict=True)
    dates = []
    for d in data:
        dates.append(d['holiday_date'].strftime("%Y-%m-%d"))
    return dates


"""
Update Timesheets, after chaning by Effort on Task. 
"""
@frappe.whitelist()
def update_timesheets(task,by_effort):
    frappe.db.sql("""UPDATE `tabTimesheet Detail`
                                  SET `by_effort` = {byeffort}
                                  WHERE `tabTimesheet Detail`.`task` = "{task}";""".format(task=task,byeffort=by_effort), as_dict=True)
                                      
    affected_rows = frappe.db.sql("""SELECT COUNT(`task`) as count FROM `tabTimesheet Detail`
                                  WHERE `tabTimesheet Detail`.`task` = "{task}";""".format(task=task,byeffort=by_effort), as_dict=True)
    return affected_rows[0];
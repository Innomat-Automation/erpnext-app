# Copyright (c) 2019-2021, Asprotec AG and contributors
# For license information, please see license.txt
# functions for migration from old systems


import frappe
from frappe.exceptions import TemplateNotFoundError
import pymssql
from frappe import _


# Migrate timesafe to erpnext
def migrate_to_erpnext(user,password):
    # get all projects
    con = get_connection(user,password)
    projectcursor = con.cursor(as_dict=True)
    projectcursor.execute('SELECT [strProjectNo] FROM [TimesafeBack].[dbo].[ViewActivities] GROUP BY [strProjectNo]')

    for row in projectcursor:
        key = row['strProjectNo']
        company_key = ""
        if(str(key).startswith('2')):
            company_key = "ASS"
        elif(str(key).startswith('3')):
            company_key = "ASP"
        elif(str(key).startswith('4')):
            company_key = "INS"
        elif(str(key).startswith('5')):
            company_key = "INP"

        print("Check {0}P{1}".format(company_key, key))
        doc = frappe.db.exists("Project","{0}P{1}".format(company_key, key))
        # if project not extist create 
        if(doc == None):
            doc = create_project(con,key)
        

        




def create_project(con,projectname):
    # get project from timesafe
    projectcursor = con.cursor(as_dict=True)
    projectcursor.execute('SELECT * From tProjects WHERE strProjectNo LIKE ' + projectname)

    if projectcursor.rowcount > 1:
        print("Error more then one project found")
    else:  
        for row in projectcursor:
            # create project 
            new_project = frappe.get_doc({
                "doctype": "Project",
                "project_key": projectname,
                "project_name": get_erp_projectname(projectname),
                "project_type": "Project" if str(row['tinState']).startswith('3') or str(row['tinState']).startswith('5') else "Service",
                "is_active": "Yes",
                "status": "Open" if row['tinState'] == 1 else "Closed",
                "title": get_erp_projectname(projectname) + " " + row['strProjectName']
            })
            if (row['dtStart'] != None):
                new_project.expected_start_date = row['dtStart']
            if (row['dtEnd'] != None):
                new_project.expected_end_date = row['dtEnd']

            # Add Teammember
            teammembers = get_team_member(con,row['lProjectID'])
            if len(teammembers) > 0:
                new_project.project_team = teammembers
            
            print("Insert project " + new_project.title)
            new_project.insert()

            return new_project
    

def get_team_member(con,projectid):
    # get project from timesafe
    membercursor = con.cursor(as_dict=True)
    membercursor.execute('SELECT tEmployees.lEmployeeID, tProjectTeam.bProjectLeader, tEmployees.strLogin, tEmployees.strLastName, tEmployees.strFirstName FROM tEmployees LEFT OUTER JOIN tProjectTeam ON tEmployees.lEmployeeID = tProjectTeam.lEmployeeID WHERE tProjectTeam.lProjectID = ' + str(projectid))

    members = []
    for meb in membercursor:
        print("Check team member " + str(meb["lEmployeeID"]))
        userid = frappe.get_all("Employee",filters={"employee_number":meb["lEmployeeID"]})
        if len(userid) == 1:
            user = frappe.get_doc("Employee",userid[0])
            print("Add team member " + user.name)
            member = frappe.get_doc({
                "doctype": "Project Member",
                "employee": user,
                "project_manager": 0 if meb['bProjectLeader'] == 0 else 1
            })
            members.append(member)
    
    return members



def get_erp_projectname(key):
    company_key = ""
    if(str(key).startswith('2')):
        company_key = "ASS"
    elif(str(key).startswith('3')):
        company_key = "ASP"
    elif(str(key).startswith('4')):
        company_key = "INS"
    elif(str(key).startswith('5')):
        company_key = "INP"
    
    return "{0}P{1}".format(company_key, key)


# function to migrate projects from Timesafe
def migrate_projects_from_timesafe(user,password):
    con = get_connection(user,password);
    cursor = con.cursor(as_dict=True)
    cursor.execute('SELECT * From Projects WHERE strProjectNr = ')
    for row in cursor:
        key = row['strProjectNo']
        company_key = "IN"
        if(str(key).startswith('2') or str(key).startswith('3')):
            company_key = "AS"

        print("Check {0}P{1}".format(company_key, key))
        doc = frappe.db.exists("Project","{0}P{1}".format(company_key, key))
        if(doc == None):
            print("Create {0}P{1}".format(company_key, key))
            # create project 
            new_project = frappe.get_doc({
                "doctype": "Project",
                "project_key": key,
                "project_name": "{0}P{1}".format(company_key, key),
                "project_type": "Project",
                "is_active": "Yes",
                "status": "Open",
                "title": row['strProjectName']
            })
            new_project.insert()
        
    frappe.db.commit();
    con.close()
    

def get_connection(user,password):
    return pymssql.connect("192.168.80.25\Timesafe",user,password,"TimesafeBack")

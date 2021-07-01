# Copyright (c) 2019-2021, Asprotec AG and contributors
# For license information, please see license.txt
# functions for migration from old systems


import frappe
from frappe.exceptions import TemplateNotFoundError
from datetime import datetime, timedelta
import pymssql
import math
from frappe import _


# Migrate timesafe to erpnext
def migrate_to_erpnext(user,password):
    # get all projects
    con = get_connection(user,password)
    projectcursor = con.cursor(as_dict=True)
    projectcursor.execute('SELECT [strProjectNo],[lProjectID] FROM [TimesafeBack].[dbo].[ViewActivities] GROUP BY [strProjectNo],[lProjectID]')

    projects = projectcursor.fetchall()
    for row in projects:
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
        elif(str(key).startswith('8')):
            company_key = "INP"

        print("Check {0}{1}".format(company_key, key))

        if check_special_project(key):
            continue
        doc = frappe.db.exists({'doctype' : "Project","project_key": key})
        # if project not extist create 
        if(doc != ()):
            continue
        
        doc = create_project(con,key)
                
        #check create sales order
        lumpcursor = con.cursor(as_dict=True)
        lumpcursor.execute('SELECT * FROM [TimesafeBack].[dbo].[tLumpSums] WHERE [lProjectID] = ' + str(row['lProjectID']))

        lumps = lumpcursor.fetchall()

        if len(lumps) > 0:
            print('Check lumps for project' + str(key))
            all_invoiced = True
            # check all invoiced
            for lump in lumps:
                if not str(lump['lInvoiceID']).isnumeric(): 
                    all_invoiced = False
                    break

            # create a salse order
            if all_invoiced == False:
                print('Create sales Order for project' + str(key))
                cursor = con.cursor(as_dict=True)
                sql = 'SELECT tProjects.*, tOrganizations.strClientNo as orgclientno, ContactOrg.strClientNo as contactclientno, tContacts.* FROM  [tProjects] LEFT JOIN [tOrganizations] ON tProjects.lOrganizationID = tOrganizations.lOrganizationID LEFT JOIN [tContacts] ON tProjects.lContactID = tContacts.lContactID LEFT JOIN [tOrganizations] AS ContactOrg ON tContacts.lOrganizationID = ContactOrg.lOrganizationID WHERE strProjectNo = \'' + str(key) + '\''
                cursor.execute(sql)
                project = cursor.fetchone()
                client = project['orgclientno'] 
                if client == None:
                    client = project['contactclientno']
                salesorder = { 
                        'doctype' : 'Sales Order',
                        'customer' : 'K-' + client, 
                        'object' : project['strProjectName'],
                        'company' : get_company_by_project_name(get_erp_projectname(row['strProjectNo'])),
                        'currency' : "EUR" if project['lInvoiceRptDefinitionID'] == 2 else "CHF",
                        'delivery_date' : '2021-12-31'
                        }
                salesorder['items'] = []
                for lump in lumps:
                    item = { 'doctype' : 'Sales Order Item',
                            'item_code' : 'MIG-PAUSCHAL',
                            'item_name' : lump['strText'][:30],
                            'description' : lump['strText'],
                            'qty' : 1,
                            'rate' : lump['decAmount'],
                            'uom' : 'Stk'
                    }
                    salesorder['items'].append(item)
            
                salesdoc = frappe.get_doc(salesorder)
                salesdoc.insert()

                prodoc = frappe.get_doc("Project",get_erp_projectname(row['strProjectNo']))
                prodoc.sales_order = salesdoc.name
                prodoc.save()

            frappe.db.commit()
    

    # create all nessecary task
    taskcursor = con.cursor(as_dict=True)
    taskcursor.execute('SELECT [strProjectNo],[strDesignation],[bForInvoice],[decHourlyRate] FROM [TimesafeBack].[dbo].[ViewActivities] GROUP BY [strProjectNo],[strDesignation],[bForInvoice],[decHourlyRate]')

    for row in taskcursor:
        #Check if task exist
        if(frappe.db.count('Task',{'Project':get_erp_projectname(row['strProjectNo']),'Subject':row['strDesignation']}) > 0):
            continue
        
        doc = frappe.db.exists({'doctype' : "Project","project_key": row['strProjectNo']})
        # if project not extist continue
        if(doc == ()):
            print('Project not found ' + row['strProjectNo'] )
            continue
        create_task(row)

    #create all timesheets
    timecursor = con.cursor(as_dict=True)
    timecursor.execute('SELECT [strProjectNo],[tinState],[strLogin],[strDesignation],[bForInvoice],[Duration],convert(date,[dtFrom],23) as dtFrom,[decHourlyRate],[lEmployeeID] FROM [TimesafeBack].[dbo].[ViewActivities] ORDER BY [dtFrom],[strLogin]')

    lastrow = {'dtFrom' : datetime(year=2021,month=1,day=1), 'strLogin':''}
    timesheet = None
    for row in timecursor:
        if not timesheet == None and (str(lastrow['dtFrom']) != str(row['dtFrom']) or lastrow['strLogin'] != row['strLogin']):
            print(str(lastrow['dtFrom']) + " : " + str(row['dtFrom']))
            print(lastrow['strLogin'] + " : " + row['strLogin'])
            print(timesheet)
            timesheetdoc = frappe.get_doc(timesheet)
            timesheetdoc.insert()
            timesheetdoc.submit()
            timesheet = None

        timesheet = create_time_sheet(timesheet,row)
        lastrow = row;
    
    print(timesheet)
    timesheetdoc = frappe.get_doc(timesheet)
    timesheetdoc.insert()
    timesheetdoc.submit()
    frappe.db.commit()
    con.close()

def create_time_sheet(timesheet,row):
    internal_starttime = datetime(year=row['dtFrom'].year,month=row['dtFrom'].month,day=row['dtFrom'].day,hour=7)
    user = get_user(row['lEmployeeID'])
    if user == 0: 
        return timesheet
   
    if timesheet == None:
        timesheet = {'doctype':'Timesheet',
                     'note':'Migration von Timesafe',
                     'employee': user}
        timesheet['time_logs'] = []
    
    if len(timesheet['time_logs']) > 0:
        from_time = timesheet['time_logs'][len(timesheet['time_logs'])-1]['from_time']
        hours = timesheet['time_logs'][len(timesheet['time_logs'])-1]['hours']
        internal_starttime = from_time.__add__(timedelta(hours=float(hours)))

    if check_special_project(row['strProjectNo']):
        timesheet['time_logs'].append({'doctype':'Timesheet Detail', 
                                        'activity_type':activity_absenzen(row['strDesignation']), 
                                        'from_time':internal_starttime,
                                        'to_time':internal_starttime.__add__(timedelta(hours=float(row['Duration']))),
                                        'hours':float(row['Duration']),
                                        'company': get_company_by_user(row['lEmployeeID'])})
    else:
        timesheet['time_logs'].append({'doctype':'Timesheet Detail', 
                                        'activity_type':'Engineering', 
                                        'project': get_erp_projectname(row['strProjectNo']),
                                        'task': get_task(get_erp_projectname(row['strProjectNo']),row['strDesignation']),
                                        'from_time':internal_starttime,
                                        'to_time':internal_starttime.__add__(timedelta(hours=float(row['Duration']))),
                                        'hours':float(row['Duration']),
                                        'company': get_company_by_user(row['lEmployeeID'])})
    
    return timesheet



def get_task(project,subject):
    tasks = frappe.db.get_all('Task',{'Project':project,'Subject':subject})
    if len(tasks) > 0:
        return tasks[0].name
    return 0

def activity_absenzen(task):
     if task == "Buchhaltung": return "Geschäftsleitung"
     if task == "Geschäftsleitung": return "Geschäftsleitung"
     if task == "Marketing": return "Verkauf"
     if task == "Offertwesen": return "Verkauf"
     if task == "Schulung Mitarbeiter": return "Schulung Mitarbeiter"
     if task == "Sitzung Intern": return "Sitzung Intern"
     if task == "Verkauf": return "Verkauf"
     if task == "Ferien": return "Ferien"
     if task == "Krankheit": return "Krankheit"
     if task == "Militär": return "Militär/Zivildienst"
     if task == "Unfall": return "Unfall"
     if task == "Vaterschaftsurlaub": return "Vaterschaftsurlaub"
     if task == "Zügeltag": return "Zügeltag"
     if task == "Projektleitung": return "Sitzung Intern"
     if task == "EDV Installation / Support": return "EDV Intern"
     if task == "Workshops": return "Sitzung Intern"
     if task == "Batchmanagement, Datenbank": return "Entwicklung"
     return "Kurzarbeit"

# Check for special project like "Absenzen"
def check_special_project(key):
    if(key == '2012001'): return True
    if(key == '8019001'): return True
    if(key == '200121'): return True
    if(key == '400319'): return True
    if(key == '4000621'): return True
    if(key == '800120'): return True
    if(key == '800119'): return True

    return False

def create_task(row):
    task = frappe.get_doc({
        'doctype':'Task',
        'project':get_erp_projectname(row['strProjectNo']),
        'subject':row['strDesignation'],
        'by_effort':row['bForInvoice'],
        'item_code': get_item_code_for_task(row['decHourlyRate']),
        "company" : get_company_by_project_name(get_erp_projectname(row['strProjectNo'])),
        "status" : "Open" if 'tinState' in row.keys() and row['tinState'] == 1 else "Completed"
    })
    print(task.as_dict())
    task.insert()
    frappe.db.commit()
    return task


def get_item_code_for_task(rate):
    if(rate == 135.0): 
        return 'ENG-SW'
    if(rate == 95.0): 
        return 'ENG-CAD'
    if(rate == 145.0):
        return 'ENG-PL'

    return 'ENG-RS'
    

def create_project(con,projectname):
    # get project from timesafe
    cursor = con.cursor(as_dict=True)
    sql = 'SELECT tProjects.*, tOrganizations.strClientNo as orgclientno, ContactOrg.strClientNo as contactclientno, tContacts.* FROM  [tProjects] LEFT JOIN [tOrganizations] ON tProjects.lOrganizationID = tOrganizations.lOrganizationID LEFT JOIN [tContacts] ON tProjects.lContactID = tContacts.lContactID LEFT JOIN [tOrganizations] AS ContactOrg ON tContacts.lOrganizationID = ContactOrg.lOrganizationID WHERE strProjectNo = \'' + str(projectname) + '\''
    cursor.execute(sql)
    project = cursor.fetchone()
    client = project['orgclientno'] 
    if client == None:
        client = project['contactclientno']


    projectcursor = con.cursor(as_dict=True)
    projectcursor.execute('SELECT * From tProjects WHERE strProjectNo LIKE ' + projectname)

    if projectcursor.rowcount > 1:
        print("Error more then one project found")
    else:  
        for row in projectcursor:
            # create project 
            new_project_data = {
                "doctype": "Project",
                "project_key": projectname,
                "project_name": get_erp_projectname(projectname),
                "project_type": "Project" if str(row['tinState']).startswith('3') or str(row['tinState']).startswith('5') else "Service",
                "is_active": "Yes",
                "status": "Open" if 'tinState' in row.keys() and row['tinState'] == 1 else "Completed",
                "title": get_erp_projectname(projectname) + " " + row['strProjectName'],
                "company" : get_company_by_project_name(get_erp_projectname(projectname))
            }
            if (row['dtStart'] != None):
                new_project_data['expected_start_date'] = row['dtStart']
            if (row['dtEnd'] != None):
                new_project_data['expected_end_date'] = row['dtEnd']
            if client != None:
                new_project_data['customer'] = "K-" + client

            # Add Teammember
            teammembers = get_team_member(con,row['lProjectID'])
            if len(teammembers) > 0:
                new_project_data['project_team'] = []
                for item in teammembers:
                    new_project_data['project_team'].append(item.as_dict())
            
            print("Insert project " + new_project_data['title'])
            new_project = frappe.get_doc(new_project_data)
            new_project.insert()
            return new_project
    

def get_team_member(con,projectid):
    # get project from timesafe
    membercursor = con.cursor(as_dict=True)
    membercursor.execute('SELECT tEmployees.lEmployeeID, tProjectTeam.bProjectLeader, tEmployees.strLogin, tEmployees.strLastName, tEmployees.strFirstName FROM tEmployees LEFT OUTER JOIN tProjectTeam ON tEmployees.lEmployeeID = tProjectTeam.lEmployeeID WHERE tProjectTeam.lProjectID = ' + str(projectid))

    members = []
    for meb in membercursor:
        print("Check team member " + str(meb["lEmployeeID"]))
        user = get_user(meb["lEmployeeID"])
        if user != 0:
            print("Add team member " + user)
            member = frappe.get_doc({
                "doctype": "Project Member",
                "employee": user,
                "project_manager": 0 if meb['bProjectLeader'] == 0 else 1
            })
            members.append(member)
    
    return members


def get_user(employee_nr):
    userid = frappe.get_all("Employee",filters={"employee_number":employee_nr})
    if len(userid) == 1:
        user = frappe.get_doc("Employee",userid[0])
        return user.employee
    return 0

def get_company_by_user(employee_nr):
    userid = frappe.get_all("Employee",filters={"employee_number":employee_nr})
    if len(userid) == 1:
        user = frappe.get_doc("Employee",userid[0])
        return user.company
    return "Innomat-Automation AG"

def get_company_by_project_name(projectname):
    if str(projectname).startswith("A"): return "Asprotec AG"
    return "Innomat-Automation AG"

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

    if(str(key).startswith("21")):
        company_key = "ASP"

    return "{0}{1}".format(company_key, key)


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

        print("Check {0}{1}".format(company_key, key))
        doc = frappe.db.exists("Project","{0}{1}".format(company_key, key))
        if(doc == None):
            print("Create {0}{1}".format(company_key, key))
            # create project 
            new_project = frappe.get_doc({
                "doctype": "Project",
                "project_key": key,
                "project_name": "{0}{1}".format(company_key, key),
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

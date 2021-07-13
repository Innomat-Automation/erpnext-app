# Copyright (c) 2019-2021, Asprotec AG and contributors
# For license information, please see license.txt
# functions for migration from old systems


import frappe
from frappe.exceptions import TemplateNotFoundError
from datetime import datetime, time, timedelta
import pymssql
import os
from frappe.utils import get_site_name
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
    taskcursor.execute('SELECT [strProjectNo],[strDesignation],[bForInvoice],[decHourlyRate],[tinState] FROM [TimesafeBack].[dbo].[ViewActivities] GROUP BY [strProjectNo],[strDesignation],[bForInvoice],[decHourlyRate],[tinState]')

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
    timecursor.execute('SELECT [strProjectNo],[tinState],[strLogin],[strDesignation],[bForInvoice],[Duration],convert(date,[dtFrom],23) as dtFrom,[decHourlyRate],[lEmployeeID],[lInvoiceID] FROM [TimesafeBack].[dbo].[ViewActivities] ORDER BY [dtFrom],[strLogin]')

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
    frappe.db.sql("UPDATE `tabTimesheet Detail` SET `by_effort` = 0,`billable` = 0 WHERE `billable` = 1;")
    frappe.db.commit()
    con.close()

def migrate_timesheet_text(user,password):
    con = get_connection(user,password)
    #create all timesheets
    timecursor = con.cursor(as_dict=True)
    timecursor.execute('SELECT [strProjectNo],[tinState],[strLogin],[strDesignation],[bForInvoice],[Duration],convert(date,[dtFrom],23) as dtFrom,[decHourlyRate],[lEmployeeID],[lInvoiceID],[strRemarks],[strIntRemarks] FROM [TimesafeBack].[dbo].[ViewActivities] ORDER BY [dtFrom],[strLogin]')
    count = 0
    for row in timecursor:
        if check_special_project(row['strProjectNo']):
            continue

        user = get_user(row['lEmployeeID'])

        if user == 0:
            continue

        timedata = frappe.db.sql("""SELECT detail.`name` FROM `tabTimesheet Detail` as detail
                         LEFT JOIN `tabTimesheet` As sheet ON detail.parent = sheet.name 
                         WHERE Date(detail.from_time) = "{dt_from}"
                         AND detail.`project` = "{project}"
                         AND sheet.`employee` = "{employee}"
                         AND detail .hours = {hours}
                         AND detail.docstatus = 1"""
                         .format(dt_from=row['dtFrom'],project=get_erp_projectname(row['strProjectNo']),employee=user,hours=row['Duration']),as_dict = True)
        
        if len(timedata) == 1 :
            internal = str(row['strIntRemarks']).replace("\"","'")
            external = str(row['strRemarks']).replace("\"","'")
            if internal == "None":
                internal = ""
            if external == "None":
                external = ""
            frappe.db.sql("""UPDATE `tabTimesheet Detail` SET `internal_remarks` = "{int}",`external_remarks` = "{ext}" 
                             WHERE `name` = '{name}';  """.format(int=internal,ext=external,name=timedata[0].name))
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
                                        'billable': 0 if row['bForInvoice'] and not row['lInvoiceID'] else 1,
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


def migrate_invoice(user,password):
    con = get_connection(user,password);
    errorlist = []
    cursor = con.cursor(as_dict=True)
    cursor.execute('SELECT * From InvoiceData')

    for row in cursor:
        invoice = create_invoice(row,errorlist)
        if invoice != None:
            print(invoice.as_dict())
            get_invoice_pdf(row,invoice,errorlist)
    
    print(errorlist)
    frappe.db.commit()


def create_invoice(row, errorlist):

    client = row['orgclientno'] 
    if client == None:
        client = row['contactclientno']

    if client == None:
        errorlist.append("Error Client not found : " + str(row['lInvoiceNo']))
        return;
    invoicedatetime = row['dtPerDate']
    payterm = timedelta(days = row['lTermOfPayment'])
    duedate = invoicedatetime.__add__(payterm)
    sales_item_group = "Migration";

    project = None
    doc = frappe.db.exists({'doctype' : "Project","project_key": row['strProjectNo']})
        # if project not extist continue
    if doc != ():
        project = get_erp_projectname(row['strProjectNo'])

    invoice = frappe.get_doc({'doctype' : 'Sales Invoice',
               'company' : get_company_with_reportdefinition(row['lInvoiceRptDefinitionID']),
               'customer' : "K-" + client,
               'posting_date' : invoicedatetime.date(),
               'posting_time' : invoicedatetime.time(),
               'set_posting_time' : 1,
               'due_date' : invoicedatetime.date().__add__(timedelta(30)) if duedate == None else duedate.date(),
               'project' : project,
               'po_no' : row['bestellreferenz'],
               'po_date' : '' if row['bestelldatum'] == None else row['bestelldatum'].date(),
               'currency' : get_currency_with_reportdefinition(row['lInvoiceRptDefinitionID']),
               'selling_price_list' : 'Verkauf Normal',
               'taxes_and_charges' : get_taxes(row['lInvoiceRptDefinitionID'])
              })

    tax_template = frappe.get_doc('Sales Taxes and Charges Template', get_taxes(row['lInvoiceRptDefinitionID']))
    if tax_template != None:
        invoice.taxes = tax_template.taxes

    row = invoice.append('items', {
        'item_code' : 'MIG-PAUSCHAL',
        'item_name' : 'Betrag aus Migration',
        'qty' : 1,
        'description': 'Timesafe Migration Rechnung {0}'.format(row['lInvoiceNo']),
        'rate' :  calculate_amount(row['decAmount'],row['lInvoiceRptDefinitionID'] != 3),
        'uom' : 'Stk',
        'price_list_rate' : 0.0,
        'sales_item_group': sales_item_group,
        'cost_center': get_cost_center(row['lInvoiceRptDefinitionID'] )
    })
    # create sales invoice
    row = invoice.append('sales_item_groups', {
            'group': sales_item_group, 
            'title': sales_item_group, 
            'sum_caption': 'Summe {0}'.format(sales_item_group)})
    print(invoice.as_dict())
    invoice.save()
    invoice.submit()

    return invoice

def get_invoice_pdf(row,invoice, errorlist):
    filename = get_site_name(frappe.local.site) + '/private/files/' + row['dateiname']
    print(filename)
    if os.path.exists(filename):
        new_file = frappe.get_doc({"doctype": "File",
                               "file_name": row['dateiname'],
                               "attached_to_doctype": "Sales Invoice",
                               "attached_to_name": invoice.name,
                               "attached_to_field": None,
                               "file_url": '/private/files/' + row['dateiname'],
                               "file_size": os.stat(filename).st_size,
                               "is_private": 1}).insert()
        print(new_file.as_dict())


def get_company_with_reportdefinition(id):
    if id == 4: return "Innomat-Automation AG"
    else: return "Asprotec AG"

def get_cost_center(id):
    if id == 4: return "Haupt - I"
    else: return "Main - A"

def get_currency_with_reportdefinition(id):
    if id == 3: return "EUR"
    else: return "CHF"

def get_taxes(id):
    if id == 3: return "Export - A"
    if id == 4: return "MwSt CH (302) - I"
    else: return "MwSt CH (302) - A"

def calculate_amount(amount,mwst = True):
    if mwst == False: return float(amount)
    else: return round_to_05(float(amount) / 1.077)

def round_to(n, precision):
    correction = 0.5 if n >= 0 else -0.5
    return int( n/precision+correction ) * precision

def round_to_05(n):
    return round_to(n, 0.05)

def get_connection(user,password):
    return pymssql.connect("192.168.80.25\Timesafe",user,password,"TimesafeBack")

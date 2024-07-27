#########################################################################################
#  Description: 
#  Developer:   Omprakash Tiwari(omprakash.tiwari@wipro.com)
#  Version:     1.0.0
#  Orgnization: Wipro Ltd
#########################################################################################

from ansible.module_utils.basic import AnsibleModule
import paramiko
import pymssql
import time
import socket
import re
import sys
from datetime import datetime

#####INPUT PARAMETERS#######################################################################
module = AnsibleModule(
    argument_spec={
        "db_host": {"required": True, "type": "str"},
        "db_name": {"required": True, "type": "str"},
        "username": {"required": True, "type": "str"},
        "password": {"required": True, "type": "str"},
        "incidentNo": {"required": True, "type": "str"},
        "startTime": {"required": False, "type": "str"},
        "jobID": {"required": False, "type": "str"},
        "templateName": {"required": False, "type": "str"},
        "AutomationState": {"required": False, "type": "str"},
        "EndTime": {"required": False, "type": "str"},
    }
)

db_host = module.params["db_host"]
db_name = module.params["db_name"]
uname = module.params["username"]
passwd = module.params["password"]
startTime = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
incidentNo = module.params["incidentNo"]
jobID = module.params["jobID"]
templateName = module.params["templateName"]
AutomationState = module.params["AutomationState"]
EndTime = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

response=f"{db_host}\n{db_name}\n{uname}\n{passwd}\n{startTime}\n{templateName}\n{jobID}\n{AutomationState}"

# ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
try:
    conn= pymssql.connect(db_host,uname,passwd,db_name)
    cursor= conn.cursor()
    if(jobID != None) and (templateName != None):
        cursor.execute(f"update Incident set JobID= '{jobID}', TemplateName= '{templateName}', StartTime='{startTime}' where IncidentNo= '{incidentNo}'")
        conn.commit()
        response= "jobID, template_name and startTime updated sucessfully back to db."
    elif(AutomationState != None):
        cursor.execute(f"update Incident set AutomationStatus= '{AutomationState}', EndTime='{EndTime}' where IncidentNo= '{incidentNo}'")
        conn.commit()
        response= "Automation state and EndTime updated sucessfully back to db."
    # if('INSERT' in query[0] or 'insert' in query[0]):
    #     conn.commit()
    #     response= "Incidents has been pushed to the database successfully." #cursor.fetchall() 
    # elif('SELECT' in query[0] or 'select' in query[0]):
    #     response=cursor.fetchall()
    module.exit_json(changed=True, result=response)
except Exception as e:
    failed_msg= (f"Failed to update the details to db, error: {e}")
    module.fail_json(changed=False, msg=failed_msg)

finally:
    conn.close()
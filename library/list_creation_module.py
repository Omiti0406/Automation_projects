from ansible.module_utils.basic import AnsibleModule

import re
import pandas as pd
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from email.mime.text import MIMEText


#####INPUT PARAMETERS#######################################################################
module = AnsibleModule(
    argument_spec={
        "staskNo": {"required": True, "type": "str"},
        "description": {"required": True, "type": "list"}
    }
)

sctask_No = module.params["staskNo"]
description_value = module.params["description"]
description_value  = "\n".join(description_value)


EMAIL_SERVER = 'appmail.ntrs.com'
SUBJECT = sctask_No + " Listserv New List Creation"
EMAIL_FROM = 'List_Messaging@ntrs.com'
EMAIL_TO = 'LISTSERV@LISTS.NTRs.com'
rcpt = [EMAIL_TO]
msg = MIMEMultipart()
msg['Subject'] = SUBJECT 
msg['From'] = EMAIL_FROM
msg['To'] = EMAIL_TO
server = smtplib.SMTP(EMAIL_SERVER)
response = ""


try:
    description_value = re.sub("Pw=(.*)", "PW=NORTHERN", description_value, flags=re.IGNORECASE)
    
    listServCreationCodes = []
    countIndex = -1
    for line in [line for line in description_value.split("\n") if line.startswith("PUT") or line.startswith("*")]:
        if str(line).startswith("PUT"):
            countIndex += 1
            listServCreationCodes.append("") 
        listServCreationCodes[countIndex] = listServCreationCodes[countIndex] + str(line) + "\n"
        
        
    if listServCreationCodes:
        for listServCreationCode in listServCreationCodes:
            try:
                Body = listServCreationCode
                Body = MIMEText(Body)
                msg.attach(Body)
                server.sendmail(EMAIL_FROM, rcpt, msg.as_string())
                response = response + "\nSucceess Email sent to LISTSERV@LISTS.NTRs.com with Following details for list creation\n"
                response = response + listServCreationCode
            except Exception as e:
                response = response + "Exception: " + str(e)
                response = response +"\nFailure Unable to send email to LISTSERV@LISTS.NTRs.com with Following details for list creation\n"
                response = response +listServCreationCode
    else:
        response = response +"\nUnable to read List description code for new list creation"
except Exception as e:
    response = response + "\nFailure Unable to send email to LISTSERV@LISTS.NTRs.com for list creation\n"
    response = response + "Exception: " + str(e)

    #print(response)
    
module.exit_json(changed=True, result=response)	

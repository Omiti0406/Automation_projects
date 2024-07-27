#######################################################################################################
#!/usr/bin/python
# -*- coding: utf-8 -*-
#author			:Anas khan
#version		:0.1        
#title			:Listserv_Emailsend_ListCreation
#usage			:python Listserv_Emailsend_ListCreation.py
#description	: This is .

import re
import pandas as pd
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from email.mime.text import MIMEText


itsm_dict = Input_Data

EMAIL_SERVER = 'appmail.ntrs.com'
SUBJECT = itsm_dict["stask_num"]+" Listserv New List Creation"
EMAIL_FROM = 'List_Messaging@ntrs.com'
EMAIL_TO = 'LISTSERV@LISTS.NTRs.com'
rcpt = [EMAIL_TO]
msg = MIMEMultipart()
msg['Subject'] = SUBJECT 
msg['From'] = EMAIL_FROM
msg['To'] = EMAIL_TO
server = smtplib.SMTP(EMAIL_SERVER)


description = """Input_Description"""
try:
    description = re.sub("Pw=(.*)", "PW=NORTHERN", description, flags=re.IGNORECASE)
    
    listServCreationCodes = []
    countIndex = -1
    for line in [line for line in description.split("\n") if line.startswith("PUT") or line.startswith("*")]:
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
                print("\nSucceess Email sent to LISTSERV@LISTS.NTRs.com with Following details for list creation\n")
                print(listServCreationCode)
            except Exception as e:
                print("\nFailure Unable to send email to LISTSERV@LISTS.NTRs.com with Following details for list creation\n")
                print(listServCreationCode)
    else:
        print("\nUnable to read List description code for new list creation")
except Exception as e:
    print("\nFailure Unable to send email to LISTSERV@LISTS.NTRs.com for list creation\n")

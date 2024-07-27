#########################################################################################
#  Description: 
#  Developer:   Omprakash Tiwari(omprakash.tiwari@wipro.com)
#  Version:     1.0.0
#  Orgnization: Wipro Ltd
#########################################################################################

from ansible.module_utils.basic import AnsibleModule
import paramiko
import pymssql
import requests
import json
import threading
from requests.packages.urllib3.exceptions import InsecureRequestWarning
import time
import datetime
import traceback
import socket
import re
import sys
from datetime import date

#####INPUT PARAMETERS#######################################################################
db_host = sys.argv[1] 
db_name = sys.argv[2] 
uname = sys.argv[3] 
passwd = sys.argv[4] 
awx_user = sys.argv[5] 
awx_pass = sys.argv[6] 
awx_instance = sys.argv[7]   #"awx-dev.wrkld-awx-1-system-1.k8s.ntrs.com"
query_fetch_parser= "select * from bots_parser_mapping"
lock=threading.Lock()
# query_fetch_incidents = "select * from Incident where IncidentNo = 'INC007505899'"
query_fetch_incidents = f"""SELECT top(10)
                                IncidentNo,
                                templateID,
                                TargetHost,
                                AssignmentGroup,
                                OpenedBy,
                                Description,
                                ShortDescription,
                                CreationDate,
                                AutomationStatus
                            FROM
                                Incident
                            WHERE
                                AutomationStatus='Queued'
                            """
# WHERE     
#    templateID= '9' and AssignmentGroup = 'DCTS-Unix Prod Support' and
# WHERE
#      TargetHost != 'None' and AutomationStatus = 'Queued'
try:
    def trigger_action_bots(inc_data, awx_instance):
        retries=0
        conn= pymssql.connect(db_host,uname,passwd,db_name)
        cursor= conn.cursor(as_dict=True)
        thread_id = threading.current_thread().ident
        for incident in inc_data:
            try:
                time.sleep(0.5)
                if(incident['TargetHost'] != 'None'):  #(incident['TargetHost'] != None) or 
                    incident['CreationDate'] = str(incident['CreationDate'])
                    incident['templateID'] = str(incident['templateID'])  
                    # print(incident)
                    url = f"http://{awx_instance}/api/v2/job_templates/{incident['templateID']}/launch/"
                    # url = f"{awx_instance}/api/v2/job_templates/76/launch/"
                    ticketDetails= json.dumps(incident)
                    # print(ticketDetails)
                    # print("after serialization: ", type(ticketDetails))
                    payload = json.dumps({ 
                        "extra_vars": {
                            "ticket": ticketDetails
                            }
                        })

                    # print(payload)
                    headers = {
                        'Content-Type': 'application/json'
                    
                    }
                    # requests.packages.urllib3.disable_warnings(InsecureRequestWarning)
                    resp = requests.request("POST",url, 
                                            headers=headers, 
                                            data=payload,
                                            auth=(awx_user, awx_pass), 
                                            verify=False)
                    retries += 1
                    # response= resp.json()
                    if(resp.status_code == 200) or (resp.status_code == 201):
                        # lock.acquire()
                        print(f"{incident['IncidentNo']} : Job launched, {resp.status_code}, {resp.reason} - {thread_id}")
                        cursor.execute(f"update Incident set AutomationStatus='Triggered', Remarks= 'API status: {resp.status_code}, {resp.reason}' where IncidentNo= '{incident['IncidentNo']}'")   # fetching incidents
                        conn.commit()
                        # lock.release()
                    else:
                        while(retries<=3):
                            # time.sleep(2)
                            print(f"Rrtries {incident['IncidentNo']}: {retries}")
                            resp = requests.request("POST",url, 
                                            headers=headers, 
                                            data=payload,
                                            auth=(awx_user, awx_pass), 
                                            verify=False)
                            if(resp.status_code == 200) or (resp.status_code == 201):
                                # lock.acquire()
                                print(f"{incident['IncidentNo']} : Job launched, {resp.status_code}, {resp.reason} - {thread_id}")
                                cursor.execute(f"update Incident set AutomationStatus='Triggered', Remarks= 'API status: {resp.status_code}, {resp.reason}' where IncidentNo= '{incident['IncidentNo']}'")   # fetching incidents
                                conn.commit()
                                break 
                            retries+=1
                        retries=0
                        # lock.acquire()
                        print(f"{incident['IncidentNo']}- Failed to launch job, API status: {resp.status_code}, {resp.reason}")
                        cursor.execute(f"update Incident set AutomationStatus='FAILED', Remarks= 'API status: {resp.status_code}, {resp.reason}' where IncidentNo= '{incident['IncidentNo']}'")   # fetching incidents
                        conn.commit()
                        # lock.release()
                                
                else:
                    # lock.acquire()
                    print(f"Unable to launch job for {incident['IncidentNo']}, incindent has no Target host.")
                    cursor.execute(f"update Incident set AutomationStatus='FAILED', Remarks= 'No target host on the ticket.' where IncidentNo= '{incident['IncidentNo']}'")   # fetching incidents
                    conn.commit()
                    # lock.release()
            except Exception as e:
                # lock.acquire()
                print(f"Error occured: Unable to trigger solution for {incident['IncidentNo']}, {e}")
                cursor.execute(f"update Incident set AutomationStatus= 'FAILED', Remarks= '{e}' where IncidentNo= '{incident['IncidentNo']}'")   # fetching incidents
                conn.commit()
                # lock.release()
                traceback.print_exc()
        # print(f"total launched: {count} - {thread_id}")
        conn.close()

    #########creating database connection
    conn= pymssql.connect(db_host,uname,passwd,db_name)
    cursor= conn.cursor(as_dict=True)
    cursor.execute(query_fetch_parser)      # fetching mapping inputs 
    mappings= cursor.fetchall()
    # print(f"parser: {mappings}")
    cursor.execute(query_fetch_incidents)   # fetching incidents
    inc_data= cursor.fetchall()
    conn.close()
    print(f"ticket count: {len(inc_data)}")
    # print(f"fetched data: {type(inc_data[0])}")
    if(len(inc_data) > 0):
        if(len(inc_data)<30):
            trigger_action_bots(inc_data, awx_instance)
        ### breaking down the fetched incidents into smaller batches
        else:
            batchSize=len(inc_data)//30
            inc_batches=[inc_data[i:i+batchSize] for i in range(0,len(inc_data), batchSize)]
            threads=[]
            start = time.perf_counter()
            for inc_lot in inc_batches:
                # print(f"length: {len(inc_lot)}")
                thread=threading.Thread(target=trigger_action_bots, args=(inc_lot, awx_instance))
                thread.start()
                threads.append(thread)
            for t in threads:
                t.join()
            end = time.perf_counter()
            print(f'Time taken = {round(end-start)} Sec.')
        
    else:
        print("No tickets found.")

except Exception as e:
    failed_msg= (f"Error: {e}")
    print(failed_msg)
    traceback.print_exc()
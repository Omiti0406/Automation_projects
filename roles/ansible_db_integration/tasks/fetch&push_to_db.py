#########################################################################################
#  Description: 
#  Developer:   Omprakash Tiwari(omprakash.tiwari@wipro.com)
#  Version:     1.0.0
#  Orgnization: Wipro Ltd
#########################################################################################

# from ansible.module_utils.basic import AnsibleModule
import pymssql
import time
import traceback
import requests
import json
import re
import sys
from datetime import date

#####INPUT PARAMETERS#######################################################################

db_host = sys.argv[1] 
db_name = sys.argv[2] 
uname = sys.argv[3] 
passwd = sys.argv[4] 
query_fetch_parser= "select * from bots_parser_mapping where bot_state = 'ENABLED'"
snow_instance = sys.argv[5] 
snow_username = sys.argv[6] 
snow_pass = sys.argv[7] 
snow_query= f"https://{snow_instance}.service-now.com/api/now/table/incident?sysparm_query="
try:
    conn= pymssql.connect(db_host,uname,passwd,db_name)
    print(f"Connecting to database {conn}")
    cursor= conn.cursor(as_dict=True)
    cursor.execute(query_fetch_parser)
    parsing_data= cursor.fetchall()
    print(f"Fetching solutions mapping data.")
    # print(f"parsing data: {parsing_data}")
            
    #### merging each mappings to single sysparm query ####
    try:
        for data in parsing_data:
            # if(data['bot_state']=="ENABLED"):
            assignmentGroup= data['assignmentGroup']
            assignmentGroup= assignmentGroup.replace(' ','%20')
            parsing_keywords= data['parsingKey'].split(",")
            parsing_keywords_final="descriptionLIKE"
            temp_sys_query= f"active=true^caller_id.user_nameINsys-il-moo-snow-p,EventMgmt^assignment_group.nameIN{assignmentGroup}"
            for keyword in parsing_keywords:
                if(parsing_keywords_final == "descriptionLIKE"):
                    parsing_keywords_final=parsing_keywords_final+str(keyword.replace(' ','%20'))
                else:
                    parsing_keywords_final=f"{parsing_keywords_final}^ORdescriptionLIKE{keyword.replace(' ','%20')}"
            # print("keys: ",parsing_keywords_final)
            temp_sys_query= f"{temp_sys_query}^{parsing_keywords_final}^state=1^ORDERBYDESCsys_created_on"
            # print(f"\n\n query: {temp_sys_query}")
            if(snow_query.endswith('sysparm_query=')):
                snow_query= f"{snow_query}{temp_sys_query}"
            else:
                snow_query= f"{snow_query}^NQ{temp_sys_query}"
        
        snow_query=f"{snow_query}&sysparm_order=sys_created_on&sysparm_fields=number%2Cstate%2Ccmdb_ci%2Cdescription%2Cshort_description%2Cassignment_group%2Csys_created_by%2Csys_created_on&sysparm_order_direction=dec&sysparm_limit=100&sysparm_display_value=true"
        print(f"snow query generated: {snow_query}")
    except Exception as e:
        print(f"Error: unable to generating snow query, {e}")

    ##### calling the servicenow API to fetch the relevant incidents
    try:
        final_url= snow_query
        headers = {
            'Accept' : 'application/json',
            'Content-Type' : 'application/json'
            }

        response = requests.request("GET", 
                                    final_url, 
                                    headers=headers, 
                                    auth=(snow_username,snow_pass))
                                    # verify=False)
        resp= response.json()
        # print(f"tickets: {resp}")
        if(response.status_code == 200):
            print(f"snow API response: {response.status_code}")
            if(len(resp['result'])>0):
                try:
                    data_to_insert = ""
                    for data in resp['result']:
                        if(data['cmdb_ci']== '') or (data['cmdb_ci']== None):
                            data['cmdb_ci']= {'display_value':None}
                        if(data_to_insert == ""):
                            for mapping in parsing_data:
                                parsingKeys= mapping['parsingKey'].split(",")
                                for parsing_key in parsingKeys:
                                    if(parsing_key in data['description']):
                                        data_to_insert = f"('{data['number']}','{mapping['templateID']}','{data['cmdb_ci']['display_value']}','{data['assignment_group']['display_value']}','{data['sys_created_by']}','{data['description']}','{data['short_description']}','Queued','{data['sys_created_on']}')"
                                        break
                        else:
                            for mapping in parsing_data:
                                parsingKeys= mapping['parsingKey'].split(",")
                                for parsing_key in parsingKeys:
                                    if(parsing_key in data['description']):
                                        data_to_insert = f"{data_to_insert},('{data['number']}','{mapping['templateID']}','{data['cmdb_ci']['display_value']}','{data['assignment_group']['display_value']}','{data['sys_created_by']}','{data['description']}','{data['short_description']}','Queued','{data['sys_created_on']}')"
                                        break
                    # sql_query = f"{sql_query}{data_to_insert}"
                    sql_query = f"""INSERT INTO
                                        Staging_Incident (
                                            IncidentNo,
                                            templateID,
                                            TargetHost,
                                            AssignmentGroup,
                                            OpenedBy,
                                            Description,
                                            ShortDescription,
                                            AutomationStatus,
                                            CreationDate
                                        )
                                    VALUES
                                        {data_to_insert}
                                    INSERT INTO
                                        Incident
                                    SELECT
                                        s.*
                                    FROM
                                        Staging_Incident s
                                        LEFT JOIN Incident t ON s.IncidentNo = t.IncidentNo
                                    WHERE
                                        t.IncidentNo IS NULL
                                    delete from
                                        Staging_Incident"""
                    # print(f"sql_query: {sql_query}")
                # try:
                    cursor.execute(sql_query)
                    conn.commit()
                    print("Fetched tickets has been successfully pushed to the database.")
                except Exception as e:
                    print(f"Error: Unable to push fetched tickets to database. {e}")
                    traceback.print_exc()
                    sys.exit()
            else:
                print("No tickets found.")
                sys.exit()
        else:
            print(f"Error occured API call failed.\n{response.status_code}\n{response.reason}")
            sys.exit()

    except Exception as e:
        print(f'Error: REST API call failed, unable to fetch tickets from ServiceNow. {e}')
        traceback.print_exc()
        sys.exit()
except Exception as e:
    failed_msg= (f"Exception: Unable to connect to Database. Error: {e}")
    print(f"{failed_msg}")
    traceback.print_exc()

finally:
    conn.close()

import requests
from bs4 import BeautifulSoup
import json
import xml.etree.ElementTree as ET
import logging
import datetime
import csv
import pandas as pd

def WDB_Metering(start_script_time, end_script_time, status):
    '''    :param start_script_time: add execution Start time of the script to start of main function

           :param end_script_time: add execution end time of the script to end of main function

           :param status: Script status (FAILED or SUCCESS in try and catch of main function)

           :return: updates CSV File with execution timestamp'''

    try:

        usecase = "Unimax_User_Onboarding"  # <Add usecase name >
        execution_type = "One touch"  # <Add execution type>
        list1 = [usecase, execution_type,
                 start_script_time, end_script_time, status]
        f = open(r"\\WPCHOLU01\OnTouch_solutions_WDB_logs\Unixmax_user_onboarding\WDB_logs.csv", "a")
        writer = csv.writer(f, lineterminator='\n')
        writer.writerow(list1)

    except Exception as e:
        raise Exception(
            "Something went wrong in WDB Metering function, check filepath and input parameters")


try:
    logging.basicConfig(filename=r'\\WPCHOLU01\Unixmax_user_onboarding\Logs\Unimax_onboarding.log', filemode='a',
                        format='%(asctime)s - %(levelname)s - %(message)s')
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    logger.info("**********************Onboard User through Unimax*********************")
    start_time = '{:%Y.%m.%d-%H.%M.%S}'.format(datetime.datetime.now())
    execution_status = ""
	#################user_details#######
    lan_id = "R_LAN_ID"   #Will be fetched from ServiceNow
    lan_id = lan_id.upper()
    SNLocationCode = "Input_Location" #Will be fetched from ServiceNow
    ticket_Number = "TicketNo" # will be fetched from ServiceNow
    req_Lan_ID= "RF_LAN_ID"
    work_notes_details = ""

    logger.info(f"Lan id is : {lan_id}")
    print(f"Lan id is : {lan_id}")
    logger.info(f"ServiceNow Location code is {SNLocationCode}")
    print(f"ServiceNow Location code is {SNLocationCode}")
    logger.info(f"Ticket Number is {ticket_Number}")
    print(f"Ticket Number is {ticket_Number}")
    work_notes_details += f"The onboarding is to be done for the Lan ID : {lan_id} \n"

    locationDict = {}
    onboard_item = {}
    onboard_details = {}
    workFlow_URI_dict = {}

    #####Fetching URI from the config file##############
    with open(r"\\WPCHOLU01\Unixmax_user_onboarding\url.txt", 'r') as f:
        fData = f.read()
    uri = fData.split("\n")[0]
    location_url = f"{uri}/2N/System/30/Number?columns=Number+SecondaryKey+Field2"

    #######Creating dictionary for Region and url for onboarding from config file#########
    csv_detail = pd.read_csv(r"\\WPCHOLU01\Unixmax_user_onboarding\workflow_url_details.csv")
    colRegion = csv_detail.Region
    colWorkflowUrl = csv_detail.Workflow_url
    colWorkId = csv_detail.WorkItem_id
    for i in range(len(colRegion)):
        workFlow_URI_dict[f"{colRegion[i]}"] = [f"{colWorkflowUrl[i]}",f"{colWorkId[i]}"]  # Mapping onboard api with region

    ####Fetching Location details from ServiceNow code #############
    acode = fData.split("\n")[1]
    location_headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Basic {acode}'
    }

    location_response = requests.request("GET", location_url, headers=location_headers)
    #print(location_response.text)
    if location_response.status_code != 200:
        print("Failed to fetch the location details")
        print('Status:', location_response.status_code)
        logger.error("Unable to fetch the response for the location")
        logger.error(location_response.status_code)
        logger.error(location_response.text)
        work_notes_details += f"Unable to fetch the work location from ServiceNow code : {SNLocationCode}. Please perform it manually and check the log files for the issue."
        exit()
    else:
        data = location_response.text
        #print(data)
        soup = BeautifulSoup(data, 'xml')
        recordData = soup.find_all('Record')
        for record in recordData:
            locationList = []
            #print(record)
            bs_data = str(record)
            if "<SecondaryKey/>" in bs_data:
                continue
            else:
                location = (bs_data.split('<SecondaryKey>')[1]).split('</SecondaryKey>')[0]
                region = (bs_data.split('<Field2>')[1]).split('</Field2>')[0]
                city = (bs_data.split('<Number>')[1]).split('</Number>')[0]
                #print(location)
                #print(region)
                #print(city)
                locationList.append(region)
                locationList.append(city)
                locationDict[location] = locationList
        #print(locationDict)
    country = locationDict[SNLocationCode][0]
    print(f"Region is : {country}")
    logger.info(f"Region is : {country}")
    work_location = locationDict[SNLocationCode][1]
    print(f"Work Location is : {work_location}")
    logger.info(f"Work Location is : {work_location}")
    work_notes_details += f"The work location is : {work_location}\n"
    work_notes_details += f"The Region is : {country}\n"

    #####Fetching onboarding URL and work item ID with Country code
    if country == "CA" or country == "IN" or country == "LU" or country == "CH":
        onboarding_url = workFlow_URI_dict[country][0]
        work_item_id = workFlow_URI_dict[country][1]
    else:
        onboarding_url = workFlow_URI_dict["default"][0]
        work_item_id = workFlow_URI_dict["default"][1]
    print(f"User Onboarding URL is : {onboarding_url}")
    print(f"Onboarding work item ID is : {work_item_id}")
    logger.info(f"User Onboarding URL is : {onboarding_url}")
    logger.info(f"Onboarding work item ID is : {work_item_id}")

    onboarding_headers = {
        'Content-Type': 'application/json',
        'Sn-Work-Ticket': f'{ticket_Number}',
        'Authorization': f'Basic {acode}'
    }
    payload = json.dumps({
        f'''{work_item_id}''': {
            "LAN ID*": f'''{lan_id}''',
            "Work Location": f'''{work_location}'''
        }
    })

    #print(payload)
    logger.info(f"Onboarding Payload is : {payload}")

    #####Block for onboarding the user and fetching the details from it
    onboarding_response = requests.request("POST", onboarding_url, headers=onboarding_headers, data=payload)
    #print(onboarding_response.text)
    if onboarding_response.status_code != 201:
        print('Status:', onboarding_response.status_code)
        logger.error("Failed to onboard user")
        fail_data = onboarding_response.text
        soup = BeautifulSoup(fail_data, 'xml')
        f_recordData = soup.find_all('Details')
        fail_recordData = str(f_recordData[0])
        error_msg = (fail_recordData.split("<Details>"))[1].split("</Details>")[0] ######fetching the error message
        print(error_msg)
        logger.error(f"{error_msg} ")
        execution_status = "Failed"
        work_notes_details += f"Failed to perform onbaording operation.\n"
        work_notes_details += f"The response status code is {onboarding_response.status_code} and the error message is {error_msg}"
        
    else:
        onboarding_data = onboarding_response.text
        execution_status = "Success"
        #print(onboarding_data)
        soup = BeautifulSoup(onboarding_data, 'xml')
        SN_project_uri = str(soup.find_all('Sn-Project-Uri'))
        SN_project_uri = (SN_project_uri.split('<Sn-Project-Uri>')[1]).split('</Sn-Project-Uri>')[0]
        #print(SN_project_uri)
        logger.info(f"SN Project Uri is : {SN_project_uri}")
        SN_resource_uri = str(soup.find_all('Sn-Resource-Uri'))
        SN_resource_uri = (SN_resource_uri.split('<Sn-Resource-Uri>')[1]).split('</Sn-Resource-Uri>')[0]
        #print(SN_resource_uri)
        logger.info(f"SN Resource uri is : {SN_resource_uri}")
        tree = ET.fromstring(onboarding_data)
        results = tree.findall('ExtraInfo')
        res = (results[0]).findall('Item')
        #print(res)
        #####Block for fetching the details after user is onboarded
        for element in res:
            key = element.find("Key").text
            #print(key)
            value = element.find("Value").text
            #print(value)
            onboard_details[key] = value
            logger.info(f"Key is {key} and value is {value}")
        #print(onboard_details)
        dialupNumber = onboard_details['E.164 number']
        if len(dialupNumber.split("+")[1]) <= 15:
            print(f"Dialup Number is {dialupNumber}")
            logger.info(f"Dialup Number is {dialupNumber}")
        else:
            execution_status = "Failed"
            print("The length of Dialup Number is more than 15, please check manually",
                  f"{dialupNumber}")
            logger.info(f"The length of Dialup Number is more than 15, please check manually : {dialupNumber}")

        jabberNumber = onboard_details['Create Jabber Directory Number']
        if len(jabberNumber) == 7:
            print(f"Cisco Jabber Directory Number is {jabberNumber}")
            logger.info(f"Cisco Jabber Directory Number is {jabberNumber}")
        else:
            execution_status = "Failed"
            print("The length of the Cisco Jabber Directory Number is not 7, please check manually", f"{jabberNumber}")
            logger.info(
                f"The length of the Cisco Jabber Directory Number is not 7, please check manually : {jabberNumber}")
        if execution_status == "Success":
            work_notes_details += f"The dialup Number for the user {lan_id} is {dialupNumber}\n"
            work_notes_details += f"The CISCO Jabber Directory Number for the user {lan_id} is {jabberNumber}"
        else:
            work_notes_details += f"There is an issue with either DialupNumber or CISCO Jabber dierctory number. Please check the script logs for more details."
except Exception as e:
    execution_status = "Failed"
    print("Error occured: ", e)
    logger.error(f"Error Occured while excecution : {e} \n")
    work_notes_details += f"There is error while execution {e}. Please look into it manually"
finally:
    end_time = '{:%Y.%m.%d-%H.%M.%S}'.format(datetime.datetime.now()) 
    print(execution_status)
    WDB_Metering(start_time, end_time, execution_status)
    #print("Work Notes :", work_notes_details)
    logger.info("*****************************BOT Proccessing Ends***********************************\n")
    logging.shutdown()
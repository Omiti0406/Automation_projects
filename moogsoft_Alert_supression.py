
############################################################################################################################################
#
# -*- coding: utf-8 -*-
#Developer     :   Omprakash Tiwari
#version       :   1.0
#title         :   Moogsoft alert supression.py
#description   :   This script will create maintanence window for the requested servers in Moogsoft portal.
############################################################################################################################################


import requests
import csv
import datetime
import logging
import time
import traceback
import getpass

print("hellow")
logging.basicConfig(filename=r'.\Logs\Maintenace_WindowCreation.log', filemode='a',
                    format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger()
logger.setLevel(logging.INFO)
logger.info("**********************Welcome to the maintenace window creation*********************")
start_time='{:%Y.%m.%d-%H.%M.%S}'.format(datetime.datetime.now())
execution_status=""

def WDB_Metering(start_script_time, end_script_time, status):
    '''    :param start_script_time: add execution Start time of the script to start of main function

           :param end_script_time: add execution end time of the script to end of main function

           :param status: Script status (FAILED or SUCCESS in try and catch of main function)

           :return: updates CSV File with execution timestamp'''

    try:

        usecase = "Block Alerts in Moogsoft"  # <Add usecase name >
        execution_type = "One touch"  # <Add execution type>
        list1 = [usecase, execution_type,
                 start_script_time, end_script_time, status]
        f = open(r".\Logs\WDB_Logs.csv", "a")
        writer = csv.writer(f, lineterminator='\n')
        writer.writerow(list1)

    except Exception as e:
        raise Exception(
            "Something went wrong in WDB Metering function, check filepath and input parameters")

try:
    username =input("Enter your username: ") #'graze'
    password =getpass.getpass("Enter password: ") #'graze'
    inputFile = r".\Config\serverList.txt"
    main_srvList = []
    srvList = []
    duration_in_days = 31
    batch_size = 250
    date_format = '%Y-%m-%d %H:%M'

    #Reading API url
    with open(r".\Config\url.txt", 'r') as file:
            inputUrl = file.readline()
    inputUrl=inputUrl.replace('\n','')        
    url = inputUrl+"graze/v1/createMaintenanceWindow"

    logger.info(f"BOT Execution Time is : {datetime.datetime.now()}")
    input_WindowName = input("Enter the window Name : ")
    input_rp = input("Do you have a file path of server list? (Y/N)  :")
    if (input_rp == 'N') or (input_rp == 'n'):
        input_srv = input("Enter your server List(',' separated value) :")
        main_srvList = input_srv.split(",")
    else:
        with open(inputFile, 'r') as file:
            next_line = file.readline()
            while next_line:
                line = next_line.replace('\n', '')
                main_srvList.append(line.lower())
                next_line = file.readline()
    temp_srvList=[]
    for srv in main_srvList:
        if ("*.*") in srv or (".*") in srv or ("*") in srv or ("*?") in srv or ("?") in srv:
            continue
        else:
            temp_srvList.append(srv)
    main_srvList=temp_srvList
    input_ad = input("Do you want to disable alerts permanently (Y/N) : ")
    if (input_ad == 'N') or (input_ad == 'n'):
        input_date = input("Enter start date(YYYY-MM-DD hh:mm): ")
        input_EndDate = input("Enter End date(YYYY-MM-DD hh:mm): ")
        curr_Date = datetime.datetime.strptime(input_date, date_format)
        print(curr_Date)
        strt_epochTime = int(curr_Date.timestamp())
        end_Date = datetime.datetime.strptime(input_EndDate, date_format)
        print(end_Date)
        duration = int((end_Date - curr_Date).total_seconds())
        input_batchSize = input("Please provide batch size(by default it is 250) : ")
        if (input_batchSize != ""):
            batch_size = int(input_batchSize)
    elif (input_ad == 'Y') or (input_ad == 'y'):
        curr_Date = datetime.datetime.now()
        print(curr_Date)
        strt_epochTime = int(curr_Date.timestamp())
        end_Date = curr_Date + datetime.timedelta(days=duration_in_days)
        duration = int((end_Date - curr_Date).total_seconds())

    if (input_WindowName is None) or (input_WindowName == ""):
        # print("Inside No")
        if (input_ad == 'N') or (input_ad == 'n'):
            windowName = "Framed Maintenance Window "
        elif (input_ad == 'Y') or (input_ad == 'y'):
            windowName = "Decomissioning Window"
    else:
        windowName = input_WindowName
    # print(windowName)

    logger.info(f"Start time is {curr_Date}")
    logger.info(f"Duration in seconds {duration}")
    logger.info(f"End time is {end_Date}")
    logger.info(f"URL is: {url}")

    #Moogsoft API calling function to create the maintenance window
    def MoogsoftCall(url, username, password, source_str, windowName, strt_epochTime, duration):
        body = {
            'name': f"{windowName}",
            'description': f"{windowName}",
            'filter': f''' {source_str} ''',
            'start_date_time': f'''{strt_epochTime}''',
            'duration': f'''{duration}''',
            'forward_alerts': 'false'
        }
        #print(body)
        headers = {
            'Content-Type': 'application/json; charset=UTF-8',
        }
        response = requests.request("POST", url, auth=(username, password), headers=headers, json=body, verify=False)
        data = response.json()
        # print(response.text)
        if (response.status_code == 200):
            print("Maintenance windows for the requested servers has been created successfully.")
            print("Window ID: ", data['window_id'])
            logger.info("Maintenance windows for the requested servers has been created successfully.")
            logger.info(f" Window ID is : {data['window_id']} \n")
            execution_status="Success"

        else:
            print("Error: ", response.text)
            logger.error(f"Error occured In request's response : {response.text} \n")
            execution_status="Failed"

        return execution_status



    if (input_ad == 'Y') or (input_ad == 'y'):
        srvList_Lower = []
        srvList_Upper = []
        srvList_Lower = [x.lower() for x in main_srvList]
        srvList_Upper = [x.upper() for x in main_srvList]
        srvList_Lower.extend(srvList_Upper)
        srvList=srvList_Lower

        logger.info(f"Server List is {srvList}")
        logger.info(f"window Name is {windowName}")

        source_str = 'source in ('
        for i in srvList:
            source_str += '"' + i + '"' + ","
        source_str = source_str[:-1]
        source_str += ")"
        #print(source_str)
        execution_status= MoogsoftCall(url, username, password, source_str, windowName, strt_epochTime, duration)
    else:
        if (len(main_srvList) > 0):
            srvList_Upper = []
            srvList_Upper = [x.upper() for x in main_srvList]
            srvList_Lower = [x.lower() for x in main_srvList]

            main_srvList_len = len(main_srvList)
            batch_len = batch_size

            j = 0
            loop_count = 1
            name_counter = 1
            if(batch_size > main_srvList_len):
                num_batches = 1
            else:
                #added_list_len = len(srvList_Lower) + len(srvList_Upper)
                num_batches = main_srvList_len // batch_len + (main_srvList_len % batch_len > 0)
            while (loop_count <= num_batches):
                srvList = srvList_Lower[j:batch_len]
                #for srv in srvList_Upper[i:batch_len]:
                #    srvList.append(srv)
                srvList.extend(srvList_Upper[j:batch_len])
                #print("srv list:",srvList)
                if (name_counter != 1):
                    name_counter_str=name_counter
                    windowName_rev = windowName + "-" + str(name_counter_str)
                else:
                    windowName_rev=windowName

                logger.info(f"window Name is {windowName}")
                logger.info(f"Server List is {srvList}")

                # Source List prepration
                #print(srvList)
                source_str = 'source in ('
                for i in srvList:
                    source_str += '"' + i + '"' + ","
                source_str = source_str[:-1]
                source_str += ")"
                
                #print(source_str)
                if (len(source_str) <= 55000):
                    execution_status=MoogsoftCall(url, username, password, source_str, windowName_rev, strt_epochTime, duration)
                    print("sorce len ",len(source_str))
                else:
                    print("Check with developer to change batch length as the string size is more than 55K : ",len(source_str))
                    logger.error(f"Check with developer to change batch length as the string size is more than 55K ; {len(source_str)}")
                    logger.error(f"Batch length : {batch_len}")
                    execution_status="Failed"
                    break
                #print(type(name_counter))
                j += batch_size
                batch_len = batch_len + batch_size
                name_counter += 1
                loop_count += 1
                #print("j is ", j)
                #print("batch length is ", batch_len)
                #print("Loop count is", loop_count)
        else:
            execution_status="Failed"
            print("No data in the server List")
            logger.error(f"Data unavailable : Server List is empty")
    

except Exception as e:
    execution_status="Failed"
    print("Error occured: ", e)
    logger.error(f"Error Occured while excecution : {e} \n")
    traceback.print_exc()

finally:
    time.sleep(10)
    end_time='{:%Y.%m.%d-%H.%M.%S}'.format(datetime.datetime.now())
    WDB_Metering(start_time, end_time, execution_status)
    logger.info("*****************************BOT Proccessing Ends***********************************\n")
    logging.shutdown()

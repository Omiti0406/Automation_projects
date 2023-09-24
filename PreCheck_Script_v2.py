############################################################################################
#
#author        :   Omprakash Tiwari
#version       :   1.0
#title         :   PreCheck_script
#description   :   This script will run the health check for pre unix patching servers and generats the report(HTML and Excel). 

#######################################################################################################
import paramiko
import socket
import time
#import sys
import os
import re
import logging
import traceback
import threading
import datetime
import pandas as pd
#import glob
import getpass
import csv


#####INPUT PARAMETERS#######################################################################

username=input("Enter your username: ")
password=getpass.getpass("Enter your password: ")
########################################################
lock=threading.Lock()
shell = None
client = None
exit_code= None
srvIndexCount=successCount=failedCount=0
outputs=[]
curr_date= datetime.datetime.now()
date_time=curr_date.strftime("%d_%m_%y_%H_%M_%S")
failed_srv_header=['server','Error']
failed_srv_output=[]
host1 = []
srv_ty = []
dr_pr = []
os_v = []
lpat_de = []
pat_date = []
cpu=[]
mem1=[]
swap_mem=[]
pandora_sta = []
disk_uti=[]
sys_disk=[]
up_time=[]
load_avg=[]
nfs=[] 
tlaName=[]
console=[]
cluster=[]

#Log creation
logFile=f"./logs/PreCheck_log_{date_time}.log"
file_handler=logging.FileHandler(logFile,mode='a')
file_handler.setLevel(logging.INFO)
formatter= logging.Formatter('%(asctime)s - %(levelname)s - %(message)s') 
file_handler.setFormatter(formatter)
logger=logging.getLogger(__name__)
logger.setLevel(logging.INFO)
logger.addHandler(file_handler)
logger.info(f"\n*********************PRE CHECK LOGS {curr_date} *********************")

def login(hostname, username, password):
    global shell
    global client
    client = paramiko.SSHClient()
    try:
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect(hostname=hostname, username=username, password=password)
        shell = client.invoke_shell()
    except paramiko.AuthenticationException:
        raise Exception(
            "Authentication failed, please verify your credentials")
    except socket.error as e:
        raise Exception("Entered IP Address is wrong")
    except paramiko.BadHostKeyException as badHostKeyException:
        raise Exception("Unable to verify server's host key")
    except paramiko.SSHException as sshException:
        raise Exception("Unable to establish SSH connection")
    except Exception as ex:
        raise Exception("Something went wrong")
        
def execute_shell(command, sleeptime=3):
    
    
    command = command + "\n"
    shell.send(command)
    time.sleep(sleeptime)
    receive_buffer = shell.recv(9999).decode("utf-8")
    return receive_buffer
def exe_command(command,timeOut=30):
    try:
        global exit_code
        stdin,stdout,stderr=client.exec_command(command,timeOut)
        stdin.close()
        temp= stdout.readlines()
        result= temp
        exit_status= stdout.channel.recv_exit_status()
        if exit_status==0:
            exit_code= "SUCCESS"
        else:
            exit_code= "FAILURE"
        return result              
    except socket.timeout:
        print("TimeoutError")
        return "FAILURE"
    except Exception as e:
        print("FAILURE unable to execute command", e.__str__)  
        return "FAILURE" 


def Linux_CapturePreChecks(commands,server,output):
    global srvIndexCount
    global failed_srv_output
    today=curr_date.strftime("%Y%m%d")
    data=[]
    try:
        #Hostname 
        temp=exe_command(commands[0])
        temp=temp[0].strip()
        data.append(temp)
       
        #Major Os Version
        temp=exe_command(commands[2])
        temp=temp[0].strip()
        data.append(temp)
        
        #Last kernal applied date
        temp=exe_command(commands[4])
        temp=temp[0].strip()
        data.append(temp)

        #CPU util-
        var=exe_command(commands[5])
        value=[]
        value.append(float((var[3].split())[-1].strip()))
        value.append(float((var[4].split())[-1].strip()))
        value.append(float((var[5].split())[-1].strip()))
        value.sort()
        if value[-1]<=30 and value[-1]>10:
            var='Warning'
        elif value[-1]<=10:
            var='Unhealthy'
        else:
            var='Healthy'
        data.append(var)
       
        #Memory util
        temp=exe_command(commands[6])
        temp=temp[1].split("\n")
        temp=temp[0].split()
        usedPer=round((float(temp[2])/float(temp[1]))*100,2)
        if usedPer>=70 and usedPer<=90:
            temp='Warning'
        elif usedPer>=90:
            temp='Unhealthy'
        else:
            temp='Healthy'
        data.append(temp)
     
        srvIndexCount+=1
        lock.acquire()
        try:
            output.append(data)
        finally:
            lock.release()
            
    except Exception as e:
        all_lists=[host1,srv_ty,dr_pr,os_v,lpat_de,pat_date,cpu,mem1,swap_mem,pandora_sta,disk_uti,sys_disk,up_time,load_avg,nfs,tlaName,console,cluster]
        for li in all_lists:
            if len(li)>srvIndexCount:
                li.pop(srvIndexCount)
        #print("Error: ",e)
        traceback.print_exc()
        logger.error("error:{}".format(traceback.format_exc()))
        failed_srv_output.append([server,e])

def healthCheck(srvList):
    global successCount
    global failedCount
    global outputs
    today=curr_date.strftime("%Y%m%d")
    #getting the commands 
    filePath=r".\ConfigFile.csv"
    aix=[]
    solaris=[]
    linux=[]
    with open(filePath) as csvfile:
        reader= csv.DictReader(csvfile)
        for row in reader:
            aix_cmd=row['AIX'].strip()
            solaris_cmd=row['solaris'].strip()
            linux_cmd=row['linux'].strip()
            
            if aix_cmd:
                aix.append(aix_cmd)
            if solaris_cmd:
                solaris.append(solaris_cmd)
            if linux_cmd:
                linux.append(linux_cmd)
    for server in srvList:
        try:
            login(server,username,password)
            execute_shell(today)
            print("Logged in to "+server)
            logger.info(f"Logged in to -----> {server}")
            serverType=str(exe_command('uname'))
            print("server type: ",serverType)
            logger.info(f"server type: {serverType}")
            print("Executing health check commands...")
            logger.info("Executing health check commands...")

            if('Linux' in serverType):
                Linux_CapturePreChecks(linux, server,outputs)
            
            #outputs=[]
            lock.acquire()
            successCount +=1
            lock.release()
            print("Execution completed for the server ",server)
            logger.info("Execution completed for the server " + server)
            #srvIndexCount +=1 
            print('srvIndexCount:',srvIndexCount)
            clean_up()
                    
        except Exception as sshException:
            print("Error occurred in "+server+": "+str(sshException))
            logger.error(f"Error occurred in {server}: {str(sshException)}")
            traceback.print_exc()
            lock.acquire()
            failed_srv_output.append([server,sshException])
            failedCount +=1
            lock.release()

    
def ExcelColorGrading(val):
    val=str(val)
    if isinstance(val, str):
        
        if val == 'Healthy':
            return 'background-color: #6AD519'
        elif val == 'Unhealthy':
            return 'background-color: #F6400D'
        elif val== 'Warning':
            return 'background-color: #FFC300'
        elif val== 'Running':
            return 'background-color: #6AD519'
        elif val== 'Stopped':
            return 'background-color: #F6400D'
    return ''

def clean_up():
    client.close()  
    
def main():
    global failed_srv_header
    global failed_srv_output
    global srvIndexCount
    
    try:
        
        colm_header=['hostname','Major os','Last karnal','CPU','Memory']
        HTMLtable=""
        HTMLtable_failed=""
        start_time='{:%Y.%m.%d-%H.%M.%S}'.format(datetime.datetime.now())
        execution_status=""
        #username=input("Enter your username: ")
        #password=getpass.getpass("Enter your password: ")
        #Fatching server list
        srvList=[]
        #srvIndexCount=0    
        inputFile=r".\serverList.csv"
        with open(inputFile,'r') as file:
            data=csv.reader(file)
            for row in data:
                srvList.append(row[0])
               
    	
        batchSize=len(srvList)//2
        srv_batches=[srvList[i:i+batchSize] for i in range(0,len(srvList), batchSize)]
        print("batches: ",srv_batches)
        threads=[]
        for srvs in srv_batches:
            thread=threading.Thread(target=healthCheck, args=(srvs,))
            thread.start()
            threads.append(thread)
        
        for t in threads:
            t.join()
            
        final=pd.DataFrame(outputs,columns=colm_header)
        print(final)
        report=final.style.applymap(ExcelColorGrading)
        if successCount>0:
            report.to_excel(r".\PreCheck Reports\PreCheck_report_"+date_time+".xlsx", engine='openpyxl', index=False)
            logger.info("Excel Report generated successfully...")
            print("Excel Report generated successfully...")
            logger.info(f"Successfully executed server count: {successCount}")
            print("Successfully executed server count: ",successCount)
        if failedCount>0:
            failed_srv_report= pd.DataFrame(failed_srv_output,columns=failed_srv_header)
            failed_srv_report.to_csv(r".\Faliure\PreCheck_failed_srv_"+date_time+".csv", index=False)
            logger.info("Failed server's report generated... ")
            print("Failed server's report generated... ")
            logger.info(f"Servers count for faliure attempts: {failedCount}")
            print("Servers count for faliure attempts: ",failedCount)

        execution_status="Success"
    except Exception as e:
        execution_status="Failed"
        logger.error("error:{}".format(traceback.format_exc()))
        traceback.print_exc()
        
    finally:
        end_time='{:%Y.%m.%d-%H.%M.%S}'.format(datetime.datetime.now())
        logger.info("********************* END *********************")
        logging.shutdown()
main()

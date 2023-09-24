############################################################################################
#
#author        :   Omprakash Tiwari(omprakash.tiwari@wipro.com)
#version       :   1.0
#Organization  :   Wipro
#title         :   NetApp_export_policy_deletion_script
#description   :   The automation script will login to the storage cluster and delete the
#                  NetApp export policies for the requested servers 

#######################################################################################################
import paramiko
import socket
import time
import os
import re
import logging
import traceback
import datetime
import getpass
import csv
#########Inputs##############
username= input("Enter your username: ")
password= getpass.getpass("Enter your password: ")
curr_date= datetime.datetime.now()
date_time=curr_date.strftime("%d_%m_%y_%H_%M_%S")

#Log creation
logFile=f"./Logs/NetApp_log_{date_time}.log"
file_handler=logging.FileHandler(logFile,mode='a')
file_handler.setLevel(logging.INFO)
formatter= logging.Formatter('%(asctime)s - %(levelname)s - %(message)s') 
file_handler.setFormatter(formatter)
logger=logging.getLogger(__name__)
logger.setLevel(logging.INFO)
logger.addHandler(file_handler)
logger.info(f"\n*********************NETAPP EXPORT POLICY DELETION LOGS {curr_date} *********************")


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
        
def exe_command(command,timeOut=30):
    try:
        stdin,stdout,stderr=client.exec_command(command,timeOut)
        logger.info(f"Executing Command: {command}")
        stdin.close()
        temp= stdout.readlines()
        result= temp
        exit_status= stdout.channel.recv_exit_status()        
        return result              
    except socket.timeout:
        print("TimeoutError")
        return "FAILURE"
    except Exception as e:
        print("FAILURE unable to execute command", e.__str__)  
        return "FAILURE" 
    
def execute_shell(command, sleeptime=3):
    command = command + "\n"
    shell.send(command)
    time.sleep(sleeptime)
    logger.info(f"Executing Command: {command}")
    receive_buffer = shell.recv(99999).decode("utf-8")
    return receive_buffer

def WDB_Metering(start_script_time, end_script_time, status):
    '''    :param start_script_time: add execution Start time of the script to start of main function

           :param end_script_time: add execution end time of the script to end of main function

           :param status: Script status (FAILED or SUCCESS in try and catch of main function)

           :return: updates CSV File with execution timestamp'''

    try:

        usecase = "Storage_NetApp_export_policy_deletion"  # <Add usecase name >
        execution_type = "One touch"  # <Add execution type>
        list1 = [usecase, execution_type,
                 start_script_time, end_script_time, status]
        f = open(r"\\WPCHOLU01\OnTouch_solutions_WDB_logs\Storage_NetApp_export_policy_deletion\WDB_Logs.csv", "a")
        writer = csv.writer(f, lineterminator='\n')
        writer.writerow(list1)

    except Exception as e:
        raise Exception(
            "Something went wrong in WDB Metering function, check filepath and input parameters")

def main():
   try:
       srvList=[]
       vserver=[]
       volume=[]
       tempData=[]
       start_time='{:%Y.%m.%d-%H.%M.%S}'.format(datetime.datetime.now())
       clusterCheck=r"E:\Orchestrator\Usecases-OM\Storage Ops automation\ClusterCheck.csv"
       DecomSrvList=r"E:\Orchestrator\Usecases-OM\Storage Ops automation\decom_srvList.csv"
       execStatus="success"
       if(os.path.exists(DecomSrvList)):
           # Reading decommisioning server details
           with open(DecomSrvList,'r') as inputCsv:
               inputfile= csv.DictReader(inputCsv)
               for row in inputfile:
                   srvList.append(row['server'])
                   tempData.append(row['vserver/volume'])
            #print(srvList,"\n",tempData)
               for data in tempData:
                   temp=data.split(":")
                   vserver.append(temp[0].strip())
                   volume.append(temp[1].strip())
            #print(volume,"\n",vserver)
           logger.info("Reading serverlist input file.")
           print("Reading serverlist input file.")
       else:
           print("No server list found...")
           logger.info("No server list found...")
           execStatus="Failed"
           exit()
           
       for (v_srv,srv,vol) in zip(vserver,srvList,volume):
           #print(f"vsrv= {v_srv}\n srv= {srv}\nvolume={vol}")   
           if(os.path.exists(clusterCheck)):
               # Reading clusters
               with open(clusterCheck,'r') as inputCsv:
                   inputfile= csv.DictReader(inputCsv)
                   for row in inputfile:
                       if(row['StorageVM']==v_srv):
                           storage_cluster= row['Cluster']
                           print(f"Found storage cluster for {v_srv} ---> {storage_cluster}.")
                           logger.info(f"Found storage cluster for {v_srv} is {storage_cluster}.")
                           ClusterMatch=""
                           break
                       else:
                           ClusterMatch="Not found"
                   if(ClusterMatch):
                       print(f"No storage cluster found for vserver: {v_srv}")
                       logger.info(f"No storage cluster found for vserver: {v_srv}")
                       continue
           else:
               print("Storage cluster details not found...")
               logger.info("Storage cluster details not found...")
               execStatus="Failed"
               exit()
               
            # Login to the storage cluster
           login(storage_cluster, username, password)
           print(f"Logged In to cluster -> {storage_cluster}")
           logger.info(f"Logged In to cluster -> {storage_cluster}")
           output= exe_command(f"vol show -vserver {v_srv} -volume {vol} -fields policy")
           policy=(output[-2].split(" ")[2]).strip()
           print('policy= ',policy)
           if(policy != ''):   
               ruleIndex= execute_shell(f'export-policy rule show -vserver {v_srv} -policyname {policy} -clientmatch {srv} -fields ruleindex')
               regPattern=r"\w+\s+\w+\s+(\d+)(?! entries)"
               ruleIndex= re.findall(regPattern,ruleIndex)
               print("Rule Index Found: ",ruleIndex)
               logger.info(f"Rule Index Found: {ruleIndex}")
           else:
               print(f"No policies found against vserver:{v_srv} & volumn:{vol}")
               logger.info(f"No policies found against vserver:{v_srv} & volumn:{vol}")
           for r_index in ruleIndex:
               output=execute_shell(f'export-policy rule delete -vserver {v_srv} -policyname {policy} -ruleindex {r_index}')
               #print("Deletion: ",output)
               if("Do you want to continue? {y|n}:" in output):
                   output=execute_shell("y")
               output=output.split("\n")[1:-1]
               output="\n".join(output)
               print("Deletion after spliting: ",output)
               print(f"NetApp export policy deleted for {srv} (RuleIndex {r_index})")
           #Validating the deletion
           ruleIndex= execute_shell(f'export-policy rule show -vserver {v_srv} -policyname {policy} -clientmatch {srv} -fields ruleindex')
           regPattern=r"\w+\s+\w+\s+(\d+)(?! entries)"
           ruleIndex= re.findall(regPattern,ruleIndex)
           if(len(ruleIndex)==0):
               print(f"NetApp export policy deleted for server: {srv}")
               logger.info(f"NetApp export policy deleted for server: {srv}")
           
   except Exception as e:
       print("Error occured: ",e)
       logger.error("Error:{}".format(traceback.format_exc()))
       traceback.print_exc()
       execStatus="Failed"

   finally:
       end_time='{:%Y.%m.%d-%H.%M.%S}'.format(datetime.datetime.now())
       WDB_Metering(start_time, end_time, execStatus)
       logger.info("********************* END *********************")
       logging.shutdown()
      
main()
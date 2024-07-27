
#---------------------------Import Module-----------------------------------

import paramiko
import socket
import logging
import datetime
import time
import sys
import re
import os



name = sys.argv[1] 
LAN_ID = sys.argv[2]
sctaskNo = sys.argv[3]
short_descr = sys.argv[4]
hostname = sys.argv[5]
ansible_user = sys.argv[6]
ansible_password = sys.argv[7]
gidnumber_conf = sys.argv[8]
loginshell_conf = sys.argv[9]
environment = sys.argv[10]
tlalist = sys.argv[11]
print("Tla list is "+tlalist)

# ldap_conf = "//sdcholp003/HO_21.4.0_Solutions/Unix_usecases/TLA_Removal/ldap_conf.cfg"
# app_log   = "//sdcholp003/HO_21.4.0_Solutions/Unix_usecases/TLA_Removal//ldap_bot.log"

#logging.basicConfig(filename=app_log, filemode='w',
#                     format='%(asctime)s - %(levelname)s - %(message)s', datefmt='%d-%b-%y %H:%M:%S', level=logging.INFO)

# conf_dict    = {}
# if os.path.isfile(ldap_conf) == False:
#     logging.error("Configuration file 'ldap_conf.cfg' not present!")
#     logging.error("Exit")    
#     sys.exit()
   
#Configuration file present, reading input values
# with open(ldap_conf, 'r') as confinput:
#     for line in confinput:
#         inarr = line.split(":-")
#         conf_dict[inarr[0]] = inarr[1].strip()
        
# username = conf_dict['username']
# password = conf_dict['password']
# hostname = conf_dict['host']


client = None
shell = None
success_msg = ""

#First thing should be log initiation
# logging.basicConfig(filename='CPUhealthcheck.log', filemode='w',
#                     format='%(asctime)s - %(levelname)s - %(message)s', datefmt='%d-%b-%y %H:%M:%S', level=logging.INFO)

#-------------------Logging into remote server----------------------

#Login to the servers
def login(hostn, uname, pwd):
    #login function using paramiko
    global client
    global shell
    client = paramiko.SSHClient()
    try:
        # logging.info("-------------Trying to establish connection with server-------------")
        # logging.info("IPAddress : " + hostn + ", Username : " + uname)
        # logging.info("Establishing ssh connection")
        print("Trying to establish connection with server ")
        print("IPAddres : " + hostn + ", Username : " + uname)
        print("Establishing ssh connection")
        client.load_system_host_keys()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect(hostname=hostn, username=uname, password=pwd)
        #logging.info("-------------Successfully connected to Server-------------")
        print("Successfully connected to Server ")
        shell = client.invoke_shell()
    except paramiko.AuthenticationException as authenticationException:
        #logging.error("Authentication failed, please verify your credentials : %s" % authenticationException)
        print("Authentication failed, please verify your credentials : "+str(authenticationException))
        print("Authentication failed, please verify your credentials.")
        #raise Exception("Authentication failed, please verify your credentials")
        sys.exit()
    except socket.error as e:
        #logging.error("Communication problem : %s" % e)
        print("Communication failed : "+str(e))
        print("Server communication problem.") 
        sys.exit()
        #raise Exception("Entered IP Address is wrong")
    except paramiko.BadHostKeyException as badHostKeyException:
        #logging.error("Unable to verify server's host key: %s" % badHostKeyException)
        print("Unable to verify server's host key: %s" % badHostKeyException)
        print("Unable to verify server's host key")
        #raise Exception("Unable to verify server's host key")
        sys.exit()
    except paramiko.SSHException as sshException:
        #logging.error("Unable to establish SSH connection: %s" % sshException)
        print("Unable to establish SSH connection: %s" % sshException)
        print("Unable to establish SSH connection")
        #raise Exception("Unable to establish SSH connection")
        sys.exit()
    except Exception as e:
        #ogging.error("Something went wrong : %s" % e)
        print("Something went wrong : %s" % e)
        print("Something went wrong")
        #raise Exception("Something went wrong")
        sys.exit()

#---------------Execute function for command execution------------------------

def execute_command(command, sleeptime):
    command = command + "\n"
    shell.send(command)
    time.sleep(sleeptime)
    receive_buffer = shell.recv(9999).decode("utf-8")
    return receive_buffer
    
#-----------------TLA removal------------------------------------------------

def remove_tlas(account, stask_num, tlalist):
    global success_msg
    #Retreive existing TLAs - ntaccount -L -u "_account_" -a tla
    try:    
        print("Account is "+account)
        print("tlalist is "+tlalist)
        exist_tla = execute_command("ntaccount -L -u \""+account+"\" -a tla",20)
        #logging.info ("Find existing TLA for enable user "+exist_tla)
        print("Find existing TLA for enable user "+exist_tla)
        exist_tla_list  = exist_tla.split("\n")
        exist_tla_list[2] = exist_tla_list[2].strip()
        tla_check = " ".join(exist_tla_list)
        x = re.search("0 ROWS RETURNED", tla_check)
    except Exception as e:
        #logging.error("Find existing TLA for enable user exception : "+str(e))
        print("Find existing TLA for enable user exception : "+str(e))
        #logging.error("ntaccount -L -u account -a tla "+exist_tla)
        print("ntaccount -L -u account -a tla "+exist_tla)
        print("Exception3: "+str(e))
        #raise Exception("ntaccount -L -u account -a tla   command execution error!")
        print("ntaccount -L -u account -a tla   command execution error!")
        sys.exit()
    if x or len(exist_tla_list[2]) < 2:
        return("No TLA for account")
        print("No TLA found")
    else: 
        try:
            #remtla = execute_command("ntaccount -M -u \""+account+"\" -tD \""+tlalist+"\" -REASON \""+stask_num+"\"",20)
            # tlalist = tlalist.strip()[1:-1].replace(" ", "").replace("'", "")  
            # print("tlatype-", type(tlalist),"\n", tlalist)
            print("before join ", tlalist)
            print(type(tlalist))
            tlalist= "".join(tlalist)
            print("TLA Removal ", tlalist)
            print(f"ntaccount -M -u {account} -tD {tlalist} -REASON {stask_num}")
            remtla = execute_command(f"ntaccount -M -u {account} -tD {tlalist} -REASON {stask_num}",20)

            print(tlalist + " TLA has been removed")
            #print(account)
            #print(tlalist)
            #print(stask_num)
            #logging.info ("Removing existing TLAs for enable user "+remtla)
            #print("TLA removed")
        except Exception as e:
            #logging.error("Remove existing TLA exception : "+str(e))
            #logging.error("ntaccount -M -u account -tD tlalist -REASON stask_num"+ remtla)
            print("Exception4: "+str(e))
            #raise Exception("ntaccount -M -u account -tD tlalist -REASON stask_num   command execution error!")    
            sys.exit()
                
    return(remtla)

#-------------Finding host for provided TLA--------------------------------------

def remove_hosts(account, stask_num, tlalist):

    #Retreive existing hosts        ntaccount -L -u "_account_" -a host
    try:
        print(tlalist, type(tlalist))
        for i in tlalist:
    
         #print(i)
         if '-' in i:
             #print("Inside if Condition")
             sepration = i.lower().split("-")
             print(sepration)
             #host_finding = execute_command("nttla -L -t \""+sepration[0]+"\" -a host-\""+sepration[1]+"\"",20)
             print(f"nttla -L -t \""+sepration[0]+"\" -a host-\""+sepration[1]+"\"")
             host_finding = execute_command(f"nttla -L -t {sepration[0]} -a host-{sepration[1]}",20)
             #host_finding = execute_command(f"nttla -L -t '{sepration[0]}' -a host-'{sepration[1]}'")             
             print(f"nttla -L -t {sepration[0]} -a host-{sepration[1]}")
             #print(host_finding)
             logging.info ("Find host for TLA "+host_finding)
             print("Find host for TLA "+host_finding)
             exist_host_list = host_finding.split("\n")
             exist_host_list[2] = exist_host_list[2].strip()
             host_check = " ".join(exist_host_list)
             x = re.search("0 ROWS RETURNED", host_check)
             if x or len(exist_host_list[2]) < 2:
                 print("No Host to find")
                 return("No Host to find")
             else:
                 #print("Inside Host Removing")
                 hostlist                = exist_host_list[2]
                 #Remove existing hosts ntaccount -M -u "_account_" -hD "_hostsToRemove_" -REASON "_ticketNumber_"

#-----------------------------------Removing host for provided TLA----------------------------------------------------

                 try:
                     remhost = execute_command("ntaccount -M -u \""+account+"\" -hD \""+hostlist+"\" -REASON \""+stask_num+"\"",20)
                     print("Host has been removed")
                     logging.info ("Removing existing hosts for enable user "+remhost)
                     print("Removing existing hosts for enable user "+remhost)
                 except Exception as e:
                     logging.error("Remove existing hosts exception : "+str(e))
                     logging.error("ntaccount -M -u account -hD hostlist -REASON stask_num"+ remhost)
                     print("Exception2: "+str(e))
                     #raise Exception("ntaccount -M -u account -hD hostlist -REASON stask_num - command execution error!")        
                     sys.exit()
                 return(remhost)
             
    except Exception as e:
        logging.error("Find existing hosts for enable user exception : "+str(e))
        logging.error("ntaccount -L -u account -a host")
        print("Exception1: "+str(e))
        #raise Exception("ntaccount -L -u account -a host command execution error!")
        sys.exit()
    current_TLA          = execute_command("ntaccount -L -u \""+account+"\" -a tla",15)
    current_TLA_list     = current_TLA.split("\n")
    current_TLAdet       = ",".join(current_TLA_list)
    
#----------------------Adding host for present TLA----------------------------------------------

    flag = False
    for i in current_TLAdet:
        if '-' in i:
            spilting = i.split("-")
            present_host = execute_command("nttla -L -t \""+spilting[0]+"\" -a host-\""+spilting[1]+"\"",30)
            logging.info ("Find host for TLA "+present_host)
            exist_host_list = present_host.split("\n")
            exist_host_list[2] = exist_host_list[2].strip()
            flag = True
    if flag == True:
        hosts = exist_host_list[2]
        Addhost = execute_command("ntaccount -A -u \""+account+"\" -h \""+hosts+"\" -REASON \""+stask_num+"\"", 20)    
    #print(Addhost)

def remove_group(account, stask_num, tlalist):

#----------------------FInding groups for ID---------------------------------------------------------
    
    try:
        exist_grp        = execute_command("ntgroup -L -m \""+account+"\"",10)
        logging.info ("Find account existing hosts for enable user "+exist_grp)
        exist_grp_list  = exist_grp.split("\n")
        grp_check       = " ".join(exist_grp_list)
        x = re.search("FAILED VERIFICATION\: These members do not exist|0 ROWS RETURNED", grp_check)
    except Exception as e:
        logging.error("Find account existing hosts for enable user exception : "+str(e))
        logging.error("ntgroup -L -m account "+exist_grp)
        print("Exception: "+str(e))
        #raise Exception("ntgroup -L -m account - command execution error!")    
        sys.exit()
    if x:
        return("Account is not in any group")
    else:
        #Remove from existing groups (for each group)   ntgroup -M -g "_group_" -mD "_account_" -REASON "_ticketNumber_"

#---------------------------Removing provided TLA groups------------------------------------------------------

        try:
            for i in tlalist:
              if '-' in i:
                  sepration = i.split("-")
                  grprem = execute_command("ntgroup -M -g \""+sepration[0]+"\" -mD \""+account+"\" -REASON \""+stask_num+"\"",10)
                  print("Groups's has been removed")
            time.sleep(5)
            exist_tla = execute_command("ntaccount -L -u \""+account+"\" -a tla",20)
            #print(exist_tla)
            logging.info ("Find existing TLA for enable user "+exist_tla)
            exist_tla_list  = exist_tla.split("\n")
            exist_tla_list[2] = exist_tla_list[2].split()
            #print(exist_tla_list)

#----------------------------Adding into groups for present TLA------------------------------------------------

            for j in exist_tla_list[2]:
              if '-' in j:
                   sep = j.split("-")
                   grprem = execute_command("ntgroup -M -g \""+sep[0]+"\" -m \""+account+"\" -REASON \""+stask_num+"\"",15)
                   #print(grprem)


        except Exception as e:
            logging.error("Remove account from each group for enable user : "+str(e))
            logging.error("ntgroup -M -g grp -mD account -REASON stask_num"+ grprem)
            print("Exception: "+str(e))
            #raise Exception("ntgroup -M -g grp -mD account -REASON stask_num - command execution error!")        
            sys.exit()

        return("Account removed from groups ")

	
def  main():
    logging.info ("Inside main function ")        
    global success_msg
    itsm_dict    = {'stask_num': sctaskNo, 'name': name, 'LAN_ID': LAN_ID, 'environment': environment, 'short_desc':  short_descr } 
    conf_dict    = { 'host': hostname, 'username': ansible_user, 'password': ansible_password, 'gidnumber': gidnumber_conf, 'loginshell': loginshell_conf }
    #inputData = Input_itsm_dict #{'loginid': 'sb456', 'tlalist': 'mts-int', 'Reason': 'test'}
    inputData    = { 'loginid': LAN_ID, 'tlalist': tlalist, 'Reason': sctaskNo, 'username': ansible_user, 'password': ansible_password, 'gidnumber': gidnumber_conf, 'loginshell': loginshell_conf  }
    print(inputData)
    #inputData = Input_itsm_dict#{'loginid': 'sb456', 'tlalist': 'mts-int', 'Reason': 'test'}
    #print(loginid)
    #Initiating login function to connect remote server where the LDAP command are executed.                
    #login(hostname,username,password)
    login(conf_dict['host'],conf_dict['username'],conf_dict['password'])
    #print(hostname)
    print("Action name: TLA_Removal \n")

#------------------Check whether user exists or not using "check_user_exist" function---------------------

    try:
        accout          = execute_command("ntaccount -L -u \""+inputData["loginid"]+"\" -a tla",15)
        accout_list     = accout.split("\n")
        #print(accout)
        accoutdet       = ",".join(accout_list)
        #print(accoutdet)
        acc_act       = "_en"
        #print("1 "+accoutdet+"1")
        if "Not authorized to use this system. Unauthorized attempt has been logged" in accoutdet:
            #print(accoutdet)
            sys.exit()
        if "0 ROWS RETURNED" in accoutdet:
            accout          = execute_command("ntaccount -L -u \"_"+inputData["loginid"]+"\" -a tla",15)
            accout_list     = accout.split("\n")
            accoutdet       = ",".join(accout_list)
            acc_act       = "_dis"
            print("User has been disabled")
            if "0 ROWS RETURNED" in accoutdet:
                return("User does not exist")
            else:
                return("User exist"+acc_act)
                
        else:
#---------------------Remove required TLAs from accounts--------------------------------------------
            print("user is Active")
            rt = remove_tlas(inputData["loginid"], inputData["Reason"],inputData["tlalist"])
            logging.info ("Remove mentioned TLAs "+str(rt))

#----------------------Remove Hosts belongs to TLA--------------------------------------------------
            rh = remove_hosts(inputData["loginid"], inputData["Reason"],inputData["tlalist"].split(','))
            logging.info ("Remove hostss "+str(rh))

#----------------------Remove account from group----------------------------------------------------
            rg = remove_group(inputData["loginid"], inputData["Reason"],inputData["tlalist"].split(','))
            logging.info ("Remove account from groups "+str(rg))
        print("Script executed successfully and TLA's has been removed")
            
    except Exception as e:
        logging.error("Exception : "+str(e))
        logging.error("ntaccount -M -u _account_ "+accout)
        print("Exception5: "+str(e))
        #raise Exception("ntaccount -M -u _account_  command execution error!")
main()



#!/usr/bin/python
# -*- coding: utf-8 -*-

import paramiko
import socket
import logging
import datetime
import time
import sys
import re
import os




#org_path = os.path.realpath(__file__)
#patharr = org_path.split("/")
#cfull_path = patharr[-1]
#org_path = re.sub('%s' % patharr[-1],'',org_path)


#!/usr/bin/python
# -*- coding: utf-8 -*-

################### Solution to resolve IDM requests for add and enable users and addition of TLAs. #####################  




client = None
shell = None
success_msg = ""


name = sys.argv[1] 
login_id = sys.argv[2]
sctaskNo = sys.argv[3]
group_names= sys.argv[4]
short_descr = sys.argv[5]
hostname = sys.argv[6]
ansible_user = sys.argv[7]
ansible_password = sys.argv[8]
gidnumber_conf = sys.argv[9]
loginshell_conf = sys.argv[10]


#org_path = os.path.realpath(__file__)
#patharr = org_path.split("/")
#cfull_path = patharr[-1]
#org_path = re.sub('%s' % patharr[-1],'',org_path)

#itsm_input = "E:\\IDM_usecases\\idm\\idm\\itsm_input.txt"
#ldap_conf = "//sdcholp003/HO_21.4.0_Solutions/IDM_usecases/idm/idm/ldap_conf.cfg"
#app_log   = "//sdcholp003/HO_21.4.0_Solutions/IDM_usecases/idm/idm/log/ldap_bot.log"

#First thing should be log initiation
#logging.basicConfig(filename=app_log, format='%(asctime)s %(message)s %(lineno)d')
#logger=logging.getLogger() 
#logger.setLevel(logging.DEBUG)


#Login to the servers
def login(hostn, uname, pwd):
    global client
    global shell
    global success_msg

   
    client = paramiko.SSHClient()

    try:
        print("Trying to establish connection with server ")
        print("IPAddres : " + hostn + ", Username : " + uname)
        print("Establishing ssh connection")
        client.load_system_host_keys()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect(hostname=hostn ,username=uname,password=pwd)
        print("Successfully connected to Server ")
        success_msg += "Successfully connected to server."
        shell = client.invoke_shell()
    except paramiko.AuthenticationException as authenticationException:
        logger.error("Authentication failed, please verify your credentials : "+str(authenticationException))
        print("Authentication failed, please verify your credentials.")
        #raise Exception("Authentication failed, please verify your credentials")
        sys.exit()
    except socket.error as e:
        logger.error("Communication problem : "+str(e))
        print("Server cmmunication problem.")    
        #raise Exception("Entered IP Address is wrong")
        sys.exit()
    except paramiko.BadHostKeyException as badHostKeyException:
        logger.error("Unable to verify server's host key: "+str(badHostKeyException))
        print("Unable to verify server's host key.")    
        #raise Exception("Unable to verify server's host key")
        sys.exit()
    except paramiko.SSHException as sshException:
        logger.error("Unable to establish SSH connection: "+str(sshException))
        print("Unable to establish SSH connection.")
        #raise Exception("Unable to establish SSH connection")
        sys.exit()
    except Exception as e:
        logger.error("Exception : "+str(e))
        print("Exception: "+str(e))
        #raise Exception("Exception")
        sys.exit()


def execute_command(command, sleeptime):
    command = command + "\n"
    shell.send(command)
    time.sleep(sleeptime)
    receive_buffer = shell.recv(9999).decode("utf-8")
    return receive_buffer


def tlareadnonprod(tla):
    #Read non prod TLAs
    #nttla -L -t "_tla_" -a host-sys,host-int,host-uat
    try:
        tlanprod        = execute_command("nttla -L -t \""+tla+"\" -a host-sys,host-int,host-uat",30)
        tlanprod_list   = tlanprod.split("\n")
        tlas_nprod         = tlanprod_list[2]
    except Exception as e:
        logger.error("Exception : "+str(e))
        logger.error("nttla -L -t _tla_ -a host-sys,host-int,host-uat "+tlanprod)
        print("Exception: "+str(e))
        #raise Exception("nttla -L -t _tla_ -a host-sys,host-int,host-uat command execution error!")    
        sys.exit()

    return(tlas_nprod)

def tlareadprod(tla):
    #Read prod TLAs
    #nttla -L -t "_tla_" -a host-prod
    try:    
        tlaprod         = execute_command("nttla -L -t \""+tla+"\" -a host-prod",30)
        tlaprod_list    = tlaprod.split("\n")
        tlas_prod         = tlaprod_list[2]
    except Exception as e:
        logger.error("Exception : "+str(e))
        logger.error("nttla -L -t _tla_ -a host-prod "+tlaprod)
        print("Exception: "+str(e))
        #raise Exception("nttla -L -t _tla_ -a host-prod command execution error!")
        sys.exit()
        
    return(tlas_prod)

def update_tla(account, tla, prodnonprod, stask_num):
    #ntaccount -M -u "_account_" -h "_host_" -REASON "_ticketNumber_"
    global success_msg

    if prodnonprod == "prod":
        allhosts = tlareadprod(tla)
        hostarr  = allhosts.split("|")
        allhosts = ",".join(hostarr)
        finaltla = tla+"-prod"

    elif prodnonprod == "nonprod":
        allhosts = tlareadnonprod(tla)
        hostarr  = allhosts.split("|")
        allhosts = ",".join(hostarr)
        finaltla = tla+"-sys,"+tla+"-int,"+tla+"-uat"
    try:
        if tla == "unixuser":
            finaltla = "unixuser"
            
        tlacom  = execute_command("ntaccount -M -u \""+account+"\" -t \""+finaltla+"\" -h \""+allhosts+"\" -REASON \""+stask_num+"\"",50)
        print("tlacom: "+tlacom)
        success_msg += "TLA and Hosts updated successfully. "
    except Exception as e:
        logger.error("Exception : "+str(e))
        logger.error("ntaccount -M -u _account_ -h _host_ -REASON _ticketNumber_ "+tlacom)
        print("Exception: "+str(e))
        #raise Exception("ntaccount -M -u _account_ -h _host_ -REASON _ticketNumber_  command execution error!")    
        sys.exit()
    return(tlacom)

def tla_group_mgmnt(application,loginid,prodnonprod,stask_num):
    tlalist         = application.strip()
    
    tla_list        = tlalist.split(",")
    tla_list.append("unixuser")
    try:
        for tla in tla_list:
            tla = tla.strip()
            update_tla_stat = update_tla(loginid, tla, prodnonprod, stask_num)
            final_stat      = update_tla_stat.split("\n")
            print ("TLA Status for "+final_stat[-2])
            fstat = "".join(final_stat)
            matline = re.search(r'FAILED VERIFICATION',str(fstat),re.I)
            if matline:
                print(final_stat[-2])        
                sys.exit()
            
            group_stat      = update_group(loginid, tla, stask_num)
            final_grp_stat  = group_stat.split("\n")
            print ("Group Status for "+final_grp_stat[-2])
    except Exception as e:
        logger.error("TLA and Group Exception : "+str(e))
        print("Exception: "+str(e))
        #raise Exception("TLA and Group Exception !")
        sys.exit()

    return("tla_added")

def update_group(account, tla, stask_num):
    global success_msg
    #ntgroup -M -g "_tla_" -m"_account_" -REASON "_ticketNumber_"
    
    try:
        group_det = execute_command("ntgroup -M -g \""+tla+"\" -m \""+account+"\" -REASON \""+stask_num+"\"",15)
        print(group_det)
        success_msg += "Account added to groups. "
    except Exception as e:
        logger.error("Exception : "+str(e))
        logger.error("ntgroup -M -g _tla_ -m_account_ -REASON _ticketNumber_ "+group_det)
        print("Exception: "+str(e))
        #raise Exception("ntgroup -M -g _tla_ -m_account_ -REASON _ticketNumber_   command execution error!")
        sys.exit()
    return(group_det)

#ntgroup -M -g "unixuser " -m "_account_" -REASON "_ticketNumber_" 
def check_user_exist(account):

    #ntaccount -M -u "_account_"
    try:
        print("Inside check user exist function")
        accout          = execute_command("ntaccount -L -u \""+account+"\" -a tla",15)
        print(accout)
        accout_list     = accout.split("\n")
        accoutdet       = ",".join(accout_list)
        acc_act       = "_en"
        #print("1 "+accoutdet+"1")
        if "Not authorized to use this system. Unauthorized attempt has been logged" in accoutdet:
            #print(accoutdet)
            sys.exit()
                
        if "0 ROWS RETURNED" in accoutdet:
            accout          = execute_command("ntaccount -L -u \"_"+account+"\" -a tla",15)
            accout_list     = accout.split("\n")
            accoutdet       = ",".join(accout_list)
            acc_act       = "_dis"
            #print("2 "+accoutdet+" 2")
            if "0 ROWS RETURNED" in accoutdet:
                return("User does not exist")
            else:
                return("User exist"+acc_act)
        else:
            return("User exist"+acc_act)
        
    except Exception as e:
        logger.error("Exception : "+str(e))
        logger.error("ntaccount -M -u _account_ "+accout)
        print("Exception: "+str(e))
        #raise Exception("ntaccount -M -u _account_  command execution error!")
        sys.exit()

        
 

def enable_account(disabledAccount,ticketNumber):
    global success_msg
    #ntaccount -ENABLE -u "_disabledAccount_" -REASON "_ticketNumber_"
    try:
        enable_acc = execute_command("ntaccount -ENABLE -u \""+disabledAccount+"\" -REASON \""+ticketNumber+"\"",50)
        success_msg += "Account enabled. "
    except Exception as e:
        logger.error("Account enable exception : "+str(e))
        logger.error("ntaccount -ENABLE -u _disabledAccount_ -REASON _ticketNumber_ "+enable_acc)
        print("Exception: "+str(e))
        #raise Exception("ntaccount -ENABLE -u _disabledAccount_ -REASON _ticketNumber_   command execution error!")    
        sys.exit()
    return(enable_acc)

def remove_tlas(account, stask_num):
    global success_msg
    #Retreive existing TLAs - ntaccount -L -u "_account_" -a tla
    try:    
        exist_tla = execute_command("ntaccount -L -u \""+account+"\" -a tla",20)
        print ("Find existing TLA for enable user "+exist_tla)
        exist_tla_list  = exist_tla.split("\n")
        exist_tla_list[2] = exist_tla_list[2].strip()
        tla_check = " ".join(exist_tla_list)
        x = re.search("0 ROWS RETURNED", tla_check)
    except Exception as e:
        logger.error("Find existing TLA for enable user exception : "+str(e))
        logger.error("ntaccount -L -u account -a tla "+exist_tla)
        print("Exception: "+str(e))
        #raise Exception("ntaccount -L -u account -a tla   command execution error!")
        sys.exit()
    if x or len(exist_tla_list[2]) < 2:
        return("No TLA for account")
    else:
        tlalist = exist_tla_list[2]
        account  = re.sub("^_", "", account)
        #Remove existing tlas ntaccount -M -u "_account_" -tD "_tlasToRemove_" -REASON "_ticketNumber_"
        try:
            remtla = execute_command("ntaccount -M -u \""+account+"\" -tD \""+tlalist+"\" -REASON \""+stask_num+"\"",20)
            print ("Removing existing TLAs for enable user "+remtla)
        except Exception as e:
            logger.error("Remove existing TLA exception : "+str(e))
            logger.error("ntaccount -M -u account -tD tlalist -REASON stask_num"+ remtla)
            print("Exception: "+str(e))
            #raise Exception("ntaccount -M -u account -tD tlalist -REASON stask_num   command execution error!")    
            sys.exit()
                
    return(remtla)

def remove_hosts(account, stask_num):

    #Retreive existing hosts        ntaccount -L -u "_account_" -a host
    try:
        exist_host = execute_command("ntaccount -L -u \""+account+"\" -a host",20)
        print ("Find existing hosts for enable user "+exist_host)
        exist_host_list = exist_host.split("\n")
        exist_host_list[2] = exist_host_list[2].strip()
        host_check = " ".join(exist_host_list)
        x = re.search("0 ROWS RETURNED", host_check)
    except Exception as e:
        logger.error("Find existing hosts for enable user exception : "+str(e))
        logger.error("ntaccount -L -u account -a host"+exist_host)
        print("Exception: "+str(e))
        #raise Exception("ntaccount -L -u account -a host command execution error!")
        sys.exit()
    
    if x or len(exist_host_list[2]) < 2:
        return("No Host for account")
    else:
        hostlist                = exist_host_list[2]
        #Remove existing hosts ntaccount -M -u "_account_" -hD "_hostsToRemove_" -REASON "_ticketNumber_"
        try:
            remhost = execute_command("ntaccount -M -u \""+account+"\" -hD \""+hostlist+"\" -REASON \""+stask_num+"\"",20)
            print ("Removing existing hosts for enable user "+remhost)
        except Exception as e:
            logger.error("Remove existing hosts exception : "+str(e))
            logger.error("ntaccount -M -u account -hD hostlist -REASON stask_num"+ remhost)
            print("Exception: "+str(e))
            #raise Exception("ntaccount -M -u account -hD hostlist -REASON stask_num - command execution error!")        
            sys.exit()
        return(remhost)

def remove_group(account, stask_num):

    #Retreive existing groups       ntgroup -L -m "_account_"
    try:
        exist_grp        = execute_command("ntgroup -L -m \""+account+"\"",10)
        print ("Find account existing hosts for enable user "+exist_grp)
        exist_grp_list  = exist_grp.split("\n")
        grp_check       = " ".join(exist_grp_list)
        x = re.search("FAILED VERIFICATION\: These members do not exist|0 ROWS RETURNED", grp_check)
    except Exception as e:
        logger.error("Find account existing hosts for enable user exception : "+str(e))
        logger.error("ntgroup -L -m account "+exist_grp)
        print("Exception: "+str(e))
        #raise Exception("ntgroup -L -m account - command execution error!")    
        sys.exit()
    if x:
        return("Account is not in any group")
    else:
        #Remove from existing groups (for each group)   ntgroup -M -g "_group_" -mD "_account_" -REASON "_ticketNumber_"
        try:
            for grp in exist_grp_list:
                chk1 = re.search("ROWS RETURNED", grp)
                chk2 = re.search("^\W", grp)
                chk5 = re.search("cn", grp)
                if chk1 or chk2 or chk5:
                        continue

                grprem = execute_command("ntgroup -M -g \""+grp+"\" -mD \""+account+"\" -REASON \""+stask_num+"\"",10)

        except Exception as e:
            logger.error("Remove account from each group for enable user : "+str(e))
            logger.error("ntgroup -M -g grp -mD account -REASON stask_num"+ grprem)
            print("Exception: "+str(e))
            #raise Exception("ntgroup -M -g grp -mD account -REASON stask_num - command execution error!")        
            sys.exit()

        return("Account removed from groups ")
        
def add_account(account, firstname, lastname, shell, homedir, gid, ticketNumber):
    global success_msg
    #ntaccount -A -u "_account_" -f "_first name_" -l "_last name_" -s "_shell_" -d "_home dir_" -p "_gid_" -t "unixuser,_tla_-sys,_tla_-int,_tla_-uat" -h "_hostList_" -REASON "_ticketNumber_"
    try:
        add_acc = execute_command("ntaccount -A -u \""+account+"\" -f \""+firstname+"\" -l \""+lastname+"\" -s \""+shell+"\" -d \""+homedir+"\" -p \""+gid+"\" -REASON \""+ticketNumber+"\"",30)
        success_msg += "Account added. "
    except Exception as e:
        logger.error("Add account : "+str(e))
        logger.error("ntaccount -A -u account -f firstname -l lastname -s shell..."+ add_acc)
        print("Exception: "+str(e))
        #raise Exception("ntaccount -A -u account -f firstname -l lastname -s shell... - command execution error!")
        sys.exit()
    return(add_acc)

#Create directory for user in Jump Server(Alvin)
def create_usrdir(hdir,usrid,pwd,stat):
    global success_msg
    try:
        #Check user dircetory exists; if else create.                
        if stat == "exist":
            checkud    =   execute_command("ls -ld /home/home01/*"+usrid,10)
            dirchek    = " ".join(checkud.split("\n"))
            chk01    = re.search("No such file or directory", dirchek)
            if chk01:
                checkud    =   execute_command("ls -ld /home/home02/*"+usrid,10)
                dirchek    = " ".join(checkud.split("\n"))
                chk02    = re.search("No such file or directory", dirchek)
                if chk02:
                    sudo    =   execute_command("sudo mkdir -m 750 "+hdir+usrid,10)
                    passexe =   execute_command(pwd,10)
                    print("sudo and pass"+sudo+" "+passexe)
                    sudochown    =    execute_command("sudo chown "+usrid+":unixuser "+hdir+usrid,10)
                    passchhown    =    execute_command(pwd,10)
                    print("sudo chown and pass"+sudochown+" "+passchhown)
                    checkud    =   execute_command("ls -ld "+hdir+"*"+usrid,10)
                    dirchek    = " ".join(checkud.split("\n"))
                    chkfnl    = re.search("No such file or directory", dirchek)
                    if chkfnl:
                        return("User directory cannot be created")
                    else:
                        return("User directory created successfully")
                        success_msg += "User directory created in server. "
                else:
                    return("User directory exists")
            else:
                return("User directory exists")
        else:    
            checkud    =   execute_command("ls -ld "+hdir+"*"+usrid,10)
            dirchek    = " ".join(checkud.split("\n"))
            chk1    = re.search("No such file or directory", dirchek)
            if chk1:
                sudo    =   execute_command("sudo mkdir -m 700 "+hdir+usrid,10)
                passexe =   execute_command(pwd,10)
                print("sudo and pass"+sudo+" "+passexe)
                sudochown    =    execute_command("sudo chown "+usrid+":unixuser "+hdir+usrid,10)
                passchhown    =    execute_command(pwd,10)
                print("sudo chown and pass"+sudochown+" "+passchhown)
                checkud    =   execute_command("ls -ld "+hdir+"*"+usrid,10)
                dirchek    = " ".join(checkud.split("\n"))
                chkfnl    = re.search("No such file or directory", dirchek)
                if chkfnl:
                    return("User directory cannot be created")
                else:
                    return("User directory created successfully")
                    success_msg += "User directory created in server. "
            else:
                return("User directory exists")
         
    except Exception as e:
        logger.error("User directory creation in remote server error : "+str(e))
        print("Exception: "+str(e))
        #raise Exception("User directory creation in remote server error "+str(e))            
        sys.exit()
     


def  main():
    print ("Inside main function ")  
    global success_msg
    itsm_dict    = {'stask_num': sctaskNo, 'name': name, 'loginid': login_id, 'group': group_names, 'short_desc':  short_descr }   #{'stask_num': 'testing-Please add access to the application Unix - Application TLA Access - NON-PROD for the individual shown below.', 'name': 'Deeksha Singh', 'loginid': 'Newprod', 'application': 'PACE', 'short_desc': 'Add Employee/Contractor Access : Unix - Application TLA Access - NON-PROD'}
    conf_dict    = { 'host': hostname, 'username': ansible_user, 'password': ansible_password, 'gidnumber': gidnumber_conf, 'loginshell': loginshell_conf }


    #Initiating login function to connect remote server where the LDAP command are executed.                
    login(conf_dict["host"], conf_dict["username"], conf_dict["password"])
    #login(host, username, password)

    group_value = itsm_dict['group'].split('\n')
    
    for i in range(0,len(group_value)):
      group_value[i] = re.sub(r'\s+', '',group_value[i])
      print ("Group is :" +group_value[i]) 



    #Finding the ticket is for PROD or NON-PROD from short description in STASK
    '''short_desc      = itsm_dict['short_desc']
    findnonprod     = re.search('Application TLA Access - NON-PROD', short_desc, re.IGNORECASE)
    findprod        = re.search('Application TLA Access - PROD', short_desc, re.IGNORECASE)
    prodnonprod     = ""
    if findnonprod:
        prodnonprod = "nonprod"
    elif findprod:
        prodnonprod = "prod"'''

    print ("Name is :" +itsm_dict["name"])
    print("Short description is : " +itsm_dict["short_desc"])   #### testing 
    print ("LOGIN ID is :" +itsm_dict["loginid"])
    print ("SCTASK number is :" +itsm_dict["stask_num"])

    # Loop through the group values
    for g in group_value:
      parts = g.split('-')
      if len(parts) == 2:
        prefix, suffix = parts
        application = prefix
        if suffix in ['INT', 'DEV', 'UAT', 'SYS']:
            application = prefix
            prodnonprod = 'nonprod'
        elif suffix == 'PROD':
            application = prefix
            prodnonprod = 'prod' 

    print(application)
    print(prodnonprod)

    
    #Check whether user exists or not using "check_user_exist" function
    print("we are going to next function")
    itsm_dict["loginid"] = itsm_dict["loginid"].lower()
    print("We are going to call check user exits function")
    tlastat = check_user_exist(itsm_dict["loginid"])
    print ("User stat "+str(tlastat))
    account_stat = tlastat.split("_")
    #print("accstat "+account_stat[0]+"|"+account_stat[1])
    
    
    #User directory creation for new account
    #/home/home01/login id -  for odd months and /home/home02/login id -  for even months
    dates   = datetime.datetime.now().strftime("%m")
    oddeven = int(dates)%2
    if oddeven == 0:
        homedirectory = "/home/home02/"
    else:
        homedirectory = "/home/home01/"


    #If account exists, check for disabled account or only TLA addition
    if account_stat[0] == "User exist":
        #ntaccount -L -u lk147-sa -a disableautoprovision
        try:
            if account_stat[1] == "dis":
                autoprov = execute_command("ntaccount -L -u _"+itsm_dict["loginid"]+" -a disableautoprovision",10)
                autoprovchk    = "".join(str(autoprov).split())
                print ("Find autoprovision for disabled user "+autoprov)
                #print("autoprov |"+ autoprovchk +"|\n")
                if "11ROWSRETURNED" not in autoprovchk:
                    print("This is an auto provision case!")
                    sys.exit()
                #else:
                   #print("This is not an auto provision case!")
                   #sys.exit()
            else:
                autoprov = execute_command("ntaccount -L -u "+itsm_dict["loginid"]+" -a disableautoprovision",10)
                autoprovchk    = "".join(str(autoprov).split())
                print ("Find autoprovision for enabled user "+autoprov)
                #print("autoprov |"+ autoprovchk +"|\n")
                if "11ROWSRETURNED" not in autoprovchk:
                    print("This is an auto provision case!")
                    sys.exit()
                #else:
                #   print("This is not an auto provision case! enable ")
                #   sys.exit()
                   
        except Exception as e:
            logger.error("Find auto provision for user exception : "+str(e))
            print("Exception: ",e)
            #raise Exception("ntaccount -L -u account -a tla   command execution error!")

        #Accounts starting with "_" is disabled accounts, which need to be enabled.
        
        if account_stat[1] == "dis":
            
            #enable_account function will enable account
            ea = enable_account("_"+itsm_dict["loginid"], itsm_dict["stask_num"])
            print ("Enable account "+str(ea))
            #print("ea "+str(e)a)
           
            
            #Remove "_" of account to add TLAs and Hosts    
            itsm_dict["loginid"] = re.sub("^_", "", itsm_dict["loginid"])
           
            #Remove existing TLAs for enabled accounts    
            rt = remove_tlas(itsm_dict["loginid"], itsm_dict["stask_num"])
            print ("Remove existing TLAs "+str(rt))

            #Remove existing Hosts for enabled accounts
            rh = remove_hosts(itsm_dict["loginid"], itsm_dict["stask_num"])
            print ("Remove existing hostss "+str(rh))

            #Remove account from group for enabled accounts
            itsm_dict["loginid"] = re.sub("^_", "", itsm_dict["loginid"])
            rg = remove_group(itsm_dict["loginid"], itsm_dict["stask_num"])
            print ("Remove account from groups "+str(rg))
            
            cud  = create_usrdir(homedirectory,itsm_dict["loginid"], conf_dict["password"],"exist")
            print ("Create user directory for new account -"+str(cud))

        #Accounts exists and not disabled, New TLA addition.
        #print(itsm_dict["application"],itsm_dict["loginid"],prodnonprod,itsm_dict["stask_num"])
        tgmn = tla_group_mgmnt(application,itsm_dict["loginid"],prodnonprod,itsm_dict["stask_num"])
        print ("New TLA and Group addition for existing account "+str(tgmn))
        success_msg += "New TLA and Group added for account. "
        print(success_msg+", success")

    #If account does not exists, new account is added with TLA, Host and Group addition
    elif(account_stat[0] == "User does not exist"):
        
        print ("Account "+itsm_dict["loginid"]+" does not exist!")
        print ("Adding new account "+itsm_dict["loginid"])
       
        #Given name should have first name and last name, or else first name is taken as last name
        givenname = itsm_dict["name"].split(" ")
        if len(givenname) == 2:
                itsm_dict["firstname"] = givenname[0]
                itsm_dict["lastname"]  = givenname[1]
        else:
                itsm_dict["firstname"] = givenname[0]
                itsm_dict["lastname"]  = givenname[0]

 
        #Add new Account
             
        aa = add_account(itsm_dict["loginid"], itsm_dict["firstname"], itsm_dict["lastname"], conf_dict["loginshell"], homedirectory+itsm_dict["loginid"], conf_dict["gidnumber"], itsm_dict["stask_num"])
        print ("Add account command status -"+str(aa))

        #TLA and Group management
            
        tgmn = tla_group_mgmnt(application,itsm_dict["loginid"],prodnonprod,itsm_dict["stask_num"])
        print ("TLA and Group management -"+str(tgmn))

        #Create user directory for new account
        
        cud  = create_usrdir(homedirectory,itsm_dict["loginid"], conf_dict["password"],"new")

        print ("Create user directory for new account -"+str(cud))
        
        print(success_msg+", success")

main()

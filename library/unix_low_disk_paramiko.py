#########################################################################################
#  Description: This is a ansible custom module which can be used to connect to any
#		device like unix/storage/network via ssh using paramiko module and
#		execute the commands.
#  Developer:   Pratiti Srivastava(pratiti.srivastava@wipro.com)
#  Version:     1.0.0
#  Orgnization: Wipro Ltd
#########################################################################################

from ansible.module_utils.basic import AnsibleModule
import paramiko
import time
import socket
import re
import sys
#import traceback
from datetime import date
today = date.today().strftime('%Y%m%d')

#####INPUT PARAMETERS#######################################################################
module = AnsibleModule(
    argument_spec={
        "host": {"required": True, "type": "str"},
        "username_unix": {"required": True, "type": "str"},
        "password_unix": {"required": True, "type": "str"},
        "FSname": {"required": True, "type": "str"}
    }
)


remote_host = module.params["host"]
uname = module.params["username_unix"]
passwd = module.params["password_unix"]
FS_name = module.params["FSname"]

########################################################

filesize = '10M'
countdown = '20'
threshold_limit = 75  # value is added for testing purpose

shell = None
client = None
timeout = 20
response = ""
failed_msg = None

shell = None
client = None
timeout = 20
array = []
user2grp = {
    'ALN': 'ALN Batch Support',
	'moo': 'EMS Moogsoft',
	'EBP': 'EBP support',
	'so51': 'EMS SOA',
	'Oracle': 'GDP OPS Oracle',
    'dba': 'GDP OPS Oracle',
    'oinstall': 'GDP OPS Oracle',
	'confluence': 'IT ENG HFS Infrastructure',
	'edm': 'EDM Support',
	'to50': 'EMS JFAS',
	'cam ': 'CAM',
	'Impala': 'GDP OPS Hadoop',
	'Sybase': 'GDP OPS Sybase',
	'Cant able to login looks like HFS': 'IT ENG HFS Infrastructure',
	'csx': 'Colline Support',
	'Hrs': 'HRA-Support',
	'aip': 'AIP Support',
	'icr': 'IRAS Reporting Support',
	'ohs': 'EMS JFAS',
	'python': 'GDP OPS Hadoop',
	'999': 'EMS DOCKER',
	'tsm': 'Storage Ops Backups',
	'lawson': 'BPP Support',
	'AIX server': 'GDP OPS Sybase',
	'Hadoop': 'GDP OPS Hadoop',
	'mts': 'MTS SUPPORT',
	'odeploy ': 'EMS JFAS',
	'pce': 'Pace-Pare Support',
	'pae': 'PAE Support ',
	'lme': 'LME Support',
	'idf': 'IDF - Identity Federation',
	'CCR': 'CCR / MR',
	'MarkLogic': 'GDP OPS MarkLogic',
	'bnz': 'Global Entitlements Hub',
	'pre': 'Pace-Pare Support',
	'oxd': 'OXD Support',
	'wilytech': 'EMS APM',
	'uatw': 'EMS JFAS',
	'prodwlp0': 'EMS JFAS',
	'ovd': 'EMS JFAS',
	'IDM': 'EMS datastage',
	'dstage': 'EMS DataStage',
	'sld': 'Global Securities Lending',
	'CIE': 'EMS CI',
	'WAA': 'EMS WAS',
	'RIV': 'ISS Charles River',
	'OSM': 'EMS Pandora FMS',
	'dis': 'Summit Support Team',
	'plc': 'TLM-Support',
	'zds': 'EMS DataStage',
	'IS': 'ISS Eagle',
	'cbs': 'Treasury Passport Support',
	'tdp': 'TLM-Support',
	'gxd': 'GXS Support',
	'lgd': 'LGD Tech Support',
	'OER': 'EMS SOA',
	'FGL': 'FGL-ERP GL AP ePRO AM AR Bil - FGL Production Support',
	'aml': 'Compliance Systems Support',
	'erm': 'ERM',
	'kaf': 'EMS EAI',
	'dtg': 'Egate Support',
	'mqm': 'EMS EAI',
	'rtv': 'IT Eng EMS APM',
	'mlg': 'GDP OPS MarkLogic',
	'ict': 'Incorta L3 Support',
	'pem': 'pem support',
	'plb': 'TLM-Support',
	'tfc': 'GFA-L1-Support',
	'ldi': 'ldi support',
	'cdr': 'cdr support',
	'dsadm': 'EMS DataStage',
	'cdm': 'EMS Code Migration',
	'qta': 'GSY:NTGL Applications',
	'sas': 'SAS',
	'ELM': 'GFA-L1-Support',
	'oes': 'EMS SOA',
    'pms': 'EMS Pandora FMS',
    'doc': 'EMS Docker',
    'controlm': 'Control-M Admins - Distributed',
    'cdq': 'CDQ Architecture Support',
    'tco': 'EMS Monitoring',
    'bcw': 'BCW',
    'wds': 'Wealth Data Systems Support',
    'plf': 'TLM-Support',
    'emadmin': 'Control-M Admins - Distributed',
    'bas': 'BI & Analytics Team',
    'dar': 'XACT Ops Support',
    'bnx': 'CDR Support',
    'gfb': 'GFB APP SUPPORT',
    'col': 'Colline Support',
    'dia': 'DIA - Accounting Data Warehouse',
    'upp': 'MTS Support',
    'ofe': 'Compliance Systems Support',
    'its': 'ISS Charles River',
    'irl': 'GFA-L1-Support',
    'cha': 'CAST Support',
    'kfe': 'EMS EAI',
    'oud': 'Oracle LDAP Support',
    'nwa': 'Inbox Support',
    'eai': 'EMS EAI',
    'epv': 'EPV Engineering',
    'ixs': 'PMEI',
    'ghe': 'EMS GitHub',
    'idp': 'ISS Active Equity',
    'rpm': 'IRAS Web Services Support',
    'prodetl': 'EPM-Warehouse',
    'laa': 'IT Eng EMS Elk'
}

# 7-bit C1 ANSI sequences
ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')

def login(hostn, uname, pwd):
    global client
    global shell
    global failed_msg

    client = paramiko.SSHClient()

    try:
        # logger.info("Trying to establish connection with server ")
        # logger.info("IPAddres : " + hostn + ", Username : " + uname)
        # logger.info("Establishing ssh connection")
        client.load_system_host_keys()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect(hostname=hostn, username=uname, password=pwd)
        # logger.info("Successfully connected to Server ")
        shell = client.invoke_shell()
    except paramiko.AuthenticationException as authenticationException:
        failed_msg = "Authentication failed, please verify your credentials."
        module.fail_json(changed=False, msg=failed_msg)
        sys.exit()
    except socket.error as e:
        # logger.error("Communication problem : "+str(e))
        failed_msg = "Server communication problem."
        module.fail_json(changed=False, msg=failed_msg)
        # raise Exception("Entered IP Address is wrong")
        sys.exit()
    except paramiko.BadHostKeyException as badHostKeyException:
        # logger.error("Unable to verify server's host key: "+str(badHostKeyException))
        failed_msg = "Unable to verify server's host key."
        module.fail_json(changed=False, msg=failed_msg)
        # raise Exception("Unable to verify server's host key")
        sys.exit()
    except paramiko.SSHException as sshException:
        # logger.error("Unable to establish SSH connection: "+str(sshException))
        failed_msg = "Unable to establish SSH connection."
        module.fail_json(changed=False, msg=failed_msg)
        # raise Exception("Unable to establish SSH connection")
        sys.exit()
    except Exception as e:
        # logger.error("Exception : "+str(e))
        failed_msg = "Exception: "+str(e)
        module.fail_json(changed=False, msg=failed_msg)
        # raise Exception("Exception")
        sys.exit()


def execute_command(command, sleeptime=1):
    command = command + "\n"
    shell.send(command)
    time.sleep(sleeptime)
    receive_buffer = shell.recv(9999).decode("utf-8")
    return receive_buffer

	# Function to close the server connection


def clean_up():
    client.close()
    # log.info("-------------Successfully closed Server connection-------------")


def linuxcheck():
    global response
    execute_command("\n")
    

    if (str(FS_name) == '/var'):
        month_Old_Files_messages = execute_command(
            "find /var/log/messages-* -type f -mtime +30 -exec ls -l {} \;")
        month_Old_Files_messages = "\n".join(
            month_Old_Files_messages.split("\n")[1:-1])

        month_Old_Files_secure = execute_command(
            "find /var/log/secure-* -type f -mtime +30 -exec ls -l {} \;")
        month_Old_Files_secure = "\n".join(
            month_Old_Files_secure.split("\n")[1:-1])

        if (len(month_Old_Files_messages) == 0 and len(month_Old_Files_secure) == 0):
            output = "No files found in /var directory older than 30 days\n"
            response=response+output+"\n\n"
            
            # month_Old_Files_messages = "No Files Found!"
        else:
            month_Old_Files = month_Old_Files_messages + "\n" + month_Old_Files_secure
            month_Old_Files = ansi_escape.sub('', month_Old_Files)
            output = "Files Older than 1 month under "+str(FS_name)
            response=response+output+"\n\n"
            output = month_Old_Files
            response=response+output+"\n\n"
            
        large_size_files = execute_command(
            "find /var/log/ -xdev -type f -size +100M -exec du -sh {} ';' | sort -rn | head")
        large_size_files = "\n".join(large_size_files.split("\n")[1:-1])

        if (len(large_size_files) == 0):
            output = "No large size files found in /var directory\n"
            
        else:
            large_size_files = ansi_escape.sub('', large_size_files)
            output = "Large size files under directory "+ str(FS_name)
            response=response+output+"\n\n"
            
            
            output=large_size_files
            response=response+output+"\n\n"
            

    df_usage=execute_command("df -hk "+FS_name)
    # print("||",df_usage,"||")
    df_usage="\n".join(df_usage.split("\n")[2:-1])
    df_usage=ansi_escape.sub('', df_usage)
    # print("||",df_usage,"||")

    output="Disk Utilization \n"+ df_usage+ "\n\n"
    response=response+output+"\n\n"
    
    lsld=execute_command("ls -ld "+FS_name)
    lsld="\n".join(lsld.split("\n")[1:-1])
    lsld=ansi_escape.sub('', lsld)
    output="File system owners details for "+FS_name
    response=response+output+"\n\n"
    
    output=lsld
    response=response+output+"\n\n"

    ownr=lsld.split(" ")[3]
    # print("owner ", ownr)
    topuser=ownr.strip()



    listofvalue=df_usage.split(" ")
    stripvalue=list(filter(None, listofvalue))
    print(stripvalue)
    percentdf=stripvalue[-2].replace('%', '')
    # print(float(percentdf)," >= ",float(threshold_limit))

    if float(percentdf) >= float(threshold_limit):
        output= 'The current FS Utilization is ' + str(percentdf) + \
                '% and is above the threshold value of ' + str(threshold_limit)+'%'
        response=response+output+"\n\n"
        
    else:
        output='The current FS Utilization is ' + str(percentdf) + '%'
        response=response+output+"\n\n"

    # find_files = "du -xm "+FS_name+" |  sort -rn | head -"+countdown
    find_files="find "+FS_name+" 2>/dev/null -xdev -type f -size +" + \
    filesize+" -print | xargs ls -lh | sort -k5,5 -h -r | head -"+countdown
    # find_filess = "find "+FS_name+" -xdev -size "+filesize+" -type f -exec ls -l {} \; | awk '{ print $5, $6, $7, $8, $9 }' | sort -nr | head -"+countdown
    # print("find_filess ",find_filess)
    listfiles=execute_command(find_files, 20)
    listfiles="\n".join(listfiles.split("\n")[1:-1])
    if len(listfiles) == 0:
        listfiles="No Files Found!"
    else:
        listfiles=ansi_escape.sub('', listfiles)
        output="\nTop files under "+str(FS_name)
        response=response+output+"\n\n"
        
        output=listfiles
        response=response+output+"\n\n"
        

    dt=execute_command("date")
    dt="\n".join(dt.split("\n")[1:-1])
    output="Date "
    response=response+output+"\n\n"
    output=dt
    response=response+output+"\n\n"
    
    if topuser in user2grp:
         output = " Assignment Group is: " + user2grp[topuser]
         response=response+output
 
    else:
        output = " No assignment group present for " + topuser
        response=response+output+"\n\n"
        
        
def aixcheck():
    global response
    execute_command("\n")

    df_usage = execute_command ("df -k "+FS_name)
    df_usage = df_usage.split("\n")[2]
    
    output = "Disk Utilization \n" + df_usage + "\n\n"
    response=response+output+"\n\n"
    lsld = execute_command ("ls -ld "+FS_name)
    lsld = "\n".join(lsld.split("\n")[1:-1])
    output= "File system owners details for " + FS_name
    response=response+output+"\n\n"
    output = lsld
    response=response+output+"\n\n"

    
    ownr = lsld.split(" ")[3]
    #print("owner ", ownr)
    topuser = ownr.strip()	

    
    listofvalue = df_usage.split(" ")
    stripvalue 	= list (filter (None, listofvalue))
    percentdf 	= stripvalue[-2].replace('%','')

    if float(percentdf) >= float(threshold_limit):
        output = 'The current FS Utilization is ' + str(percentdf) + '% and is above the threshold value of ' +str(threshold_limit)+'%'
        response=response+output+"\n\n"
    else:
        output = 'The current FS Utilization is ' + str(percentdf) + '%'
        response=response+output+"\n\n"
            
    find_files = "du -sm "+FS_name+" |  sort -rn | head -"+countdown
    listfiles = execute_command(find_files,20)
    listfiles = "\n".join(listfiles.split("\n")[1:-1])
    if len(listfiles) == 0:
        listfiles = "No Files Found!"
    else:
        output = "\nTop files under "+str(FS_name)
        output = listfiles

    dt = execute_command ("date")
    dt = "\n".join(dt.split("\n")[1:-1])

    output = "Date "
    output = dt
    
    if topuser in user2grp:
         output = " Assignment Group is:  " + user2grp[topuser]
         response=response+output
 
    else:
        output = "No assignment group present for " + topuser
        response=response+output+"\n\n"
        
def solarischeck():
    global response
    execute_command("\n")
    df_usage = execute_command ("df -kh "+FS_name)
    df_usage = df_usage.split("\n")[2]
    
    output = "Disk Utilization \n",df_usage,"\n\n"
    response=response+output+"\n\n"
    lsld = execute_command ("ls -ld "+FS_name)
    lsld = "\n".join(lsld.split("\n")[1:-1])
    output = "File system owners details for ",FS_name
    response=response+output+"\n\n"
    output = lsld
    response=response+output+"\n\n"


    ownr = lsld.split(" ")[3]
    #print("owner ", ownr)
    topuser = ownr.strip()
    listofvalue = df_usage.split(" ")
    stripvalue 	= list (filter (None, listofvalue))
    percentdf 	= stripvalue[-2].replace('%','')

    if float(percentdf) >= float(threshold_limit):
        output = 'The current FS Utilization is ' + str(percentdf) + '% and is above the threshold value of ' +str(threshold_limit)+'%'
        response=response+output+"\n\n"
    else:
        output = 'The current FS Utilization is ' + str(percentdf) + '%'
        response=response+output+"\n\n"
            
    find_files = "du -h "+FS_name+" |  sort -rn | head -"+countdown
    #find_files = "find "+FS_name+" -xdev -type f -size +"+filesize+" -print | xargs ls -lh | sort -k5,5 -h -r | head -"+countdown
    #find_filess = "find "+FS_name+" -xdev -size "+filesize+" -type f -exec ls -l {} \; | awk '{ print $5, $6, $7, $8, $9 }' | sort -nr | head -"+countdown
    #print("find_filess ",find_filess)
    listfiles = execute_command(find_files,20)
    listfiles = "\n".join(listfiles.split("\n")[1:-1])
    if len(listfiles) == 0:
        listfiles = "No Files Found!"
    else:
        output = "\nTop files under "+str(FS_name)
        response=response+output+"\n\n"
        output = listfiles
        response=response+output+"\n\n"

    dt = execute_command ("date")
    dt = "\n".join(dt.split("\n")[1:-1])
    output = "Date "
    response=response+output+"\n\n"
    output = dt
    response=response+output+"\n\n"
        
    if topuser in user2grp:
         output = " Assignment Group is:  " + user2grp[topuser]
         response=response+output
 
    else:
        output = "No assignment group present for " + topuser
        response=response+output+"\n\n"    


def main():

    global response
    global failed_msg
    
    output=" Low Disk \n"
    response=response+output+"\n\n"
    # login to server
    login(remote_host, uname, passwd)
    execute_command(today)
    output="Server --> "+remote_host+"\n\n"
    response=response+output+"\n\n"
    
    execute_command("\n")
    os_flavour=execute_command("uname -s").strip()
    if "Linux" in os_flavour:
        linuxcheck()
    elif "Solaris" in os_flavour:
        solarischeck()
    elif "AIX" in os_flavour:
        aixcheck()			
    else:
        linuxcheck()
        
    module.exit_json(changed=True, result=response)	

    clean_up()
    print(response)

if __name__ == "__main__":
  main()

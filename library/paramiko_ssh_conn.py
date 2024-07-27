#########################################################################################
#  Description: This is a ansible custom module which can be used to connect to any 
#		device like unix/storage/network via ssh using paramiko module and 
#		execute the commands.
#  Developer:   Omprakash Tiwari(omprakash.tiwari@wipro.com)
#  Version:     1.0.0
#  Orgnization: Wipro Ltd
#########################################################################################

from ansible.module_utils.basic import AnsibleModule
import paramiko
import time
import socket
import re
import sys
from datetime import date

#####INPUT PARAMETERS#######################################################################
module = AnsibleModule(
    argument_spec={
        "host": {"required": True, "type": "str"},
        "username": {"required": True, "type": "str"},
        "password": {"required": True, "type": "str"},
        "commands": {"required": True, "type": "list"},
    }
)


remote_host = module.params["host"]
uname = module.params["username"]
passwd = module.params["password"]
cmds = module.params["commands"]
ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')

########################################################

shell = None
client = None
timeout = 20
response= ""
failed_msg= None


def login(hostn, uname, pwd):
    global client
    global shell
    global failed_msg
   
    client = paramiko.SSHClient()

    try:
        client.load_system_host_keys()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect(hostname=hostn ,username=uname,password=pwd)
        shell = client.invoke_shell()
    except paramiko.AuthenticationException as authenticationException:
        failed_msg=("Authentication failed, please verify your credentials. ")
        module.fail_json(changed=False, msg=failed_msg)
        sys.exit()
    except socket.error as e:
        failed_msg= ("Target host communication problem.")
        module.fail_json(changed=False, msg=failed_msg)
        sys.exit()
    except paramiko.BadHostKeyException as badHostKeyException:
        failed_msg= ("Unable to verify server's host key. ")
        module.fail_json(changed=False, msg=failed_msg)
        sys.exit()
    except paramiko.SSHException as sshException:
        failed_msg= ("Unable to establish SSH connection. ")
        module.fail_json(changed=False, msg=failed_msg)
        sys.exit()
    except Exception as e:
        failed_msg= ("Exception: Unable to connect to target host.")
        module.fail_json(changed=False, msg=failed_msg)
        sys.exit()

def execute_command(command, sleeptime=1):
    command = command + "\n"
    shell.send(command)
    time.sleep(sleeptime)
    receive_buffer = shell.recv(9999).decode("utf-8")
    return receive_buffer
        
def main():
    try:
        global response
        global failed_msg
        
        # login to server
        login(remote_host,uname,passwd)
        for cmd in cmds:
            output = execute_command(cmd, sleeptime=5)
            if('YYYYMMDD' in output):
                today = date.today().strftime("%Y%m%d")
                execute_command(today)
                output = execute_command(cmd, sleeptime=5)
            if('[sudo] password' in output):
                output=execute_command(passwd)
            response=response+output+"\n\n"
        response = ansi_escape.sub('',response)
        module.exit_json(changed=True, result=response)
    except Exception as e:
        failed_msg= f'error: {e}'
        module.fail_json(changed=False, msg=failed_msg)
    finally:
        client.close()
        
main()
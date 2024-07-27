"""
 coding: utf-8
 Module conversion done by Jithin jeffry
 modified Date : 15-01-2024
 This module will execute the given command from ansible and provide necessary output.

"""
#Import necessary packages
import time
import socket
import paramiko
from ansible.module_utils.basic import AnsibleModule

#######Ansible Implementation ###############


def get_argument_spec():
    """
    Takes the input as serverip,username,password and command
    :return:
    """
    module_args = dict(
        serverip=dict(type="str", required=False),
        username=dict(type="str", required=False),
        password=dict(type="str", required=False, no_log=True),
        commandstring=dict(type="str", required=False)
    )
    return module_args

##########################################

############################

def cpu_cmd(cmd):
    """
    This function will execute the given command using
    paramiko module
    """
    ssh_client = paramiko.SSHClient()
    ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh_client.connect(hostname=SERVER_IP, username=USER_NAME, password=PASSWORD)
    #print(ssh_client)
    #ssh_stdin, ssh_stdout, ssh_stderr = ssh_client.exec_command(command)
    con = ssh_client.invoke_shell()

    output = con.recv(9999)
    val = []
    for i in cmd:
        #print(output)
        #con.send(command+"\n")
        con.send(i+"\n")
        time.sleep(2)
        out = ""

        if con.recv_ready():
            output = con.recv(9999)
        out = output.decode("UTF-8")
        val.append(out)

    return "\n".join(val)

if __name__ == '__main__':
    try:

        MODULE = AnsibleModule(argument_spec=get_argument_spec())

        SERVER_IP = MODULE.params["serverip"]
        USER_NAME = MODULE.params["username"]
        PASSWORD = MODULE.params["password"]
        COMMAND_STRING = MODULE.params["commandstring"]
        COMMAND = COMMAND_STRING.split(";")

        RESULT = {
            "status": "",
            "log": "",
            "error": "",
        }
        STATUS = "Failure"

        RESULT["log"] = cpu_cmd(COMMAND)
        STATUS = "Success"

    except paramiko.AuthenticationException as authentication_exception:
        #logging.error("Authentication failed, please verify your credentials : %s" % authenticationException)
        RESULT["error"] = "Authentication failed, please verify your credentials"
    except socket.error as socket_error:
        #logging.error("Communication problem : %s" % e)
        RESULT["error"] = "Entered IP Address is wrong"
    except paramiko.BadHostKeyException as bad_host_key_exception:
        #logging.error("Unable to verify server's host key: %s" % badHostKeyException)
        RESULT["error"] = "Unable to verify server's host key"
    except paramiko.SSHException as ssh_exception:
        #logging.error("Unable to establish SSH connection: %s" % sshException)
        RESULT["error"] = "Unable to establish SSH connection"
    except Exception as general_error:
        #logging.error("Something went wrong : %s" % e)
        RESULT["error"] = "Something went wrong"
    finally:
        RESULT["status"] = STATUS
        MODULE.exit_json(changed=True, output=RESULT)

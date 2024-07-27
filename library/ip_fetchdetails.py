from __future__ import absolute_import, division, print_function
from infoblox_client import connector,objects,utils
from ansible.module_utils.basic import AnsibleModule
import requests
import json

module = AnsibleModule(
    argument_spec={
        "ipaddress": {"required": True, "type": "str"},
        "username": {"required": True, "type": "str"},
        "password": {"required": True, "type": "str"},
        "host": {"required": True, "type": "str"},
    }
)

ip_address = module.params["ipaddress"]
Username = module.params["username"]
Password = module.params["password"]
Host = module.params["host"]

result = ""

opts = {'host': Host, 'username': Username, 'password': Password}
conn = connector.Connector(opts)
def main(ip_address,result):
    try:
        ip_object = conn.get_object("ipv4address", {"ip_address": ip_address}) 
        ref_obj =  ip_object[0]["_ref"]
        mesg = "Ip details fetched successfully."
        module.exit_json(changed=True,ip_record=ip_object,output=mesg)
    except Exception as e:
        exp_msg = f"Failed to get IP details: {ip_address}" + str(e)
        module.fail_json(changed=False,msg=exp_msg)
    finally:
        conn.logout()

if __name__ == "__main__":
    main(ip_address,result)

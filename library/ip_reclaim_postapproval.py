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
        ip_state = ip_object[0]["status"]
        if ip_state == 'USED':
          ref="https://" + Host + "/wapi/v2.0/" + ref_obj
          session=requests.Session()
          session.auth=(Username,Password)
          session.verify = False
          r=session.delete(ref)   
          mesg=ip_address + "- Successfully reclaimed IP address."
          module.exit_json(changed=True,ip_record=ip_object,output=mesg)
        else:
          err_msg=ip_address + "- Ip status is UNUSED."
          module.fail_json(changed=False, msg=err_msg)
    except Exception as e:
        exp_msg = f"Failed to reclaim IP address: {ip_address}.\n" + str(e)
        module.fail_json(changed=False, msg=exp_msg)
    finally:
        conn.logout()

if __name__ == "__main__":
    main(ip_address,result)

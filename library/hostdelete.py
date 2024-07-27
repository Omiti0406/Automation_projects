from __future__ import absolute_import, division, print_function
from infoblox_client import connector,objects,utils
from ansible.module_utils.basic import AnsibleModule
import requests
import json

module = AnsibleModule(
    argument_spec={
        "hostRecord": {"required": True, "type": "str"},
        "username": {"required": True, "type": "str"},
        "password": {"required": True, "type": "str"},
        "host": {"required": True, "type": "str"},
    }
)

host_record = module.params["hostRecord"]
Username = module.params["username"]
Password = module.params["password"]
Host = module.params["host"]

result = ""

def main(result,host_record):
    try:
        hostrecord_rest_url = "https://" + Host + "/wapi/v2.0/" + "record:host?_return_fields%2B=aliases&name=" + host_record
        ip_object=requests.get(url=hostrecord_rest_url,verify=False,auth=(Username,Password))
        r2=ip_object.json()
        mesg="Fetched host details successfully" + host_record
        module.exit_json(changed=True,host_record=r2,output=mesg)
    except Exception as e:
        exp_msg = f"Failed to fetch host details for: {host_record}" + str(e)
        module.fail_json(changed=False, msg=exp_msg)
    finally:
        conn.logout()

if __name__ == "__main__":
    main(result,host_record)

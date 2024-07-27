# 
# Plugin to enable toil savings in Ansible executions
# (c) 2021 Northern Operating Solutions
# (c) Platform Engineering Team
# 
from __future__ import (absolute_import, division, print_function)
__metaclass__ = type

# Not only visible to ansible-doc, it also 'declares' the options the plugin requires
# and how to configure them.

DOCUMENTATION = '''
    callback: toil_savings
    callback_type: aggregate
    requirements:
         - enable in configuration
    description: 
         - This callback just adds toil savings per host to the play stats.
           Toils savings stat are then pushed to kafka topic so that consumer can consume the details.
    options:
         toil_savings:
            description: Toil savings in hours per host in execution
            default: 8 hours
    output:
         json_object:
            description: Json object which to be sent to Kafka topics at playbook end
            default: '{
                  "@version"   => "1",
                  "@timestamp"   => 2021-05-11T10:43:20.415Z,
                  "name"   => "TECH4TECH_DEMO",
                  "tla"   => "pag",
                  "team_name"   => "Platform Automation Engineering",
                  "owner_email"   => "Platform_Automation_Engineering@ntrs.com",
                  "start"   => "2021-05-11T10:25:46.392356Z",
                  "target"   => "ut14838.ntrs.com",
                  "end"   => "2021-05-11T10:25:48.788066Z",
                  "run_status"   => "success",
                  "user_name" => "admin"
                  "toil_hrs_saved"   => 0.15
               }'
'''
 
from datetime import datetime
from datetime import timezone
from dateutil import tz
import json 
import os 
import re
import ssl
import certifi
from ansible.plugins.callback import CallbackBase
from kafka import KafkaProducer
from kafka.errors import KafkaError
from confluent_kafka import Producer

try:
    from __main__ import cli
except ImportError:
    cli = None

class CallbackModule(CallbackBase):
    """
    This callback module collects playbook run statistics and send it to Kafka Topic from where consumer can eaisly access.
    """
    CALLBACK_VERSION = 1.0
    CALLBACK_TYPE = 'aggregate'
    CALLBACK_NAME = 'toil-savings-wipro'
    
    # only needed if you ship it and don't want to enable by default
    # CALLBACK_NEEDS_WHITELIST = True

    #def __init__(self, display=None):
    def __init__(self):
        
        #  self.disabled = False
        
        # make sure the expected objects are present, calling the base's __init__
        #super(CallbackModule, self).__init__(display=display)
        super(CallbackModule, self).__init__()

        # start the timer when the plugin is loaded, the first play should start a few milliseconds after.
        self.start_time = datetime.now()
        self.result = None
        self.effort = "0" 
        self.play = None
        self.playbook_name = None
        self.jobtemplate_name = None
        self.host = None
        self.playbook = None
        self.key = 'awx_job_template_name'
        self.hosts = []
        self.usage_data = {}
        self.team = None
        self.email = None
        self.tla = None
        self.run_status = None
        self.metering_metric = None
        self.iterations = None
        self.TOIL_SAVINGS_VARIABLE = 'toil_savings'
        self.TEAM_NAME = 'team_name'
        self.OWNER_EMAIL = 'owner_email'
        self.ITERATIONS = 1
        self.METERING_METRIC = 'metering_metric'
        self.TLA = 'tla'
        self.user = None
        self.launchkey = 'tower_job_launch_type'
        self.kafka_topic = 'nt_elk_pag_filebeat'
        if "UAT_SSL_certificate" in os.environ:
          self.ssl_cert = os.environ.get("UAT_SSL_certificate")
          self.ssl_key = os.environ.get("UAT_SSL_key")
          self.passwo = os.environ.get("UAT_key_password")
          self.caRootLocation = os.environ.get("CA_ROOT_certificate")
          self.kafkaBrokers='lnaukfe0002.ntrs.com:9092,lnaukfe0004.ntrs.com:9092,lnaukfe0006.ntrs.com:9092,lnaukfe0001.ntrs.com:9092,lnaukfe0003.ntrs.com:9092,lnaukfe0005.ntrs.com:9092'
        elif "PROD_SSL_CERTIFICATE" in os.environ:
          self.ssl_cert = os.environ.get("PROD_SSL_CERTIFICATE")
          self.ssl_key = os.environ.get("PROD_SSL_KEY")
          self.passwo = os.environ.get("PROD_KEY_PASSWORD")
          self.caRootLocation = os.environ.get("CA_ROOT_CERTIFICATE")
          self.kafkaBrokers='lnapkfe0002.ntrs.com:9092,lnapkfe0004.ntrs.com:9092,lnapkfe0006.ntrs.com:9092,lnapkfe0008.ntrs.com:9092,lnapkfe0007.ntrs.com:9092,lnapkfe0009.ntrs.com:9092,lnapkfe0011.ntrs.com:9092,lnapkfe0013.ntrs.com:9092'
        else:
          self.kafkaBrokers='lnadkfe0022.ntrs.com:9094,lnadkfe0024.ntrs.com:9094,lnadkfe0026.ntrs.com:9094'
          
    # Routine to take care of event when playbook execution starts 
    def v2_playbook_on_start(self, playbook):
        self.playbook = playbook
        self.playbook_name = os.path.basename(self.playbook._file_name)
 
    # Routine to take care of event when every play execution starts 
    def v2_playbook_on_play_start(self, play):
    
        self.play = play
        play_vars = play._variable_manager.get_vars()
        var_mgr = play.get_variable_manager()
        e_vars = var_mgr.extra_vars
        self.hosts = play_vars['groups']['all']
        
        if play_vars[self.launchkey] == 'scheduled':
           self.user = play_vars['tower_schedule_name']
        else:
           self.user = play_vars['tower_user_name']
           self.team = e_vars.get(self.TEAM_NAME)
        
        #self._display.display("play vars %s" % play_vars)
       
        if self.key in play_vars.keys():
           self.playbook_name =  play_vars[self.key] 

    # this is only event we care about for display, when the play shows its summary stats; the rest are ignored by the base class
    def v2_playbook_on_stats(self, stats):
        end_time = datetime.now()
        runtime = end_time - self.start_time

        play_vars = self.play._variable_manager.get_vars()
        var_mgr = self.play.get_variable_manager()
        e_vars = var_mgr.extra_vars
        self.hosts = play_vars['groups']['all']
        
        if e_vars.get(self.TOIL_SAVINGS_VARIABLE):
           self.effort = e_vars.get(self.TOIL_SAVINGS_VARIABLE)
           self.email = e_vars.get(self.OWNER_EMAIL)
           self.tla = e_vars.get(self.TLA)
        else:
           self.effort = play_vars['hostvars'][self.hosts[0]][self.TOIL_SAVINGS_VARIABLE]
           self.team = play_vars['hostvars'][self.hosts[0]][self.TEAM_NAME]
           self.email = play_vars['hostvars'][self.hosts[0]][self.OWNER_EMAIL]
           self.tla = play_vars['hostvars'][self.hosts[0]][self.TLA]

        
        #self._display.display("Stats are %s" % stats.custom)
        
        try:
          self.metering_metric = e_vars.get(self.METERING_METRIC)
          sent_metering_metric = list(stats.custom['_run'][self.metering_metric])
        except:
          self.metering_metric = "Not Defined"
          sent_metering_metric = []
          self.iteration = 1
            
        self._display.display("Metering Metric key is %s" % self.metering_metric)
        self._display.display("Metering Metric value is %s" % sent_metering_metric)
              
        effort_value = re.findall(r'[-+]?\d*\.\d+|\d+', self.effort)
        self.effort = float(effort_value[0])
        
        if self.jobtemplate_name == None:
           self._display.display("Playbook name %s" % self.playbook_name)
        else: 
           self._display.display("Job template name is %s" % self.playbook_name)
        
        self.usage_data['end'] = str(end_time.astimezone(tz.gettz('UTC')).replace(tzinfo=None).isoformat()+'Z')
        self.usage_data['start'] = str(self.start_time.astimezone(tz.gettz('UTC')).replace(tzinfo=None).isoformat()+'Z')
        self.usage_data['name'] = self.playbook_name
        self.usage_data['team_name'] = self.team
        self.usage_data['owner_email'] = self.email
        self.usage_data['tla'] = self.tla
        self.usage_data['user.name'] = self.user
        self.effort_saving_per_execution = self.effort

        #Wipro Holmes automations execute on localhosts so for each metric, one entry will be added
        for i in range(len(sent_metering_metric)):
           self.effort = self.effort_saving_per_execution
           if ((stats.summarize(self.hosts[0])['unreachable'] > 0) or (stats.summarize(self.hosts[0])['failures'] > 0)):
              self.run_status = "fail"
              self.effort = 0
           else:
              self.run_status = "success" 
 
           self.usage_data['run_status'] = self.run_status
           self.usage_data['toil_hrs_saved'] = float(self.effort)
           self.usage_data[self.metering_metric] = sent_metering_metric[i]
           self.usage_data['target'] = self.hosts[0]
           json_dump = json.dumps(self.usage_data)
           json_object = json.loads(json_dump)
           print(json_object)
        
           try:
             # Define producer obejct to push messages to Kafka topic

             if ("UAT_SSL_certificate" in os.environ) or ("PROD_SSL_CERTIFICATE" in os.environ):
                producer = KafkaProducer(bootstrap_servers=self.kafkaBrokers,
                           security_protocol='SSL',
                           ssl_check_hostname=True,
                           ssl_cafile=self.caRootLocation,
                           ssl_certfile=self.ssl_cert,
                           ssl_keyfile=self.ssl_key,
                           ssl_password=self.passwo)
                producer.send(self.kafka_topic, json_dump.encode('utf-8') )

             else:
                producer = KafkaProducer(bootstrap_servers=self.kafkaBrokers, value_serializer=lambda x: json.dumps(x).encode('utf-8'))
                producer.send(self.kafka_topic, json_object )

             # Push a toil savings detials to Kafka topic
             producer.flush()
             self._display.display("Message Sent")
             producer.close() 

           except KafkaError as ke:
             self._display.display("Issue with message send to Kafka Error -> %s" % ke)

############################################################################################
#
#author        :   Omprakash Tiwari
#version       :   1.0
#title         :   PreCheck_script
#description   :   This script will run the health check for pre unix patching servers and generats the report. 

###################################################################################################
import paramiko
import socket
import time
#import sys
import os
import re
import logging
import traceback
import datetime
import pandas as pd
#import glob
import getpass
import csv


#####INPUT PARAMETERS#######################################################################
username=input("Enter your username: ")
password=getpass.getpass("Enter your password: ")
###########################################################################################

shell = None
client = None
exit_code= None
srvIndexCount=0 
curr_date= datetime.datetime.now()
date_time=curr_date.strftime("%d_%m_%y_%H_%M_%S")
failed_srv_header=['server','Error']
failed_srv_output=[]
host1 = []
srv_ty = []
dr_pr = []
os_v = []
lpat_de = []
pat_date = []
cpu=[]
mem1=[]
swap_mem=[]
pandora_sta = []
disk_uti=[]
sys_disk=[]
up_time=[]
load_avg=[]
nfs=[] 
tlaName=[]
console=[]
cluster=[]

#Log creation
Logfile=r'.\logs\Pre&Post_Check_Logs_'+date_time+'.log' 
logging.basicConfig(filename=Logfile, filemode='a',
                    format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger()
logger.setLevel(logging.INFO)
logger.info(f"\n*********************PRE CHECK LOGS {curr_date} *********************")

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
        
def execute_shell(command, sleeptime=3):
    
    
    command = command + "\n"
    shell.send(command)
    time.sleep(sleeptime)
    receive_buffer = shell.recv(9999).decode("utf-8")
    return receive_buffer
def exe_command(command,timeOut=30):
    try:
        global exit_code
        stdin,stdout,stderr=client.exec_command(command,timeOut)
        stdin.close()
        temp= stdout.readlines()
        result= temp
        exit_status= stdout.channel.recv_exit_status()
        if exit_status==0:
            exit_code= "SUCCESS"
        else:
            exit_code= "FAILURE"
        return result              
    except socket.timeout:
        print("TimeoutError")
        return "FAILURE"
    except Exception as e:
        print("FAILURE unable to execute command", e.__str__)  
        return "FAILURE" 

def TableContaint(server,outputs):

    table=f'''
    <div id="{server}" class="reports">
        <table id="report">
          <thead>
            <tr>
              <th>Command</th>
              <th>Pre-Check Output</th>
            </tr>
          </thead>
          <tbody>
    '''
    tableRow=""
    for command,output in outputs:
        tableRow +=f'''
        <tr>
            <td>{command}</td>
            <td>{output}</td>
        </tr>
        '''
    table +=tableRow+'''
          </tbody>
        </table>
    </div>
    '''
    return table

def HTML_templateCreation(serverList,table,failedServer):
    Path = r".\PreCheck Reports"
    servers=serverList
    if not os.path.exists(Path):
        os.makedirs(Path) 
    filename = datetime.datetime.now().strftime("PrePatchReport_%m%d%Y%H%M%S.html")
    HTML_file = os.path.join(Path, filename)
    HTML_file = open(HTML_file, "w")
    tempHtml = '''
    <html>
    <head>
          <title>Server Pre-Patching Report</title>
          <link rel="stylesheet" type="text/css" href="style.css">
    <link rel="preconnect" href=https://fonts.gstatic.com crossorigin>
<link href=https://fonts.googleapis.com/css2?family=Merriweather:wght@700&display=swap rel="stylesheet">
    </head>
    <style>
       #container {
    display: flex;
    height:100%
    
  }
 body{
  font-family: 'Merriweather', serif;
 }
  
  #sidebar {
    width: 20%;
    height: auto;
    overflow-y: scroll;
    padding: 10px;
    background-color: 1a1a1a;
    text-align: center;
    padding-bottom: none;
    background: linear-gradient(to bottom right, #0f2b3c,#636161);
  }
 
  ul{
    padding: 0px;
  }
  .srvrBtns {
    display: block;
    outline: none;
    width: 100%;
    height: 36px;
    border: antiquewhite;
    border-radius: 8px;
    font-family: 'Merriweather';
  }
  h1{
    margin: 10px;
    color: whitesmoke;
  }
  h3{
    marign: 10px;
    color: Red
  }
.srvrBtns:active{
  box-shadow: inset 2px 4px 5px 4px rgb(169, 163, 162);

}
button:hover{
  background-color: a6a6a6;
}
.serverList{
  padding: 3px 10px;
  margin: 0px;
}
.reports tbody{
    font-size: 12px
    }
  #reportContainer {
    width: 80%;
    padding: 5px;
    height: auto;
    overflow-y: scroll;
  }
  .reports{
    display: none;
  }
  
  table {
    width: 100%;
    border-collapse: collapse;
  }
  
  th, td {
    border: 1px solid black;
    padding: 8px;
    text-align: left;
  }
  
  th {
    background-color: 1a1a1a;
    color: white;
  }

    </style>

    <script>
        function displayContent(tableName)
        {
            var element=document.getElementById(tableName);
            var tables=document.querySelectorAll('.reports')
            for(let i=0;i<tables.length;i++)
            {
                let name=tables[i].id
                if(name==tableName)
                {
                    element.style.display="inline-block"
                }
                else{
                    tables[i].style.display='none'
                }
            }
            
        }
    </script>
    <body> 
        <div id="container">
            <div id="sidebar">
                <h1>Server List</h1>
                 
    '''
    HTML_file.write(tempHtml)
    for server in servers:
        tempHtml= f'''<ul class= serverList><button class="srvrBtns" onclick="displayContent('{server}')">{server}</button></ul>'''
        HTML_file.write(tempHtml)

    tempHtml=''' </div>
    <div id="reportContainer">
        <h1 style="color: black;text-align: center;margin: 3px;text-decoration: underline">Server Pre-Patching Report</h1>

    '''
    HTML_file.write(tempHtml)
    HTML_file.write(table)
    HTML_file.write(failedServer)
    #if(failed_server!=" "):
    #    HTML_file.write(failed_server)
    tempHtml='''
    </div></div></body></html>
    '''
    HTML_file.write(tempHtml)
    HTML_file.close()
    #Arranging the Outputs properly
    with open(HTML_file.name ,'r') as file:
        content=file.read()
    content=content.replace(r'\n','<br></br>')
    content=content.replace(r"['"," ")
    content=content.replace(r"']"," ")
    content=content.replace(r"', '"," ")
    content=content.replace(r"\t"," ")
    content=content.replace(r"\t\t","  ")
    content=content.replace(r"\t\t","  ")
    content=content.replace(r"\r","<br></br>")

    with open(HTML_file.name,'w') as file:
        file.write(content)
 
def failed_server_TableContaint(server,exception):
    table=f'''
    <div id='{server}' id="report1" class="reports">
        <h3>Error occured: {exception}</h3>
    </div>
    '''
    return table

def AIX_CapturePreChecks(commands,server,output):
    global srvIndexCount
    global failed_srv_output
    today=curr_date.strftime("%Y%m%d")
    try:       
        #Hostname
        temp=exe_command(commands[0])
        HtmlTemp=str(temp)
        HtmlTemp="\n".join(HtmlTemp.split("\n"))
        output.append([commands[0],HtmlTemp])
        temp=temp[0].strip()
        
        if len(temp)>0:
            host1.append(temp)
        else:
            host1.append('None')
   
        #Major Os Version
        temp=exe_command(commands[2])
        HtmlTemp=str(temp)
        HtmlTemp="\n".join(HtmlTemp.split("\n"))
        output.append([commands[2],HtmlTemp])
        temp=temp[0].strip()
        
        if len(temp)>0:
            os_v.append(temp)
        else:
            os_v.append('None')
                                #OS version, Kernal patch and last patch details are available in command[2]
        #Kernal patch details
        
        if len(temp)>0:
            lpat_de.append(temp)
        else:
            lpat_de.append('None')
        
        #last patch applied date
        
        if len(temp)>0:
            pat_date.append(temp)
        else:
            pat_date.append('None')

        
        #CPU util-
        temp=exe_command(commands[3])
        HtmlTemp=str(temp)
        HtmlTemp="\n".join(HtmlTemp.split("\n"))
        output.append([commands[3],HtmlTemp])
        temp=temp[-1].split()
        if len(temp)>0:
            temp=float(temp[3])
            if temp<=30 and temp>10:
                print('warning')
                cpu.append("Warning")
            elif temp<=10:
                ##print('Unhealthy')
                cpu.append("Unhealthy")

            else:
                cpu.append("Healthy")
                #print('Healthy')
        else:
            cpu.append('None')

        
        #Memory util-------------------------------------
        temp=exe_command(commands[4])
        HtmlTemp=str(temp)
        HtmlTemp="\n".join(HtmlTemp.split("\n"))
        output.append([commands[4],HtmlTemp])
        
        temp=exe_command(commands[4]+"| head -2|tail -1| awk {'print 100 - $6/$2*100'}")
        if len(temp)>0:
            temp=float(temp[0].strip())
            if temp>=70 and temp<=90:
                temp='Warning'
            elif temp>=90:
                temp='Unhealthy'
            else:
                temp='Healthy'
            mem1.append(temp)
        else:
            mem1.append('None')
         
        
        #Swap Memory-------------------------------------
        temp=exe_command("lsps -s")
        temp=(temp[-1].strip()).split()[-1].strip("%")
        if len(temp)>0:
            temp=float(temp)
            if temp>=70 and temp<=90:
                temp='Warning'
            elif temp>=90:
                temp='Unhealthy'
            else:
                temp='Healthy'
            swap_mem.append(temp)
        else:
            swap_mem.append('None')
         
        #pandora status
        temp=exe_command(commands[5])
        HtmlTemp=str(temp)
        HtmlTemp="\n".join(HtmlTemp.split("\n"))
        output.append([commands[5],HtmlTemp])
        temp=temp[0].strip()
        if len(temp)>0:
            if 'Pandora FMS Agent is running with PID' in temp:
                pandora_sta.append('Running')
            else:
                pandora_sta.append('Stopped')
                print('Stopped')
        else:
                pandora_sta.append('None')

        #disk Utilization
        temp=exe_command(commands[6])
        HtmlTemp=str(temp)
        HtmlTemp="\n".join(HtmlTemp.split("\n"))
        output.append([commands[6],HtmlTemp])
        
        temp=exe_command(commands[6]+"| awk '{print $4}'")
        temp=[i.strip('%\n') for i in temp]
        temp=[x for x in temp if x!='-'] 
        temp=temp[1:]
        count_cri=0
        count_warn=0
        temp=[float(i.strip()) for i in temp]
        if len(temp)>0:
            for i in range(len(temp)):
                if(90>temp[i]>85):
                    count_warn+=1
                elif(temp[i]>90):
                    count_cri+=1
            if(count_cri>0):
                disk_uti.append("Unhealthy")
               
            elif(count_warn>0):
                disk_uti.append("Warning")
               
            else:
                disk_uti.append("Healthy")
            #NFS hung check
            nfs.append("Healthy")
        else:
            nfs.append("Unhealthy")
            disk_uti.append('None')
        
        #System Disk utlization----------------------------------
        temp=exe_command(commands[6]+'''|grep -E "/$|/var$|/tmp$|/usr$|/opt$"|awk '{print $4}' ''')
        temp=[i.strip('%\n') for i in temp]
        count_cri=0
        count_warn=0
        temp=[float(i.strip()) for i in temp]
        if len(temp)>0:
            for i in range(len(temp)):
                if(90>temp[i]>85):
                    count_warn+=1
                elif(temp[i]>90):
                    count_cri+=1
            if(count_cri>0):
                sys_disk.append("Unhealthy")
               
            elif(count_warn>0):
                sys_disk.append("Warning")
               
            else:
                sys_disk.append("Healthy")
               #print("Healthy")
        else:
            sys_disk.append('None')

        
        #UpTime
        temp=exe_command(commands[7])
        HtmlTemp=str(temp)
        HtmlTemp="\n".join(HtmlTemp.split("\n"))
        output.append([commands[7],HtmlTemp])
        temp=temp[0].strip()
        if len(temp)>0:
            up_time.append(temp)
        else:
            up_time.append('None')
        
        #load Average
        RegEx=r'load average: ([\d., ]+)'
        temp=re.findall(RegEx,temp)[0].split(', ')
        temp=[float(i.strip()) for i in temp]
        temp.sort()
        if len(temp)>0 :
            if temp[-1]>=85 and temp[-1]<90:
                print('warning')
                load_avg.append("Warning")
            elif temp[-1]>=90:
                ##print('Unhealthy')
                load_avg.append("Unhealthy")

            else:
                load_avg.append("Healthy")
                #print('Healthy')
        else:
            load_avg.append('None')
            
        #Routing table
        temp=exe_command(commands[8])
        HtmlTemp=str(temp)
        HtmlTemp="\n".join(HtmlTemp.split("\n"))
        output.append([commands[8],HtmlTemp])
        
        #fstab check
        temp=exe_command(commands[9])
        HtmlTemp=str(temp)
        HtmlTemp="\n".join(HtmlTemp.split("\n"))
        output.append([commands[9],HtmlTemp])
        
        #Top 10 CPU consumers 
        temp=exe_command(commands[12])
        HtmlTemp=str(temp)
        HtmlTemp="\n".join(HtmlTemp.split("\n"))
        output.append([commands[12],HtmlTemp])
        
        #Top 10 Memory consumers
        temp=exe_command(commands[13])
        HtmlTemp=str(temp)
        HtmlTemp="\n".join(HtmlTemp.split("\n"))
        output.append([commands[13],HtmlTemp])
        
        #cluster check
        cluster.append('No')
    
        #-----------------------Connecting to ALVIN SERVER------------------------
        login('alvin',username,password)
        execute_shell(today)
        
        #Server type
        execute_shell('uname')
        if('<hostname>' in commands[1]):
            cmd=commands[1].replace('<hostname>', server)
        temp=execute_shell(cmd)
        temp_DRPR=temp
        temp=temp.split("\n")
        temp=temp[1].split("|")[4]
        if len(temp)>0:
            srv_ty.append(temp)
        else:
            srv_ty.append('None')

        #DR/Primary
        temp=temp_DRPR
        temp=temp.split("\n")
        temp=temp[-2]
        HtmlTemp=str(temp)
        HtmlTemp="\n".join(HtmlTemp.split("\n"))
        output.append([cmd,HtmlTemp])
        #temp=""
        if len(temp)>0:
            dr_pr.append(temp) 
        else:
            dr_pr.append('None')
        
        #TLA Tool Name
        #execute_shell('uname')
        if('<hostname>' in commands[10]):
            cmd=commands[10].replace('<hostname>', server)
        temp=execute_shell(cmd)
        temp=temp.split("\n")[1:-1]
        HtmlTemp=str(temp)
        HtmlTemp="\n".join(HtmlTemp.split("\n"))
        output.append([cmd,HtmlTemp])
        temp=[i.strip() for i in temp]
        temp=[i.replace("\t", "") for i in temp]
        if len(temp)>0:
            tlaName.append(temp)
        else:
            tlaName.append('None')
            
        #console details
        #execute_shell('uname')
        if('<hostname>' in commands[11]):
            cmd=commands[11].replace('<hostname>', server)
        temp=execute_shell(cmd)
        temp=temp.split("\n")[1]
        HtmlTemp=str(temp)
        HtmlTemp="\n".join(HtmlTemp.split("\n"))
        output.append([cmd,HtmlTemp])
        if len(temp)>0:
            console.append(temp)
        else:
            console.append('None')
            
        srvIndexCount+=1 
        
    except Exception as e:
        all_lists=[host1,srv_ty,dr_pr,os_v,lpat_de,pat_date,cpu,mem1,swap_mem,pandora_sta,disk_uti,sys_disk,up_time,load_avg,nfs,tlaName,console,cluster]
        for li in all_lists:
            if len(li)>srvIndexCount:
                li.pop(srvIndexCount)
        #print("Error: ",e)
        traceback.print_exc()
        logger.info(f"Error: {e}")
        failed_srv_output.append([server,e])

def Linux_CapturePreChecks(commands,server,output):
    global srvIndexCount
    global failed_srv_output
    today=curr_date.strftime("%Y%m%d")
    try:
        #Hostname 
        temp=exe_command(commands[0])
        temp=temp[0].strip()
        HtmlTemp=str(temp)
        HtmlTemp="\n".join(HtmlTemp.split("\n"))
        output.append([commands[0],HtmlTemp])
        
        if len(temp)>0:
            host1.append(temp)
        else:
            host1.append('None')
       
        #Major Os Version
        temp=exe_command(commands[2])
        temp=temp[0].strip()
        HtmlTemp=str(temp)
        HtmlTemp="\n".join(HtmlTemp.split("\n"))
        output.append([commands[2],HtmlTemp])
        
        if len(temp)>0:
            os_v.append(temp)
        else:
            os_v.append('None')

        #kernal patch details
        temp=exe_command(commands[3])
        HtmlTemp=str(temp)
        HtmlTemp="\n".join(HtmlTemp.split("\n"))
        output.append([commands[3],HtmlTemp])
        var=""
        for i in range(len(temp)):
            var+=temp[i].strip()+", \n"
        if len(var)>0:
            lpat_de.append(var)
        else:
            lpat_de.append('None')
        
        
        #Last kernal applied date
        temp=exe_command(commands[4])
        temp=temp[0].strip()
        HtmlTemp=str(temp)
        HtmlTemp="\n".join(HtmlTemp.split("\n"))
        output.append([commands[4],HtmlTemp])
        if len(temp)>0:
            pat_date.append(temp)
        else:
            pat_date.append('None')

        
        #CPU util-
        var=exe_command(commands[5])
        HtmlTemp=str(var)
        HtmlTemp="\n".join(HtmlTemp.split("\n"))
        output.append([commands[5],HtmlTemp])
        value=[]
        value.append(float((var[3].split())[-1].strip()))
        value.append(float((var[4].split())[-1].strip()))
        value.append(float((var[5].split())[-1].strip()))
        value.sort()
        if value[-1]<=30 and value[-1]>10:
            var='Warning'
        elif value[-1]<=10:
            var='Unhealthy'
        else:
            var='Healthy'
        if len(var)>0:
            cpu.append(var)
        else:
            cpu.append('None')


        
        #Memory util
        temp=exe_command(commands[6])
        HtmlTemp=str(temp)
        HtmlTemp="\n".join(HtmlTemp.split("\n"))
        output.append([commands[6],HtmlTemp])
        temp=temp[1].split("\n")
        temp=temp[0].split()
        usedPer=round((float(temp[2])/float(temp[1]))*100,2)
        if usedPer>=70 and usedPer<=90:
            temp='Warning'
        elif usedPer>=90:
            temp='Unhealthy'
        else:
            temp='Healthy'
        if len(temp)>0:
            mem1.append(temp)
        else:
            mem1.append('None')

        
        #Swap tempory
        temp=exe_command(commands[6])
        temp=temp[-1].split("\n")
        temp=temp[0].split()
        usedPer=round((float(temp[2])/float(temp[1]))*100,2)
        if usedPer>=70 and usedPer<=90:
            temp='Warning'
        elif usedPer>=90:
            temp='Unhealthy'
        else:
            temp='Healthy'
        if len(temp)>0:
            swap_mem.append(temp)
        else:
            swap_mem.append('None')
        
        #pandora status
        status=exe_command(commands[7])
        status=status[0].strip()
        HtmlTemp=str(status)
        HtmlTemp="\n".join(HtmlTemp.split("\n"))
        output.append([commands[7],HtmlTemp])
        if len(status)>0:
            if 'Pandora FMS Agent is running with PID' in status:
                pandora_sta.append('Running')
                
            else:
                pandora_sta.append('Stopped')
                print('Stopped')
        else:
                pandora_sta.append('None') 

        #disk Utilization
        temp=exe_command(commands[8])
        HtmlTemp=str(temp)
        HtmlTemp="\n".join(HtmlTemp.split("\n"))
        output.append([commands[8],HtmlTemp])
        if len(temp)>0:                 
            nfs.append("Healthy")               #NFS hung check
        else:
            nfs.append("Unhealthy")
        temp=exe_command(commands[8]+" -P | awk '{print $5}'")
        temp=[i.strip('%\n') for i in temp]
        temp=temp[1:]
        count_cri=0
        count_warn=0
        temp=[float(i.strip()) for i in temp]
        if len(temp)>0:
            for i in range(len(temp)):
                if(90>temp[i]>85):
                    count_cri+=1
                elif(temp[i]>90):
                    count_warn+=1
            if(count_cri>0):
                disk_uti.append("Unhealthy")
               
            elif(count_warn>0):
                disk_uti.append("Warning")
               
            else:
                disk_uti.append("Healthy")
               #print("Healthy")
        else:
                disk_uti.append("None") 


        #System Disk utlization
        temp=exe_command(commands[8]+" -P |grep rootvg | awk '{print $5}'")
        temp=[i.strip('%\n') for i in temp]
        count_cri=0
        count_warn=0
        temp=[float(i.strip()) for i in temp]
        if len(temp)>0:
            for i in range(len(temp)):
                if(90>temp[i]>85):
                    count_warn+=1
                elif(temp[i]>90):
                    count_cri+=1
            if(count_cri>0):
                sys_disk.append("Unhealthy")
               
            elif(count_warn>0):
                sys_disk.append("Warning")
               
            else:
                sys_disk.append("Healthy")
               #print("Healthy")
        else:
                sys_disk.append("None")
        
        #UpTime
        temp=exe_command(commands[9])
        temp=temp[0].strip()
        HtmlTemp=str(temp)
        HtmlTemp="\n".join(HtmlTemp.split("\n"))
        output.append([commands[9],HtmlTemp])
        if len(temp)>0:
            up_time.append(temp)
        else:
            up_time.append('None')
        
        
        #load Average
        temp=exe_command(commands[9])
        temp=temp[0].strip()
        RegEx=r'load average: ([\d., ]+)'
        temp=re.findall(RegEx,temp)[0].split(', ')
        temp=[float(i.strip()) for i in temp]
        temp.sort()
        if len(temp)>0:
            if temp[-1]>=85 and temp[-1]<90:
                print('warning')
                load_avg.append("Warning")
            elif temp[-1]>=90:
                ##print('Unhealthy')
                load_avg.append("Unhealthy")

            else:
                load_avg.append("Healthy")
                #print('Healthy')
        else:
            load_avg.append('None')
        
        #Routing table
        temp=exe_command(commands[10])
        HtmlTemp=str(temp)
        HtmlTemp="\n".join(HtmlTemp.split("\n"))
        output.append([commands[10],HtmlTemp])
        
        #fstab check
        temp=exe_command(commands[11])
        HtmlTemp=str(temp)
        HtmlTemp="\n".join(HtmlTemp.split("\n"))
        output.append([commands[11],HtmlTemp])
        
        
        
        #cluster check
        temp=exe_command(commands[13])
        temp=str(temp)
        if len(temp)>0:
            if '/etc/corosync' in temp:
                cluster.append('Yes')
            else:
                cluster.append('No')
        else:
            cluster.append('None')
          
        #Top 10 CPU & MEM consumers
        temp=exe_command(commands[15])
        HtmlTemp=str(temp)
        HtmlTemp="\n".join(HtmlTemp.split("\n"))
        output.append([commands[15],HtmlTemp])
        
        #-----------------------Connecting to ALVIN SERVER------------------------
        login('alvin',username,password)
        execute_shell(today)
        
        #Server type
        execute_shell('uname')
        if('<hostname>' in commands[1]):
            cmd=commands[1].replace('<hostname>', server)
        temp=execute_shell(cmd)
        temp_DRPR=temp
        temp=temp.split("\n")
        temp=temp[1].split("|")[4]
        if len(temp)>0:
            srv_ty.append(temp)
        else:
            srv_ty.append('None')
        #DR/Primary
        temp=temp_DRPR
        temp=temp.split("\n")
        temp=temp[1]
        HtmlTemp=str(temp)
        HtmlTemp="\n".join(HtmlTemp.split("\n"))
        output.append([cmd,HtmlTemp])
        
        if len(temp)>0:
            dr_pr.append(temp)
        else:
            dr_pr.append('None')
            
        #TLA Name
        #execute_shell('uname')
        if('<hostname>' in commands[12]):
            cmd=commands[12].replace('<hostname>', server)
        temp=execute_shell(cmd)
        temp=temp.split("\n")[1:-1]
        HtmlTemp=str(temp)
        HtmlTemp="\n".join(HtmlTemp.split("\n"))
        output.append([cmd,HtmlTemp])
        temp=[i.strip() for i in temp]
        temp=[i.replace("\t", "") for i in temp]
        if(len(temp)>0):
            tlaName.append(temp)
        else:
            tlaName.append('None')

        #console details
        #execute_shell('uname')
        if('<hostname>' in commands[14]):
            cmd=commands[14].replace('<hostname>', server)
        temp=execute_shell(cmd)
        temp=temp.split("\n")[1]
        HtmlTemp=str(temp)
        HtmlTemp="\n".join(HtmlTemp.split("\n"))
        output.append([cmd,HtmlTemp])
        if len(temp)>0:
            console.append(temp)
        else:
            console.append('None')
        
        srvIndexCount+=1

    except Exception as e:
        all_lists=[host1,srv_ty,dr_pr,os_v,lpat_de,pat_date,cpu,mem1,swap_mem,pandora_sta,disk_uti,sys_disk,up_time,load_avg,nfs,tlaName,console,cluster]
        for li in all_lists:
            if len(li)>srvIndexCount:
                li.pop(srvIndexCount)
        #print("Error: ",e)
        traceback.print_exc()
        logger.info(f"Error: {e}")
        failed_srv_output.append([server,e])
    
def Solaris_CapturePreChecks(commands,server,output):
    global srvIndexCount
    global failed_srv_output
    today=curr_date.strftime("%Y%m%d")
    try:
        #Hostname 
        temp=exe_command(commands[0])
        temp=temp[0].strip()
        HtmlTemp=str(temp)
        HtmlTemp="\n".join(HtmlTemp.split("\n"))
        output.append([commands[0],HtmlTemp])
        if len(temp)>0:
            host1.append(temp)
        else:
            host1.append('None')

        #Major Os Version
        temp=exe_command(commands[3])
        temp=temp[0].strip()
        HtmlTemp=str(temp)
        HtmlTemp="\n".join(HtmlTemp.split("\n"))
        output.append([commands[10],HtmlTemp])
        
        if len(temp)>0:
            os_v.append(temp)
        else:
            os_v.append('None')

                                #OS version, Kernal patch and last patch details are available in command[2]
        #Kernal patch details
        
        if len(temp)>0:
            lpat_de.append(temp)
        else:
            lpat_de.append('None')

        
        #last patch applied date
        
        if len(temp)>0:
            pat_date.append(temp)
        else:
            pat_date.append('None')

        #CPU util-
        temp=exe_command(commands[4])
        HtmlTemp=str(temp)
        HtmlTemp="\n".join(HtmlTemp.split("\n"))
        output.append([commands[10],HtmlTemp])
        value=[]
        value.append(float((temp[4].split())[-1].strip()))
        value.append(float((temp[5].split())[-1].strip()))
        value.append(float((temp[7].split())[-1].strip()))
        value.sort()
        if len(value)>0:
            if value[-1]<=30 and value[-1]>10:
                temp='Warning'
            elif value[-1]<=10:
                temp='Unhealthy'
            else:
                temp='Healthy'
            cpu.append(temp)
        else:
            cpu.append('None')

        #Memory util-------------------------------------
        temp=exe_command(commands[5])
        HtmlTemp=str(temp)
        HtmlTemp="\n".join(HtmlTemp.split("\n"))
        output.append([commands[5],HtmlTemp])
        temp=exe_command('''a=$(/usr/sbin/prtconf | /usr/bin/awk '/Memory/ {print $3*1024}'); vmstat 1 1 | tail -1 | awk "{print (\$5/$a)*100}"''')
        if len(temp)>0:
            temp=float(temp[0].split("\n")[0])
            temp=round(temp,2)
            if 10<=temp<=30 :
                temp='Warning'
            elif temp<10:
                temp='Unhealthy'
            else:
                temp='Healthy' 
            mem1.append(temp)
        else:
            mem1.append('None')

        #Swap Memory-------------------------------------
        temp=exe_command("swap -s|/usr/bin/tr -d /k/|awk '{u= $9}{a= $11}{t= u+a}END{print u/t*100}'")
        if len(temp)>0:
            temp=float(temp[0].strip())
            if temp>=70 and temp<=90:
                temp='Warning'
            elif temp>=90:
                temp='Unhealthy'
            else:
                temp='Healthy'
            swap_mem.append(temp)
        else:
            swap_mem.append('None')

        #pandora status
        temp=exe_command(commands[6])
        temp=temp[0].strip()
        HtmlTemp=str(temp)
        HtmlTemp="\n".join(HtmlTemp.split("\n"))
        output.append([commands[6],HtmlTemp])
        if 'Pandora FMS Agent is running with PID' in temp:
            pandora_sta.append('Running')
            
        else:
            pandora_sta.append('Stopped')

        #disk Utilization
        temp=exe_command(commands[7])
        HtmlTemp=str(temp)
        HtmlTemp="\n".join(HtmlTemp.split("\n"))
        output.append([commands[7],HtmlTemp])
        if len(temp)>0:
            nfs.append("Healthy")     #NFS hung check
        else:
            nfs.append("Unhealthy")
        temp=exe_command(commands[7]+"| awk '{print $5}'")
        temp=[i.strip('%\n') for i in temp]
        temp=[x for x in temp if x!='-']
        temp=temp[1:]
        count_cri=0
        count_warn=0
        temp=[float(i.strip()) for i in temp]
        if len(temp)>0:
            for i in range(len(temp)):
                if(90>temp[i]>85):
                    count_warn+=1
                elif(temp[i]>90):
                    count_cri+=1
            if(count_cri>0):
                disk_uti.append("Unhealthy")
               
            elif(count_warn>0):
                disk_uti.append("Warning")
               
            else:
                disk_uti.append("Healthy")
               #print("Healthy")
        else:
            disk_uti.append("None") 

        #System Disk utlization----------------------------------
        temp=exe_command(commands[7]+"| awk '/\/$|\/var$|\/opt$|\/tmp$/ {print $5}' ")
        temp=[i.strip('%\n') for i in temp]
        count_cri=0
        count_warn=0
        temp=[float(i.strip()) for i in temp]
        
        if len(temp)>0:
            for i in range(len(temp)):
                if(90>temp[i]>85):
                    count_warn+=1
                elif(temp[i]>90):
                    count_cri+=1
            if(count_cri>0):
                sys_disk.append("Unhealthy")
               
            elif(count_warn>0):
                sys_disk.append("Warning")
               
            else:
                sys_disk.append("Healthy")
               #print("Healthy")
        else:
            sys_disk.append("None")


        #UpTime
        temp=exe_command(commands[8])
        temp=temp[0].strip()
        HtmlTemp=str(temp)
        HtmlTemp="\n".join(HtmlTemp.split("\n"))
        output.append([commands[8],HtmlTemp])
        if len(temp)>0:
            up_time.append(temp)
        else:
            up_time.append('None')
        
        
        #load Average
        RegEx=r'load average: ([\d., ]+)'
        temp=re.findall(RegEx,temp)[0].split(', ')
        temp=[float(i.strip()) for i in temp]
        temp.sort()
        if len(temp)>0:
            if temp[-1]>=85 and temp[-1]<90:
                print('warning')
                load_avg.append("Warning")
            elif temp[-1]>=90:
                ##print('Unhealthy')
                load_avg.append("Unhealthy")

            else:
                load_avg.append("Healthy")
                #print('Healthy')
        else:
            load_avg.append("None")
            
        #Routing table
        temp=exe_command(commands[9])
        HtmlTemp=str(temp)
        HtmlTemp="\n".join(HtmlTemp.split("\n"))
        output.append([commands[9],HtmlTemp])
        
        #fstab check
        temp=exe_command(commands[10])
        HtmlTemp=str(temp)
        HtmlTemp="\n".join(HtmlTemp.split("\n"))
        output.append([commands[10],HtmlTemp])
        
        #cluster check
        temp=exe_command(commands[12])
        temp=str(temp)
        if len(temp)>0:
            if "/opt/VRTSvcs/bin/had" in temp:
                cluster.append('Yes')
            else:
                cluster.append('No')
        else:
            cluster.append('None')
        
        #-----------------------Connecting to ALVIN SERVER------------------------
        login('alvin',username,password)
        execute_shell(today)
        
        #Server type
        execute_shell('uname')
        if('<hostname>' in commands[1]):
            cmd=commands[1].replace('<hostname>', server)
        temp=execute_shell(cmd)
        temp_DRPR=temp
        temp=temp.split("\n")
        temp=temp[1].split("|")[4]
        print("server Type:")
        if len(temp)>0:
            srv_ty.append(temp)
        else:
            srv_ty.append('None')
            #DR/Primary
        temp=temp_DRPR
        temp=temp.split("\n")
        temp=temp[-2]
        HtmlTemp=str(temp)
        HtmlTemp="\n".join(HtmlTemp.split("\n"))
        output.append([cmd,HtmlTemp])
        
        if len(temp)>0:
            dr_pr.append(temp) 
        else:
            dr_pr.append(temp) 
        
        #TLA Tool Name
        #execute_shell('uname')
        if('<hostname>' in commands[11]):
            cmd=commands[11].replace('<hostname>', server)
        temp=execute_shell(cmd)
        temp=temp.split("\n")[1:-1]
        HtmlTemp=str(temp)
        HtmlTemp="\n".join(HtmlTemp.split("\n"))
        output.append([cmd,HtmlTemp])
        temp=[i.strip() for i in temp]
        temp=[i.replace("\t", " ") for i in temp]
        if len(temp)>0:
            tlaName.append(temp)
        else:
            tlaName.append('None')
            
        #console details
        #execute_shell('uname')
        if('<hostname>' in commands[13]):
            cmd=commands[13].replace('<hostname>', server)
        temp=execute_shell(cmd)
        temp=temp.split("\n")[1]
        HtmlTemp=str(temp)
        HtmlTemp="\n".join(HtmlTemp.split("\n"))
        output.append([cmd,HtmlTemp])
        if len(temp)>0:
            console.append(temp)
        else:
            console.append('None')
            
        srvIndexCount+=1
        
    except Exception as e:
        all_lists=[host1,srv_ty,dr_pr,os_v,lpat_de,pat_date,cpu,mem1,swap_mem,pandora_sta,disk_uti,sys_disk,up_time,load_avg,nfs,tlaName,console,cluster]
        for li in all_lists:
            if len(li)>srvIndexCount:
                li.pop(srvIndexCount)
        #print("Error: ",e)
        traceback.print_exc()
        logger.info(f"Error: {e}")
        failed_srv_output.append([server,e])
 
def ExcelColorGrading(val):
    val=str(val)
    if isinstance(val, str):
        
        if val == 'Healthy':
            return 'background-color: #6AD519'
        elif val == 'Unhealthy':
            return 'background-color: #F6400D'
        elif val== 'Warning':
            return 'background-color: #FFC300'
        elif val== 'Running':
            return 'background-color: #6AD519'
        elif val== 'Stopped':
            return 'background-color: #F6400D'
    return ''

def clean_up():
    client.close()  
    
def WDB_Metering(start_script_time, end_script_time, status):
    '''    :param start_script_time: add execution Start time of the script to start of main function

           :param end_script_time: add execution end time of the script to end of main function

           :param status: Script status (FAILED or SUCCESS in try and catch of main function)

           :return: updates CSV File with execution timestamp'''

    try:

        usecase = "Unix Pre Check script"  # <Add usecase name >
        execution_type = "One touch"  # <Add execution type>
        list1 = [usecase, execution_type,
                 start_script_time, end_script_time, status]
        f = open(r".\WDB_Logs\WDB_Logs.csv", "a")
        writer = csv.writer(f, lineterminator='\n')
        writer.writerow(list1)

    except Exception as e:
        raise Exception(
            "Something went wrong in WDB Metering function, check filepath and input parameters")

def main():
    global failed_srv_header
    global failed_srv_output
    global srvIndexCount
    try:
        outputs=[]
        HTMLtable=""
        HTMLtable_failed=""
        successCount=failedCount=0
        start_time='{:%Y.%m.%d-%H.%M.%S}'.format(datetime.datetime.now())
        execution_status=""
        today=curr_date.strftime("%Y%m%d")
        #username=input("Enter your username: ")
        #password=getpass.getpass("Enter your password: ")
        #Fatching server list
        srvList=[]
        #srvIndexCount=0    
        inputFile=r".\serverList.csv"
        with open(inputFile,'r') as file:
            data=csv.reader(file)
            for row in data:
                srvList.append(row[0])
               
    	#getting the commands 
        filePath=r".\ConfigFile.csv"
        aix=[]
        solaris=[]
        linux=[]
        with open(filePath) as csvfile:
            reader= csv.DictReader(csvfile)
            for row in reader:
                aix_cmd=row['AIX'].strip()
                solaris_cmd=row['solaris'].strip()
                linux_cmd=row['linux'].strip()
                
                if aix_cmd:
                    aix.append(aix_cmd)
                if solaris_cmd:
                    solaris.append(solaris_cmd)
                if linux_cmd:
                    linux.append(linux_cmd)
        for server in srvList:
            try:
                login(server,username,password)
                execute_shell(today)
                print("Logged in to "+server)
                logger.info(f"Logged in to -----> {server}")
                serverType=str(exe_command('uname'))
                print("server type: ",serverType)
                logger.info(f"server type: {serverType}")
                print("Executing health check commands...")
                logger.info("Executing health check commands...")

                if('Linux' in serverType):
                    Linux_CapturePreChecks(linux, server,outputs)
                elif('AIX' in serverType):
                    AIX_CapturePreChecks(aix, server,outputs)
                elif('SunOS' in serverType):
                    Solaris_CapturePreChecks(solaris , server,outputs)
                HTMLtable+= TableContaint(server,outputs)
                outputs=[]
                successCount +=1
                print("Execution completed for the server ",server)
                logger.info("Execution completed for the server " + server)
                #srvIndexCount +=1 
                print('srvIndexCount:',srvIndexCount)
                clean_up()
                        
            except Exception as sshException:
                print("Error occurred in "+server+": "+str(sshException))
                logger.info(f"Error occurred in {server}: {str(sshException)}")
                traceback.print_exc()
                HTMLtable_failed+=failed_server_TableContaint(server,sshException)
                failed_srv_output.append([server,sshException])
                failedCount +=1
                
        # HTML report creation
        HTML_templateCreation(srvList,HTMLtable,HTMLtable_failed)
       
        final=pd.DataFrame(data={'Hostname':host1,'Server Type':srv_ty,'DR/primary':dr_pr,'Mejor OS version':os_v,
                                 'latest patch details':lpat_de,'last patch applied date':pat_date,'Cluster':cluster ,'CPU':cpu,
                                 'Memory':mem1,'Swap memory':swap_mem,'Pandora status':pandora_sta,'Disk utilization':disk_uti,
                                 'Sys Disk Utilization':sys_disk,'Load Avg':load_avg,'NFS hung check':nfs,'Uptime':up_time,'TLA Name':tlaName, 'Console Details':console})
        print(final)
        report=final.style.applymap(ExcelColorGrading)
        if successCount>0:
            report.to_excel(r".\PreCheck Reports\PreCheck_report_"+date_time+".xlsx", engine='openpyxl', index=False)
            logger.info("Excel Report generated successfully...")
            logger.info(f"Successfully executed server count: {successCount}")
        if failedCount>0:
            failed_srv_report= pd.DataFrame(failed_srv_output,columns=failed_srv_header)
            failed_srv_report.to_csv(r".\Faliure\PreCheck_failed_srv_"+date_time+".csv", index=False)
            logger.info("Failed server's report generated... ")
            logger.info(f"Servers count for faliure attempts: {failedCount}")

        execution_status="Success"
    except Exception as e:
        execution_status="Failed"
        logger.info("Error: ",traceback.print_exc())
        traceback.print_exc()
        
    finally:
        end_time='{:%Y.%m.%d-%H.%M.%S}'.format(datetime.datetime.now())
        WDB_Metering(start_time, end_time, execution_status)
        logger.info("********************* END *********************")
        logging.shutdown()
main()

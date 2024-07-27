
#region LICENSE
'''
.NOTES
==========================================================================================
       Created on         : 20/07/2023
       Created by         : Sayan Chatterjee [sayan.09@wipro.com]
       Last Reviewed By   : Somnath Banerjee [somnath.banerjee1@wipro.com]
       Organization       : Wipro
       Filename           : NT_Oracle-DB_HO_Temp_Tablespace_Enhancement_V2.0.py
       Version            : 2.0
       Copy Rights        : Copyright (C) 2022 Wipro Technologies. All rights reserved.
==========================================================================================
'''
# endregion


#region Script Functionality
'''
Whenever the TEMP Tablespace Utilization crosses the set Threshold value (e.g.- 85%), alert will be raised in the SNOW, Database team should find the 
TEMP Tablespace Utilization details and send to application team and take necessary action to mitigate any outage. The solution would fetch the 
TEMP Tablespace Utilization details and will send the notification with the details to concerned teams right at the moment the ticket is picked up by 
Holmes Orchestrator. This solution is designed & developed to check for TEMP Tablespace Utilization in database. For whichever CON_ID, we find Tablespace 
Utliization is HIGH we will query the PDB name & create the listserv for creating the mail ID.
'''
# endregion


#region Package Import Block
try:
    import paramiko
    import re
    import time
    import logging
    import os
    import datetime
    import sys
    import oracledb
    import subprocess
    from cryptography.fernet import Fernet
    from inspect import stack    

    from os.path import basename
    from email.mime.multipart import MIMEMultipart
    from email.mime.text import MIMEText
    from email.mime.base import MIMEBase
    from email import encoders
    import smtplib
except Exception as e:
    print("Exception in Package Import Block:- ", str(e))
    sys.exit(0)
# endregion

awx_job_id = sys.argv[1] 
database_name = sys.argv[2] 
ansible_user = sys.argv[3]
ansible_password = sys.argv[4]
OraUser= sys.argv[5]
DBUser = sys.argv[6]
ticketNo = sys.argv[7]

class TEMPTablespace:
    #region Class Member Variables
    code = []
    conn = ""
    crsr = ""
    ssh = ""
    channel = ""
    cmdOp = ""
    htmlStr = ""
    htmlList = []
    path = "/wipro_logs/"
    racType = ""
    version = ""
    incNum = ""
    mailRepo = ".\\App_Email.csv"
    smtp = "appmail.ntrs.com:25"
    fileName = ""
    overall = True
    overallStatus = ""
    dbPwd = b''
    key = b''
    prod = False
    excludedDbList = ["cdb954p"]

    queryTimeout = 240000
    thresholdChkWait = 1800
    itsrOutput = ""
    mailMsg = ""
    fromMail = "noreply@ntrs.com" 
    #ccMail = "Wipro_GDP_OPS_Oracle@ntrs.com"
    toMail = ""
    #toMail = "yc55@ntrs.com,kk419@ntrs.com,na226@ntrs.com,sb840@ntrs.com"
    #ccMail = "sc860@ntrs.com"
    ccMail = "ps720@ntrs.com"
    
    prodPwd = "/tnt/canon/dba/.prodpwd"
    qaPwd = "/tnt/canon/dba/.qapwd"
    thresholdValue = 85.0
    # endregion


    #region Constructor - Instantiates Object & Initiates Logging
    def __init__(self, inc):
        inc = self.incNum
        logPath = self.path + "Logs/"
        if not os.path.exists(logPath):
            os.system("mkdir " + logPath)

        logging.basicConfig(filename=datetime.datetime.now().strftime(logPath + inc + '_TEMPTablespaceLog_%d-%m-%Y_"+ awx_job_id +".log'),
                            level=logging.DEBUG, format='%(asctime)s - %(message)s', datefmt='%Y-%m-%d_%H:%M:%S')
        logging.info("\n\n-----------------------------Starting New Logging Session--------------------------------")
        del logPath
    # endregion


    #region Sends Email
    def sendMail(self, host, sid):
        excep = message = ""
        server = ""
        try:
            excep = "Setting Up Mail Address, Subject & Body"
            #print("To-", self.toMail, "; CC-", self.ccMail)
            msg = MIMEMultipart()
            msg['From'] = self.fromMail
            msg['To'] = self.toMail
            msg['Cc'] = self.ccMail
            msg['Subject'] = self.incNum + " : TEMP Tablespace : " + sid

            if not self.overall:
                self.mailMsg = "No Problems found in TEMP Tablespace."

            message = """Dear TLA Team,

""" + self.mailMsg + """


Thanks
Automation Tool

"""
# """ + self.itsrOutput + """

            if self.overall and self.fileName != "":
                excep = "Attaching Report File in Mail"
                file = open(self.fileName, "rb")
                content = file.read()
                file.close()
                part = MIMEBase('application', 'octate-stream')
                part.set_payload(content)
                encoders.encode_base64(part)
                part['Content-Disposition'] = 'attachment; filename="%s"' % basename(self.fileName)
                msg.attach(part)

            # add in the message body
            msg.attach(MIMEText(message, 'plain'))

            excep = "Initiating SMTP Server Connection"
            server = smtplib.SMTP(self.smtp)
            if server == "":
                #print("SMTP Server Connection Initiation Failed")
                logging.info("SMTP Server Connection Initiation Failed")
                return False
            #print("SMTP Server Connection Initiated")
            logging.info("SMTP Server Connection Initiated")

            excep = "Initiating TLS With SMTP Server"
            stat = server.starttls()
            status = ""
            try:
                status = str(stat[1], 'utf-8')
            except Exception:
                status = stat[1].decode('ascii')
            #print("Status-", stat, "-", stat[0], ";", status)
            if not "ready" in status.lower():
                #print("TLS With SMTP Server Failed:- " + status)
                logging.info("TLS With SMTP Server Failed:- " + status)
                return False
            #print("TLS Started With SMTP Server:- " + status)
            logging.info("TLS Started With SMTP Server:- " + status)


            excep = "Sending Mail"
            recipients = self.toMail.split(",") + self.ccMail.split(",")
            server.sendmail(msg['From'], recipients, msg.as_string())
            #print("Successfully Sent Email To- " + self.toMail)
            logging.info("Successfully Sent Email To- " + self.toMail)

            server.quit()
            server.close()
            #print("SMTP Closed")
            logging.info("SMTP Closed")

            del msg
            return True
        except Exception as e:
            #logging.info("Exception Occurred in sendMail while " + excep + ":- " + str(e))
            exc_type, exc_obj, exc_tb = sys.exc_info()
            lineno = exc_tb.tb_lineno
            print("Exception in " + stack()[0][3] + " While, " + excep + " :- " + str(e) + ".\nException Line: " + str(lineno) + " - " + self.code[lineno-1])
            logging.info("Exception in " + stack()[0][3] + " While, " + excep + " :- " + str(e) + ".\nException Line: " + str(lineno) + " - " + self.code[lineno-1])
            #print("Exception Occurred in sendMail while " + excep + ":- " + str(e))
            if server: 
                server.quit()
                server.close()
                #print("SMTP Closed in Exception")
                logging.info("SMTP Closed in Exception")
            return False
    # endregion


    #region HTML Report Creation Function
    def createFinalHtml(self):
        excep = ""
        try:
            opPath = self.path + "Output/"
            if not os.path.exists(opPath):
                os.system("mkdir " + opPath)

            
            self.leftPane = ""
            self.fileName = ""
            self.fileName = datetime.datetime.now().strftime(opPath + self.incNum + "_TEMPTablespaceReport_%d%m%Y_"+ awx_job_id +".html")
            #self.fileName = datetime.datetime.now().strftime(opPath + self.incNum + "_TEMPTablespaceReport_%d%m%Y_%H%M%S.html")

            finalFile = open(self.fileName, "w")
            excep = "Writing Initial CSS"
            initialCss = """
<html>
<head>
    <!-- Tell the browser to be responsive to screen width -->
    <meta content="width=device-width, initial-scale=1, maximum-scale=1, user-scalable=no" name="viewport">
    <meta charset = "UTF-8" name = "viewport" content = "width = device-width, initial-scale = 1">
        <style type = "text/css">

        {box-sizing: border-box;}
            i{
              border: solid white;
              border-width: 0 2px 2px 0;
              display: inline-block;
              padding: 4px;
            }
            .up {
                transform: rotate(-135deg);
                -webkit-transform: rotate(-135deg);
            }

            body { 
                margin: 0;
                font-family: Arial, Helvetica, sans-serif;
            }
            #topBtn {
                display: none;
                position: fixed;
                bottom: 25px;
                right: 30px;
                z-index: 99;
                font-size: 12px;
                border: none;
                outline: none;
                background-color: #2196F3;
                color: white;
                cursor: pointer;
                padding: 12px;
                border-radius: 5px;
            }
            #topBtn:hover { background-color: red; }                                             

            .header {
                color: white;
                font-size: 25px;
                text-align: center;
                overflow: hidden;
                background-color: grey;
                padding: 10px 10px;
            }

            #sidebar-wrapper {
                width: 290px;
                background:#eee;
                margin-top:10px;
                height:91vh;
                float: left;
            }

            #sidebar-wrapper .sidebar-nav {
                background-color: lightGrey;
                position: absolute;
                top: 56px;
                width: 270px;
                font-size: 15px;
                margin: 8px;
                padding: 2px;
                list-style: none; 
            }
            #sidebar-wrapper .sidebar-nav li {                                                           
                width: 260px;
                text-indent: 2px;
                line-height: 35px;
                margin-left:10px;                             
            }
            #sidebar-wrapper .sidebar-nav li button {
                height: 37px;
                font-size: 15px;
                width: 250px;
                text-align: left;
                border: none;
                border-color: none;
                display: block;
                text-decoration: none;
                outline:5px;
                color:green;
                background-color: #eee;
                align: left;
            }
            #sidebar-wrapper .sidebar-nav li button.active, #sidebar-wrapper .sidebar-nav li button:hover {
                background-color:#22fff2;
                color: #1564b2;
            }              

            #sidebar-wrapper .sidebar-nav li button.sidebar-title-failed{
                background-color: #EF3341;
                color: black;
            }
            #sidebar-wrapper .sidebar-nav li button.sidebar-title-failed.active, #sidebar-wrapper .sidebar-nav li button.sidebar-title-failed:hover{
                background-color: #ff40ff;
                color: blue;
            }                                              

            .tabcontent{
                display: none;                                                    
                font-color: black;                                                              
                position: relative;
                padding: 6px 12px;                    
                --border: 1px solid #ccc;
                border-top: none;   
            }                                

            @media screen and (min-width: 985px) {
                table {
                width: 100%;}
            }

            table {font-family: Alegreya SC;
                font-size: 13px;
                border-collapse: collapse;
                width: 100%;}

            td, th {border: 2px solid #BDCCBA;
                text-align: left;
                padding: 8px;}                                   

            div.pane{                                             
                margin-left:20px;
                width: 75%;
                height:relative;
                display:inline-block;
                white-space: nowrap;
                text-align: left;
                border: none !important;
                background-color: white;
            }              
    </style>               
</head>

"""
            finalFile.write(initialCss)
            logging.info("Initial CSS Written & Closed")

            finalFile.close()
            finalFile = open(self.fileName, "a")

            self.leftPane = """
    <body>    
    <button onclick = "topFunction()" id = "topBtn" title = "Go To Top"><i class="up"></i></button>
    <div class="header">
        <span class="logo-lg" style="font-size: 22px; padding-right: 5px;"><b>&nbsp&nbsp&nbsp&nbsp&nbsp&nbsp&nbsp&nbsp&nbsp&nbsp&nbsp&nbsp&nbsp
        &nbsp&nbsp&nbsp&nbsp&nbsp&nbsp TEMP TABLESPACE REPORT</b></span>
    </div>

    <div id="sidebar-wrapper">
      <aside id="sidebar">
        <ul id="sidemenu" class="sidebar-nav" style = "color: green">

            """
            finalFile.write(self.leftPane)

            excep = "Reading Temporary Files to Read LeftPane"
            for i in range(0, len(self.htmlList)):
                val = self.htmlList[i]
                leftPane = val.split("Leftpane Ends Here")[0]
                finalFile.write(leftPane)

            self.leftPane = """</ul>
        </aside>

    </div>               

    <nav class="navbar navbar-right">    
        <div class="pane"> 

"""
            finalFile.write(self.leftPane)
            excep = "Reading Temporary Files to Read Main Content"
            # print(files)
            for i in range(0, len(self.htmlList)):
                val = self.htmlList[i]
                content = val.split("Leftpane Ends Here")[1]
                finalFile.write(content)

            logging.info("Temporary Files of Instance Details HTMLs Reading Complete.")

            tmp = """
            </div>
        </nav>

        <script>
                function createReport(evt, command) {
                var i, tabContent, sidebar_title;

                tabContent = document.getElementsByClassName("tabcontent")
                for (i = 0; i < tabContent.length; i++)
                {    tabContent[i].style.display = "none";  }

                sidebar_title = document.getElementsByClassName("sidebar-title")
                for(i = 0; i < sidebar_title.length; i++)
                {   sidebar_title[i].className = sidebar_title[i].className.replace(" active", "");   }

                sidebar_title_failed = document.getElementsByClassName("sidebar-title-failed")
                for(i = 0; i < sidebar_title_failed.length; i++)
                {   sidebar_title_failed[i].className = sidebar_title_failed[i].className.replace(" active", "");   }

                document.getElementById(command).style.display = "block";
                evt.currentTarget.className += " active";

                document.body.scrollTop = 0;
                document.documentElement.scrollTop = 0;
                }
        </script>  

        <script>
                // When the user scrolls down 500 px from the top of the document the button
                window.onscroll = function() {scrollFunction()};

                function scrollFunction() {
                    if (document.body.scrollTop > 500 || document.documentElement.scrollTop > 500) {
                        document.getElementById("topBtn").style.display = "block";
                    } else {
                        document.getElementById("topBtn").style.display = "none";
                    }
                }

                // When the user clicks on the button, scroll to the top of the document
                function topFunction() {
                    document.body.scrollTop = 0;
                    document.documentElement.scrollTop = 0;
                }
        </script>      
    </body>
</html>
"""
            excep = "Writing JS To Final HTML"
            finalFile.write(tmp)
            finalFile.close()

            excep = "Reading Final File for displaying output in Output Pane."
            finalFile = open(self.fileName, "r")
            Output = finalFile.read()
            finalFile.close()
            logging.info("Final Output Read & Rendered in Output Variable")
            #print("</pre>" + Output + "<pre>")

            return True
        except Exception as e:
            #logging.info("Exception Occurred in createFinalHtml while " + excep + ":- " + str(e))
            #print("Exception Occurred in createFinalHtml while", excep, ":-", str(e))
            exc_type, exc_obj, exc_tb = sys.exc_info()
            lineno = exc_tb.tb_lineno
            print("Exception in " + stack()[0][3] + " While, " + excep + " :- " + str(e) + ".\nException Line: " + str(lineno) + " - " + self.code[lineno-1])
            logging.info("Exception in " + stack()[0][3] + " While, " + excep + " :- " + str(e) + ".\nException Line: " + str(lineno) + " - " + self.code[lineno-1])
            return False
    #endregion


    # region Decrypts Password Password
    def decrypt(self):
        excep = ""
        pswd = ""
        try:
            excep = "Decrypting Password"
            fernet = Fernet(self.key)
            pswd = fernet.decrypt(self.dbPwd).decode()

            return pswd
        except Exception as e1:
            print("Exception Occurred in Decryption Block:- " + str(e1))
            logging.info("Exception Occurred in Decryption Block:- " + str(e1))
            return pswd
    #endregion


    # region Encrypts Passed Password
    def encrypt(self, dbPwd):
        excep = ""
        pswd = b''
        try:
            excep = "Generating Key"
            self.key = Fernet.generate_key()

            excep = "Encrypting Password"
            fernet = Fernet(self.key)
            self.dbPwd = fernet.encrypt(dbPwd.encode())

            return True
        except Exception as e1:
            print("Exception Occurred in Encryption Block:- " + str(e1))
            logging.info("Exception Occurred in Encryption Block:- " + str(e1))
            return False
    #endregion


    # region Releases SSH Connection From Server
    def terminateConn(self, host):
        if self.channel:
            self.channel.close()
            self.channel = ""
            #print("Channel Closed From " + host + "\n")
            logging.info("Channel Closed From " + host)
        if self.ssh:
            self.ssh.close()
            self.ssh = ""
            #print("SSH Closed From " + host + "\n")
            logging.info("SSH Closed From " + host)
    # endregion


    # region Tracks Ending of Remote Command & Stores Output in cmdOp Variable of This Class
    def chkCmdEnd(self, cmd, prmpt):
        try:
            buf = ""
            self.cmdOp = ""
            while not buf.endswith(prmpt):
                res = self.channel.recv(65535)
                try:
                    buf = res.decode('ascii')
                except Exception as e1:
                    buf = str(res, 'utf-8')
                if "exit" in cmd:
                    #print("Buf-", cmd, ":-", buf)
                    pass
                self.cmdOp += buf

        except Exception as e:
            err = ""
            err = str(e)
            if err == "":
                err = cmd + ": Command Execution Timed Out"

            logging.info("Exception while tracking \"" + cmd + "\":- " + err)
            #print("Exception while tracking \"" + cmd + "\":-" + err)
    # endregion


    # region Establishes SSH With Target Server
    def getConn(self, host, user, pwd, keyFile, keyPwd, oraUsr):
        excep = ""
        self.dbList = []
        try:
            logging.info("Requesting SSH Connection.........")
            excep = "Creating SSH To DB Server: " + host
            self.ssh = paramiko.SSHClient()
            self.ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

            if pwd == "":
                key = paramiko.RSAKey.from_private_key_file(keyFile, password=keyPwd)
                self.ssh.connect(host, port=22, username=user, pkey=key)
            else:
                self.ssh.connect(host, port=22, username=user, password=pwd)
            logging.info("SSH Established With Remote Host: " + host)

            logging.info("Requesting Remote Channel......")
            excep = "Creating Secure Channel With DB Server"
            self.channel = self.ssh.invoke_shell()  # Create Channel For Sending File System Access Shell Command
            logging.info("Remote Channel Created With Host: " + host)
            #print("Connected To Remote Host")

            excep = "Fetching Primary Prompt"
            time.sleep(5)
            res = self.channel.recv(131070)
            buf = ""
            try:
                buf = res.decode('ascii')
            except Exception:
                buf = str(res, 'UTF-8')

            if "YYYY" in buf.upper() and "MM" in buf.upper() and "DD" in buf.upper():
                dte = datetime.datetime.now().strftime('%Y%m%d')
                #print("Date:-", dte)
                self.channel.send(dte + "\n")
                time.sleep(2)
                buf = ""
                res = self.channel.recv(65535)
                try:
                    buf = res.decode('ascii')
                except Exception as e1:
                    buf = str(res, 'utf-8')
                #print("Date-", buf)

            lines = buf.split("\n")
            self.prompt = lines[-1]
            #print("primary Prompt-", self.prompt)


            excep = "Sudo'ing to Oracle User For: " + host
            logging.info(excep)
            cmd = "sudo -iu " + oraUser
            self.channel.send(cmd + "\n")

            sudoStat = True
            buf = ""
            quit = oraUsr + "@"
            while True:
                res = self.channel.recv(65535)
                try:
                    buf = res.decode('ascii')
                except Exception as e1:
                    buf = str(res, 'utf-8')
                #print("SUDO-", buf)

                self.cmdOp += buf
                if "password:" in buf or "Password:" in buf or buf.endswith(": ") or quit in buf:
                    break

                if self.prompt in buf:
                    sudoStat = False
                    break

            if not sudoStat:
                self.cmdOp = buf + "\n" + "Sudo To Oracle User Failed For: " + host
                self.terminateConn(host)
                #print(self.cmdOp)
                logging.error(self.cmdOp)
                return False

            excep = "Checking for Authentication of Oracle User"
            if "password:" in buf or "Password:" in buf or buf.endswith(": "):
                self.channel.send(pwd + "\n")
                buf = ""
                quit = oraUser + "@"

                while not quit in buf:
                    res = self.channel.recv(65535)
                    try:
                        buf = res.decode('ascii')
                    except Exception as e1:
                        buf = str(res, 'utf-8')

                    #print("SUDO_Pass-", buf)
                    self.cmdOp += buf
                    #print(buf.rstrip())
                    if self.prompt in buf:
                        sudoStat = False
                        break

            if not sudoStat:
                self.cmdOp = buf + "\n" + "Sudo To Oracle User Failed For: " + host
                self.terminateConn(host)
                return False

            logging.info("Oracle User Authenticated For: " + host)
            #print("Oracle User Authenticated For: " + host)

            excep = "Fetching Prompt"
            self.prompt = self.cmdOp.split("\n")[-1]
            logging.info("Prompt Fetched- " + self.prompt)
            #print("Prompt-", self.prompt)

            return True
        except Exception as e:
            #logging.info("Exception Occurred in getConn While " + excep + ":- " + str(e))
            #print("Exception Occurred in getConn While " + excep + ":- " + str(e))
            exc_type, exc_obj, exc_tb = sys.exc_info()
            lineno = exc_tb.tb_lineno
            print("Exception in " + stack()[0][3] + " While, " + excep + " :- " + str(e) + ".\nException Line: " + str(lineno) + " - " + self.code[lineno-1])
            logging.info("Exception in " + stack()[0][3] + " While, " + excep + " :- " + str(e) + ".\nException Line: " + str(lineno) + " - " + self.code[lineno-1])
            self.cmdOp = str(e)

            self.terminateConn(host)
            return False
    # endregion


    # region Closes Existing DB Connection
    def closeDB(self, host):
        if self.crsr:
            self.crsr.close()
            self.crsr = ""
            #print("\nCursor Closed From " + host)
            logging.info("Cursor Closed From " + host)
        if self.conn:
            self.conn.close()
            self.conn = ""
            #print("DB Connection Released From " + host)
            logging.info("DB Connection Released From " + host)
    # endregion


    # region Establishes DB Connection
    def connDB(self, dbUsr, dbPwd, host, port, service):
        excep = ""
        try:
            db = service.lower().split(".")[0]
            print("DB- ",db)
            dsn_tns = "(DESCRIPTION=(ADDRESS=(PROTOCOL=TCP)(HOST=" + str(host) + ")(PORT=" + port + "))(CONNECT_DATA=(SERVICE_NAME=" + service + ")))"

            excep = "Requesting DB Connection For " + host + "_" + db
            print(excep, "-", dsn_tns)
            #print("DB USER- ",dbUsr)
            if dbUsr.upper() == "SYS":
                self.conn = oracledb.connect(user=dbUsr, password=self.decrypt(), dsn=dsn_tns, mode=oracledb.SYSDBA)
            else:
                self.conn = oracledb.connect(user=dbUsr, password=dbPwd, dsn=dsn_tns)

            if (self.conn):
                logging.info("Connected to Database:- " + host + "_" + db)
                excep = "Creating Cursor For DB Connection"
                self.crsr = self.conn.cursor()
                logging.info("Cursor Created For The Same")
                #print("Connected to Database- " + host + "_" + db)

                excep = "Setting Call Timeout on db Connection For " + host + "_" + db
                #self.conn.callTimeout = self.queryTimeout

                excep = "Checking Version"
                qry = "select version from gv$instance"
                self.crsr.execute(qry)
                res = self.crsr.fetchall()

                excep = "Fetching DB Version"
                self.version = res[0][0]
                #print("DB Version is -", self.version)
                logging.info("DB Version is - " + str(self.version))

                return True
        except Exception as e:
            #self.cmdOp = "Exception Occurred in connDB While " + excep + ":- " + str(e)
            #logging.info(self.cmdOp)
            #print(self.cmdOp)
            self.cmdOp = str(e)
            exc_type, exc_obj, exc_tb = sys.exc_info()
            lineno = exc_tb.tb_lineno
            msg = "Exception in " + stack()[0][3] + " While, " + excep + " :- " + str(e) + ".\nException Line: " + str(lineno) + " - " + self.code[lineno - 1]
            logging.info(msg)
            print(msg)

            self.closeDB(host)
            return False
    # endregion


    # region Performs Entire Temp Tablespace Operations
    def fetchTEMPTablespaceStatus(self, user, pwd, oraUsr, keyFile, keyPwd, dbUsr, dbPwd, host, port, service, osHost):
        excep = ""
        dbHost = ""
        try:
            timestamp = datetime.datetime.now().strftime("_%H_%M_%S")
            db = service.split(".")[0]

            stat = False
            stat = self.getConn(osHost, user, pwd, keyFile, keyPwd, oraUsr)
            if not stat:
                self.htmlStr += "<li><button class=\"sidebar-title-failed\" onclick = \"createReport(event, '" + host + "_" + db + timestamp + "')\">&nbsp &nbsp " + host + " (" + db + """)</button></a>
            </li>

        Leftpane Ends Here"""
                self.htmlStr += "<div id = \"" + host + timestamp + """" class = "tabcontent">
                    <h3 style="text-align: center; color: Green;"><u> Report For """ + host + "</u><br> </h3>\n"
                self.htmlStr += """<br><br>
                <table style = "background-color: #EFEFEF">     
                    <tr>    <td class="custom"><b>TEMP Tablespace Check Failed For Below Issue. <br>SSH Failed In Attempt of Fetching DB Password. 
<br>Error: - </b>"""
                if "getaddrinfo failed" in self.cmdOp:
                    self.cmdOp += "\nPlease Check If The Hostname is Correct or Not."

                lines = self.cmdOp.split("\n")
                for i in range(0, len(lines)):
                    self.htmlStr += """<br> <b>
""" + lines[i].rstrip() + "</b>"

                self.htmlStr += """    </td>   </tr>   </table>    <br><br>
        </div>"""
                self.htmlList.append(self.htmlStr)

                self.mailMsg = osHost + "_" + db + ": SSH Failed In Attempt of Fetching DB Password. Error:- \n" + "\n".join(lines[0:])
                stat = self.sendMail(osHost, db)
                return False


            excep = host + "_" + db + ": Fetching DB Password"
            cmd = ""
            if osHost.upper().startswith("UT") or osHost.upper().startswith("XDT"):
                cmd = "cat " + self.qaPwd
            else:
                cmd = "cat " + self.prodPwd
            self.channel.send(cmd + "\n")
            self.chkCmdEnd(cmd, self.prompt)

            try:
                #print("pswd-", self.cmdOp.split("\n")[1].rstrip())
                stat = self.encrypt(self.cmdOp.split("\n")[1].rstrip())
                #print(host + "_" + db + ": DB Password Fetched & Encrypted")
                logging.info(host + "_" + db + ": DB Password Fetched & Encrypted")
            except Exception as e1:
                msg = osHost + "_" + db + ": DB Password Fetching Failed. " + str(e1)
                print(msg)
                logging.info(msg)
                stat = self.sendMail(osHost, db)


            if self.dbPwd == b'':
                msg = osHost + "_" + db + """: Blank DB Password Received After Encryption.
TEMP Tablespace Utilization Check failed.
"""
                print(msg)
                logging.info(msg)
                self.sendMail(osHost, db)
                self.terminateConn(osHost)
                return False

            self.terminateConn(osHost)

            excep = host + "_" + db + ": Calling DB Connection"
            # print(excep)
            dbStat = False
            dbStat = self.connDB(dbUsr, dbPwd, host, port, service)
            tmpHtml = ""

            if not dbStat:
                tmpHtml += "<li><button class=\"sidebar-title-failed\" onclick = \"createReport(event, '" + host + "_" + db + timestamp + "')\">&nbsp &nbsp " + host + " (" + db + """)</button></a>
            </li>

        Leftpane Ends Here"""
                tmpHtml += "<div id = \"" + host + "_" + db + timestamp + """" class = "tabcontent">
                        <h3 style="text-align: center; color: Green;"><u> Report For """ + host + " (" + db + ")</u><br> </h3>\n"
                tmpHtml += """<br><br>
                    <table style = "background-color: #EFEFEF">     <tr>    <td class="custom"><b>    DB Connection To This Remote Database Failed with Following Error: - </b>"""
                lines = self.cmdOp.split("\n")
                for j in range(0, len(lines)):
                    tmpHtml += "<br> <b>" + lines[j] + "</b>"
                tmpHtml += """    </td>   </tr>   </table>    <br><br>
                </div>"""
                self.htmlList.append(tmpHtml)

                self.mailMsg = "DB Connection With " + host + "_" + db + " failed with following error:- \n" + "\n".join(lines[0:])
                stat = self.sendMail(host, db)
                return False


            excep = "Creating Leftpane for " + host
            tmpHtml += "<li><button style= \"font-size:14px\" class=\"sidebar-title\" onclick = \"createReport(event, '" + host + "_" + db + timestamp + "')\">&nbsp &nbsp " + host + " (" + db + """)</button></a>
            </li>

        Leftpane Ends Here"""
            tmpHtml += "   <div id = \"" + host + "_" + db + timestamp + """\" class = "tabcontent">
        <h3 style="text-align: center; color: Green;"><u> TEMP TABLESPACE UTILIZATION REPORT__""" + host + " (" + db + ")</u><br> </h3>\n"""


            excep = self.incNum + "_" + host + ": Fetching DB Type"
            dbType = "Standalone"
            if db[:3].lower() == "cdb":
                dbType = "CDB"
            elif db[:3].lower() == "pdb":
                dbType = "PDB"

            self.toMail = "UNSDBA-" + db.upper() + "@LISTS.NTRS.COM"
            
            '''
            excep = host + ": Fetching Container/Main DB Name"
            qry = "select name from v$database"
            self.crsr.execute(qry)
            res = self.crsr.fetchall()
            self.toMail += ",UNSDBA-" + res[0][0].split(".")[0].upper() + "@LISTS.NTRS.COM"

            excep = osHost + ": Checking If Container or Not"
            tmp = int(self.version.split(".")[0])
            if tmp > 11:
                if service[0:3].upper() == "CDB":
                    excep = osHost + ": Fetching PDBS"
                    qry = "select name from gv$pdbs"
                    self.crsr.execute(qry)
                    res = self.crsr.fetchall()

                    for i in range(0, len(res)):
                        db = res[i][0]
                        if not "$" in db:
                            self.toMail += ",UNSDBA-" + db.split(".")[0].upper() + "@LISTS.NTRS.COM"

            if not self.prod:
                excep = "Sending Initial Mail"
                bs.mailMsg = """ TEMP Tablespace Utilization is high and please investigate if any adhoc SQL's running in the database immediately."""
                stat = False
                stat = bs.sendMail(host, service.split(".")[0])
                if not stat:
                    print("Initial Mail Sending Failed")
                    logging.info("Initial Mail Sending Failed")
                else:
                    print("Initial Mail Sending Successful")
                    logging.info("Initial Mail Sending Successful")
            '''


            excep = "Running Query To Fetch TEMP Tablespace"
            qry = ""
            #colCount = ""
            #colCounts = [21, 15, 15]
            qryHdr = ["Temp Tablespace Utilization - " + dbType , "Session Details - " + dbType, "SQL Text - " + dbType, "Status Details - " + dbType]
            session = "select S.CON_ID, S.UERSNAME, S.SID, S.SERIAL#, U.TABLESPACE, U.CONTENTS, U.EXTENTS, U.BLOCKS FROM GV$SESSION S, GV$SORT_USAGE U where S.CON_ID=U.CON_ID and S.SADDR=U.SESSION_ADDR order by U.BLOCKS desc"

            if dbType == "CDB":
                #colCount = str(colCounts[0])
                qry = ["""SELECT A.CON_ID,A.TABLESPACE_NAME,ROUND((C.TOTAL_BLOCKS*B.BLOCK_SIZE)/1024/1024/1024,2) "TOTAL SIZE [GB]",
ROUND((A.USED_BLOCKS*B.BLOCK_SIZE)/1024/1024/1024,2) "USED_SIZE[GB]",ROUND(((C.TOTAL_BLOCKS-A.USED_BLOCKS)*B.BLOCK_SIZE)/1024/1024/1024,2) "FREE_SIZE[GB]", 
ROUND((A.MAX_BLOCKS*B.BLOCK_SIZE)/1024/1024/1024,2) "MAX_SIZE_EVER_USED[GB]",
ROUND((A.MAX_USED_BLOCKS*B.BLOCK_SIZE)/1024/1024/1024,2) "MAXSIZE_EVER_USED_BY_SORTS[GB]" , 
ROUND((A.USED_BLOCKS/C.TOTAL_BLOCKS)*100,2) "USED PERCENTAGE" 
FROM GV$SORT_SEGMENT A,CDB_TABLESPACES B,(SELECT TABLESPACE_NAME,SUM(BLOCKS) TOTAL_BLOCKS FROM CDB_TEMP_FILES GROUP BY TABLESPACE_NAME) C 
WHERE A.TABLESPACE_NAME=B.TABLESPACE_NAME AND A.CON_ID=B.CON_ID AND A.TABLESPACE_NAME=C.TABLESPACE_NAME""",

"select S.CON_ID, S.USERNAME, S.SID, S.SERIAL#, U.TABLESPACE, U.CONTENTS, U.EXTENTS, U.BLOCKS FROM GV$SESSION S, GV$SORT_USAGE U where S.CON_ID=U.CON_ID and S.SADDR=U.SESSION_ADDR order by U.BLOCKS desc",

"""SELECT * FROM
(SELECT A.CON_ID,D.TABLESPACE_NAME,A.SID,A.SERIAL#,A.PROGRAM,A.MODULE,A.ACTION,A.USERNAME "DB USERNAME",A.OSUSER,ROUND((B.BLOCKS*D.BLOCK_SIZE)/1024/1024,2) "USED MB",C.SQL_TEXT
FROM GV$SESSION A, GV$TEMPSEG_USAGE B, GV$SQLAREA C,CDB_TABLESPACES D
WHERE A.SADDR = B.SESSION_ADDR AND A.CON_ID=B.CON_ID AND A.CON_ID=C.CON_ID AND A.CON_ID=D.CON_ID AND C.ADDRESS= A.SQL_ADDRESS AND C.HASH_VALUE = A.SQL_HASH_VALUE AND D.TABLESPACE_NAME=B.TABLESPACE ORDER BY B.TABLESPACE, B.BLOCKS DESC)
WHERE ROWNUM <=10""",

"""SELECT * FROM (
SELECT S.CON_ID,S.SID,S.STATUS,S.SQL_HASH_VALUE SESSHASH,U.SQLHASH SORTHASH,S.USERNAME,U.TABLESPACE,SUM(U.BLOCKS*P.VALUE/1024/1024) MBUSED ,SUM(U.EXTENTS) NOEXTS,
NVL(S.MODULE,S.PROGRAM) PROGINFO,FLOOR(LAST_CALL_ET/3600)||':'||FLOOR(MOD(LAST_CALL_ET,3600)/60)||':'||MOD(MOD(LAST_CALL_ET,3600),60) LASTCALLET FROM GV$SORT_USAGE U,
GV$SESSION S,GV$PARAMETER P WHERE U.SESSION_ADDR = S.SADDR AND S.CON_ID=U.CON_ID AND P.NAME = 'DB_BLOCK_SIZE' GROUP BY  S.CON_ID,S.SID,S.STATUS,S.SQL_HASH_VALUE,U.SQLHASH,S.USERNAME,U.TABLESPACE,
NVL(S.MODULE,S.PROGRAM),FLOOR(LAST_CALL_ET/3600)||':'||FLOOR(MOD(LAST_CALL_ET,3600)/60)||':'||MOD(MOD(LAST_CALL_ET,3600),60) ORDER BY 7 DESC,3)WHERE ROWNUM < 11"""]
                
            else:
                #colCount = str(colCounts[0])
                qry = ["""SELECT A.TABLESPACE_NAME,ROUND((C.TOTAL_BLOCKS*B.BLOCK_SIZE)/1024/1024/1024,2) "TOTAL SIZE [GB]",
ROUND((A.USED_BLOCKS*B.BLOCK_SIZE)/1024/1024/1024,2) "USED_SIZE[GB]",ROUND(((C.TOTAL_BLOCKS-A.USED_BLOCKS)*B.BLOCK_SIZE)/1024/1024/1024,2) "FREE_SIZE[GB]", 
ROUND((A.MAX_BLOCKS*B.BLOCK_SIZE)/1024/1024/1024,2) "MAX_SIZE_EVER_USED[GB]",
ROUND((A.MAX_USED_BLOCKS*B.BLOCK_SIZE)/1024/1024/1024,2) "MAXSIZE_EVER_USED_BY_SORTS[GB]" , ROUND((A.USED_BLOCKS/C.TOTAL_BLOCKS)*100,2) "USED PERCENTAGE"
FROM GV$SORT_SEGMENT A,DBA_TABLESPACES B,(SELECT TABLESPACE_NAME,SUM(BLOCKS) TOTAL_BLOCKS FROM DBA_TEMP_FILES GROUP BY TABLESPACE_NAME) C
WHERE A.TABLESPACE_NAME=B.TABLESPACE_NAME AND A.TABLESPACE_NAME=C.TABLESPACE_NAME""",

"""SELECT S.USERNAME,S.SID,S.SERIAL#,U.TABLESPACE, U.CONTENTS, U.EXTENTS, U.BLOCKS FROM GV$SESSION S, GV$SORT_USAGE U 
WHERE S.SADDR=U.SESSION_ADDR ORDER BY U.BLOCKS DESC""",

"""SELECT * FROM
(SELECT D.TABLESPACE_NAME,A.SID,A.SERIAL#,A.PROGRAM,A.MODULE,A.ACTION,A.USERNAME "DB USERNAME",A.OSUSER,ROUND((B.BLOCKS*D.BLOCK_SIZE)/1024/1024,2) "USED MB",C.SQL_TEXT
FROM GV$SESSION A, GV$TEMPSEG_USAGE B, GV$SQLAREA C,DBA_TABLESPACES D
WHERE A.SADDR = B.SESSION_ADDR AND C.ADDRESS= A.SQL_ADDRESS AND C.HASH_VALUE = A.SQL_HASH_VALUE AND D.TABLESPACE_NAME=B.TABLESPACE 
ORDER BY B.TABLESPACE, B.BLOCKS DESC)
WHERE ROWNUM <=10""",

"""SELECT * FROM (
SELECT S.SID,S.STATUS,S.SQL_HASH_VALUE SESSHASH,U.SQLHASH SORTHASH,S.USERNAME,U.TABLESPACE,SUM(U.BLOCKS*P.VALUE/1024/1024) MBUSED ,SUM(U.EXTENTS) NOEXTS,
NVL(S.MODULE,S.PROGRAM) PROGINFO,FLOOR(LAST_CALL_ET/3600)||':'||FLOOR(MOD(LAST_CALL_ET,3600)/60)||':'||MOD(MOD(LAST_CALL_ET,3600),60) LASTCALLET FROM V$SORT_USAGE U,
GV$SESSION S,GV$PARAMETER P WHERE U.SESSION_ADDR = S.SADDR AND P.NAME = 'DB_BLOCK_SIZE' GROUP BY S.SID,S.STATUS,S.SQL_HASH_VALUE,U.SQLHASH,S.USERNAME,U.TABLESPACE,
NVL(S.MODULE,S.PROGRAM),FLOOR(LAST_CALL_ET/3600)||':'||FLOOR(MOD(LAST_CALL_ET,3600)/60)||':'||MOD(MOD(LAST_CALL_ET,3600),60) ORDER BY 7 DESC,3)WHERE ROWNUM < 11"""]
                

            q = 1
            infra = host + "_" + db
            while True:
                excep = infra + ": Starting Iteration: " + str(q)
                logging.info(excep)

                self.overall = False
                self.itsrOutput = ""
                self.htmlList = []
                self.htmlStr = ""

                usedPercentCol = 0.0

                highUtil = False
                
                
                for n in range (len(qry)):
                    excep = infra + ": Running Query For " + qryHdr[n]
                    logging.info(excep)
                    query = qry[n]
                    
                    #print("Query-", query, "\n")
                    #time.sleep(1)

                    self.crsr.execute(query)
                    result = self.crsr.fetchall()
                    excep = infra + ": Reading Column Names For " + qryHdr[n]
                    header = [x[0] for x in self.crsr.description]

                    #print("Header-", self.header)

                    excep = infra + ": Iteration-" + str(q) + ": Creating Table Columns for " + qryHdr[n]
                    logging.info(excep)
                    self.htmlStr += """
                        <div style= "overflow-x: auto;">  <table>
                            <tr>  <th colspan=""" + str(len(header)) + " bgcolor= #87CEEB>" + qryHdr[n].upper() + """</th>  </tr>
                            <tr>"""

                    # self.itsrOutput = "Columns:- "
                    for k in range(0, len(header)):
                        self.htmlStr += "   <th class=\"custom\">" + header[k] + "</th>"
                    self.htmlStr += """   </tr>
                        """

                    self.itsrOutput += "\n\n\nPlease Find Below " + qryHdr[n] + ":- \n\n"


                    excep = infra + ": Iteration-" + str(q) + ": Inserting Rows in Table for " + qryHdr[n]
                    logging.info(excep)
                    if len(result) > 0:
                        #print("Length-", len(result))

                        for k in range(0, len(result)):
                            self.htmlStr += "   <tr>"
                            #self.itsrOutput += "TEMP Tablespace" + str(k + 1) + " :- \n"

                            if n == 0:
                                if dbType == "CDB":
                                    usedPercentCol = result[0][7]

                                    excep = infra + ": Fetching PDB"
                                    logging.info(excep)
                                    pdbQry = "select NAME from v$pdbs where CON_ID=" + str(result[0][0])
                                    self.crsr.execute(pdbQry)
                                    pdbOp = self.crsr.fetchone()
                                    #print("PDB list-", pdbOp, "; ", str(result[0][0]))

                                    if pdbOp is not None:
                                        self.toMail += "UNSDBA-" + pdbOp[0].split(".")[0].upper() + "@LISTS.NTRS.COM,"
                                    else:
                                        self.toMail += "UNSDBA-" + db.upper() + "@LISTS.NTRS.COM,"
                                        
                                else:
                                    usedPercentCol = result[0][6]
                                    self.toMail += "UNSDBA-" + db.upper() + "@LISTS.NTRS.COM,"

                                if usedPercentCol >= self.thresholdValue:
                                    highUtil = True

                            for j in range(0, len(result[k])):
                                self.htmlStr += "   <td>" + str(result[k][j]) + "</td>   "
                                self.itsrOutput += header[j] + " :- " + str(result[k][j]) + "; \n"

                            self.itsrOutput += "\n"
                            self.htmlStr += """</tr>
                        """
                        
                        logging.info(infra + ": Used percentage col- " + str(usedPercentCol))
                        #print(infra + ": Used percentage col- " + str(usedPercentCol))
                        self.overall = True
                        #15, 17, 20, 22, 23, 30
                    else:
                        logging.info(infra + ": No Data Found For " + qryHdr[n])
                        self.itsrOutput += "No Data Found For " + qryHdr[n] + "\n"
                        self.htmlStr += "<tr>   <td colspan=" + str(len(header)) + " bgcolor= #87CEEB> <b> No Data Found in this Table </b> </td>   </tr>"

                    self.htmlStr += """
                    </table>  </div>    <br><br>
                    """

                self.htmlStr = tmpHtml + self.htmlStr
                self.htmlList.append(self.htmlStr)

                excep = infra + ": Iteration-" + str(q) + ": Calling Final HTML Creation Function"
                logging.info(excep)
                self.createFinalHtml()

                if self.prod:
                    break

                #file = open(self.path + "ThresholdValue.txt", "r")
                #thresholdValue = int(file.read())
                #file.close()

                if highUtil:
                    logging.info(infra + ": Temp Tablespace Utilization is Still High- " + str(usedPercentCol))
					
                    self.mailMsg = """Please investigate TEMP Tablespace in the subjected database immediately.
Please Find the Attached TEMP Tablespace Utilization Report."""
                    stat = False
                    excep = "Iteration-" + str(q) + ": Calling Mail Sending Function"
                    self.toMail = self.toMail[:-1]
                    stat = self.sendMail(osHost, service.split(".")[0])

                    if not stat:
                        print(infra + ": Mail Sending Failed")
                        logging.info(infra + ": Mail Sending Failed")
                    else:
                        print(infra + ": Mail Sending Successful")
                        logging.info(infra + ": Mail Sending Successful")

                    logging.info("Iteration-" + str(q) + ": Waiting For " + str(self.thresholdChkWait) + "Seconds")
                    time.sleep(self.thresholdChkWait)

                elif service.split(".")[0] in self.excludedDbList:
                    self.overall = True
                    self.mailMsg = """The Subjected Database is Excluded From Continuous Check Due To Some Problem Inside Database. Details Are Updated in INC.
Please investigate TEMP Tablespace in the subjected database immediately.
Please Find the Attached TEMP Tablespace Utilization Report."""

                    excep = osHost + "_" + self.incNum + ": Calling Mail Sending Function"
                    stat = self.sendMail(osHost, service.split(".")[0])

                    if not stat:
                        print("Mail Sending Failed")
                        logging.info("Mail Sending Failed")
                    else:
                        print("Mail Sending Successful")
                        logging.info("Mail Sending Successful")

                    print(osHost + "_" + self.incNum + "_" + service.split(".")[0] + ": This Database is Excluded From Continuous Check Due To Some Problem.")
                    logging.info(osHost + "_" + self.incNum + "_" + service.split(".")[0] + ": This Database is Excluded From Continuous Check Due To Some Problem.")
                    break
                else:
                    self.mailMsg = "Now Temp Tablespace Utilization is Below Threshold- " + str(usedPercentCol)
                    logging.info(self.mailMsg)
                    self.itsrOutput += "\n\n" + "Now Temp Tablespace Utilization is Below Threshold- " + str(usedPercentCol)
                    
                    stat = False
                    excep = "Iteration-" + str(q) + ": Calling Mail Sending Function"
                    stat = self.sendMail(osHost, service.split(".")[0])

                    if not stat:
                        print("Mail Sending Failed")
                        logging.info("Mail Sending Failed")
                    else:
                        print("Mail Sending Successful")
                        logging.info("Mail Sending Successful")
                    break

                q += 1

                file = self.path + self.incNum.upper() + ".txt"
                if os.path.exists(file):
                    os.remove(file)
                    break

            return True
        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            lineno = exc_tb.tb_lineno
            print("Exception in " + stack()[0][3] + " While, " + excep + " :- " + str(e) + ".\nException Line: " + str(lineno) + " - " + self.code[lineno-1])
            logging.info("Exception in " + stack()[0][3] + " While, " + excep + " :- " + str(e) + ".\nException Line: " + str(lineno) + " - " + self.code[lineno-1])
            return False
        finally:
            self.terminateConn(osHost)
            self.closeDB(host)
    # endregion


bs = ""
host = ""
excep = ""


try:
    excep = "Reading Inputs"
    inc = "inc_inp"
    bs = TEMPTablespace(inc)
    #itsm_dict = {'service': target_host, 'host' : target_name, 'username': ansible_user, 'password': ansible_password, 'oraUser': OraUser, 'dbUsr': DBUser, 'dbPwd': DBPwd, 'incident': ticketNo, 'path' : block_path} 

    #itsm_dict = {'service': 'cdb680a', 'host' : 'xdt531db01', 'username': 'uatholorchunix', 'password': 'ntrs1234', 'oraUser': 'oracle', 'dbUsr': 'sys', 'dbPwd': '', 'incident': 'inc123', 'path' : '\\WPCHOLU01\DB_usecase'} 

    itsm_dict = {'awx_job_id': awx_job_id, 'service': database_name, 'username': ansible_user, 'password': ansible_password, 'oraUser': OraUser, 'dbUsr': DBUser,  'incident': ticketNo }
   
	
    awx_job_id = itsm_dict['awx_job_id']
    dbUsr = itsm_dict['dbUsr']
    dbPwd = ""
    port = "1521"
    service = itsm_dict['service']
    user = itsm_dict['username']
    pwd = itsm_dict['password']
    bs.incNum = itsm_dict['incident']
    keyFile = ""
    keyPwd = ""
    oraUser = itsm_dict['oraUser']
	
    excep = "Reading Current File Content"
    logging.info(excep)
    program = os.path.abspath(__file__)
    file = open(program, "r")
    bs.code = file.read().split("\n")
    file.close()
    logging.info("Code Reading Complete")

    service = service.strip().lower()
    print(f"SERVICE- {service}")
    if not service.endswith(".ntrs.com"):
        service += ".ntrs.com"

    nsService = service.split(".")[0]
    print(nsService)
    if len(nsService) > 7 and nsService[-1] == "a":
    #if nsService[7] == "a":
        nsService = nsService[:-1]
        print(nsService)

    nsService += ".ntrs.com"
    print("service name- " + nsService)
	
    logging.info("Initiating Operation For INC: " + bs.incNum)

    if True:
        excep = "Validating Input Parameters"
        inpChk = False
        inputs = [(user, pwd, oraUser, dbUsr, port, service),
                  ("Server Login Username", "Server Login Password", "Oracle Username", "DB Login Username", "DB Port", "DB Service Name")]

        for i in range(0, len(inputs[0])):
            if inputs[0][i] == "":
                print("No Input Given For " + inputs[1][i])
                logging.info("No Input Given For " + inputs[1][i])
                chkInp = True

        if inpChk == True:
            print("Input Validation Failed. Terminating The Program")
            logging.info("Input Validation Failed. Terminating The Program")
            del bs
            sys.exit(0)


    excep = "Fetching Hostname For DB Service: " + service
    cmd = "nslookup " + nsService
    val = subprocess.check_output(cmd, shell=True)
    data = ""
    try:
        data = val.decode("ascii")
    except Exception:
        data = str(val, 'utf-8')

    if "can't find" in data.lower() or "non-existent domain" in data:
        #print("Hostname not found for Impacted DB. Nslookup Failed For Service Name: " + service)
        logging.info("Hostname not found for Impacted DB. Nslookup Failed For Service Name: " + service)
        del bs
        sys.exit(0)

    data = data.replace("\r", "")
    dataSet = data.split("\n")
    for i in range (0, len(dataSet)):
        line = dataSet[i].rstrip()
        if  "NAME:" in line.upper():
                #host = line.split(":")[1].replace("\t", "").replace(" ", "")
                host = line.split(":")[1].lstrip('\t')
                print("Impacted db server name:- " + host)
                logging.info("Impacted db server name:- " + host)
                break
				
    if host == "":
        print("HostName Not Found Via NSLOOKUP. NSLOOKUP O/P:- " + "\n".join(dataSet[1:-1]))
        logging.info("HostName Not Found Via NSLOOKUP. NSLOOKUP O/P:- " + "\n".join(dataSet[1:-1]))
        del bs
        sys.exit(0)

    osHost = host
    if "-" in host:
        osHost = host.split("-")[0].replace(" ", "") + "db02.ntrs.com"
        print(f"os hostname-{osHost}")

    if osHost.upper().startswith("UT") or osHost.upper().startswith("XDT"):
        bs.prod = True
        print(osHost + "_" + service + ": Problem Occurred in Non-Prod Database. No EMail Will Be Sent.")
        logging.info(osHost + "_" + service + ": Problem Occurred in Non-Prod Database. No EMail Will Be Sent.")
        
    #bs.prod = False

    stat = False
    excep = "Calling TEMP Tablespace Check Function"
    stat = bs.fetchTEMPTablespaceStatus(user, pwd, oraUser, keyFile, keyPwd, dbUsr, dbPwd, host, port, service, osHost)
    if not stat:
        print("TEMP Tablespace Check Failed For " + host + "_" + service.split(".")[0])
        logging.info("TEMP Tablespace Check Failed For " + host + "_" + service.split(".")[0])
    else:
        print("TEMP Tablespace Check Successful For " + host + "_" + service.split(".")[0])
        logging.info("TEMP Tablespace Check Successful For " + host + "_" + service.split(".")[0])

    print(bs.itsrOutput)  #Prints Email body

    stat = False
    stat = bs.createFinalHtml()
    if not stat:
        #print(self.incNum + ": Final HTML Creation Failed")
        logging.warning(bs.incNum + ": Final HTML Creation Failed")

except Exception as e:
    exc_type, exc_obj, exc_tb = sys.exc_info()
    lineno = exc_tb.tb_lineno
    print("Exception in Start Segment While " + excep + " :- " + str(e) + ".\nException Line: " + str(lineno) + " - " + bs.code[lineno-1])
    logging.info("Exception in Start Segment While " + excep + " :- " + str(e) + ".\nException Line: " + str(lineno) + " - " + bs.code[lineno-1])

finally:
    logging.info("\n\n----------------------------- Session Finished --------------------------------")
    #del bs

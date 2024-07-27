
# #region Copyright Information
# '''
# .NOTES
# ==========================================================================================
#        Created on         : 12/08/2022
#        Created by         : Sayan Chatterjee [sayan.09@wipro.com]
#        Last Reviewed By   : Somnath Banerjee [somnath.banerjee1@wipro.com]
#        Organization       : Wipro
#        Filename           : Oracle Control-M Alerts Solutions
#        Version            : 1.0
#        Copy Rights        : Copyright © 2022 Wipro Technologies. All rights reserved.
# ==========================================================================================
# '''
# #endregion

# #region Brief Description of this Usecase - GOV0023773
# '''
# This solution would fetch the logs of following jobs :
#     1. Full Backup Logs (B)
#     2. Incremental Backup Logs (I)
#     3. Archive Backup Logs (L)
#     4. Data Guard Sync GAP logs (GAP)
#     5. FRA Logs (FRA)
#     6. Primary Archive Log Cleanup (LC)

# And also, will display the fully qualified file name and the logfiles will get downloaded in a folder. 
# Logfile(s) will be uploaded in INC and few specific error logs will be updated in description.
# '''
#endregion

# ------------------------------- Script Functionality ------------------------------

#region Package Import Block
#!/usr/bin/python
# -*- coding: utf-8 -*-

import paramiko
import time
import logging
import os
import datetime
import sys
import cx_Oracle
import oracledb
import subprocess
import getpass
import re
import json
from inspect import stack
from scp import SCPClient
from cryptography.fernet import Fernet
from os.path import basename
#endregion

# def get_argument_spec():
#     module_args = dict(
#         user=dict(type="str", required=True),
#         pwd=dict(type="str", required=True),
#         ticketNo=dict(type='str',required=True),
#         jobName=dict(type='str',required=True),
#     )
#     return module_args
# module = AnsibleModule(argument_spec=get_argument_spec())

res_log = []
res_error = []
result = {
    "log": [],
    "error": []
    }

class ControlMAlerts:
    #region Class Objects
    conn = ""  # Database connection object
    crsr = ""  # Database cursor object
    ssh = ""  # SSH Connection object
    channel = ""  # SSH Channel object
    scp = ""  # Create SCP object
    cmdOp = ""  # Contains Any SSH Command Output
    path = "/runner/project/" #/tmp/oracle_automation/control_m_alert/"  # Path for Log and Output folder
    dbPwd = b''  # Encrypted Database Password
    key = b''  # Encryption key
    inc = "" # Incident number
    queryTimeout = 600  # Timeout for Query execution

    prodPwd = "/tnt/canon/dba/.prodpwd"
    qaPwd = "/tnt/canon/dba/.qapwd"
    #endregion


    #region This Constructor Function. This Also Initiates The Logging For The Solution
    def __init__(self):
        if not self.path.endswith(os.sep):
            self.path += os.sep

        logPath = f"{self.path}Logs{os.sep}"
        if not os.path.exists(logPath):
            os.system("mkdir " + logPath)

        logging.basicConfig(
            filename=datetime.datetime.now().strftime(logPath + 'ControlMAlertsLog_%d-%m-%Y.log'),
            level=logging.DEBUG, format=('%(asctime)s - %(message)s'), datefmt='%Y-%m-%d %H-%M-%S')
        logging.info("\n\n-----------------------------Starting New Logging Session--------------------------------")
        res_log.append("\n\n-----------------------------Starting New Logging Session--------------------------------")

        del logPath
    #endregion


    #region Decrypts The Encrypted String Given In Function Parameter
    def decrypt(self):
        excep = ""
        pswd = ""
        fernet = Fernet(self.key)
        try:
            excep = "Decrypting Password"
            pswd = fernet.decrypt(self.dbPwd).decode()

            return pswd
        except Exception as e1:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            print("Exception in " + stack()[0][3] + " While, " + excep + ", At Line " + str(exc_tb.tb_lineno) + ":- " + str(e1))
            res_error.append("Exception in " + stack()[0][3] + " While, " + excep + ", At Line " + str(
                exc_tb.tb_lineno) + ":- " + str(e1))

            logging.info("Exception in " + stack()[0][3] + " While, " + excep + ", At Line " + str(exc_tb.tb_lineno) + ":- " + str(e1))
            res_error.append(("Exception in " + stack()[0][3] + " While, " + excep + ", At Line " + str(exc_tb.tb_lineno) + ":- " + str(e1)))
            return pswd

        finally:
            del excep, fernet
    #endregion


    #region Encrypts The String Given In Function Parameter
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
            exc_type, exc_obj, exc_tb = sys.exc_info()
            res_error.append("Exception in " + stack()[0][3] + " While, " + excep + ", At Line " + str(exc_tb.tb_lineno) + ":- " + str(e1))
            logging.info("Exception in " + stack()[0][3] + " While, " + excep + ", At Line " + str(exc_tb.tb_lineno) + ":- " + str(e1))
            return False

        finally:
            del excep
    #endregion


    #region This releases any existing SSH connection
    def terminateConn(self, host):
        if self.channel:
            self.channel.close()
            self.channel = ""
            # print("Channel Closed From " + host + "\n")
            logging.info("Channel Closed From " + host)
            res_log.append("Channel Closed From " + host)
        if self.ssh:
            self.ssh.close()
            self.ssh = ""
            # print("SSH Closed From " + host + "\n")
            logging.info("SSH Closed From " + host)
            res_log.append("SSH Closed From " + host)
        if self.scp:
            self.scp.close()
            self.scp = ""
            # print("SCP Closed From " + host + "\n")
            logging.info("SCP Closed From " + host)
            res_log.append("SCP Closed From " + host)
    #endregion


    #region Tracks an SSH Command When Ends and Reads O/P. Checks Remote Command ended or not and captures output in cmdOp class member.
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
                    # print("Buf-", cmd, ":-", buf)
                    pass
                self.cmdOp += buf

        except Exception as e:
            err = ""
            err = str(e)
            if err == "":
                err = cmd + ": Command Execution Timed Out"

            exc_type, exc_obj, exc_tb = sys.exc_info()
            res_error.append("Exception in " + stack()[0][3] + " While, " + excep + ", At Line " + str(exc_tb.tb_lineno) + ":- " + str(e))
            logging.info("Exception in " + stack()[0][3] + " While, " + excep + ", At Line " + str(exc_tb.tb_lineno) + ":- " + str(e))

        finally:
            del buf, res
    #endregion


    #region Establishes SSH Connection to Server and creates Remote Channel. Switching to ORACLE user.
    def getConn(self, host, user, pwd, keyFile, keyPwd, oraUsr):
        excep = buf = cmd = quit = dte = ""
        res = b''
        try:
            logging.info("Requesting SSH Connection.........")
            res_log.append("Requesting SSH Connection.........")
            excep = "Creating SSH To DB Server: " + host
            self.ssh = paramiko.SSHClient()
            self.ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            # print("SSH Established With Remote Host: " + str(host) + " " + str(user) + " " + str(pwd))
            if pwd == "":
                key = paramiko.RSAKey.from_private_key_file(keyFile, password=keyPwd)
                self.ssh.connect(host, port=22, username=user, pkey=key)
            else:
                self.ssh.connect(host, port=22, username=user, password=pwd)

            logging.info("SSH Established With Remote Host: " + host)
            res_log.append("SSH Established With Remote Host: " + host)

            # <----- Creating SCP object ----->
            excep = "Creating SCP object to download files"
            logging.info(excep)
            res_log.append(excep)
            self.scp = SCPClient(self.ssh.get_transport())

            logging.info("Requesting Remote Channel......")
            res_log.append("Requesting Remote Channel......")
            excep = "Creating Secure Channel With DB Server"
            self.channel = self.ssh.invoke_shell()  # Create Channel For Sending File System Access Shell Command
            logging.info("Remote Channel Created With Host: " + host)
            res_log.append("Remote Channel Created With Host: " + host)
            # print("Connected To Remote Host")

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
                # print("Date:-", dte)
                self.channel.send(dte + "\n")
                time.sleep(2)
                buf = ""
                res = self.channel.recv(65535)
                try:
                    buf = res.decode('ascii')
                except Exception as e1:
                    buf = str(res, 'utf-8')
                # print("Date-", buf)

            lines = buf.split("\n")
            self.prompt = lines[-1]
            # print("primary Prompt-", self.prompt)

            excep = "Sudo'ing to Oracle User For: " + host
            logging.info(excep)
            res_log.append(excep)
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
                # print("SUDO-", buf)

                self.cmdOp += buf
                if "password:" in buf or "Password:" in buf or buf.endswith(": ") or quit in buf:
                    break

                if self.prompt in buf:
                    sudoStat = False
                    break

            if not sudoStat:
                self.cmdOp = buf + "\n" + "Sudo To Oracle User Failed For: " + host
                self.terminateConn(host)
                # print(self.cmdOp)
                logging.error(self.cmdOp)
                res_log.append(self.cmdOp)
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

                    # print("SUDO_Pass-", buf)
                    self.cmdOp += buf
                    # print(buf.rstrip())
                    if self.prompt in buf:
                        sudoStat = False
                        break

            if not sudoStat:
                self.cmdOp = buf + "\n" + "Sudo To Oracle User Failed For: " + host
                self.terminateConn(host)
                return False

            logging.info("Oracle User Authenticated For: " + host)
            res_log.append("Oracle User Authenticated For: " + host)
            # print("Oracle User Authenticated For: " + host)

            excep = "Fetching Prompt"
            self.prompt = self.cmdOp.split("\n")[-1]
            logging.info("Prompt Fetched- " + self.prompt)
            res_log.append("Prompt Fetched- " + self.prompt)
            # print("Prompt-", self.prompt)

            return True
        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            res_error.append("Exception in " + stack()[0][3] + " While, " + excep + ", At Line " + str(exc_tb.tb_lineno) + ":- " + str(e))
            logging.info("Exception in " + stack()[0][3] + " While, " + excep + ", At Line " + str(exc_tb.tb_lineno) + ":- " + str(e))
            # logging.info("Exception Occurred in getConn While " + excep + ":- " + str(e))
            # print("Exception Occurred in getConn While " + excep + ":- " + str(e))
            self.cmdOp = str(e)

            self.terminateConn(host)
            return False

        finally:
            del excep, buf, res, cmd, quit, dte
    #endregion


    #region Releases Existing DB Connection
    def closeDB(self, host):
        if self.crsr:
            self.crsr.close()
            self.crsr = ""
            # print("\nCursor Closed From " + host)
            logging.info("Cursor Closed From " + host)
            res_log.append("Cursor Closed From " + host)
        if self.conn:
            self.conn.close()
            self.conn = ""
            # print("DB Connection Released From " + host)
            logging.info("DB Connection Released From " + host)
            res_log.append("DB Connection Released From " + host)
    #endregion


    #region Establishes DB Connection
    def connDB(self, dbUsr, dbPwd, host, port, service):
        excep = db = dsn_tns = ""
        try:
            db = service.split(".")[0]
            dsn_tns = "(DESCRIPTION=(ADDRESS=(PROTOCOL=TCP)(HOST=" + host + ")(PORT=" + port + "))(CONNECT_DATA=(SERVICE_NAME=" + service + ")))"

            excep = "Requesting DB Connection For " + host + "_" + db
            # print(excep, "-", dsn_tns)
            if dbUsr.upper() == "SYS":
                self.conn = oracledb.connect(user=dbUsr, password=self.decrypt(), dsn=dsn_tns, mode=oracledb.SYSDBA)
            else:
                self.conn = oracledb.connect(user=dbUsr, password=self.decrypt(), dsn=dsn_tns)

            if (self.conn):
                logging.info(host + "_" + service + ": Connected to Database.")
                res_log.append(host + "_" + service + ": Connected to Database.")

                excep = "Creating Cursor For DB Connection"
                self.crsr = self.conn.cursor()
                logging.info(host + "_" + service + ": Cursor Created.")
                res_log.append(host + "_" + service + ": Cursor Created.")

                # excep = "Setting Call Timeout on db Connection For " + host + "_" + service
                # self.conn.callTimeout = self.queryTimeout

                return True
        except Exception as e:
            self.cmdOp = "Exception Occurred in connDB While " + excep + ":- " + str(e)
            self.closeDB(host)
            exc_type, exc_obj, exc_tb = sys.exc_info()
            res_error.append("Exception in " + stack()[0][3] + " While, " + excep + ", At Line " + str(exc_tb.tb_lineno) + ":- " + str(e))
            logging.info("Exception in " + stack()[0][3] + " While, " + excep + ", At Line " + str(exc_tb.tb_lineno) + ":- " + str(e))
            return False

        finally:
            del excep, db, dsn_tns
    #endregion


    #region Download files from source to destination path
    def fileDownload(self, db, op, host):
        excep = targetPath = sourcePath = ""
        try:
            excep = self.inc + "_" + host + ": Checking Alert log folder"
            logging.info(excep)
            res_log.append(excep)
            targetPath = self.path + "AlertLogs" + os.sep
            if not os.path.exists(targetPath):
                os.system("mkdir " + targetPath)
                res_log.append("Alert log folder created")

            excep = self.inc + "_" + host + ": Downloading files"
            logging.info(excep)
            res_log.append(excep)
            for i in range(0, len(op)):
                sourcePath = "/u01/app/oracle/local/log/" + db + "/" + op[i].rstrip()
                targetFilePath = targetPath + self.inc + "_" + op[i].rstrip()
                res_log.append("sourcepath is  - " + sourcePath)
                self.scp.get(sourcePath, targetFilePath)

            return True
        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            res_error.append("Exception in " + stack()[0][3] + " While, " + excep + ", At Line " + str(exc_tb.tb_lineno) + ":- " + str(e))
            logging.info("Exception in " + stack()[0][3] + " While, " + excep + ", At Line " + str(exc_tb.tb_lineno) + ":- " + str(e))
            return False

        finally:
            del excep, targetPath, sourcePath
    #endregion


    #region Full and Incremental Backup Logs
    def fullandIncrBkpLogs(self, db, cmd, size, host):
        excep = result = qry = ""
        try:
            # <----- Running Commands to find Full Backup & Incremental Backup Logs ----->
            excep = self.inc + "_" + host + ": Running Commands to find Full Backup & Incremental Backup Logs"
            logging.info(excep)
            res_log.append(excep)
            excep = "Running Command: " + cmd
            self.channel.send(cmd + "\n")
            self.chkCmdEnd(cmd, self.prompt)
            op = self.cmdOp.split("\n")[-5:-1]
            res_log.append("The extracted files are : \n" + str(op))
            logging.info("The extracted files are : \n" + str(op))

            excep = self.inc + "_" + host + ": Downloading Full and Incremental Backup Log files"
            logging.info(excep)
            res_log.append(excep)
            dwn = False
            dwn = self.fileDownload(db, op, host)
            res_log.append("File downloaded : " + str(dwn) + "\n")
            logging.info("File downloaded : " + str(dwn) + "\n")
            if not dwn:
                res_log.append(self.inc + "_" + host + ": Download for Full and Incremental Backup log files failed")
                logging.info(self.inc + "_" + host + ": Download for Full and Incremental Backup log files failed")
                return False

            excep = self.inc + "_" + host + ": Checking size of Error log file"
            logging.info(excep)
            res_log.append(excep)
            excep = "Running command to check size of error file" + size
            logging.info(excep)
            res_log.append(excep)

            self.channel.send(size + "\n")
            self.chkCmdEnd(size, self.prompt)
            ops = self.cmdOp.split("\n")[-2:-1][0]
            # print(type(ops))
            if int(ops) == 0:
                res_log.append("No error found in Error Log \n")
                logging.info("No error found in Error Log \n")
            else:
                res_log.append(f"Size of Error Log file = {ops}")
                logging.info(f"Size of Error Log file = {ops}")

            res_log.append("Following Command Executed: " + cmd + "\n")
            logging.info("Following Command Executed: " + cmd + "\n")

            excep = self.inc + "_" + host + ": Running Query to fetch Backup Job details"
            logging.info(excep)
            res_log.append(excep)
            qry = """select 
SESSION_KEY, INPUT_TYPE, STATUS,
to_char(START_TIME,'mm/dd/yy hh24:mi:ss') start_time,
to_char(END_TIME,'mm/dd/yy hh24:mi:ss')   end_time,
TIME_TAKEN_DISPLAY, INPUT_BYTES_DISPLAY, OUTPUT_BYTES_DISPLAY, INPUT_BYTES_PER_SEC_DISPLAY, OUTPUT_BYTES_PER_SEC_DISPLAY 
from V$RMAN_BACKUP_JOB_DETAILS where INPUT_TYPE='DB INCR' order by session_key"""

            # print(qry)
            self.crsr.execute(qry)
            result = self.crsr.fetchall()[-10:]
            # print(result)
            res_log.append("Full/Incremental Backup Job Details - \n")
            format_row = '{:>12}{:>11}{:>24}{:>18}{:>18}{:>11}{:>17}{:>18}{:13}{:>12}'
            columns = ['SESSION_KEY', 'INPUT_TYPE', 'STATUS', 'start_time', 'end_time', 'TIME_TAKEN',
                       'INPUT_BYTES_DISP', 'OUTPUT_BYTES_DISP', 'INPUT_BYTES', 'OUTPUT_BYTES']
            # format_row = "{:>20}" * (len(columns) + 1)
            res_log.append(format_row.format(*columns))

            for team, row in zip(columns, result):
                res_log.append(format_row.format(*row))

            # print(f"Full/Incremental Backup Job Details - \n{result}")

            return True
        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            res_error.append("Exception in " + stack()[0][3] + " While, " + excep + ", At Line " + str(exc_tb.tb_lineno) + ":- " + str(e))
            logging.info("Exception in " + stack()[0][3] + " While, " + excep + ", At Line " + str(exc_tb.tb_lineno) + ":- " + str(e))
            return False

        finally:
            del excep, size, dwn, result, qry
    #endregion


    #region Archive Backup Logs
    def archBkpLogs(self, db):
        excep = cmd = size = ""
        try:
            # <----- Running Commands to find Archive Backup Logs ----->
            excep = self.inc + "_" + host + ": Running Commands to find Archive Backup Logs"
            logging.info(excep)
            res_log.append(excep)
            cmd = "ls -latr arch*" + db + "* | awk '{print($9)}'"
            self.channel.send(cmd + "\n")
            self.chkCmdEnd(cmd, self.prompt)
            op = self.cmdOp.split("\n")[-5:-1]
            res_log.append("Commands for Archive Backup Logs Executed: " + cmd + "\n" + str(op) + "\n")
            logging.info("Commands for Archive Backup Logs Executed: " + cmd + "\n" + str(op) + "\n")

            excep = self.inc + "_" + host + ": Downloading Archive Backup Log file"
            logging.info(excep)
            res_log.append(excep)
            dwn = False
            dwn = self.fileDownload(db, op, host)
            res_log.append("File downloaded : " + str(dwn) + "\n")
            logging.info("File downloaded : " + str(dwn) + "\n")
            if not dwn:
                res_log.append(self.inc + "_" + host + ": Download for Archive Backup log files failed")
                logging.info(self.inc + "_" + host + ": Download for Archive Backup log files failed")
                # return False,False

            fileNames = op
            fileDateCheck = False
            for file in fileNames:
                datetime_str = file.split(".")[2]
                fileCreatedDate = datetime.datetime.strptime(datetime_str, '%Y%m%d-%H%M%S')
                latestLogDate = datetime.datetime.now() - datetime.timedelta(hours=4, minutes=0)  # printed in default format

                if (fileCreatedDate >= latestLogDate):
                    fileDateCheck = True
                else:
                    fileDateCheck = False
                    break

            excep = self.inc + "_" + host + ": Checking size of Error log file"
            logging.info(excep)
            res_log.append(excep)
            size = "ls -latr arch*" + db + "*.err | awk '{print($5)}'"
            self.channel.send(size + "\n")
            self.chkCmdEnd(size, self.prompt)
            op = self.cmdOp.split("\n")[-2:-1][0]
            errorLogFlag = False
            if int(op) == 0:
                res_log.append("No error found in Error Log \n")
                logging.info("No error found in Error Log \n")
                errorLogFlag = True
            else:
                res_log.append("Size of Error Log file = " + str(op) + "\n")
                logging.info("Size of Error Log file = " + str(op) + "\n")
                errorLogFlag = False
                # return True,False

            res_log.append("Following Command Executed: " + cmd + "\n")
            logging.info("Following Command Executed: " + cmd + "\n")

            excep = self.inc + "_" + host + ": Running Query to fetch Archive Backup Job details"
            logging.info(excep)
            res_log.append(excep)
            qry = """select 
SESSION_KEY, INPUT_TYPE, STATUS,
to_char(START_TIME,'mm/dd/yy hh24:mi:ss') start_time,
to_char(END_TIME,'mm/dd/yy hh24:mi:ss')   end_time,
TIME_TAKEN_DISPLAY, INPUT_BYTES_DISPLAY, OUTPUT_BYTES_DISPLAY, INPUT_BYTES_PER_SEC_DISPLAY, OUTPUT_BYTES_PER_SEC_DISPLAY
from V$RMAN_BACKUP_JOB_DETAILS order by session_key"""

            # print(qry)
            self.crsr.execute(qry)
            result = self.crsr.fetchall()[-10:]
            jobTableFlag = False
            res_log.append("Archive Backup Job Details - \n")
            format_row = '{:>12}{:>11}{:>24}{:>18}{:>18}{:>11}{:>17}{:>18}{:13}{:>12}'
            columns = ['SESSION_KEY', 'INPUT_TYPE', 'STATUS', 'start_time', 'end_time', 'TIME_TAKEN',
                       'INPUT_BYTES_DISP', 'OUTPUT_BYTES_DISP', 'INPUT_BYTES', 'OUTPUT_BYTES']
            # format_row = "{:>20}" * (len(columns) + 1)
            res_log.append(format_row.format(*columns))

            for team, row in zip(columns, result):
                res_log.append(format_row.format(*row))

            # print(f"Archive Backup Job Details - \n{result}")
            for row in reversed(result):
                if (row[1].upper() == "ARCHIVELOG"):
                    datetime_str = row[3]
                    jobExecutionDate = datetime.datetime.strptime(datetime_str, '%m/%d/%y %H:%M:%S')
                    latestLogDate = datetime.datetime.now() - datetime.timedelta(hours=4, minutes=0)

                    if (jobExecutionDate >= latestLogDate) and (
                            row[2].upper() == "COMPLETED WITH WARNINGS" or row[2].upper() == "COMPLETED"):
                        jobTableFlag = True
                    else:
                        jobTableFlag = False

                    break

            if dwn == False and errorLogFlag == False and jobTableFlag == False and fileDateCheck == False:
                return False, False
            elif dwn == True and errorLogFlag == True and jobTableFlag == True and fileDateCheck == True:
                return True, True

            return True, False
        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            res_error.append("Exception in " + stack()[0][3] + " While, " + excep + ", At Line " + str(exc_tb.tb_lineno) + ":- " + str(e))
            logging.info("Exception in " + stack()[0][3] + " While, " + excep + ", At Line " + str(exc_tb.tb_lineno) + ":- " + str(e))
            return False, False

        finally:
            del excep, cmd, size
    #endregion


    #region Data Guard Sync GAP logs that checks the gap between Primary and Standby Database
    def dgGapLogs(self, db):
        excep = standbyDB = buf = res = dwn = ""
        try:
            excep = self.inc + "_" + host + ": Running Commands to find Data Guard Gap logs"
            logging.info(excep)
            res_log.append(excep)
            cmd = "ls -latr *gap*" + db + "* | awk '{print($9)}'"
            self.channel.send(cmd + "\n")
            self.chkCmdEnd(cmd, self.prompt)
            op = self.cmdOp.split("\n")[-2:-1]
            res_log.append("Command for Data Guard Gap Log Executed: " + cmd + "\n" + str(op) + "\n")
            logging.info("Command for Data Guard Gap Log Executed: " + cmd + "\n" + str(op) + "\n")

            excep = self.inc + "_" + host + ": Downloading GAP log file"
            logging.info(excep)
            res_log.append(excep)
            dwn = False
            dwn = self.fileDownload(db, op, host)
            res_log.append("File downloaded : " + str(dwn) + "\n")
            logging.info("File downloaded : " + str(dwn) + "\n")
            if not dwn:
                res_log.append(self.inc + "_" + host + ": Download for GAP log file failed")
                logging.info(self.inc + "_" + host + ": Download for GAP log file failed")
                return False

            excep = self.inc + "_" + host + ": changing to ora admin path \n"
            logging.info(excep)
            res_log.append(excep)
            cmd = db
            self.channel.send(cmd + "\n")
            time.sleep(2)
            buf = ""
            res = self.channel.recv(65535)
            try:
                buf = res.decode('ascii')
            except Exception as e1:
                buf = str(res, 'utf-8')

            self.prompt = buf.split("\n")[-1]
            # print("Moving to DGMGRL path -" + self.prompt)
            prmt = self.prompt

            excep = self.inc + "_" + host + ": Moving to DGMGRL path to check gap lag: \n"
            logging.info(excep)
            res_log.append(excep)
            cmd = "dgmgrl"
            self.channel.send(cmd + "\n")
            time.sleep(2)
            buf = ""
            res = self.channel.recv(65535)
            try:
                buf = res.decode('ascii')
            except Exception as e1:
                buf = str(res, 'utf-8')

            # op = self.cmdOp.split("\n")[1:-1]
            self.prompt = buf.split("\n")[-1]
            # print("Moved to DGMGRL path")
            logging.info("Moved to DGMGRL path \n")
            res_log.append("Moved to DGMGRL path \n")

            excep = self.inc + "_" + host + ": Connecting to SYSDG to check DG GAP detail"
            logging.info(excep)
            res_log.append(excep)
            cmd = "connect sys/" + self.decrypt()
            self.channel.send(cmd + "\n")
            self.chkCmdEnd(cmd, self.prompt)

            excep = self.inc + "_" + host + ": Checking Dataguard gap details- \n"
            logging.info(excep)
            res_log.append(excep)
            cmd = "show configuration"
            self.channel.send(cmd + "\n")
            self.chkCmdEnd(cmd, self.prompt)
            op = self.cmdOp.split("\n")[1:-1]
            res_log.append("Dataguard gap details- " + cmd + "\n" + self.cmdOp + "\n")
            logging.info("Dataguard gap details- " + cmd + "\n" + self.cmdOp + "\n")

            line = [x for x in op if "standby" in x.lower()]

            if len(line) > 0:
                standbyDB = (line[0].split("-")[0]).strip()
                res_log.append(standbyDB)
            else:
                res_log.append(host + ": Standby DB Not Found \n")
                logging.info(host + ": Standby DB Not Found \n")

            excep = self.inc + "_" + host + ": Checking Dataguard gap details- \n"
            logging.info(excep)
            res_log.append(excep)
            cmd = "show database " + standbyDB
            self.channel.send(cmd + "\n")
            self.chkCmdEnd(cmd, self.prompt)
            op = self.cmdOp.split("\n")[1:-1]

            res_log.append("Dataguard gap details for : " + cmd + "\n" + self.cmdOp + "\n\n")
            logging.info("Dataguard gap details for : " + cmd + "\n" + self.cmdOp + "\n\n")

            TransportLag = [x for x in op if "transport lag:" in x.lower()]
            ApplyLag = [x for x in op if "apply lag:" in x.lower()]
            if ((len(TransportLag) > 0) and (len(ApplyLag) > 0)):
                TransportLagValue = re.search("Transport Lag: (.+?)second", TransportLag[0]).group(1).strip()
                ApplyLagValue = re.search("Apply Lag:  (.+?)second", ApplyLag[0]).group(1).strip()
                difference = int(TransportLagValue) - int(ApplyLagValue)
                if difference == 0:
                    res_log.append("No GAP found. \n")
                    logging.info("No GAP found. \n")
                else:
                    res_log.append(host + ": GAP exist - " + str(difference))
                    logging.info(host + ": GAP exist - " + str(difference))
                    return True, False

            excep = self.inc + "_" + host + ": Moving out of DGMGRL path"
            logging.info(excep)
            res_log.append(excep)
            cmd = "exit"
            self.channel.send(cmd + "\n")
            self.prompt = prmt
            # print(self.prompt)
            self.chkCmdEnd(cmd, self.prompt)
            # print("Moving out from DGMGRL - " + self.cmdOp)
            # print("Moved out from DGMGRL path")
            logging.info("Moved out from DGMGRL path \n")
            res_log.append("Moved out from DGMGRL path \n")

            return True, True
        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            res_error.append("Exception in " + stack()[0][3] + " While, " + excep + ", At Line " + str(exc_tb.tb_lineno) + ":- " + str(e))
            logging.info("Exception in " + stack()[0][3] + " While, " + excep + ", At Line " + str(exc_tb.tb_lineno) + ":- " + str(e))
            return False

        finally:
            del excep, cmd, dwn, standbyDB, buf, res
    #endregion


    #region FRA Logs  storage location for backup and recovery files
    def fraLogs(self, db, host):
        excep = cmd = dwn = ""
        try:
            excep = self.inc + "_" + host + ": Running Commands to find FRA Backup Logs"
            logging.info(excep)
            res_log.append(excep)
            cmd = "ls -latr *FRA*" + db + "* | awk '{print($9)}'"
            self.channel.send(cmd + "\n")
            self.chkCmdEnd(cmd, self.prompt)
            op = self.cmdOp.split("\n")[-2:-1]
            res_log.append("The extracted files are : \n" + str(op) + "\n")
            logging.info("The extracted files are : \n" + str(op) + "\n")

            excep = self.inc + "_" + host + ": Downloading FRA Log file"
            logging.info(excep)
            res_log.append(excep)
            dwn = False
            dwn = self.fileDownload(db, op, host)
            res_log.append("File downloaded : " + str(dwn) + "\n")
            logging.info("File downloaded : " + str(dwn) + "\n")
            if not dwn:
                res_log.append(self.inc + "_" + host + ": Download for FRA log file failed")
                logging.info(self.inc + "_" + host + ": Download for FRA log file failed")
                return False

            return True
        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            res_error.append("Exception in " + stack()[0][3] + " While, " + excep + ", At Line " + str(exc_tb.tb_lineno) + ":- " + str(e))
            logging.info("Exception in " + stack()[0][3] + " While, " + excep + ", At Line " + str(exc_tb.tb_lineno) + ":- " + str(e))
            return False

        finally:
            del excep, cmd, dwn
    #endregion


    #region FRA space details
    def fraSpace(self, pService, sService, pDbHost, sDbHost, pfra=False):
        excep = qry = result = ""
        try:
            if pfra:
                self.closeDB(sDbHost)

                excep = pDbHost + "_" + pService.split(".")[0] + ": Calling connDB function"
                logging.info(excep)
                res_log.append(excep)
                # print(excep)
                dbStat = False
                dbStat = self.connDB(dbUsr, dbPwd, pDbHost, port, pService)
                if not dbStat:
                    msg = pDbHost + "_" + pService.split(".")[0] + ": Primary DB Connection failed."
                    res_log.append(msg)
                    logging.info(msg)
                    self.terminateConn(pDbHost)
                    return False

            excep = self.inc + "_" + sDbHost + ": Running Query to fetch FRA space details"  # sDbHost
            logging.info(excep)
            res_log.append(excep)
            qry = """select NAME,
floor(space_limit/1024/1024/1024) "Size_GB", ceil(space_used/1024/1024/1024) "Used_GB",
floor(space_limit/1024/1024/1024) - ceil(space_used/1024/1024/1024) "Available_GB",
round(ceil(space_used/1024/1024/1024) / floor(space_limit/1024/1024/1024) * 100)  || '%' "Percent Used"
from v$recovery_file_dest order by 1"""

            self.crsr.execute(qry)
            result = self.crsr.fetchall()[0]
            res_log.append("Standby FRA space details-\n")
            res_log.append(f"Name: {result[0]}, Size(GB): {result[1]}, Used(GB): {result[2]} , Available(GB): {result[3]}, %_Used: {result[4]} \n")
            logging.info(f"Name: {result[0]}, Size(GB): {result[1]}, Used(GB): {result[2]} , Available(GB): {result[3]}, %_Used: {result[4]} \n")

            if result[4].replace("%", "") < "70":
                res_log.append("FRA is within threshold \n")
                logging.info("FRA is within threshold \n")
            else:
                res_log.append("FRA has crossed the threshold \n")
                logging.info("FRA has crossed the threshold \n")
                return True, False

            return True, True
        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            res_error.append("Exception in " + stack()[0][3] + " While, " + excep + ", At Line " + str(exc_tb.tb_lineno) + ":- " + str(e))
            logging.info("Exception in " + stack()[0][3] + " While, " + excep + ", At Line " + str(exc_tb.tb_lineno) + ":- " + str(e))
            return False

        finally:
            # self.closeDB(pDbHost)
            del excep, result, qry
    #endregion


    #region Primary Archive Log Cleanup
    def plcLogs(self, db):
        excep = cmd = dwn = ""
        try:
            excep = self.inc + "_" + host + ": Running Commands to find PLC Backup Logs"
            logging.info(excep)
            res_log.append(excep)
            cmd = "ls -latr *delobsarch*" + db + "* | awk '{print($9)}'"
            self.channel.send(cmd + "\n")
            self.chkCmdEnd(cmd, self.prompt)
            op = self.cmdOp.split("\n")[-5:-1]
            res_log.append("Commands for PLC Backup Logs Executed: " + cmd + "\n" + str(op) + "\n")
            logging.info("Commands for PLC Backup Logs Executed: " + cmd + "\n" + str(op) + "\n")

            excep = self.inc + "_" + host + ": Downloading PLC log file"
            logging.info(excep)
            res_log.append(excep)
            dwn = False
            dwn = self.fileDownload(db, op, host)
            res_log.append("File downloaded : " + str(dwn) + "\n")
            logging.info("File downloaded : " + str(dwn) + "\n")
            if not dwn:
                res_log.append(self.inc + "_" + host + ": Download for PLC failed")
                logging.info(self.inc + "_" + host + ": Download for PLC failed")
                return False

            fileNames = op
            fileDateCheck = False
            for file in fileNames:
                datetime_str = file.split(".")[2]
                fileCreatedDate = datetime.datetime.strptime(datetime_str, '%Y%m%d-%H%M%S')
                latestLogDate = datetime.datetime.now() - datetime.timedelta(hours=4, minutes=0)  # printed in default format

                if (fileCreatedDate >= latestLogDate):
                    fileDateCheck = True
                else:
                    fileDateCheck = False
                    break

            if fileDateCheck:
                return True, True

            return True, False
        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            res_error.append("Exception in " + stack()[0][3] + " While, " + excep + ", At Line " + str(exc_tb.tb_lineno) + ":- " + str(e))
            logging.info("Exception in " + stack()[0][3] + " While, " + excep + ", At Line " + str(exc_tb.tb_lineno) + ":- " + str(e))
            return False

        finally:
            del excep, cmd, dwn
    #endregion


    #region Performs all Control-M Alerts tasks
    def controlM(self, user, pwd, oraUsr, keyFile, keyPwd, dbUsr, dbPwd, port, service, pHost, sHost, job, sDbHost, pDbHost, dbName):
        excep = host = cmd = sService = pService = ""
        try:
            db = service.split(".")[0]

            host = sHost
            if job.upper() == "LC" or job.upper() == "PFRA":
                host = pHost

            # <----- Requesting SSH connection ----->
            excep = host + ": Requesting SSH connection"
            res_log.append(excep)
            logging.info(excep)
            stat = False
            stat = self.getConn(host, user, pwd, keyFile, keyPwd, oraUsr)
            if not stat:
                msg = host + "_" + db + ": SSH Connection failed."
                res_log.append(msg)
                logging.info(msg)
                return False

            excep = host + ": Checking if Instance exists in required node"
            logging.info(excep)
            res_log.append(excep)
            cmd = "ps -ef | grep pmon | grep -i " + dbName + " | awk '{print($8)}' | cut -d'_' -f3"
            self.channel.send(cmd + "\n")
            self.chkCmdEnd(cmd, self.prompt)
            op = "\n".join(self.cmdOp.split("\n")[1:-1]).strip()[:-1]
            # print(dbName, "-", self.cmdOp, "\n", op)
            sDBname = dbName + "a"
            if dbName.lower() != op.lower() and sDBname.lower() != op.lower():
                res_log.append(dbName + ": not found in node db01. Checking in node db03.\n")
                self.terminateConn(host)

                host = host.replace("db01", "db03")

                excep = host + "_" + db + ": Re-requesting SSH connection"
                res_log.append(excep)
                logging.info(excep)
                stat = False
                stat = self.getConn(host, user, pwd, keyFile, keyPwd, oraUsr)
                if not stat:
                    msg = host + "_" + db + ": SSH Connection failed."
                    res_log.append(msg)
                    logging.info(msg)
                    return False

            sService = service + "_standby.ntrs.com"

            excep = host + "_" + db + ": Setting DB Environment To Fetch DB Version"
            logging.info(excep)
            res_log.append(excep)

            self.channel.send(op + "\n")
            time.sleep(1)
            buf = ""
            res = self.channel.recv(65535)
            try:
                buf = res.decode('ascii')
            except Exception as e1:
                buf = str(res, 'utf-8')

            if "not found" in buf.lower():
                res_log.append(host + "_" + db + ": DB Environment Setting Failed While Fetching DB Version. O/P- " + buf)
                logging.info(host + "_" + db + ": DB Environment Setting Failed While Fetching DB Version. O/P- " + buf)
                self.terminateConn(host)
                return False

            self.prompt = buf.split("\n")[-1]
            res_log.append(host + "_" + db + ": New Prompt Post DB Env Set- " + self.prompt)
            logging.info(host + "_" + db + ": New Prompt Post DB Env Set- " + self.prompt)

            excep = host + "_" + db + ": Checking Version of Oracle"
            logging.info(excep)
            res_log.append(excep)
            cmd = "sqlplus"
            self.channel.send(cmd + "\n")
            time.sleep(2)
            buf = ""
            res = self.channel.recv(65535)
            try:
                buf = res.decode('ascii')
            except Exception as e1:
                buf = str(res, 'utf-8')

            if "Enter user-name: " in buf:
                self.channel.send("\x03\n")
                time.sleep(2)
                self.channel.send("\n")
                time.sleep(1)
                self.chkCmdEnd("Ctrl+C", self.prompt)
                op = buf.replace("\r", "").split("\n")[1:-1]
                res_log.append("\nOracle Version - \n" + "".join(op))
                logging.info("\nOracle Version - \n" + "".join(op))

                if "release 19" in str(op).lower():
                    pService = service + "_primary.ntrs.com"
                elif "release 12" in str(op).lower():
                    pService = service + ".ntrs.com"
                else:
                    res_log.append("Version is neither 12c nor 19c")
                    logging.info("Version is neither 12c nor 19c")
            else:
                res_log.append("Version could not be fetched")
                logging.info("Version could not be fetched")
                self.terminateConn(host)
                return False

            # print("Standby Service Name - " + sService + "; Primary Service Name - " + pService)
            logging.info("Standby Service Name - " + sService + "; Primary Service Name - " + pService)
            res_log.append("Standby Service Name - " + sService + "; Primary Service Name - " + pService)

            # <----- Fetching DB Password ----->
            excep = host + "_" + db + ": Fetching DB Password"
            logging.info(excep)
            res_log.append(excep)
            cmd = ""
            if host.upper().startswith("UT") or host.upper().startswith("XDT"):
                cmd = "cat " + self.qaPwd
            else:
                cmd = "cat " + self.prodPwd
            self.channel.send(cmd + "\n")
            self.chkCmdEnd(cmd, self.prompt)

            try:
                #print("pswd-", self.cmdOp.split("\n")[1].rstrip())
                stat = self.encrypt(self.cmdOp.split("\n")[1].strip())
                # print(host + "_" + db + ": DB Password Fetched & Encrypted")
                logging.info(host + "_" + db + ": DB Password Fetched & Encrypted")
                res_log.append(host + "_" + db + ": DB Password Fetched & Encrypted")
            except Exception as e1:
                msg = host + "_" + db + ": DB Password Fetching Failed. " + str(e1)
                res_error.append(msg)
                logging.info(msg)

            if self.dbPwd == b'':
                msg = host + "_" + db + """: Blank DB Password Received After Encryption.
        Control-M Alerts Solutions Check failed.
        """
                res_log.append(msg)
                logging.info(msg)
                self.terminateConn(host)
                return False

            '''
            # <----- Calling connDB function ----->
            excep = dbHost + "_" + db + ": Calling connDB function"
            logging.info(excep)
            # print(excep)
            dbStat = False
            dbStat = self.connDB(dbUsr, dbPwd, dbHost, port, service)
            if not dbStat:
                msg = dbHost + "_" + db + ": DB Connection failed."
                print(msg)
                logging.info(msg)
                self.terminateConn(host)
                return False
            '''

            # <----- Commands to find Control-M Alert Logs ----->
            excep = "Moving to Backup Logfile path \n"
            logging.info(excep)
            res_log.append(excep)
            cmd = "cd /u01/app/oracle/local/log/" + db
            self.channel.send(cmd + "\n")
            time.sleep(2)
            buf = ""
            res = self.channel.recv(65535)
            try:
                buf = res.decode('ascii')
            except Exception as e1:
                buf = str(res, 'utf-8')

            # op = self.cmdOp.split("\n")[1:-1]
            self.prompt = buf.split("\n")[-1]
            # print("Moved to Backup Logfile path" + self.prompt)
            logging.info("Moved to Backup Logfile path" + self.prompt)
            res_log.append("Moved to Backup Logfile path" + self.prompt)

            excep = self.inc + host + ": Running Commands to find Control-M Alert Logs :\n"
            logging.info(excep)
            res_log.append(excep)

            #region <----- 1. Running Commands to find Full Backup & Incremental Backup Logs ----->
            cmd = size = ""
            if job.upper() == "B":
                cmd = "ls -latr level0*" + db + "* | awk '{print($9)}'"
                size = "ls -latr level0*" + db + "*.err | awk '{print($5)}'"
            if job.upper() == "I":
                cmd = "ls -latr level1*" + db + "* | awk '{print($9)}'"
                size = "ls -latr level1*" + db + "*.err | awk '{print($5)}'"

            excep = sDbHost + "_" + sService.split(".")[0] + ": Calling connDB function"
            logging.info(excep)
            res_log.append(excep)
            # print(excep)
            dbStat = False
            dbStat = self.connDB(dbUsr, dbPwd, sDbHost, port, sService)
            if not dbStat:
                msg = sDbHost + "_" + sService.split(".")[0] + ": Standby DB Connection failed."
                res_log.append(msg)
                logging.info(msg)
                self.terminateConn(sDbHost)
                return False

            if job.upper() == "B" or job.upper() == "I":
                excep = "Calling Full and Incremental Backup function"
                stat = False
                stat = self.fullandIncrBkpLogs(db, cmd, size, host)
                if not stat:
                    res_log.append(self.inc + "_" + host + ": Full and Incremental Backup execution failed")
                    logging.info(self.inc + "_" + host + ": Full and Incremental Backup execution failed")
                    return False
            #endregion

            #region <----- 2. Running Commands to find Archive Backup Logs ----->
            elif job.upper() == "L" or job.upper() == "L1":
                excep = "Calling Archive Backup function"
                stat = archBkpCheck = False
                stat, archBkpCheck = self.archBkpLogs(db)
                if not stat:
                    res_log.append(self.inc + "_" + host + ": Archive Backup execution failed")
                    logging.info(self.inc + "_" + host + ": Archive Backup execution failed")
                    return False

                res_log.append("Checking FRA space details for Archive Log Backup")
                logging.info("Checking FRA space details for Archive Log Backup")
                excep = "Calling FRA space detail function"
                stat = False
                stat = self.fraSpace(pService, sService, pDbHost, sDbHost)
                if not stat:
                    res_log.append(self.inc + "_" + host + ": Archive Backup execution failed")
                    logging.info(self.inc + "_" + host + ": Archive Backup execution failed")
                    return False

                if archBkpCheck:
                    res_log.append("Archive Backup log details executed successfully")
            #endregion

            #region <----- 3. Running Commands to find Data Guard Sync GAP logs ----->
            elif job.upper() == "GAP":
                excep = "Calling DG Gap Log function"
                stat = dggapCheck = False
                stat, dggapCheck = self.dgGapLogs(db)
                if not stat:
                    res_log.append(self.inc + "_" + host + ": DG Gap Log execution failed")
                    logging.info(self.inc + "_" + host + ": DG Gap Log execution failed")
                    return False

                if dggapCheck:
                    res_log.append("DG Gap log details executed successfully")
            #endregion

            #region <----- 4. Running Commands to find FRA logs ----->
            elif job.upper() == "PFRA" or job.upper() == "SFRA":
                excep = "Calling FRA logs function"
                stat = False
                stat = self.fraLogs(db, host)
                if not stat:
                    res_log.append(self.inc + "_" + host + ": FRA logs failed to execute")
                    logging.info(self.inc + "_" + host + ": FRA logs failed to execute")
                    return False

                if job.upper() == "SFRA":
                    res_log.append("Checking FRA space details")
                    logging.info("Checking FRA space details")
                    excep = "Calling FRA space detail function"
                    stat = False
                    fraSpaceCheck = False
                    stat, fraSpaceCheck = self.fraSpace(pService, sService, pDbHost, sDbHost)
                    if not stat:
                        res_log.append(self.inc + "_" + host + ": FRA space details execution failed")
                        logging.info(self.inc + "_" + host + ": FRA space details execution failed")
                        return False

                    res_log.append("Checking if Archive running successfully or not")
                    logging.info("Checking if Archive running successfully or not")
                    excep = "Calling Archive Backup function"
                    stat = False
                    archBkpCheck = False
                    stat, archBkpCheck = self.archBkpLogs(db)
                    if not stat:
                        res_log.append(self.inc + "_" + host + ": Archive Backup execution failed")
                        logging.info(self.inc + "_" + host + ": Archive Backup execution failed")
                        return False

                    if fraSpaceCheck and archBkpCheck:
                        res_log.append("FRA log details executed successfully")

                # print(host)
                if job.upper() == "PFRA":
                    res_log.append("Checking FRA space details")
                    logging.info("Checking FRA space details")
                    excep = "Calling FRA space detail function"
                    stat = False
                    fraSpaceCheck = False
                    stat, fraSpaceCheck = self.fraSpace(pService, sService, pDbHost, sDbHost, True)
                    if not stat:
                        res_log.append(self.inc + "_" + host + ": FRA space details execution failed")
                        logging.info(self.inc + "_" + host + ": FRA space details execution failed")
                        return False

                    res_log.append("Checking if PLC running successfully or not")
                    logging.info("Checking if PLC running successfully or not")
                    excep = "Calling Primary Archive Log Cleanup function"
                    stat = plcCheck = False
                    stat, plcCheck = self.plcLogs(db)
                    if not stat:
                        res_log.append(self.inc + "_" + host + ": PLC logs failed to execute")
                        logging.info(self.inc + "_" + host + ": PLC logs failed to execute")
                        return False

                    if fraSpaceCheck and plcCheck:
                        res_log.append("FRA log details executed successfully")
            #endregion

            #region <----- 5. Running Commands for Primary Archive Log Cleanup ----->
            elif job.upper() == "LC":
                excep = "Calling Primary Archive Log Cleanup function"
                stat = plcCheck = False
                stat, plcCheck = self.plcLogs(db)
                if not stat:
                    res_log.append(self.inc + "_" + host + ": PLC logs failed to execute")
                    logging.info(self.inc + "_" + host + ": PLC logs failed to execute")
                    return False

                res_log.append("Checking FRA space details")
                logging.info("Checking FRA space details")
                excep = "Calling FRA space detail function"
                stat = fraSpaceCheck = False
                stat, fraSpaceCheck = self.fraSpace(pService, sService, pDbHost, sDbHost, True)
                if not stat:
                    res_log.append(self.inc + "_" + host + ": FRA space details execution failed")
                    logging.info(self.inc + "_" + host + ": FRA space details execution failed")
                    return False

                if fraSpaceCheck and plcCheck:
                    res_log.append("PLC log details executed successfully")
            #endregion

            else:
                res_log.append("Incorrect Job Name \n")
                logging.info("Incorrect Job Name \n")
                return False

            return True
        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            res_error.append("Exception in " + stack()[0][3] + " While, " + excep + ", At Line " + str(exc_tb.tb_lineno) + ":- " + str(e))
            logging.info("Exception in " + stack()[0][3] + " While, " + excep + ", At Line " + str(exc_tb.tb_lineno) + ":- " + str(e))
            return False

        finally:
            self.terminateConn(host)
            self.closeDB(sDbHost)
            del excep, cmd
    #endregion



cm = ControlMAlerts()
pDbHost = ""
sDbHost = ""
host = ""
excep = ""

try:
    excep = "Reading Inputs"
    dbUsr = "sys"
    dbPwd = ""  # str(cm.encrypt(getpass.getpass("Enter The DB Login Password:- ")))
    port = "1521"
    #user = module.params['user']
    user = sys.argv[1]
    #pwd = module.params['pwd']
    pwd = sys.argv[2]
    #pwd = ""  # str(cm.encrypt(getpass.getpass("Enter The Login Password:- ")))
    keyFile = ""
    keyPwd = ""
    oraUser = "oracle"
    #ticketNo = module.params['ticketNo']
    ticketNo = sys.argv[3]
    #jobName = module.params['jobName']
    jobName = sys.argv[4]
    job = jobName[11:]
    dbName = jobName[4:11]
    service = dbName.lower()
    

    if True:
        excep = "Validating Input Parameters"
        inpChk = False
        inputs = [(user, pwd, oraUser, dbUsr, port, service, jobName),
                  ("Server Login Username", "Server Login Password", "Oracle Username", "DB Login Username", "DB Port", "DB Service Name", "Job Name")]

        for i in range(0, len(inputs[0])):
            if inputs[0][i] == "":
                res_log.append("No Input Given For " + inputs[1][i])
                logging.info("No Input Given For " + inputs[1][i])
                chkInp = True

        if inpChk == True:
            res_log.append("Input Validation Failed. Terminating The Program")
            logging.info("Input Validation Failed. Terminating The Program")
            del cm
            sys.exit(0)
    
    excep = "Fetching Hostname For DB Service: " + service
    cmd = "nslookup " + service
    val = subprocess.check_output(cmd, shell=True)  # subprocess is used to run any application(eg.- cmd) in local system
    data = ""
    try:
        data = val.decode("ascii")
    except Exception:
        data = str(val, 'utf-8')

    if "can't find" in data.lower() or "non-existent domain" in data:
        # print("Hostname not found for Impacted DB. Nslookup Failed For Service Name: " + service)
        logging.info("Hostname not found for Impacted DB. Nslookup Failed For Service Name: " + service)
        res_log.append("Hostname not found for Impacted DB. Nslookup Failed For Service Name: " + service)
        del cm
        sys.exit(0)

    dataSet = data.split("\n")
    for i in range(0, len(dataSet)):
        line = dataSet[i].strip()
        if "NAME:" in line.upper():
            pDbHost = line.split(":")[1].replace(" ", "").strip()
            host = pDbHost  #.strip()
            logging.info("host is " + host)
            res_log.append("host is " + host)
            # print("Impacted db server name:- " + host)
            logging.info("Impacted db server name:- " + host)
            res_log.append("Impacted db server name:- " + host)
            break

    if pDbHost == "":
        res_log.append("HostName Not Found Via NSLOOKUP. NSLOOKUP O/P:- " + "\n".join(dataSet[1:-1]))
        logging.info("HostName Not Found Via NSLOOKUP. NSLOOKUP O/P:- " + "\n".join(dataSet[1:-1]))
        del cm
        sys.exit(0)

    if pDbHost[3] == "8":
        sDbHost = pDbHost[:3] + "5" + pDbHost[4:]
    else:
        sDbHost = pDbHost[:3] + "8" + pDbHost[4:]

    standbyHost = ""
    primaryHost = host
    if "-" in host:
        primaryHost = host.split("-")[0] + "db01.ntrs.com"
        if primaryHost[3] == '5':
            standbyHost = primaryHost[:3] + '8' + primaryHost[4:]
            res_log.append("Host changed to - " + standbyHost + "\n")
            logging.info("Host changed to - " + standbyHost + "\n")
        elif primaryHost[3] == '8':
            standbyHost = primaryHost[:3] + '5' + primaryHost[4:]
            res_log.append("Host changed to - " + standbyHost + "\n")
            logging.info("Host changed to - " + standbyHost + "\n")

    stat = False
    excep = "Calling Control-M Alerts Check Function"
    stat = cm.controlM(user, pwd, oraUser, keyFile, keyPwd, dbUsr, dbPwd, port, service, primaryHost, standbyHost, job, sDbHost, pDbHost, dbName)
    if not stat:
        res_log.append("Control-M Alerts Check Failed For " + host + "_" + service.split(".")[0])
        logging.info("Control-M Alerts Check Failed For " + host + "_" + service.split(".")[0])
    else:
        res_log.append("Control-M Alerts Check Successful For " + host + "_" + service.split(".")[0])
        logging.info("Control-M Alerts Check Successful For " + host + "_" + service.split(".")[0])


except Exception as e:
    exc_type, exc_obj, exc_tb = sys.exc_info()
    res_error.append("Exception in " + stack()[0][3] + " While, " + excep + ", At Line " + str(exc_tb.tb_lineno) + ":- " + str(e))
    logging.info(
        "Exception in " + stack()[0][3] + " While, " + excep + ", At Line " + str(exc_tb.tb_lineno) + ":- " + str(e))


finally:
    result["log"] = res_log
    result["error"] = res_error
    logging.info("\n\n----------------------------- Session Finished --------------------------------\n\n")
    del cm
    output =result
    print(json.dumps(result))
  #  module.exit_json(changed=True, output=result)

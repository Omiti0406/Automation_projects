#!powershell
#Requires -Module Ansible.ModuleUtils.Legacy

$resultobj = @{
    Changed = $false
    output = ""
    err = ""
}


$params = Parse-Args $args -supports_check_mode $true
$username = Get-AnsibleParam -obj $params -name "username" -type "str" -failifempty $true
$password = Get-AnsibleParam -obj $params -name "password"  -type "str" -failifempty $true
$HostName = Get-AnsibleParam -obj $params -name  "server" -type "str" -failifempty $true
$TicketNo = Get-AnsibleParam -obj $params -name  "ticket" -type "str" -failifempty $true
$ToAddress = Get-AnsibleParam -obj $params -name  "to" -type "str" -failifempty $false
$pass = ConvertTo-SecureString $password  -AsPlainText -Force
$cred = New-Object System.Management.Automation.PSCredential ($username, $pass)
$mastervar = ""

[String]$SMTPServer = "appmail.ntrs.com"
[String]$SMTPPort= "25"
[String]$FromAddress = "NoReply@ntrs.com"
[String]$CCAddress = "GDP_OPS_MSSQL@ntrs.com"

try{
$var =""
$var+="<html><head><title>Blocking Sessions Report</title><style>"
$var+="
    body{
    margin=0px;
    padding=0px;
    font-family:'trebuchet ms', arial, helvetica, sans-serif;
    }

    #fragmentation
    {
    font-family:'trebuchet ms', arial, helvetica, sans-serif;
    width:100%;
    border-collapse:collapse;
    }
    #fragmentation td, #fragmentation th 
    {
    font-size:1em;
    border:1px solid #0080ff;
    padding:3px 7px 2px 7px;
    }
    #fragmentation th 
    {
    font-size:1.1em;
    text-align:left;
    padding-top:5px;
    padding-bottom:4px;
    background-color:#a9d0f5;
    color:#000000;
    }
    #fragmentation tr.alt td 
    {
    color:#000000;
    background-color:#eaf2d3;
    }
    </style>
    ";
$var+="</head><body><center>";

$timestamp = Get-Date -UFormat %D%T | foreach {$_ -replace ":", ""} | foreach {$_ -replace " ", ""} | foreach {$_ -replace "/", ""}
$ReportPath="C:\Windows\Temp\BlockingSessionsReport_$timestamp.htm"

$starttime = Get-Date
$outputstring=""


$flag = "0";
$res1 = $res = "";
$var+="<h2>Blocking Sessions Report</h2>";
$var+="<table id='fragmentation'><tr>
<th>Server</th>
<th>Header&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;</th>
<th>WaitingUserSessionLogin</th>
<th>LastBatch</th>
<th>WaitType</th>
<th>WaitingHost</th>
<th>WaitingSessionProgramName</th>
<th>WaitResourceDatabaseName</th>
<th>BATCH</th>
</tr>";


$serv = $HostName
$connectionDetails = New-Object System.Data.SqlClient.SqlConnection;
$connectionDetails.ConnectionString = "Data Source=$serv;Initial Catalog=master;Integrated Security=true;";
$dbs = new-object "System.Data.DataTable"
$dbs2 = new-object "System.Data.DataTable"

$Query1 = "
SELECT session_id,start_time,blocking_session_id 
FROM sys.dm_exec_requests 
WHERE blocking_session_id <> 0; 
"
if($connectionDetails.State -eq 'OPEN')
{
    $connectionDetails.Close();
}
$connectionDetails.open()

        $Command = $connectionDetails.CreateCommand()
        $Command.commandtext = $Query1
        $result = $Command.ExecuteReader()
        $dbs.Load($result); 
        if($dbs.rows.count -eq 0)
        {
            $var+="<tr>
            <td>$serv</td>
            <td colspan=8>No Record Found</td>            
            </tr>";
            $flag = "0";
	    $mastervar += "Blocking has not found on the alert triggered server,hence Automation will recheck after 15 minutes"
        }
          else
        {

               
                <#-----------------Create View----------------------#>
                if($connectionDetails.State -eq 'OPEN')
                {
                    $connectionDetails.Close();
                }
                $connectionDetails.open()
                                $sql2="IF OBJECT_ID('tempdb..##Blocks') IS NOT NULL
                    DROP TABLE ##Blocks
                SELECT   spid
                        ,blocked
                        ,REPLACE (REPLACE (st.TEXT, CHAR(10), ' '), CHAR (13), ' ' ) AS batch
                INTO     ##Blocks
                FROM     sys.sysprocesses spr
                CROSS APPLY sys.dm_exec_sql_text(spr.SQL_HANDLE) st"
                $SqlCmd2 = New-Object System.Data.SqlClient.SqlCommand $sql2, $connectionDetails; 
                [void]$SqlCmd2.ExecuteNonQuery()
            
                <#-----------------Fetch Details----------------------#>
                $Query2 = "WITH BlockingTree (spid, blocking_spid, [level], batch)
                    AS
                    (
                        SELECT   blc.spid
                                ,blc.blocked
                                ,CAST (REPLICATE ('0', 4-LEN (CAST (blc.spid AS VARCHAR))) + CAST (blc.spid AS VARCHAR) AS VARCHAR (1000)) AS [level]
                                ,blc.batch
                        FROM    ##Blocks blc
                        WHERE   (blc.blocked = 0 OR blc.blocked = SPID)
                        AND     EXISTS (SELECT * FROM ##Blocks blc2 WHERE blc2.BLOCKED = blc.SPID AND blc2.BLOCKED <> blc2.SPID)
                        UNION ALL
                        SELECT   blc.spid
                                ,blc.blocked
                                ,CAST(bt.[level] + RIGHT (CAST ((1000 + blc.SPID) AS VARCHAR (100)), 4) AS VARCHAR (1000)) AS [level]
                                ,blc.batch
                        FROM     ##Blocks AS blc
                        INNER JOIN BlockingTree bt ON blc.blocked = bt.SPID
                        WHERE   blc.blocked > 0
                        AND     blc.blocked <> blc.SPID
                    )
                    SELECT N'' + ISNULL(REPLICATE (N'|         ', LEN (LEVEL)/4 - 2),'')
                            + CASE WHEN (LEN(LEVEL)/4 - 1) = 0 THEN '' ELSE '|------  ' END
                            + CAST (bt.SPID AS NVARCHAR (10)) AS BlockingTree
                            ,spr.lastwaittype   AS [Type]
                            ,spr.loginame       AS [Login Name]
                            ,st.text            AS [SQL Text]
                            ,DB_NAME(spr.dbid)  AS [Database]
                            ,spr.cmd            AS [Command]
                            ,spr.waitresource   AS [Wait Resource]
                            ,spr.program_name   AS [Application]
                            ,spr.hostname       AS [HostName]
                            ,spr.last_batch     AS [Last Batch Time]
                    FROM BlockingTree bt
                    LEFT OUTER JOIN sys.sysprocesses spr ON spr.spid = bt.spid
                    CROSS APPLY sys.dm_exec_sql_text(spr.SQL_HANDLE) st
                    ORDER BY LEVEL ASC"

                $Command2 = $connectionDetails.CreateCommand()
                $Command2.commandtext = $Query2
                $result2 = $Command2.ExecuteReader()
                $dbs2.Load($result2); 
                
                $var+="";
                if($dbs2.rows.count -eq 0)
                {
                    $var+="<tr>
                    <td>$serv</td>
                    <td colspan=8>No Blocking Found</td>                    
                    </tr>";
		  
		    $mastervar += "Blocking has not found on the alert triggered server,hence Automation will recheck after 15 minutes"
                }
		
		$mastervar += $dbs2

                    for($j=0; $j -le $dbs2.rows.count-1; $j++) # recordset of databases
                {
                   
                    $Header = $dbs2.Rows[$j][0];
                    $Type = $dbs2.Rows[$j][1];
                    $WaitingUserSessionLogin = $dbs2.Rows[$j][2];
                    #$WaitingUserConnectionLogin = $dbs2.Rows[$j][3];
                    #$StartTime = $dbs2.Rows[$j][4];
                    $LastBatch = $dbs2.Rows[$j][9];
                    $WaitType = $dbs2.Rows[$j][1];
                    $WaitingHost = $dbs2.Rows[$j][8];
                    $WaitingSessionProgramName = $dbs2.Rows[$j][7];
                    #$BlockingSessionStatus = $dbs2.Rows[$j][9];
                    $WaitResourceDatabaseName = $dbs2.Rows[$j][4];
                    $BATCH = $dbs2.Rows[$j][3];

                    $Header = $Header
                    $Type = $Type.Trim();
                    $WaitingUserSessionLogin = $WaitingUserSessionLogin.Trim();
                    $WaitType = $WaitType.Trim();
                    $WaitingHost = $WaitingHost.Trim();
                    $WaitingSessionProgramName = $WaitingSessionProgramName.Trim();
                    $WaitResourceDatabaseName = $WaitResourceDatabaseName.Trim();


                    If($Header -like "|*")
                    {
                        $var+="<tr>
                        <td>$serv</td>
                        <td>$Header</td>
                        <td>$WaitingUserSessionLogin</td>
                        <td>$LastBatch</td>
                        <td>$WaitType</td>
                        <td>$WaitingHost</td>
                        <td>$WaitingSessionProgramName</td>
                        <td>$WaitResourceDatabaseName</td>
                        <td>$BATCH</td>
                        </tr>";
                    }
                    else
                    {
                        $var+="<tr bgcolor='#FF0408'>
                        <td>$serv</td>
                        <td>$Header</td>
                        <td>$WaitingUserSessionLogin</td>
                        <td>$LastBatch</td>
                        <td>$WaitType</td>
                        <td>$WaitingHost</td>
                        <td>$WaitingSessionProgramName</td>
                        <td>$WaitResourceDatabaseName</td>
                        <td>$BATCH</td>
                        </tr>";
                    }
                }

} 
$var+="</table>";
$var+="<br/>"
 
Add-content -path $ReportPath -value $var;

Function Send_EMail ($SMTPServer, $SMTPPort, $FromAddress, $ToAddress, $CCAddress, $attachment)
{
Try 
{
    #E-Mail Details
    [String]$Subject = "$TicketNo - Blocked session on $HostName"
    [String]$body = "Hi Team,
    We could see blockings on the subjected $HostName server . The Blocking details are attached in the Mail.
	Hence please check and let us know in case of any action needed from our end. 
    Thanks"; 
	
    Send-MailMessage -SmtpServer $SMTPServer -Port $SMTPPort -From $FromAddress -To $ToAddress -Cc $CCAddress -Subject $Subject -Body $body -Attachments $attachment;

}
Catch [System.exception]
{
    Write-Error "Send Mail Error:- $_.Exception.Message ";
}
}



if($dbs2.rows.count -gt 0)
{
    if($ToAddress -ne "")
    {
        Send_EMail -SMTPServer $SMTPServer -SMTPPort $SMTPPort -FromAddress $FromAddress -ToAddress $ToAddress -Cc $CCAddress -attachment $ReportPath;
    }
	else
    {
        Send_EMail -SMTPServer $SMTPServer -SMTPPort $SMTPPort -FromAddress $FromAddress -ToAddress $ToAddress -Cc $CCAddress -attachment $ReportPath;
    }
}

$resultobj.output = $mastervar #|out-string
Exit-json -obj $resultobj

}
Catch {
    $resultobj.err += "Error while executing solution. $_"
    Exit-json -obj $resultobj
}

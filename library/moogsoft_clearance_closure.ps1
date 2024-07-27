#!powershell
#Requires -Module Ansible.ModuleUtils.Legacy

####################################################################################################
# Name        : Moogsoft Resolved Ticket Closure                                                   #
# Version     : 1.1 (ansible_custom_module)                                                        #
# Developer   : shishir.78@wipro.com                                                               #
# Description : This Script will Fetch the Ticket based on state, createdby,openedby,Assignement   #
#               Groups, and fetch the tickets, based on limit, and Check If Last Worknotes         #
#               Contains resolution keyword and MoogSoft user and close the ticket based on       #
#               Resolution information report of every ticket closed in csv format with            #
#               closing information                                                                #
#                                                                                                  #
# Prerequisites:                                                                                   #
#              - Instance                                                                          #
#              - ISTM user Id and pass                                                             #
#              - Fetch and Resolution information                                                  #
#              - Output path for output file                                                       #
#                                                                                                  #
####################################################################################################

$ErrorActionPreference = "STOP"

$params = Parse-Args $args -supports_check_mode $true

$user = Get-AnsibleParam -obj $params -name "user" -type "str"
$pass = Get-AnsibleParam -obj $params -name "pass" -type "str"

$Instance = Get-AnsibleParam -obj $params -name "Instance" -type "str"
$createdby = Get-AnsibleParam -obj $params -name "createdby" -type "str"
$updatedby = Get-AnsibleParam -obj $params -name "updatedby" -type "str"

$state = Get-AnsibleParam -obj $params -name "state" -type "str"
$limit = Get-AnsibleParam -obj $params -name "limit" -type "str"
$assigned_to = Get-AnsibleParam -obj $params -name "assigned_to" -type "str"
$Assignmentgrps = Get-AnsibleParam -obj $params -name "Assignmentgrps" -type "str"

$resol_Cat = Get-AnsibleParam -obj $params -name "resol_Cat" -type "str"
$resolved_by = Get-AnsibleParam -obj $params -name "resolved_by" -type "str"
$resol_Subcat =Get-AnsibleParam -obj $params -name "resol_Subcat" -type "str"

$close_state = Get-AnsibleParam -obj $params -name "close_state" -type "str"
$close_code = Get-AnsibleParam -obj $params -name "close_code" -type "str"
$close_notes = Get-AnsibleParam -obj $params -name "close_notes" -type "str"

$last_Worknote = Get-AnsibleParam -obj $params -name "last_Worknote" -type "str"
$last_worknoteUpdatedby = Get-AnsibleParam -obj $params -name "last_worknoteUpdatedby" -type "str"

$OutputPath = Get-AnsibleParam -obj $params -name "OutputPath" -type "str"

$result = @{
    changed = $false
    log = [System.Collections.Generic.List`1[String]]@()
    err = [System.Collections.Generic.List`1[String]]@()
    report = ""
    success_tickets = [System.Collections.Generic.List`1[String]]@() # for metering purpose
}


try{
try{
#Adding SSL Cert
$result.log.Add("[$(Get-Date -Format "dd-MM-yyyy:hh-mm-ss")] Adding SSL Cert.")

add-type @"
using System.Net;
using System.Security.Cryptography.X509Certificates;
public class TrustAllCertsPolicy : ICertificatePolicy {
public bool CheckValidationResult(
ServicePoint srvPoint, X509Certificate certificate,
WebRequest request, int certificateProblem) {
return true;
}
}
"@

$AllProtocols = [System.Net.SecurityProtocolType]'Tls12'
[System.Net.ServicePointManager]::SecurityProtocol = $AllProtocols
[System.Net.ServicePointManager]::CertificatePolicy = New-Object TrustAllCertsPolicy

$result.log.Add("[$(Get-Date -Format "dd-MM-yyyy:hh-mm-ss")] Configured SecurityProtocol & CertificatePolicy.")
$Error.Clear()
}
catch{
$Error_Log = "Error occurred on line $($Error[0].InvocationInfo.ScriptLineNumber): $($Error[0].Exception.Message)"
$result.err.Add("[$(get-date -Format "dd-MM-yyyy:hh-mm-ss")] In adding ssl, $Error_Log")
}

    ########Output Variables#############

    $Reports = @()
    $OutputReport = @()
    $File_date = Get-Date -Format "ddMMyyyy"
    $outfile = "$OutputPath\Output_$File_date.csv"

    $result.log.Add("[$(Get-Date -Format "dd-MM-yyyy:hh-mm-ss")] Output file will be stored at $outfile.")

    if(Test-Path $outfile){
        $Temp = Import-Csv -Path $outfile
        $result.log.Add("[$(Get-Date -Format "dd-MM-yyyy:hh-mm-ss")] $outfile - Path is valid.")

    }
    else{
        $result.log.Add("[$(Get-Date -Format "dd-MM-yyyy:hh-mm-ss")] $outfile - Path doesn't exist.")
    }

         ####Function for Closing Ticket####

    Function Resolve-incident{
        param(
        [Parameter(Mandatory=$true)][string]$incNum,
        [Parameter(Mandatory=$true)]$close_code,
        [Parameter(Mandatory=$true)][string]$inc_sysid,
        [Parameter(Mandatory=$true)][string]$close_notes,
        [Parameter(Mandatory=$true)]$assigned_to,
        [Parameter(Mandatory=$true)]$work_notes
        )
        try{
            #Specify endpoint uri
            $uri = "https://$Instance/api/now/table/incident/$inc_sysid"
            $result.log.Add("[$(Get-Date -Format "dd-MM-yyyy:hh-mm-ss")] Using endpoint : $uri")

            #Specify HTTP method
            $method = "PUT"
    
            $body_hash = @{work_notes=$work_notes;state=$close_state;assigned_to=$assigned_to;close_code=$close_code;close_notes=$close_notes;u_resolution_category=$resol_Cat;u_resolution_subcategory=$resol_Subcat}
            $body =  $body_hash | ConvertTo-Json

            #Send HTTP request
            try{
                $res = Invoke-RestMethod -Headers $headers -Method $method -Uri $uri -Body $body
                $result.log.Add("[$(Get-Date -Format "dd-MM-yyyy:hh-mm-ss")] Updated service now notes")
                $Error.Clear()
            } 
            catch [System.Exception]{
                $Error_Log = "Error occurred on line $($Error[0].InvocationInfo.ScriptLineNumber): $($Error[0].Exception.Message)"
                $result.err.Add("[$(get-date -Format "dd-MM-yyyy:hh-mm-ss")] In making hhtp request, $Error_Log")
            }
            $Error.Clear()  
        }
        catch [System.Exception]{
            $Error_Log = "Error occurred on line $($Error[0].InvocationInfo.ScriptLineNumber): $($Error[0].Exception.Message)"
            $result.err.Add("[$(get-date -Format "dd-MM-yyyy:hh-mm-ss")] In resolving incident, $Error_Log")
        }
    }

    ############################## Main Script #####################################

    # Build auth header
    $base64AuthInfo = [Convert]::ToBase64String([Text.Encoding]::ASCII.GetBytes(("{0}:{1}" -f $user, $pass)))

    # Set proper headers
    $headers = New-Object "System.Collections.Generic.Dictionary[[String],[String]]"
    $headers.Add('Authorization',('Basic {0}' -f $base64AuthInfo))
    $headers.Add('Accept','application/json')

    # Specify endpoint uri
    $uri = "https://$Instance/api/now/table/incident?state=$state&sys_created_by=$createdby&sys_updated_by=$updatedby&sysparm_query=assignment_group.nameIN$Assignmentgrps^ORDERBYDESCsys_created_on&sysparm_display_value=true&sysparm_limit=$limit"
    #$uri = "https://$Instance/api/now/table/incident?sysparm_query=assignment_group.nameIN$Assignmentgrps^ORDERBYDESCsys_created_on"
    
    # Specify HTTP method
    $method = "get"

    # Send HTTP request

    $response = Invoke-RestMethod -Headers $headers -Method $method -Uri $uri 

    # Print response
    $ResOutputs = $response.result
    #$result.log.Add("[$(Get-Date -Format "dd-MM-yyyy:hh-mm-ss")] Response $ResOutputs .")
    #exit
    foreach($ResOutput in $ResOutputs){
        $incNum = $ResOutput.number
        $short_Desc = $ResOutput.short_description
        $Description = $ResOutput.description
        $Assignment_group = $ResOutput.assignment_group.display_value
        $state = $ResOutput.state
        $Inc_sysid = $ResOutput.sys_id
        $cmdb = $ResOutput.cmdb_ci.display_value
        $snow_assignedto = $ResOutput.assigned_to.display_value
        $Snow_worknotes = $ResOutput.work_notes
        $snow_worknotes = $snow_worknotes -split ("`n")
        $Snow_WorknoteUpdatedby = ((($snow_worknotes[0] -split (" - "))[-1]) -split (' \('))[0]
        $snowlast_worknote = $snow_worknotes[1]
   
        if($Snow_WorknoteUpdatedby -eq $last_worknoteUpdatedby -and $snowlast_worknote -eq $last_Worknote ){
            
            $result.log.Add("[$(Get-Date -Format "dd-MM-yyyy:hh-mm-ss")] Inc number is : $incNum, Inc sysid is : $Inc_sysid")

            if($snow_assignedto -ne $null -and $snow_assignedto -ne "" -and $snow_assignedto -ne " "){
                $assigned_to = $snow_assignedto
            }
            
            Resolve-incident -incNum $incNum -inc_sysid $Inc_sysid -assigned_to $assigned_to -close_code $close_code -close_notes $close_notes -work_notes $close_notes
            $result.success_tickets.Add($incNum)  # for testing purpose
            $timestamp = Get-Date -Format 'yyyy-MM-dd HH:mm:ss'
            $Report = New-Object psobject -Property @{
                Incident_No = $incNum
                Assignment_group = $Assignment_group
                Closed_on = $timestamp
            }
            $Reports += $Report
        }
    }
    if($Temp -ne $null){
        $OutputReport += $Temp
        $OutputReport += $Reports    
    }
    else{
        $OutputReport += $Reports  
    }
    $result.log.Add("[$(Get-Date -Format "dd-MM-yyyy:hh-mm-ss")] Exporting report: `n OutputReport")
    $OutputReport | Select-Object "Incident_No", "Assignment_group", "Closed_on" | Export-Csv -Path $outfile -NoTypeInformation -Force
    $result.changed = $true
    $Error.Clear()
}
catch{
    $Error_Log = "Error occurred on line $($Error[0].InvocationInfo.ScriptLineNumber): $($Error[0].Exception.Message)"
    $result.err.Add("[$(get-date -Format "dd-MM-yyyy:hh-mm-ss")] In script execution, $Error_Log")
}
finally{
    $result.log.Add("[$(get-date -Format "dd-MM-yyyy:hh-mm-ss")] Script execution is completed. Please find logs and report at $outfile.`n")
    Exit-Json -obj $result
}

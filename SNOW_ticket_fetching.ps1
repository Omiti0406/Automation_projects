Remove-Variable -Name * -ErrorAction SilentlyContinue -Force
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12

$user = "ITSM_User"
$pass = "ITSM_Pass"
$short_desc = @("Install -","Approval -")
$limit = "10"
$instance = "ntnew"
$catlog_item = "Software Install Request (Revised)"
$assignment_group = [ordered]@{"IND NATS Software Support" = "695215450a0a3c40016fffe08b90106a";
                               "NATS Business App Support" = "2fc64fbe0a0a3c26009ddc1949345c49"
                               }
$host_name = "SDCHOLP004.ent.ad.ntrs.com"
$solution_name = "Citrix_Add_User_to_SWInstallationGroup"

Function Trigger_Healix_solution{
[cmdletbinding()]
Param (
[parameter(mandatory=$false)]
[string]$Task_Value,
[string]$hostname,
[string]$Soln_name)

    Write-Output "Triggering Solution $Soln_name for $Task_Value"
    [System.Net.ServicePointManager]::ServerCertificateValidationCallback = {$true}

    ##Input##
    $HO_instance="https://10.92.53.50:8020/api/Agent/ExecuteSolutionByNameAsync"
    $api_key="8D5A6AE6A37AC13"
    $account_id="205"
    $log_content=""
    $main_log=""

    $method1="post"
 
    #[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
 
    #$base64AuthInfo = [Convert]::ToBase64String([Text.Encoding]::ASCII.GetBytes(("{0}:{1}" -f $user, $pass)))
    $healix_apiheaders = @{'content-type' = 'application/json'; 'APIKey'= $api_key}
    $Call_Soln = "" | Select-Object AccountId,HostName,SolutionName,APIKey,Parameters
    $Call_Soln.AccountID= $account_id
    $Call_Soln.HostName=$hostname
    $Call_Soln.SolutionName=$Soln_name
    $Call_Soln.APIKey=$api_key
    try{
  
        $parameters=@()
        $Input1=[ordered]@{"Name"="Tsk";"Value"="$Task_Value" }
        $parameters += $Input1

        $Call_Soln.Parameters =$parameters;
        $tempjson= $Call_Soln | ConvertTo-Json | % { [System.Text.RegularExpressions.Regex]::Unescape($_) }
        $json += $tempjson
 
        #convert-to-json
        #$tempjson | ConvertTo-Json
 
            $body="";
            $body=$tempjson;
            #$HO_response="";
 
            #web call
            $HO_response = Invoke-RestMethod -Headers $healix_apiheaders -Method $method1 -Uri $HO_instance -Body $body #-UseBasicParsing
            #$response
            if($HO_response.StatusCode -eq 200)
            {
                Write-Output -message "Response code: 200, OK"
            }
            else
            {
                Write-Output -message "Response Code is $($HO_response.StatusCode)"
            }
    
            return $HO_response
    }
    catch
    {
        $_
    }

      
}



$base64AuthInfo = [Convert]::ToBase64String([Text.Encoding]::ASCII.GetBytes(("{0}:{1}" -f $user, $pass)))

$headers = New-Object "System.Collections.Generic.Dictionary[[String],[String]]"
$headers.Add('Authorization',('Basic {0}' -f $base64AuthInfo))
$headers.Add('Accept','application/json')

$uri = "https://$instance.service-now.com/api/now/table/sc_task?sysparm_query=ORDERBYDESCsys_created_on%5Eactive%3Dtrue%5Estate%3D1%5Erequest_itemISNOTEMPTY%5Eassignment_group=$($assignment_group.'IND NATS Software Support')^ORassignment_group=$($assignment_group.'NATS Business App Support')^short_descriptionLIKE$($short_desc[0])^ORshort_descriptionLIKE$($short_desc[1])&request_item.cat_item.name=$catlog_item&sysparm_display_value=true&sysparm_fields=number%2Crequest_item%2Cshort_description%2Cdescription%2Cassignment_group%2Csys_created_on%2Crequest_item.cat_item.name&sysparm_limit=$limit"

$method = "get"

# Send HTTP request
try{
    $response = Invoke-RestMethod -Headers $headers -Method $method -Uri $uri

    $tasks = $response.result

    foreach($task in $tasks){
        $task_number = $task.number.Trim()
        #$task_number
        Trigger_Healix_solution -Task_Value $task_number -Soln_name $solution_name -hostname $host_name
        Write-Host "WORKFLOW TRIGGERED FOR $task_number "

    }
}
catch{
    $_
}

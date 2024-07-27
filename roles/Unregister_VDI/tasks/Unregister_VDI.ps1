<#
.NOTES
===========================================================================
     
Created on        : 05/26/2024
Created by        : Mayur Matey
Last Reviewed By  : 
Organization      : Wipro
Filename          : UnRegistered VDI Case3
Version           : 1.0
===========================================================================
#>
$ddc_user = "$env:cluster_user"
$ddc_pass = "$env:cluster_pass"

Try{
$username_us = $ddc_user 
$password_us = $ddc_pass #Decrypt-String -EncryptedString "152-116-89-101-162-130-128-155-105-164-145-85"
$secpasswd_us = ConvertTo-SecureString $password_us -AsPlainText -Force
$cred_us = New-Object System.Management.Automation.PSCredential ($username_us, $secpasswd_us)

$username_uk = $ddc_user 
$password_uk = $ddc_pass #Decrypt-String -EncryptedString "152-116-89-101-162-130-128-155-105-164-145-85"
$secpasswd_uk = ConvertTo-SecureString $password_uk -AsPlainText -Force
$cred_uk = New-Object System.Management.Automation.PSCredential ($username_uk, $secpasswd_uk)


#$scriptpath = $MyInvocation.MyCommand.Path
$dir = '\\WPCHOLU01\Data\unregistered_vdi'# $scriptpath

# REPORT PROPERTIES
	# Path to the report
		
		$reportPath = "$dir\Unregistered_VDI_Reports_Case3\"

	# Report name
		
        $reportNameCsv = "Unregistered_VDI_Report_$(Get-Date -Format "dd_MM_yyyy").csv";

# Path and Report name together
$ApplicationReport = $reportPath + $reportName
$ApplicationReportCsv = $reportPath + $reportNameCsv

$csv = @()

$Ddcs = @{      
    US1 = "WNAPXDS0001"
    UK1 = "WEUPXDS0001"
    US2 = "WNAPXDS0003"
    US3 = "WNAPXDS0002"
    US4 = "WNAPXDS0004"
    UK2 = "WEUPXDS0003"
    UK3 = "WEUPXDS0002"
    UK4 = "WEUPXDS0004"      
}
$keys = @($ddcs.keys)
foreach ($key in $Ddcs.Keys) {
try {
$Ddc = $Ddcs[$key]
if ($key -like "US*"){$cred = $cred_us;$ke = "US"}
else {$cred = $cred_uk;$ke = "UK"}
$csv += Invoke-Command -ComputerName $ddc -Credential $cred -ScriptBlock {
$csv = @()
$ErrorActionPreference = "SilentlyContinue"
Import-Module Citrix.XenDesktop.Admin;
Add-PSSnapin Citrix.* -ErrorAction SilentlyContinue -ErrorVariable ErrCitrixSnapin;

Try
{
$FailedRestartDatas = @()
$Unregisteres = Get-BrokerDesktop -MaxRecordCount 5000 -Filter {InMaintenanceMode -eq "False" -and PowerState -eq "On" -and RegistrationState -eq "UnRegistered"}|?{$_.hostedmachine -notmatch "-d" -and $_.hostedmachine -notmatch "-l"}|Select-Object HostedMachineName -ErrorAction SilentlyContinue
#$Unregisteres1 = Get-BrokerDesktop -MaxRecordCount 5000 -Filter {InMaintenanceMode -eq "False" -and PowerState -eq "On" -and RegistrationState -eq "UnRegistered"}|Select-Object HostedMachineName -ErrorAction SilentlyContinue
#$UnregisteredMachinesCount = $($Unregisteres|Measure-Object -Property *).count
write-host $Unregisteres
    if($Unregisteres)
    {

        $Data = ""
        $FinalDatas = @()
        foreach($Unregistere in $Unregisteres)
        {
        $MachineName = $Unregistere.HostedMachineName
        #Get-Service -ComputerName $MachineName -DisplayName 'Citrix Desktop Service' | Restart-Service -ErrorVariable ErrFlag -ErrorAction SilentlyContinue -WarningAction SilentlyContinue
       Invoke-Command -ComputerName $MachineName -ScriptBlock {Restart-Service "Citrix Desktop Service"} -ErrorVariable ErrFlag -ErrorAction SilentlyContinue
        #Invoke-Command -ComputerName $MachineName -ScriptBlock {Restart-Service "Citrix Desktop Service"} -ErrorVariable ErrFlag -ErrorAction SilentlyContinue
        #Restart-Service -InputObject $(Get-Service -Computer $MachineName -Name "Citrix Desktop Service") -ErrorVariable ErrFlag -ErrorAction SilentlyContinue;
            if($ErrFlag)
            {
                $Flag = $ErrFlag
                #$Flag = "Unable To Restart Citrix Desktop Service on $MachineName"
            }
            else
            {
               $Flag = "False"
            }    
        $FinalDatas += New-Object -TypeName psobject -Property @{MachineName=$MachineName; Flag=$Flag;}
        }
        if($FinalDatas)
        {
           Start-Sleep -Seconds 300
            foreach($FinalData in $FinalDatas)
            {
            $ErrRestart = ""
               $null = New-BrokerHostingPowerAction -Action Reset -MachineName $FinalData.MachineName -ErrorVariable ErrRestart -ErrorAction SilentlyContinue
                #Restart-Computer -ComputerName $FinalData.MachineName -Force -ErrorVariable ErrRestart -ErrorAction SilentlyContinue
                If($ErrRestart){$RestartInfo = $ErrRestart}else{$RestartInfo="False"}
                $FailedRestartDatas += New-Object -TypeName psobject -Property @{MachineName=$($FinalData.MachineName);RestartFlag=$RestartInfo;}
            }
            if($FailedRestartDatas)
            {
        Start-Sleep -Seconds 300
                foreach($FailedRestartData in $FailedRestartDatas)
                {
                    $fields = ""|Select @{l="DC";e={$using:ke}},"Checked at","Machine Name","Catalog Name","Delivery Group Name","Maintenance Mode","Power State","Registration State","Restart Status","Error"
                    Try
                    {
                        $HostedMachineName = ""
                        $HostedMachineName = $FailedRestartData.MachineName
                        $RestartCurrentState = Get-BrokerDesktop -MaxRecordCount 5000 -Filter {HostedMachineName -eq $HostedMachineName}
                        if([String]$($RestartCurrentState.InMaintenanceMode) -eq "False"){$CurrentMaintenanceMode = "Off"}else{$CurrentMaintenanceMode = "On"}
                        if($($FailedRestartData.RestartFlag) -eq "False"){$RestartStatus = "Restarted Successfully"}else{$RestartStatus = $($FailedRestartData.RestartFlag)}
                        
                        $fields.'Checked at' =  Get-Date -Format "dd/MM/yyyy HH:mm:ss"
                        $fields.'Machine Name' = $FailedRestartData.MachineName
                        $fields.'Catalog Name' = $RestartCurrentState.CatalogName
                        $fields.'Delivery Group Name' = $RestartCurrentState.DesktopGroupName
                        $fields.'Maintenance Mode' = $CurrentMaintenanceMode
                        $fields.'Power State' = $RestartCurrentState.PowerState
                        $fields.'Registration State' = $RestartCurrentState.RegistrationState
                        $fields.'Restart Status' = $RestartStatus
                        
                    }
                    catch [System.Exception]
                    {
                        $fields.'Checked at' =  Get-Date -Format "dd/MM/yyyy HH:mm:ss"
                        $fields.'Machine Name' = $FailedRestartData.MachineName
                        $fields.'Catalog Name' = ""
                        $fields.'Delivery Group Name' = ""
                        $fields.'Maintenance Mode' = ""
                        $fields.'Power State' = ""
                        $fields.'Registration State' = ""
                        $fields.'Restart Status' = ""
                        $fields.Error = $_.exception.message
                    }
                    $csv += $fields
                }
            }
            
        }
    }
   
}
catch [System.Exception]
{
    $csv = ""|select @{l="DC";e={$using:ke}},@{l="Checked at";e={Get-Date -Format "dd/MM/yyyy HH:mm:ss"}},"Machine Name","Catalog Name","Delivery Group Name","Maintenance Mode","Power State","Registration State","Restart Status",@{l="Error";e= {"Error in executing the solution in $using:key region.$_"}}
    write-host "Creating the CSV file with all the requried field it will print if Error in executing the solution in key region"
}
$csv
} -ErrorAction Stop -HideComputerName
}
Catch {
    $csv += ""|select @{l="DC";e={$ke}},@{l="Checked at";e={Get-Date -Format "dd/MM/yyyy HH:mm:ss"}},"Machine Name","Catalog Name","Delivery Group Name","Maintenance Mode","Power State","Registration State","Restart Status",@{l="Error";e= {"Error in executing the solution in server $ddc. $_"}}
    write-host "Error in executing the solution in server ddc"
}
}

$csv |select -Property * -ExcludeProperty PSComputerName,RunspaceId,PSShowComputerName | export-csv $ApplicationReportCsv -Append -notypeinformation -Force -Confirm:$false -ErrorAction Stop
write-host "Created the File"
} 
catch { 

write-host "Error in Executing the Solution $_"

}

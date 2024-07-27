<#
.NOTES
===========================================================================
Created on        : 15-04-2024
Created by        : Mayur Matey (mayur.matey@wipro.com)  
Last Reviewed By  : 
Organization      : Wipro
Filename          : VDI Decommission
Version           : 3.0
===========================================================================
#>
$env:PSModulePath=$env:PSModulePath+";"+'C:\Program Files (x86)\VMware\Infrastructure\PowerCLI\Modules'
#Get-Module -ListAvailable -Name VMware.* | Import-Module -Force -ErrorAction SilentlyContinue
#Get-module -Name VMware.VimAutomation.Sdk
#Input from AD Script
$Sendout = "{{ LANID }}"

$Request_Number = "$env:ritm_no"
$Decom_file_path = '\\sdcholp003\HO_21.4.0_Solutions\VDI_UseCase\ReadCMLCreateCSVForTask\DecomQueue.csv'

#$Decom_Queue_csv = Import-Csv -Path $Decom_file_path
#[xml]$SC_Creation_Date_xml = Get-Content -Path "\\sdcholp004\HO_21.4.0_Solutions\SR Integration\Data_Flow\Input\$($Request_Number).xml"
$SC_Creation_Date = "$env:Created_on"  #$SC_Creation_Date_xml.Task.RITM.Task_created_on
  
# $Inputs = $Sendout | ConvertFrom-Json 
# [String]$userID = $Inputs.UserID
# [String]$userID = $userID.Trim()

$userID = "$env:LanID"  
write-output $userID
$ddc_user = "$env:cluster_user"
$ddc_pass = "$env:cluster_pass"



$DDC_List = "WNAPXDS0001,WEUPXDS0001" -split ','
$Final_vdi = @()
$Flag1 = $false
$Sendoutput = $null
$Flag = $false

function Decrypt-String

{

    [CmdletBinding()]

    param( 

            [parameter(Mandatory = $true)]

            [ValidateNotNullOrEmpty()]

            [String] $EncryptedString,

            [parameter(Mandatory = $false)]

            [ValidateNotNullOrEmpty()]

            [Int] $MagicNumber=48

        )

    $CharArray = @($EncryptedString -split '-');

    Return $(-join ($CharArray|%{[char]$($_-$MagicNumber)}));

}

#Creds for DDC US
$username_us =  $ddc_user    
$password_us =  $ddc_pass   #Decrypt-String -EncryptedString "152-116-89-101-162-130-128-155-105-164-145-85"
$secpasswd_us = ConvertTo-SecureString $password_us -AsPlainText -Force
$cred_us = New-Object System.Management.Automation.PSCredential ($username_us, $secpasswd_us)

#Creds for DDC UK
$username_uk = $ddc_user  
$password_uk = $ddc_user  #Decrypt-String -EncryptedString "152-116-89-101-162-130-128-155-105-164-145-85"
$secpasswd_uk = ConvertTo-SecureString $password_uk -AsPlainText -Force
$cred_uk = New-Object System.Management.Automation.PSCredential ($username_uk, $secpasswd_uk)

#Output Json
$Entry = [PSCustomObject]@()
$FinalVDI = [PSCustomObject]@()
$Output = $null
$Error2 = $null


#Logfile path
$Date_log = (Get-Date -Format "dd-MM-yyyy")
$Out_log_1 = @()
$log_file_path = "\\sdcholp003\HO_21.4.0_Solutions\VDI_UseCase\VDI_Decomission\Log\VDI_Decommission_($($Date_log)).txt"

$CSV_ReportLocation = "\\sdcholp003\HO_21.4.0_Solutions\VDI_UseCase\VDI_Decomission\FinalCSV\VDI_Decommission_Final_Report.csv"


#Logfile Function
<#Function Write-Log
{
   Param ([string]$logstring)
   Add-content $Logfile -value $logstring
}#>

$Csv_Data = @()
$Properties = [Ordered] @{
                            Request_Number = ''
                            Creation_Date = ''
                            ServerName = ''
                            Server_Assignment_Type = ''
							LAN_ID = ''
                            Citrix_Status = ''
                            VMWare_Status = ''
                            AD_Status = ''
                            Decommission_Date = ''
                            Error_Citrix = ''
                            Error_VMWare = ''
                            Error_AD = ''
                         }

try
{

    #Looping through both the DC's to get the vdi names
    Write-Output "$(Get-Date) - Looping through both the DC's to get the vdi names"
    $Out_log_1 += "$(Get-Date) - Looping through both the DC's to get the vdi names"
    $invokerr = @()

    foreach($DDC in $DDC_List)
    {
        
        #Changing the creds as per the region

        if($DDC -in @("WNAPXDS0001"))
        {
            $cred = $cred_us
        }
        elseif ($DDC -in @("WEUPXDS0001"))
        {
            $cred = $cred_uk
        }
        
        try {
        $out_vdi_list = Invoke-Command -ComputerName $DDC -Credential $cred -scriptblock {

            #Adding citrix snapin
            Get-PSSnapin -Registered -Name Citrix* -ErrorAction SilentlyContinue | Add-PSSnapin -ErrorAction SilentlyContinue

            #Getting the VDI Names from citrix console
            $vdi_list = Get-BrokerMachine -AdminAddress $Using:DDC -AssociatedUserUPN $Using:userID | Select-Object MachineName -ErrorAction SilentlyContinue
            
            if($vdi_list -ne $null)
            {
                Write-Output $vdi_list.MachineName
            }
            else
            {
                #Write-Output "No vdi assigned for the user in region $($using:DDC)"
            }
            
        } -ErrorAction Stop
        
        #End of invoke block
        
        if($out_vdi_list -like 'No vdi assigned for the user')
        {
            #Skipping the loop
            Write-Output "No vdi assigned for the user in region $($DDC)"
            $Out_log_1 += "$(Get-Date) - No vdi assigned for the user in region $($DDC)"
            
            #$Flag = $false
            
        }
        else
        {
            #Adding to final list
           if ($out_vdi_list){
            $Final_vdi += [pscustomobject]@{vdi = $out_vdi_list; ddc =$ddc}
            }
            #out_vdi_list
            
            #$Flag = $true

        }

        }
        catch {
                $invokerr += "Errorin connecting to server $ddc . $_"
        
        }
        
        

    }#End of for each

    if($Final_vdi -ne $null)
    {
        
        if($Final_vdi.Count -gt 2)
        {
            $Flag1 = $false
            $Error2 = "More than 2 VDI's assigned to user, Assigning ticket to manual queue"
            write-output "More than 2 VDI's assigned to user, Assigning ticket to manual queue"
			$Out_log_1 += "$(Get-Date) - More than 2 VDI's assigned to user, Assigning ticket to manual queue"

        }
        else
        {
            $Flag1 = $true

            #Checking the VDI's assignment to users
            if($Final_vdi -eq $null)
            {
                Write-Output "No VDI's found"
                $Flag1 = $false
                if ($invokerr){write-output ($invokerr -join "`n")}
            }
            else
            {
                Write-Output "Checking the user assignment to VDI"
                $Out_log_1 += "$(Get-Date) - Checking the user assignment to VDI"

                #$Final_vdi = $Final_vdi.spli

                foreach($VDI in $Final_vdi)
                {
                    #Select the DDC
                    Write-Output "$(Get-Date) - Selecting the DDC"
                    $DDC = $vdi.ddc
                    $VDI = $VDI.vdi.Split("\")[1]

                    #$SelectDC = $VDI.Substring(0,2)

                    #if($SelectDC -eq 'IL')
                    #{
                        
                        $cred = $cred_us
                
                    #}
                    #elseif($SelectDC -eq 'UK')
                    #{
                     #   $DDC = "UKRCXDSP001"
                      #  $cred = $cred_uk
                    #}

                    $outvar = Invoke-Command -ComputerName $DDC -Credential $cred -scriptblock {
            
                            #Adding citrix snapin
                            Get-PSSnapin -Registered -Name Citrix* -ErrorAction SilentlyContinue | Add-PSSnapin -ErrorAction SilentlyContinue

                            $currentVM = Get-BrokerMachine -AdminAddress $using:DDC -MachineName *\$($using:VDI) -ErrorAction SilentlyContinue
                            if($currentVM -eq $null)
                            {
                                #Write-Output "$(Get-Date) - WARNING: Machine $($using:vmLine.VDIName) not found in Citrix"
                                #Write-Output $false
                            }
                            else
                            {
                                $users = $currentVM.AssociatedUserNames
                                if($users.Count -gt 1)
                                {
                                    Write-Output "Multiple"
                                }
                                else
                                {
                                    Write-Output "Single"
                                }
                            }

                    } -ErrorAction Stop #End of invoke

                    if($outvar -eq $null)
                    {
                        Write-Output "$(Get-Date) - Error: Fetching the VM details from citrix skipping to next record"
                        $Out_log_1 += "$(Get-Date) - Error: Fetching the VM details from citrix skipping to next record"
                        $Flag1 = $false
                        #continue
                    }
                    else
                    {
                        $value = $outvar.Trim()
                        $FinalVDI = $FinalVDI + (New-Object -TypeName psobject -Property @{VDIName=$VDI; Type=$value;DDC = $ddc})
                        $Flag1 = $true
                    }

                }#End of foreach

            }#End of else


            #Final output of Citrix querying
            $Entry = $Entry + (New-Object -TypeName psobject -Property @{Flag=$Flag1})
            #$Entry = $Entry + (New-Object -TypeName psobject -Property @{Output=$Output})
            $Entry = $Entry + (New-Object -TypeName psobject -Property @{Error=$Error2})
            $Entry = $Entry + (New-Object -TypeName psobject -Property @{UserID=$userID})
            $Entry = $Entry + (New-Object -TypeName psobject -Property @{VDINames=$FinalVDI | ConvertTo-Json})

            $Sendoutput = $Entry | ConvertTo-Json

            #Printing the output for 2nd script
            #Write-Output $Sendoutput

            $Out_log_1 += "$(Get-Date) - INFO: Query from citrix is completed, Starting decommission script"

            #Calling next script
            Write-Output "$(Get-Date) - Starting Decommission script"
        }
    }
    else
    {
        $Flag1 = $false
        Write-Output "Final vdi list is null" 
    }



    

   





    ###########################################################################################

    #Validating the flag of previous function proceeding only if true

    

       #VDI Decommission process

        if($Flag1 -eq "True")
        {

        $Inputt = $Sendoutput | ConvertFrom-Json
        $temp = [PSCustomObject]@()
        $temp = $Inputt.VDINames
        $vms = $temp |?{$_ -ne $null}| ConvertFrom-Json -ErrorAction Stop
        [string]$userID = $Inputt.UserID
        [string]$userID = $userID.Trim()
        $Flag_in = $Inputt.flag

        if($Flag_in -eq $true)
        {

        $VsphereServer = $null
        $currentVM = $null
        $DomainName = "ENT"
        $connection = $null
        $Finalout = [PSCustomObject]@()

        #Logfile Path
        #$Logfile = "D:\Wintel Tower\NT\VDI-Decomission\Code\Updated\remove-vms.log"

        #Creds for vmware and AD
        $username = $ddc_user  
        $password = $ddc_pass   #Decrypt-String -EncryptedString "152-116-89-101-162-130-128-155-105-164-145-85"
        $secpasswd = ConvertTo-SecureString $password -AsPlainText -Force
        $cred_2 = New-Object System.Management.Automation.PSCredential ($username.Trim(), $secpasswd)


        #Adding Citrix Snapin
		#Import-module citrix* -force
        #Get-PSSnapin -Registered -Name citrix* -ErrorAction SilentlyContinue | Add-PSSnapin -ErrorAction SilentlyContinue       


        
		
        <#$Module = Get-Module -ListAvailable -Name VMware.* -ErrorAction SilentlyContinue
        if($Module -ne $null)
        {
            Get-Module -ListAvailable -Name VMware.* | Import-Module -ErrorAction SilentlyContinue
        }#>

        #Setting log on popup to false
        #Set-XDCredentials -ProfileType OnPrem


        try
        {
		    Write-Output "Importing vmware modules"
        	#Importing vmware module
			#Get-module -Name VMware.VimAutomation.Sdk
			#Import-Module -Name VMware.VimAutomation.Sdk
			Get-Module -ListAvailable -Name VMware.* | Import-Module -Force -ErrorAction SilentlyContinue
			Start-Sleep -seconds 5
			 Write-Output "Setting powerCli commands"
            $configuration = Set-PowerCLIConfiguration -DisplayDeprecationWarnings $false -InvalidCertificateAction Ignore -Scope Session -DefaultVIServerMode Multiple -ParticipateInCEIP $false -Confirm:$false -ErrorAction Stop
			Write-Output "Setting powerCli config successful"
            #Setting request number
            $Properties.Request_Number = $Request_Number

            #Setting ticket creation date
            $Properties.Creation_Date = $SC_Creation_Date

            <#foreach($Csv_val in $Decom_Queue_csv)          
            {
                if($Csv_val.Task -match $Request_Number)
                {
                    $Properties.Creation_Date = "$($Csv_val.Task_created_date)"
                }
                
                
            }#>

            #Get the list of VDI's assigned to the user
            foreach($vmLine in $vms)
            {
    
                $Out_log_1 += "$(Get-Date) - INFO: Decommission started for machine $($vmLine.VDIName)"


                Write-Output $vmLine.VDIName
                Write-Output $vmLine.Type

                $Curr_Date = (Get-Date -Format "MM-dd-yyyy HH:mm:ss")
			
				$Properties.LAN_ID = "$($userID)"

                $Properties.ServerName = "$($vmLine.VDIName)"
                $Properties.Server_Assignment_Type = "$($vmLine.Type)"
                $Properties.Decommission_Date = "$($Curr_Date)"

                #Select based on switch
                $DDC = $null
                $VsphereServer = $null

                #Select the DDC
                #Write-Log "$(Get-Date) - Selecting the DDC"

                $SelectDC = (($vmLine.VDIName.Trim() -split ''| Where-Object {$_ -ne '' -and $_ -ne $null} |select-object -first 2) -join '') 

                #if($SelectDC -eq 'IL')
                #{
                    $DDC = $vmline.DDC
                    $cred = $cred_us
                #}
                #elseif($SelectDC -eq 'UK')
                #{
                 #   $DDC = "UKRCXDSP001"
                  #  $cred = $cred_uk
               # }

                #Select the VsphereServer
                #Write-Log "$(Get-Date) - Selecting the VsphereServer"
                $Out_log_1 += "$(Get-Date) - INFO: Selecting the VsphereServer"

                $SelectVS = (($vmLine.VDIName.Trim() -split ''| Where-Object {$_ -ne '' -and $_ -ne $null} |select-object -first 4) -join '')

                Switch($SelectVS)
                {
                    'ILRC'{
                                $VsphereServer = "wpc01dupvvc01"
                          }

                    'ILNC'{
                                $VsphereServer = "npc01dupvvc01"
                          }

                    'UKL1'{
                                $VsphereServer = "ukpc01dupvvc03"
                          }

                    'UKPC'{
                                $VsphereServer = "ukpc01dupvvc03"
                          }

                    'UKL3'{
                                $VsphereServer = "ukrc01dupvvc03"
                          }

                    'UKRC'{
                                $VsphereServer = "ukrc01dupvvc03"
                          }
                }

                if($connection -eq $null)
                {
                    $connection = Connect-VIServer -Server $VsphereServer -Credential $cred_2 -ErrorAction Stop    
                }
                else
                {
                    #Write-Log "$(Get-Date) - Vcenter connection exists"
                    $Out_log_1 += "$(Get-Date) - INFO: Vcenter connection exists"
                }
        

                #region AD
                function removefromad()
                {
                    Write-Output "`n$(Get-Date) - INFO: Machine $($vmLine.VDIName) Removal from AD started.."
                    $Out_log_1 += "$(Get-Date) - INFO: Machine $($vmLine.VDIName) Removal from AD started.."

                    $Flag_ad = $false

                    try
                    {
						$currentVM = $null
						try
						{
							$currentVM = Get-ADComputer -Identity $vmLine.VDIName -Credential $cred -ErrorAction SilentlyContinue
						}
						catch
						{
							#Write-output $_.Exception.Message
						}
                        
                        if($currentVM -eq $null)
                        {
                            #Write-Log "$(Get-Date) - ERROR: Machine $($vmLine.VDIName) not found in AD"
                            Write-Output "$(Get-Date) - INFO: Machine $($vmLine.VDIName) not found in AD"
                            $Out_log_1 += "$(Get-Date) - INFO: Machine $($vmLine.VDIName) not found in AD"

                            $Flag_ad = $false
                        }
                        else
                        {
							Write-Output "`n$(Get-Date) - INFO: Machine $($vmLine.VDIName) Removal from AD processing.."
                            Remove-ADComputer -Identity $vmLine.VDIName -Credential $cred -Confirm:$false  -ErrorAction SilentlyContinue -ErrorVariable +ADError
                            #Write-Log "$(Get-Date) - SUCCESS: Machine $($vmLine.VDIName) removed from AD"

                            Start-sleep -Seconds 90

                            #Revalidating removal from AD
							$ADStatus = $null
							try
							{
								$ADStatus = Get-ADComputer -Identity $vmLine.VDIName -Credential $cred -ErrorAction SilentlyContinue
							}
							catch
							{
								#Write-output $_.Exception.Message
							}
                            
                            if($ADStatus -eq $null)
                            {
                                $Flag_ad = $true
                                Write-Output "$(Get-Date) - SUCCESS: Machine $($vmLine.VDIName) removed from AD"
                                $Out_log_1 += "$(Get-Date) - SUCCESS: Machine $($vmLine.VDIName) removed from AD"
                            }
                            else
                            {
                                $Flag_ad = $false
                                Write-Output "$(Get-Date) - INFO: Machine $($vmLine.VDIName) removal from AD failure"
                                $Out_log_1 += "$(Get-Date) - INFO: Machine $($vmLine.VDIName) removal from AD failure"
                            }
                        }
                    }
                    catch
                    {
                        $Flag_ad = $false
                        $_.Exception.Message
                        $Out_log_1 += $_.Exception.Message

                        $Properties.Error_AD = "Exception occured while removing machine from AD"
                        
                    }
                    finally
                    {
                        Write-Output "`nMachine removal from AD please find the status: $($Flag_ad)"
                        $Out_log_1 += "$(Get-Date) - INFO: Machine removal from AD please find the status: $($Flag_ad)"

                        if($Flag_ad -eq $true)
                        {
                            $Flag = $true
                            $Properties.AD_Status = "Success"
                        }
                        else
                        {
                            $Flag = $false
                            $Properties.AD_Status = "Failure"
                        }
                        
                        Write-Output "`nFinal flag: $($Flag)"
                        $Out_log_1 += "$(Get-Date) - INFO: Final flag: $($Flag)"
                    }
					return $Out_log_1
                }
        
                 #endregion AD

                 #region VMware
                function removefromvmware()
                {
                    Write-Output "`n$(Get-Date) - INFO: Machine $($vmLine.VDIName) Removal from vmware started.."
                    $Out_log_1 += "$(Get-Date) - INFO: Machine $($vmLine.VDIName) Removal from vmware started.."

                    $Flag_vm = $false

                    try
                    {
                        $currentVM  = Get-VM -Name $vmLine.VDIName -ErrorAction Stop

                        if($currentVM -ne $null)
                        {
                            if($currentVM.PowerState -ne 'PoweredOff')
                            {
                                $currentVM | Stop-VM -Confirm:$false | Remove-VM -DeletePermanently -Confirm:$false -ErrorAction Stop -ErrorVariable +VMError
                                #Write-Output "$(Get-Date) - SUCCESS: Machine $($vmLine.VDIName) removed from vcenter"

                                Start-sleep -Seconds 60
                                Disconnect-VIServer -Confirm:$false -Force

                                Connect-VIServer -Server $VsphereServer -Credential $cred_2 -ErrorAction Stop -ErrorVariable +VMError
                                Start-sleep -Seconds 30

                                #Revalidating the VM removal
                                $VMstatus  = Get-VM -Name $vmLine.VDIName -ErrorAction SilentlyContinue
                                if($VMstatus -eq $null)
                                {
                                    $Flag_vm = $true
                                    Write-Output "$(Get-Date) - SUCCESS: Machine $($vmLine.VDIName) removed from vcenter"
                                    $Out_log_1 += "$(Get-Date) - SUCCESS: Machine $($vmLine.VDIName) removed from vcenter"

                                    
                                }
                                else
                                {
                                    $Flag_vm = $false
                                    Write-Output "$(Get-Date) - FAILURE: Machine $($vmLine.VDIName) removing from vcenter failed" 
                                    $Out_log_1 += "$(Get-Date) - FAILURE: Machine $($vmLine.VDIName) removing from vcenter failed"
                                }
                    
                            }
                            else
                            {
                                $currentVM | Remove-VM -Confirm:$false -DeletePermanently -ErrorAction Stop -ErrorVariable +VMError
                                #Write-Log "$(Get-Date) - SUCCESS: Machine $($vmLine.VDIName) removed from vcenter"
                            

                                Start-sleep -Seconds 60
                                Disconnect-VIServer -Confirm:$false -Force

                                Connect-VIServer -Server $VsphereServer -Credential $cred_2 -ErrorAction Stop -ErrorVariable +VMError
                                Start-sleep -Seconds 30

                                #Revalidating the VM removal
                                $VMstatus  = Get-VM -Name $vmLine.VDIName -ErrorAction SilentlyContinue
                                if($VMstatus -eq $null)
                                {
                                    $Flag_vm = $true
                                    Write-Output "$(Get-Date) - SUCCESS: Machine$($vmLine.VDIName) removed from vcenter"
                                    $Out_log_1 += "$(Get-Date) - SUCCESS: Machine$($vmLine.VDIName) removed from vcenter"
                                }
                                else
                                {
                                    $Flag_vm = $false
                                    Write-Output "$(Get-Date) - FAILURE: Machine $($vmLine.VDIName) removing from vcenter failed" 
                                    $Out_log_1 += "$(Get-Date) - FAILURE: Machine $($vmLine.VDIName) removing from vcenter failed"
                                }
                            }
                        }
                        else
                        {
                           Write-Output "$(Get-Date) - INFO: Machine $($vmLine.VDIName) not found in vmware"
                           $Out_log_1 += "$(Get-Date) - INFO: Machine $($vmLine.VDIName) not found in vmware"
                           $Flag_vm = $false
                        }
                    }
                    catch
                    {
                        $_.Exception.Message
                        $Out_log_1 += $_.Exception.Message
                        $Flag_vm = $false
                        
                        $Properties.Error_VMWare = "Exception occured while removing machine from vmware"
                    }
                    finally
                    {
                        Write-Output "`nMachine removal from vmware please find the status: $($Flag_vm)"
                        $Out_log_1 += "$(Get-Date) - INFO: Machine removal from vmware please find the status: $($Flag_vm)"

                        if($Flag_vm -eq $true)
                        {
                            $Flag = $true
                            $Properties.VMWare_Status = "Success"
                        }
                        else
                        {
                            $Flag = $false
                            $Properties.VMWare_Status = "Failure"
                        }
                        
                        Write-Output "`nFinal flag: $($Flag)"
                        $Out_log_1 += "$(Get-Date) - INFO: Final flag: $($Flag)"
                    }
                    return $Out_log_1
                }  
                #endregion VMware

                #region Citrix
                try
                {
                    
                    Write-Output "$(Get-Date) - INFO: Machine $($vmLine.VDIName) Removal from citrix started.."
                    $Out_log_1 += "$(Get-Date) - INFO: Machine $($vmLine.VDIName) Removal from citrix started.."


                    $outvar = Invoke-Command -ComputerName $DDC -Credential $cred -scriptblock {
            
                       #Adding Citrix Snapin
                       Get-PSSnapin -Registered -Name citrix* -ErrorAction SilentlyContinue | Add-PSSnapin -ErrorAction Stop
                        
                        $Flag_citrix = $false

                        $currentVM = Get-BrokerMachine -AdminAddress $using:DDC -MachineName *\$($using:vmLine.VDIName) -ErrorAction SilentlyContinue
                        if($currentVM -eq $null)
                        {
                            Write-Output "$(Get-Date) - WARNING: Machine $($using:vmLine.VDIName) not found in Citrix"
                            $Flag_citrix = $false
                        }
                        else
                        {
                            Write-Output "$(Get-Date) - Machine $($using:vmLine.VDIName) found in citrix"
    
                            if($using:vmLine.Type -eq 'Multiple')
                            {
                                #Remove access to specific user from that computer object
                                Write-Output "$(Get-Date) - INFO: Machine $($using:vmLine.VDIName) Multiple assignment, access removal"
                                try
                                {
                                    Remove-BrokerUser "$($using:DomainName)\$($using:userID)" -PrivateDesktop "$($using:DomainName)\$($using:vmLine.VDIName)" -ErrorAction Stop -ErrorVariable +CitrixError

                                    Write-Output "$(Get-Date) - Removed user $($using:userID) from machine $($using:vmLine.VDIName)"
                                    $Flag_citrix = $true
                                }
                                catch
                                {
                                    $Flag_citrix = $false
                                    $_.Exception.Message
                                }
                                
                            }
                            elseif($using:vmLine.Type -eq 'Single')
                            {
                                Write-Output "$(Get-Date) - INFO: Machine $($using:vmLine.VDIName) Single assignment, decommission from citrix"
                                try
                                {

                                    $MachineStatus = Get-BrokerMachine -AdminAddress $using:DDC -MachineName "$($using:DomainName)\$($using:vmLine.VDIName)" -ErrorAction Stop -ErrorVariable +CitrixError
                                    if($MachineStatus -ne $null)
                                    { 
                                          $MaintenanceStatus = Get-BrokerMachine -AdminAddress $using:DDC -MachineName "$($using:DomainName)\$($using:vmLine.VDIName)" | Select InMaintenanceMode -ErrorAction Stop -ErrorVariable +CitrixError

                                          if($MaintenanceStatus -ne $true) 
                                          {

                                              try 
                                              {
                                                    #Changing the VM to maintenance mode
                                                    $Machine  = Get-BrokerMachine -AdminAddress $using:DDC -MachineName "$($using:DomainName)\$($using:vmLine.VDIName)" -ErrorAction Stop -ErrorVariable +CitrixError
                                                    Set-BrokerMachineMaintenanceMode -InputObject $Machine $true -ErrorAction SilentlyContinue -ErrorVariable +CitrixError
                                                    Start-Sleep -Seconds 20
                                                    $status = $machine | Select InMaintenanceMode

                                                    #Write-Output "$(Get-Date) - Machine $($using:vmLine.VDIName) set to maintenance mode"
                                                    Sleep 2                   
                     
                                                    if($status -ne $True)
                                                    {
                                            
                                                        try
                                                        {
                                                            #Shutting down the VM
                                                            New-BrokerHostingPowerAction -Action Shutdown -MachineName "$($using:DomainName)\$($using:vmLine.VDIName)" -ErrorAction SilentlyContinue -ErrorVariable +CitrixError
                                                            #Write-Output "$(Get-Date) - Machine $($using:vmLine.VDIName) turned off"
                                                        }
                                                        catch
                                                        {
                                                            $_.Exception.Message
                                                        }
                                                        
                            
                                                        Start-Sleep -Seconds 20

                                                        #Remove VM from desktop group
                                                        $desktopgroupname = Get-BrokerMachine -AdminAddress $using:DDC -MachineName *\$($using:vmLine.VDIName) | Select-Object DesktopGroupName 
                                                        $group = $desktopgroupname.DesktopGroupName
                                                        Remove-BrokerMachine -AdminAddress $using:DDC -MachineName "$($using:DomainName)\$($using:vmLine.VDIName)" -DesktopGroup $group -ErrorAction Stop -ErrorVariable +CitrixError
                                                        #Write-Output "$(Get-Date) - Machine $($using:vmLine.VDIName) removed from Desktop group"

                                                        Start-Sleep -Seconds 20

                                                        #Remove VM from catalog
                                                        Remove-BrokerMachine -AdminAddress $using:DDC -MachineName "$($using:DomainName)\$($using:vmLine.VDIName)" -ErrorAction Stop -ErrorVariable +CitrixError
                                                        #Write-Output "$(Get-Date) - Machine $($using:vmLine.VDIName) removed from catalog"

                                                        Start-Sleep -Seconds 300

                                                        try
                                                        {
                                                            Get-BrokerSession | Disconnect-BrokerSession -ErrorAction SilentlyContinue
                                                        }
                                                        catch
                                                        {
                                                            $_.Exception.Message
                                                        }

                                                        #Adding Citrix Snapin
                                                        Get-PSSnapin -Registered -Name citrix* -ErrorAction SilentlyContinue | Add-PSSnapin -ErrorAction Stop

                                                        Start-Sleep -Seconds 20

                                                        #Re validating the machine status from citrix
                                                        $Ctxstatus = Get-BrokerMachine -AdminAddress $using:DDC -MachineName "$($using:DomainName)\$($using:vmLine.VDIName)" -ErrorAction SilentlyContinue
                                                        if($Ctxstatus -eq $null)
                                                        {
                                                            $Flag_citrix = $true
                                                            Write-Output "$(Get-Date) -Revalidated: Machine $($using:vmLine.VDIName) removed from citrix"
                                                        }
                                                        else
                                                        {
                                                            $Flag_citrix = $false
                                                            Write-Output "$(Get-Date) -Revalidated: Machine $($using:vmLine.VDIName) removal failure"
                                                        }

                                                    }
                                                    else
                                                    {
                                                        #Write-Output "$(Get-Date) - ERROR: Machine $($using:vmLine.VDIName) is in Shutdown state"

                                                        #Remove VM from catalog
                                                        Remove-BrokerMachine -AdminAddress $using:DDC -MachineName "$($using:DomainName)\$($using:vmLine.VDIName)" -ErrorAction Stop -ErrorVariable +CitrixError
                                                        #Write-Output "$(Get-Date) - Machine $($using:vmLine.VDIName) removed from catalog"

                                                        Start-Sleep -Seconds 300

                                                        try
                                                        {
                                                            Get-BrokerSession | Disconnect-BrokerSession -ErrorAction SilentlyContinue
                                                        }
                                                        catch
                                                        {
                                                            $_.Exception.Message
                                                        }
                                                    
                                                        #Adding Citrix Snapin
                                                        Get-PSSnapin -Registered -Name citrix* -ErrorAction SilentlyContinue | Add-PSSnapin -ErrorAction Stop

                                                        Start-Sleep -Seconds 30

                                                        #Re validating the machine status from citrix
                                                        $Ctxstatus = Get-BrokerMachine -AdminAddress $using:DDC -MachineName "$($using:DomainName)\$($using:vmLine.VDIName)" -ErrorAction SilentlyContinue
                                                        if($Ctxstatus -eq $null)
                                                        {
                                                            $Flag_citrix = $true
                                                            Write-Output "$(Get-Date) -Revalidated: Machine $($using:vmLine.VDIName) removed from citrix"
                                                        }
                                                        else
                                                        {
                                                            $Flag_citrix = $false
                                                            Write-Output "$(Get-Date) -Revalidated: Machine $($using:vmLine.VDIName) removal failure"
                                                        }
                                                    }

                                                }
                                                catch
                                                {
                                                    Write-Output $_.Exception.Message
                                                    $Flag_citrix = $false
                                                }
                                          }
                                          else
                                          {
                                                Write-Output "$(Get-Date) - ERROR: Unable to get the maintenance status for machine $($using:vmLine.VDIName) skipping to next machine"
                                                $Flag_citrix = $false
                                    
                                          }
                                     }
                                     else
                                     {
                                            Write-Output "$(Get-Date) - ERROR: Unable to get the machine $($using:vmLine.VDIName) skipping to next machine"
                                            $Flag_citrix = $false
                                     }
                                }
                                catch
                                {
                                    $Flag_citrix = $false
                                    $_.Exception.Message
                                }

                            } #end of else if Single/Multiple



                     }

                     Write-Output $Flag_citrix

                } -ErrorAction Stop #end of invoke block ddc


                }
                catch
                {
                    $_.Exception.Message
                    $Out_log_1 += $_.Exception.Message
                    $Flag = $false
                }
                finally
                {
                    Write-Output "`nMachine removal from citrix please find the below logs:"
                    $Out_log_1 += "$(Get-Date) - INFO: Machine removal from citrix please find the below logs:"
                    
                    #Write-Output $outvar
                    $Out_log_1 += "$(Get-Date) - INFO: $($outvar)"

                    if($outvar -ne $null)
                    {
                        $val = (($outvar.Length) -1)
        
                        if($outvar[$val] -eq $true)
                        {
                            Write-Output "Citrix process success, flag is $($outvar[$val])"
                            $Out_log_1 += "$(Get-Date) - INFO: Citrix process success, flag is $($outvar[$val])"
                            $Flag = $true
                            $Properties.Citrix_Status = "Success"
                        }
                        else
                        {
                            Write-Output "Citrix process failure, flag is $($outvar[$val])"
                            $Out_log_1 += "$(Get-Date) - INFO: Citrix process failure, flag is $($outvar[$val])"
                            $Flag = $false
                            $Properties.Citrix_Status = "Failure"
							$Properties.Error_Citrix = "Exception occured while removing machine from citrix"
                        }
                    }
                    elseif($Flag -eq $false)
                    {
                        Write-Output "Error connecting to invoke block"
                        $Out_log_1 += "$(Get-Date) - INFO: Error connecting to invoke block"
                        $Flag = $false
                        $Properties.Error_Citrix = "Exception occured while removing machine from citrix"
                    }
                    
                    Write-Output "Final flag: $($Flag)"
                    $Out_log_1 += "Final flag: $($Flag)"
                }
        
                #endregion Citrix


                #Remove from VmWare and AD only if the vm is single assignment
                if($vmLine.Type -eq 'Multiple')
                {
                    Write-Output "This Machine $($vmLine.VDIName) is assigned to multiple users, VM & AD Removal not processed"
                    $Out_log_1 += "$(Get-Date) - INFO: This Machine $($vmLine.VDIName) is assigned to multiple users, VM & AD Removal not processed"
                    
                    $Properties.VMWare_Status = "Not Processed"
                    $Properties.AD_Status = "Not Processed"
                }
                elseif($vmLine.Type -eq 'Single')
                {
                    Write-Output "This Machine $($vmLine.VDIName) is assigned to single user, VM & AD Removal processing"
                    $Out_log_1 += "$(Get-Date) - INFO: This Machine $($vmLine.VDIName) is assigned to single user, VM & AD Removal processing"

                    #Removing VDI from VMware
                    removefromvmware

                    #Removing the machine from ad
                    removefromad
                }
                


                #Writing to csv file
                #$CurrentDate = (Get-date -Format dd-MM-yyyy-hh:mm:ss)
                #$newRow += New-Object PsObject -Property @{ VDIName = $vmLine.VDIName ; Status = $Flag; Date = $CurrentDate }
        
                #Disconnecting from vcenter
                Disconnect-VIServer -Server $VsphereServer -Confirm:$false -Force
                $connection = $null

                #Export data to csv file
                $Csv_Data = New-Object -TypeName psobject -Property $Properties -ErrorAction SilentlyContinue;
                $Csv_Data | Export-Csv -Path $CSV_ReportLocation -Append -Force -NoTypeInformation -ErrorAction SilentlyContinue;

            }#End of for each loop
        }
        catch [System.Exception]
        {
            Write-Output $_.Exception.Message
            $Out_log_1 += $_.Exception.Message
            $Flag = $false
        }
        finally
        {

            #$csv += $newRow
            #$csv | Export-Csv "D:\Wintel Tower\NT\VDI-Decomission\Code\Deprovisioned_VDI.csv" -Force
            #Write-Log "$(Get-Date) - Script execution completed"

            #Printing output of VDI Decommission script
            Write-Output $Flag
            
            
        }
    }
    else
    {
        Write-Output "VDI Decommission not performed, since flag is false"
        $Out_log_1 += "$(Get-Date) - INFO: VDI Decommission not performed, since query from citrix is false"
    }
     }
        else
        {
            Write-Output "VDI Decommission not performed, since flag is false"
        }

}
catch
{
    $_.Exception.Message
    $Out_log_1 += $_.Exception.Message
    $Flag = $false
}
finally
{
    Write-Output "Script execution status : $($Flag)"
    $Out_log_1 += "$(Get-Date) - INFO: Script execution status : $($Flag)"

    #$Out_log_1 | Out-File -FilePath $log_file_path -Append -Force

}


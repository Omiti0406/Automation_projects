
############################################################################################################################################

#author        : Omprakash Tiwari(omprakash.tiwari@wipro.com)
#version       : 1.0
#title         : PVS vDisk Patching
#Organization  : Wipro
#description   : This script will check the status of Pandora service and restart Services in Servers
############################################################################################################################################

[Parameter(Mandatory = $true)]$vDiskPath =
[Parameter(Mandatory = $true)]$vDiskPath_Temp =
[Parameter(Mandatory = $true)]$vDisk =
[Parameter(Mandatory = $true)]$vDiskNew =
[Parameter(Mandatory = $true)]$MaintVM =
[Parameter(Mandatory = $true)]$site =
[Parameter(Mandatory = $true)]$store =
[Parameter(Mandatory = $true)]$PvsServers =
[Parameter(Mandatory = $true)]$XenServerPool =
$vDisk = "$vDisk.VHD", "$vDisk.PVP"
$vDiskNew = "$vDiskNew.VHD", "$vDiskNew.PVP"
$Tries = 10
$TryDelay = 3 
$creds = Get-Credential
#Logs creation
Function Write-Logs {
    param($message)
    $date = Get-Date -Format ddMMyyyy
    $logfile = "LogFile_" + $date + ".txt"
    $logPath = "E:\Patching Automation\" + $logfile
    New-Item -ItemType File -Path $logPath
    Add-Content -Value "$message" -path $logPath   
}
function vDiskMapping {
    param (
        [Parameter(Mandatory = $true)] [string] $MaintVM,
        [Parameter(Mandatory = $true)] [string] $site,
        [Parameter(Mandatory = $true)] [string] $store,
        [Parameter(Mandatory = $true)] [string] $vDisk
    )
    Write-Output "-----$((Get-Date).ToString("dd/MM/yyyy HH:mm"))----- Mapping vDisk to the VM"
    Add-PvsDiskLocatorToDevice -SiteName $site -Store $store -DiskLocatorName  $vDisk -DeviceName $MaintVM -RemoveExisting
    Write-Output "-----$((Get-Date).ToString("dd/MM/yyyy HH:mm"))----- The vDisk $vDiskNew has been mapped to the VM."
    
}
try {
    #Creating a new version of the vDisk from existing one
    Write-Output "-----$((Get-Date).ToString("dd/MM/yyyy HH:mm"))----- Copying the vDisk from $vDiskPath to $vDiskPath_Temp "
    foreach ($vDsk in $vDisk) {
        Get-ChildItem -Path $vDiskPath -ErrorAction Stop | Where-Object { $_.FullName -match $vDsk } | Copy-Item -Destination $vDiskPath_Temp -Verbose
    }
    Write-Output "-----$((Get-Date).ToString("dd/MM/yyyy HH:mm"))----- Renaming the vDisk to $vDiskNew "
    foreach ($vDsk in $vDisk) {
        Get-ChildItem -Path $vDiskPath_Temp -ErrorAction Stop | Where-Object { $_.FullName -match $vDsk } | Rename-Item -NewName { $_.BaseName.Replace($_.BaseName, "$vDiskNew") + $_.extension } -Verbose
    }
    Write-Output "-----$((Get-Date).ToString("dd/MM/yyyy HH:mm"))----- Moving the $vDiskNew from $vDiskPath_Temp to $vDiskPath"
    foreach ($vDsk in $vDiskNew) {
        Get-ChildItem -Path $vDiskPath_Temp -ErrorAction Stop | Where-Object { $_.FullName -match $vDsk } | Move-Item -Destination $vDiskPath -ErrorAction Stop -Verbose
    }
    
    #install the modules
    if (Get-Module | Where-Object { $_.Name.Contains('Citrix.PVS.SnapIn.dll', 'XenServerPSModule') }) {
        Import-Module “C:\Program Files\Citrix\Provisioning Services Console\Citrix.PVS.SnapIn.dll”
        Import-Module XenServerPSModule
    }
    #Connecting with the PVS servers and XenServers
    $PVS_session = Set-PvsConnection -Server $PvsServer -port 54321 -ErrorAction Stop
    $XenSrvSession = connect-XenServer -server $XenServerPool -Credential $creds -ErrorAction Stop
    if ($PVS_session -or $XenSrvSession) 
    {
        Write-Logs -message "-----$((Get-Date).ToString("dd/MM/yyyy HH:mm"))----- Connecting to PVS servers and XenServer Pools."
        #importing the vDisk
        New-PvsDiskLocator -Name $vDiskNew -Store $store -ServerName $PvsServer -SiteName $site -Verbose
        #set vDisk Access mode to private
        Set-PvsDisk -Name $vDiskNew -Store $store -SiteName $site -WriteCacheType “0” -WriteCacheSize “512” -Verbose

        #Checking the Maintainence VM boot status
        $VM = Get-XenVM -Name $VMName
        Write-Output "-----$((Get-Date).ToString("dd/MM/yyyy HH:mm"))----- The Machine is on $($VM.power_state) state"

        if ($VM.power_state -eq 'Halted') {
            vDiskMapping -MaintVM $MaintVM -site $site -store $store -vDisk $vDiskNew
        }
        else {
            Write-Output "-----$((Get-Date).ToString("dd/MM/yyyy HH:mm"))----- Shutting down the Machine"
            Invoke-XenVM -Name $MaintVM -XenAction Shutdown -Verbose -ErrorAction Stop
            # To ensure that the VM is powered down
            $try = 1
            do {
                $VM = Get-XenVM -Name $VMName
                if ($VM.power_state -eq 'Halted') {
                    Write-Output "-----$((Get-Date).ToString("dd/MM/yyyy HH:mm"))----- The machine is turned Off"
                    vDiskMapping -MaintVM $MaintVM -site $site -store $store -vDisk $vDiskNew -Verbose
                    break
                }
                else {
                    Write-Output "$($Tries-$try) retries left. Sleeping for $TryDelay seconds."
                    $try++ 
                    Start-Sleep -Minute $TryDelay
                }
            } while ($try -le $Tries)

            if ($try -gt $Tries) {
                throw "-----$((Get-Date).ToString("dd/MM/yyyy HH:mm"))----- Shutdown of VM '$MaintVM' FAILED. Timed out."
            }
        }

        Invoke-XenVM -Name $MaintVM -XenAction Start -Verbose -ErrorAction Stop
        # To ensure the VM is booted up
        $try = 1
        do {
            $VM = Get-XenVM -Name $VMName
            if ($VM.power_state -eq 'Running') {
                Write-Output "-----$((Get-Date).ToString("dd/MM/yyyy HH:mm"))----- Machine $MaintVM has been started" | 
                break
            }
            else {
                Write-Output "$($Tries-$try) retries left. Sleeping for $TryDelay minutes."
                $try++ 
                Start-Sleep -Minute 3
            }
        } while ($try -le $Tries)

        #PSremoting to the Maintenance VM
        $session=Invoke-Command -ComputerName $MaintVM -Credential -ScriptBlock {
            try 
            {
                Write-Output "-----$((Get-Date).ToString("dd/MM/yyyy HH:mm"))----- Connected to VM $MaintVM"
                #Deleting bushido Registry Key
                Remove-Item -Path HKLM:\SOFTWARE\NodeSoftware -Force -Verbose

                #Checking for the Windows update services
                if ((Get-Service -Name "wuauserv" | Select-Object -Property Status) -eq "Stopped") {
                    Set-Service -Name "wuauserv" -Status Running -Verbose -ErrorAction Stop
                    Write-Output "-----$((Get-Date).ToString("dd/MM/yyyy HH:mm"))----- 'wuauserv' has been started successfully"
                }

                if (Get-Module | Where-Object { $_.Name.Contains("PSWindowsUpdate") }) 
                {
                    [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
                    Install-PackageProvider -Name NuGet -MinimumVersion 2.8.5.201 -Confirm:$false -Force
                    Register-PSRepository -Default -InstallationPolicy Trusted -Verbose
                    Install-Module -Name PSWindowsUpdate -ErrorAction Stop -Verbose
                }
                
                # Check for updates
                $updates = Get-WUList

                # Install any updates that are found
                foreach ($update in $updates) {
                    Install-WindowsUpdate -Update $update -AcceptAll -AutoReboot -Verbose  
                }

                # Output the result
                if ($updates.Count -eq 0) {
                    Write-Output "No updates were found."
                }
                else {
                    Write-Output "$($updates.Count) updates were installed."
                }
            }
            catch {
                Write-Logs -message "Error:- $($_.Exception.Message) `r`nwhile running command :- $(($_.InvocationInfo.line).trim()) at Line number:- $($_.InvocationInfo.ScriptlineNumber)" 
            }

        } -ErrorAction Stop 

        Invoke-XenVM -Name $MaintVM -XenAction Shutdown -ErrorAction Stop
        #Replicating vDisk to the PVS002 server 
        New-PvsDiskLocator -Name $vDiskNew -Store $store -ServerName $PvsServer[1] -SiteName $site 
        Set-PvsDisk -Name $vDiskNew -Store $store -SiteName $site -WriteCacheType “1” -WriteCacheSize “512”

    }
    
}

finally {
    Disconnect-XenServer -Session $XenSrvSession
    

}
catch {
    Write-Logs -message "Error:- $($_.Exception.Message) `r`nwhile running command :- $(($_.InvocationInfo.line).trim()) at Line number:- $($_.InvocationInfo.ScriptlineNumber)" 

}


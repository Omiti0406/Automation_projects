$logFileDate = Get-Date -Format yyyyMMdd-HHmmss
$logPath = "F:\temp\DAR_cleanup_log_$logFileDate.txt"
$Output = @()
New-Item -ItemType File -Path $logPath
Try {
    $inputCsv = Import-Csv "F:\inputData.csv"
    $uname = ""
    $pass = ""
    [array]$ServerNames = $inputCsv.hostname  #"sdcdaru004.ent.ad.ntrs.com"
    [array]$prod_srv = $inputCsv.prod_server
    [array]$input_Path = $inputCsv.path
    [string]$dest_path = $inputCsv.dest_path[0]
    $pwd = ConvertTo-SecureString $pass -AsPlainText -Force 
    $cred = New-Object System.Management.Automation.PSCredential -ArgumentList $uname, $pwd
    
    foreach ($ServerName in $ServerNames) { 
        if ($ServerName -ne "") {
            write-host "Execution started on " $ServerName
            $execute = Invoke-Command -ComputerName $ServerName -Credential $cred -ArgumentList $ServerName, $input_Path, $dest_path, $prod_srv -ScriptBlock {
                $Days = 3
                $BeforeSize = 0
                $BeforeCount = 0
                $AfterSize = 0
                $AfterCount = 0
                $prodServer = $using:prod_srv  
                $des_path = $using:dest_path 
                $LogDate = Get-Date -Format yyyyMMdd-HHmm
                $ci = $using:ServerName 
                $path = $using:input_Path 
                $logData = @()
                $temp = ""
                $logPath = "E:\DAR_server_Cleanup\logs\logFile_$LogDate.txt"
                #Start-Transcript -Path "E:\DAR_server_Cleanup\logs\logFile_$LogDate.txt"

                $logData += "PERFORMING CLEANUP TASK ON SERVER- $ci "
                # SIZE BEFORE PROCCESS EXECUTION 
                Foreach ($p in $path) {
                    $size = Get-ChildItem -Recurse -File -Path $p | Measure-Object -Property Length -Sum | Select-Object @{Name = "Size(MB)"; Expression = { ("{0:N2}" -f ($_.Sum / 1mb)) } } -ErrorAction SilentlyContinue
                    $BeforeSize += $($size.'Size(MB)')
                    $count = (Get-ChildItem -Path $p | Measure-Object).Count
                    $BeforeCount += $count
                }
                $logData += Write-Output "`n____________________________"
                $logData += Write-Output "`n Details before Execution  "
                $logData += Write-Output "`n____________________________"
                $logData += Write-Output "`n SIZE= $BeforeSize MB " 
                $logData += Write-Output "`n FILE COUNT= $BeforeCount `n`n"
                
                #Moving file to the given path
                if ($prodServer -contains $ci) {
                    
                    Foreach ($p in $path) {
                        $temp = $null
                        if ((Get-ChildItem $p -File -ErrorAction SilentlyContinue | Measure-Object).Count -eq 0) {
                            $logData += Write-Host "`n $p is Empty `n"
                        }
                        else {
                            $logData += "`n`n ######  BELOW FILES ARE DELETED ON THE PATH $P ###### `n"
                            $temp = Get-ChildItem -File -Path $p -ErrorAction SilentlyContinue | Where-Object { ($_.LastWriteTime -lt $(Get-Date).AddDays(-$Days)) }
                            $logData += $temp | % { "`n $($_.Name)" }
                            $temp | Move-Item -Destination $des_path -Force -Verbose -ErrorAction SilentlyContinue
                            $logData += Write-Host "Files has been moved to the given path successfully: " $des_path
                        }

                    }
                    #Permanent deletion of the mentioned file from backup folder after 15 days
                    $delDay = -7
                    $logData += "`n ###### BELOW FILES ARE DELETED ON THE PATH $des_path ###### `n"
                    $logData += "`n _____________________________________ `n"
                    if ((Get-ChildItem $des_path -File -ErrorAction SilentlyContinue | Measure-Object).Count -eq 0) {
                        $logData += Write-Host "`n $des_path is Empty"
                    }
                    else {
                        $temp = Get-ChildItem $des_path -File -Force -Verbose -ErrorAction SilentlyContinue | Where-Object { ($_.LastwriteTime -lt $(Get-Date).AddDays($delDay)) } 
                        $logData += $temp | % { "`n $($_.Name)" }
                        $temp | remove-item -Force -Verbose -ErrorAction SilentlyContinue 
                        $logData += Write-Host "Cleanup task completed on the given path" $des_path
                    }
                }
                #Delete the file and folders from the given path.
                else {
                    Foreach ($p in $path) {
                        if ((Get-ChildItem $p -File -ErrorAction SilentlyContinue | Measure-Object).Count -eq 0) {
                            $logData += Write-Host "`n $p is Empty"
                        }
                        else {
                            $logData += "`n`n ######  BELOW FILES ARE DELETED ON THE PATH $P ###### `n"
                            $temp = Get-ChildItem $p -File -Force -Verbose -ErrorAction SilentlyContinue | Where-Object { ($_.LastwriteTime -lt $(Get-Date).AddDays(-$Days)) } 
                            $logData += $temp | % { "`n $($_.Name)" }
                            $temp | remove-item -Force -Verbose -ErrorAction SilentlyContinue 
                            $logData += Write-Host "Cleanup task completed on the given path" $p
                        }
    
                    }
                }
        
                #SIZE AFTER PROCCESS EXECUTION
                Foreach ($p in $path) {
                    $size = Get-ChildItem -Path $p -Recurse -ErrorAction SilentlyContinue | Measure-Object -Property Length -Sum |
                    Select-Object @{Name = "Size(MB)"; Expression = { ("{0:N2}" -f ($_.Sum / 1mb)) } } -ErrorAction SilentlyContinue
                    $AfterSize += $($size.'Size(MB)')
                    $count = (Get-ChildItem -Path $p | Measure-Object).Count
                    $AfterCount += $count
                }
                $logData += Write-Output "`n____________________________"
                $logData += Write-Output "`n Details before Execution  "
                $logData += Write-Output "`n____________________________"
                $logData += Write-Output "`nSIZE= $AfterSize "
                $logData += Write-Output "`nFILE COUNT= $AfterCount `n`n"

        
                
                $logData | Out-File $logPath -Append 
                #Stop-Transcript
            } 
       
        }
    }
}
catch {
    $Output += Write-Output " Error Occurred  "
    $Output += "-----------------"
    $Output += $_.Exception.Message
    $Output | Out-File $logPath #-Force -Append -Confirm:$false
}

<#
.NOTES
===========================================================================
     
Created on        : 05/26/2024
Created by        : Mayur Matey
Last Reviewed By  : 
Organization      : Wipro
Filename          : Create Html Table and send mail
Version           : 1.0
===========================================================================
#>
try {
    $dir = '\\WPCHOLU01\Data\unregistered_vdi'# $scriptpath
    $inputCSV = import-csv -Path "$dir/Inputtest.csv"
    $SMTP = $inputCSV.SMTPServer
    $DLName = $inputCSV.CitrixDLName -split ";"
    $From = $inputCSV.From
    $html = @()
    $header = "
		<html>
		<head>
		<meta http-equiv='Content-Type' content='text/html; charset=iso-8859-1'>
		<title>Unregistered VDI Report</title>
		<STYLE TYPE='text/css'>
		<!--
		td {
			font-family: Cambria;
			font-size: 11px;
			border-top: 1px solid #999999;
			border-right: 1px solid #999999;
			border-bottom: 1px solid #999999;
			border-left: 1px solid #999999;
			padding-top: 0px;
			padding-right: 0px;
			padding-bottom: 0px;
			padding-left: 0px;
		}
		body {
			margin-left: 5px;
			margin-top: 5px;
			margin-right: 0px;
			margin-bottom: 10px;
			table {
			border: thin solid #000000;
		}
		-->
		</style>
		</head>
		<body>
		<table width='100%'>
		<tr style='background-color:#0000A0;'>
		<td colspan='2' height='25' align='center'>
		<font face='Cambria' color='White' size='5'><strong>Unregistered VDI Report on:   $(Get-Date)</strong></font>
		</td>
		</tr>
		</table>
    "
    $html += $header
    $reportName = "Unregistered_VDI_Report_$(Get-Date -Format "dd_MM_yyyy").html";
    $reportNameCsv = "Unregistered_VDI_Report_$(Get-Date -Format "dd_MM_yyyy").csv";
    $reportPath = "$dir\Unregistered_VDI_Reports_Case3\"
    $ApplicationReport = $reportPath + $reportName
    $ApplicationReportCsv = $reportPath + $reportNameCsv
    $redColor = "#FF5733";
    $GreenColor = "#008000"
    $Ddcs = @("US","UK")
    $csvdata = Import-Csv $ApplicationReportCsv -ErrorAction stop

if ($csvdata.count -eq 0) {
    $tableHeader = "<table width='100%'><tbody>
                    <tr style='background-color:$redColor;' >
                    <td align='center' ><font face='Cambria' style='background-color:White;'><b>No Unregistered Machine Found</b></font></td>
                    </tr>
                    "
    $html += $tableHeader
    exit
}

    foreach ($dc in $Ddcs) {
        
        $data = $csvdata|?{$_.DC -eq $dc}
        $count = $data.count
        
        $tableHeader1 = "
    <table width='100%'><tbody>
	<tr style='background-color:#F3E5AB;'>
    <td  align='Left'><font color=Black size=3><b>Unregistered VDI Count $dc : $count</b></font></td>
    </tr>
    </table>"

        $html +=  $tableHeader1
        if ($count -eq 0) {
            $tableHeader = "<table width='100%'><tbody>
                    <tr style='background-color:$redColor;' >
                    <td align='center' ><font face='Cambria' style='background-color:White;'><b>No Unregistered Machine Found</b></font></td>
                    </tr></tbody></table>
                    "
            $html += $tableHeader
            Continue
        }

        $tableHeader1 = "<table width='100%'><tbody>
	        <tr style='background-color:Skyblue;' >
            <td align='center' ><font face='Cambria' color='White'><b>Checked At </b></font></td>
	        <td align='center' ><font face='Cambria' color='White'><b>Machine Name </b></font></td>
            <td align='center' ><font face='Cambria' color='White'><b>Catalog Name</b></font></td>
            <td align='center' ><font face='Cambria' color='White'><b>Delivery Group Name</b></font></td>
            <td align='center' ><font face='Cambria' color='White'><b>Maintenance Mode</b></font></td>
            <td align='center' ><font face='Cambria' color='White'><b>Power State</b></font></td>
            <td align='center' ><font face='Cambria' color='White'><b>Registration State</b></font></td>
            <td align='center' ><font face='Cambria' color='White'><b>Restart Status</b></font></td>
	        </tr>"
        
        $html +=  $tableHeader1

        foreach ($dat in $data) {
            if ([string]::IsNullOrWhiteSpace($dat.error)) {
                if($dat.'Registration State' -eq "UnRegistered"){$bgColor1 = $redColor}else{$bgColor1=$GreenColor}
                if($dat.'Restart Status' -eq "Restarted Successfully"){$bgColor = $GreenColor}else{$bgColor=$redColor}
                $dataRow1 = "
                        <tr>
                        <td  align='center'>$($dat.'Checked at')</td>
                        <td  align='center'>$($dat.'Machine Name')</td>
                        <td  align='center'>$($dat.'Catalog Name')</td>
                        <td  align='center'>$($dat.'Delivery Group Name')</td>
                        <td  align='center'>$($dat.'Maintenance Mode')</td>
                        <td  align='center'>$($dat.'Power State')</td>
                        <td  align='center' style='background-color:$bgcolor1;'>$($dat.'Registration State')</td>
                        <td  align='center' style='background-color:$bgColor;'>$($dat.'Restart Status')</td>
                        </tr>"
                        $html += $dataRow1
            }
            elseif ($dat.Error -like "Error in executing the solution in*") {
                $dataRow1 = "
                        <tr>
                        <td  align='center'>$($dat.'Checked at')</td>
                        <td  align='center' style='background-color:$redColor;' colspan='7'>$($dat.Error)</td>
                        </tr>"
                        $html += $dataRow1
            
            }
            else {
                $dataRow1 = "
                        <tr>
                        <td  align='center'>$($dat.'Checked at')</td>
                        <td  align='center'>$($dat.'Machine Name')</td>
                        <td  align='center' style='background-color:$redColor;' colspan='6'>$($dat.Error)</td>
                        </tr>"
                $html += $dataRow1
            }

        }
        $html +=  "</tbody></table>"
    
    }
   $Footer = "</tbody></table> 
    <tr><td align=Center><font size=1><Center><br><br><b>Unregistered VDI Report</b> Developed on (c) <b> $($(Get-Date).Year) </b> and All Rights are Reserved to </b> <b><u> GIS, Automation Team -Wipro Technologies</b></u></Center></font></td></tr>"
    $html +=  $Footer
    $html +=  "</body></html>"
   $html |out-file $ApplicationReport -Confirm:$false -ErrorAction Stop -Force
   Send-MailMessage -Body $([String]$html) -BodyAsHtml -Attachments $ApplicationReport -SmtpServer $SMTP -From $From -To $DLName -Subject "Unregistered VDI Report" -ErrorAction stop
   write-host "Mail sent successfully"
}
Catch {
    "Error in executing the solution . $_"
} 


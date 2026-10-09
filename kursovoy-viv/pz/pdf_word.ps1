param([string]$Docx, [string]$Pdf, [int]$Limit = 120)
# Word: open the document and save it to PDF right away (the only sequence that ran without hidden dialogs).
# A Word process that hangs longer than $Limit seconds is stopped.
$job = Start-Job -ScriptBlock {
    param($Docx, $Pdf)
    $before = @(Get-Process WINWORD -ErrorAction SilentlyContinue | ForEach-Object { $_.Id })
    $w = New-Object -ComObject Word.Application
    $new = @(Get-Process WINWORD | Where-Object { $before -notcontains $_.Id } | ForEach-Object { $_.Id })
    'pid ' + ($new -join ',')
    $w.Visible = $false
    $w.DisplayAlerts = 0
    $w.Options.UpdateFieldsAtPrint = $false
    try {
        $d = $w.Documents.Open($Docx)
        $d.SaveAs2($Pdf, 17)
        'pdf ok'
        $d.Close([ref]0)
    }
    catch { 'ERROR ' + $_.Exception.Message }
    finally { $w.Quit([ref]0) }
} -ArgumentList $Docx, $Pdf
$ok = Wait-Job $job -Timeout $Limit
$out = @(Receive-Job $job)
$out
if (-not $ok) {
    'HUNG'
    Stop-Job $job
}
# the hidden Word started here sometimes stays alive after Quit: stop it (only the process this script started)
Start-Sleep -Seconds 2
$ids = ($out | Where-Object { $_ -like 'pid *' }) -replace 'pid ', ''
foreach ($i in ($ids -split ',')) {
    if ($i) { Get-Process -Id ([int]$i) -ErrorAction SilentlyContinue | Where-Object { $_.MainWindowTitle -eq '' } | Stop-Process -Force }
}
Remove-Job $job -Force

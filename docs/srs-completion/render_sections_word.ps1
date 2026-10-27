$ErrorActionPreference = 'Stop'
$documentPath = 'D:\capstone_project\docs\srs-completion\ProjectForge_Sections_4_to_6_1.docx'
$pdfPath = 'D:\capstone_project\docs\srs-completion\qa-sections\ProjectForge_Sections_4_to_6_1.pdf'
New-Item -ItemType Directory -Path (Split-Path $pdfPath) -Force | Out-Null
$reportWord = $null
$reportDocument = $null
try {
    $reportWord = New-Object -ComObject Word.Application
    $reportWord.Visible = $false
    $reportWord.DisplayAlerts = 0
    $reportWord.AutomationSecurity = 3
    $reportDocument = $reportWord.Documents.Open($documentPath, $false, $false)
    $reportDocument.Repaginate()
    $reportDocument.Fields.Update() | Out-Null
    $reportDocument.ExportAsFixedFormat($pdfPath, 17)
    $reportDocument.Save()
    Write-Output ('Pages: ' + $reportDocument.ComputeStatistics(2))
    Write-Output $pdfPath
} finally {
    if ($null -ne $reportDocument) { $reportDocument.Close(0) }
    if ($null -ne $reportWord) { $reportWord.Quit() }
}

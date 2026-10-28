$taskWord = $null
$taskDoc = $null
try {
    $taskWord = New-Object -ComObject Word.Application
    $taskWord.Visible = $false
    $taskWord.DisplayAlerts = 0
    $taskDoc = $taskWord.Documents.Open('C:\Users\siraj\Downloads\Mini project Phase 1 report SS - Times New Roman and Borders.docx', $false, $false)
    $taskDoc.Fields.Update() | Out-Null
    foreach ($taskToc in $taskDoc.TablesOfContents) { $taskToc.Update() }
    $taskDoc.Repaginate()
    foreach ($taskToc in $taskDoc.TablesOfContents) { $taskToc.UpdatePageNumbers() }
    $taskDoc.Save()
    $taskDoc.ExportAsFixedFormat('E:\AI_Trading\report_revision\borders.pdf', 17)
    Write-Output ('Pages: ' + $taskDoc.ComputeStatistics(2))
} finally {
    if ($taskDoc) { $taskDoc.Close(0) }
    if ($taskWord) { $taskWord.Quit() }
}

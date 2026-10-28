$taskWord = $null
try {
    $taskWord = New-Object -ComObject Word.Application
    $taskWord.Visible = $false
    $taskWord.DisplayAlerts = 0
    foreach ($taskSpec in @(
        @('C:\Users\siraj\Downloads\Mini project Phase 1 report.docx', 'E:\AI_Trading\report_revision\remove-source.pdf'),
        @('C:\Users\siraj\Downloads\Mini project Phase 1 report - No Borders or Page Numbers.docx', 'E:\AI_Trading\report_revision\removed.pdf')
    )) {
        $taskDoc = $null
        try {
            $taskDoc = $taskWord.Documents.Open($taskSpec[0], $false, $true)
            $taskDoc.Repaginate()
            $taskDoc.ExportAsFixedFormat($taskSpec[1], 17)
            Write-Output ($taskSpec[1] + ' Pages: ' + $taskDoc.ComputeStatistics(2))
        } finally {
            if ($taskDoc) { $taskDoc.Close(0) }
        }
    }
} finally {
    if ($taskWord) { $taskWord.Quit() }
}

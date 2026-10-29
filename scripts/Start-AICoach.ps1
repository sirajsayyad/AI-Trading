param([string]$Model = 'qwen3:4b-thinking')
$ErrorActionPreference = 'Stop'
$aiInstalledCommand = Get-Command ollama -ErrorAction SilentlyContinue
$aiPortablePath = Join-Path $env:LOCALAPPDATA 'AITrade\ollama\ollama.exe'
if ($aiInstalledCommand) {
    $aiExecutable = $aiInstalledCommand.Source
} elseif (Test-Path -LiteralPath $aiPortablePath) {
    $aiExecutable = $aiPortablePath
    $env:OLLAMA_MODELS = Join-Path $env:LOCALAPPDATA 'AITrade\models'
} else {
    throw 'Install Ollama from https://ollama.com/download/windows, then rerun this script.'
}
$env:OLLAMA_HOST = '127.0.0.1:11434'
try {
    $null = Invoke-RestMethod 'http://127.0.0.1:11434/api/tags' -TimeoutSec 3
} catch {
    $aiLogDirectory = Join-Path $env:LOCALAPPDATA 'AITrade\ollama'
    New-Item -ItemType Directory -Path $aiLogDirectory -Force | Out-Null
    Start-Process -FilePath $aiExecutable -ArgumentList 'serve' -WindowStyle Hidden `
        -RedirectStandardOutput (Join-Path $aiLogDirectory 'server.out.log') `
        -RedirectStandardError (Join-Path $aiLogDirectory 'server.err.log') | Out-Null
    $aiReady = $false
    for ($aiAttempt = 0; $aiAttempt -lt 20; $aiAttempt++) {
        Start-Sleep -Milliseconds 500
        try {
            $null = Invoke-RestMethod 'http://127.0.0.1:11434/api/tags' -TimeoutSec 2
            $aiReady = $true
            break
        } catch { }
    }
    if (-not $aiReady) { throw 'Ollama did not start. Check the local AITrade Ollama logs.' }
}
$aiInstalledModels = (Invoke-RestMethod 'http://127.0.0.1:11434/api/tags' -TimeoutSec 5).models
$aiExpectedModel = if ($Model.Contains(':')) { $Model } else { $Model + ':latest' }
if (-not ($aiInstalledModels | Where-Object { $_.name -eq $aiExpectedModel -or $_.model -eq $aiExpectedModel })) {
    & $aiExecutable pull $Model
    if ($LASTEXITCODE -ne 0) { throw 'Model download failed. Check connectivity and rerun to resume.' }
}
Write-Output "Local AI Coach model ready: $Model. If AITrade is already running, use Retry last question."

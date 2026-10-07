# Canh Ollama: port 11434 chet -> khoi dong lai "ollama serve" (headless, co env
# OLLAMA_MODELS + OLLAMA_CONTEXT_LENGTH). Chay tu Task Scheduler moi 5 phut.
# KHONG mo "ollama app.exe" - app do co auto-updater tu giet chinh no (bug da
# gap: update 0.35.1 giet server roi chet do, de lai Ollama tat nguyen).
$ErrorActionPreference = "SilentlyContinue"
try {
    $r = Invoke-WebRequest "http://127.0.0.1:11434/api/tags" -UseBasicParsing -TimeoutSec 8
    if ($r.StatusCode -eq 200) { exit 0 }
} catch {}

$env:OLLAMA_MODELS = "E:\Ollama\models"
$env:OLLAMA_CONTEXT_LENGTH = "16384"
$exe = "$env:LOCALAPPDATA\Programs\Ollama\ollama.exe"
if (-not (Test-Path $exe)) { exit 1 }
Start-Process -FilePath cmd -WindowStyle Hidden -ArgumentList '/c',
  "`"$exe`" serve >> `"E:\CLAUDECODE\H2O-JOYCE-OS\server\ollama.log`" 2>&1"

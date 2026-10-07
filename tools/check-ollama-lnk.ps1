$lnk = "$env:APPDATA\Microsoft\Windows\Start Menu\Programs\Startup\Ollama.lnk"
$ws = New-Object -ComObject WScript.Shell
if (Test-Path $lnk) {
    $s = $ws.CreateShortcut($lnk)
    "Target:  " + $s.TargetPath
    "Args:    " + $s.Arguments
    "WorkDir: " + $s.WorkingDirectory
    "Exists:  " + (Test-Path $s.TargetPath)
} else { "KHONG CO Ollama.lnk" }
"---"
"OLLAMA_MODELS env (user): " + [Environment]::GetEnvironmentVariable("OLLAMA_MODELS","User")
"OLLAMA_CONTEXT_LENGTH:    " + [Environment]::GetEnvironmentVariable("OLLAMA_CONTEXT_LENGTH","User")
"E:\Ollama\models exists:  " + (Test-Path "E:\Ollama\models")
"ollama.exe path exists:   " + (Test-Path "C:\Users\Admin\AppData\Local\Programs\Ollama\ollama.exe")
"ollama app.exe exists:    " + (Test-Path "C:\Users\Admin\AppData\Local\Programs\Ollama\ollama app.exe")

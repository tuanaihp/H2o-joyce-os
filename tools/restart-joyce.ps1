# Restart chi server Joyce (giu cloudflared + Ollama) - dung sau khi sua server/*.py
$procs = Get-CimInstance Win32_Process -Filter "Name='python.exe'" |
         Where-Object { $_.CommandLine -like '*server\main.py*' }
foreach ($p in $procs) { Stop-Process -Id $p.ProcessId -Force; "killed $($p.ProcessId)" }
Start-Sleep -Seconds 1
Start-Process -FilePath cmd -ArgumentList '/c','cd /d "E:\CLAUDECODE\H2O-JOYCE-OS" && .venv\Scripts\python.exe server\main.py >> server\joyce.log 2>&1' -WindowStyle Hidden
Start-Sleep -Seconds 8
try { (Invoke-WebRequest http://localhost:7777/health -UseBasicParsing -TimeoutSec 5).Content } catch { "health FAIL: $_" }

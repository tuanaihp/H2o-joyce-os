# Task "Joyce Ollama Watchdog": chay khi dang nhap roi lap lai moi 5 phut vo han.
# Neu port 11434 chet (app crash, updater giet, E: chua mount...) -> bat lai serve.
$act = New-ScheduledTaskAction -Execute "powershell.exe" `
  -Argument '-NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File "E:\CLAUDECODE\H2O-JOYCE-OS\tools\ollama-watchdog.ps1"'
$trg = New-ScheduledTaskTrigger -AtLogOn -User $env:USERNAME
# Trick: -AtLogOn khong nhan -RepetitionInterval, muon .Repetition tu trigger -Once.
$trg.Repetition = (New-ScheduledTaskTrigger -Once -At "00:00" `
  -RepetitionInterval (New-TimeSpan -Minutes 5)).Repetition
$set = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries `
  -DontStopIfGoingOnBatteries -StartWhenAvailable -ExecutionTimeLimit (New-TimeSpan -Minutes 2)
Register-ScheduledTask -TaskName "Joyce Ollama Watchdog" -Action $act `
  -Trigger $trg -Settings $set -Force -Description `
  "Tu khoi dong lai ollama serve neu port 11434 chet (5 phut/lan)" | Out-Null
$t = Get-ScheduledTask -TaskName "Joyce Ollama Watchdog"
"TASK: " + $t.State + " | repeat: " + $t.Triggers[0].Repetition.Interval

# Go Ollama.lnk khoi Startup: "ollama app.exe" mang auto-updater - no TU GIET
# server de update roi co the khong bat lai (da xay ra 05/10). ollama serve
# headless tu watchdog/vbs khong co updater nen khong tu chet.
$lnk = "$env:APPDATA\Microsoft\Windows\Start Menu\Programs\Startup\Ollama.lnk"
if (Test-Path $lnk) { Remove-Item $lnk -Force; "REMOVED Ollama.lnk" }

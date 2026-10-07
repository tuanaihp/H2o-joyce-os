# Tao scheduled task: dang nhap -> cho 5 phut -> chay start-joyce.vbs (an).
# Tre 5 phut de Windows khoi dong xong, mang len, Ollama khong dung RAM luc boot.
$root = "E:\CLAUDECODE\H2O-JOYCE-OS"
$act = New-ScheduledTaskAction -Execute "wscript.exe" `
       -Argument "`"$root\start-joyce.vbs`""
$trg = New-ScheduledTaskTrigger -AtLogOn -User $env:USERNAME
$trg.Delay = "PT5M"
$set = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries `
       -DontStopIfGoingOnBatteries -StartWhenAvailable
Register-ScheduledTask -TaskName "Joyce OS - Delayed Start" -Action $act `
       -Trigger $trg -Settings $set -Force -Description `
       "Khoi dong H2O Joyce OS sau 5 phut dang nhap" | Out-Null
Write-Output "TASK OK"

# Bo shortcut cu trong Startup (no chay ngay luc login, khong delay)
$lnk = "$env:APPDATA\Microsoft\Windows\Start Menu\Programs\Startup\JOYCE OS.lnk"
if (Test-Path $lnk) { Remove-Item $lnk -Force; Write-Output "REMOVED LNK" }

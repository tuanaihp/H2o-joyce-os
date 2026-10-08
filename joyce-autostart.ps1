# ============================================================
# JOYCE OS - tu khoi dong cung Windows (ban sao cua bin/joyce-autostart.sh ben Mac).
# Goi qua joyce-autostart.bat, dung goi truc tiep tru khi biet minh dang lam gi.
#
# Cach lam MOI (10/2026) - "RELAY", bo wscript ngu 5 phut:
#   Run key "JoyceOS"       -> joyce-boot.vbs chay TUC THI luc logon (khong ngu):
#                              tao one-shot task "JoyceOS-Boot" dung 5 phut nua roi
#                              thoat ngay. Do tre do Task Scheduler giu - khong con
#                              process an ngu de phan mem diet virus/360 giet cam.
#   Task "JoyceOS-Watchdog" -> cu 5 phut chay joyce-watchdog.vbs: may da len >= 5'
#                              ma server chet (va khong phai nguoi dung bam stop)
#                              thi tu song lai. Du phong luon cho duong Run key.
# Vi sao khong dung trigger ONLOGON: may nay (360) tra Access Denied cho moi task
# tao voi /sc onlogon, con /sc once va /sc minute thi qua. Khong can quyen admin.
# Cong tac "Tu bat Joyce" trong trang Cai dat goi cung logic nay trong main.py.
# ============================================================
param([string]$Action = "status")

$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$RunKey = "HKCU:\Software\Microsoft\Windows\CurrentVersion\Run"
$RunName = "JoyceOS"
$BootVbs = Join-Path $Root "joyce-boot.vbs"
$DogVbs = Join-Path $Root "joyce-watchdog.vbs"
$CmdBoot = 'wscript.exe //nologo "' + $BootVbs + '"'
$CmdDog = 'wscript.exe //nologo "' + $DogVbs + '"'

switch ($Action.ToLower()) {
  "install" {
    if (-not (Test-Path $BootVbs) -or -not (Test-Path (Join-Path $Root "start-joyce.vbs"))) {
      Write-Host "Khong thay joyce-boot.vbs / start-joyce.vbs canh script nay."
      exit 1
    }
    New-Item -Path $RunKey -Force | Out-Null
    Set-ItemProperty -Path $RunKey -Name $RunName -Value $CmdBoot
    & schtasks /create /tn "JoyceOS-Watchdog" /sc minute /mo 5 /rl limited /f /tr $CmdDog | Out-Null
    Write-Host "Da bat tu khoi dong (relay):"
    Write-Host "  Run key '$RunName' -> joyce-boot.vbs -> task JoyceOS-Boot (+5 phut) -> server"
    Write-Host "  + task 'JoyceOS-Watchdog' 5 phut/lan tu song lai neu server chet."
    Write-Host "Kiem tra: taskschd.msc, hoac trang Cai dat cua Joyce."
    Write-Host "Go bo: joyce-autostart.bat uninstall hoac cong tac trong trang Cai dat"
  }
  "uninstall" {
    Remove-ItemProperty -Path $RunKey -Name $RunName -ErrorAction SilentlyContinue
    & schtasks /delete /tn "JoyceOS-Boot" /f 2>$null | Out-Null
    & schtasks /delete /tn "JoyceOS-Watchdog" /f 2>$null | Out-Null
    Write-Host "Da tat tu khoi dong cung Windows (xoa Run key + 2 task lien quan)."
  }
  default {
    $reg = (Get-ItemProperty -Path $RunKey -Name $RunName -ErrorAction SilentlyContinue).$RunName
    if ($reg) {
      Write-Host "DANG bat tu khoi dong. Lenh: $reg"
      if ($reg -like "*start-joyce-delayed*") {
        Write-Host "  !! Day la co che CU (wscript ngu 5 phut, de bi diet virus giet cam)."
        Write-Host "     Chay 'joyce-autostart.bat install' de chuyen sang relay moi."
      }
      & schtasks /query /tn "JoyceOS-Watchdog" /fo list 2>$null | Select-String "Status|Next Run"
    } else {
      Write-Host "CHUA bat tu khoi dong. Bat bang: joyce-autostart.bat install"
      Write-Host "hoac cong tac 'Tu bat Joyce' trong trang Cai dat"
    }
  }
}

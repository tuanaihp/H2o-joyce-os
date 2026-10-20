# ============================================================
# JOYCE OS - tu khoi dong cung Windows (ban sao cua bin/joyce-autostart.sh ben Mac).
# Goi qua joyce-autostart.bat, dung goi truc tiep tru khi biet minh dang lam gi.
#
# Cach lam 1.3.25 - MOT task "JoyceOS-AutoStart", 5 phut/lan chay THANG
#   .venv\Scripts\pythonw.exe tools\joyce_boot.py   (khong cua so, khong .vbs)
# joyce_boot.py: may len >= 90 giay ma cong 7777 khong ai nghe (va nguoi dung khong bam
# stop-joyce) thi bat server + tunnel (gui link moi qua Telegram) + Ollama; server dang
# song thi chi canh tunnel va Ollama.
#
# Vi sao bo Run key -> joyce-boot.vbs -> JoyceOS-Boot / JoyceOS-Watchdog: 360 Total
# Security moi lan mo may TAT moi muc tu chay tro toi file .vbs (360ScanLog 20 + 21/10/2026).
# Task chay thang mot .exe thi 360 de yen. /sc minute tranh trigger luc dang nhap (may nay Access
# Denied). Khong can quyen admin. Cong tac "Tu bat Joyce" trong trang Cai dat goi cung logic
# nay trong main.py.
# ============================================================
param([string]$Action = "status")

$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$RunKey = "HKCU:\Software\Microsoft\Windows\CurrentVersion\Run"
$RunName = "JoyceOS"
$Task = "JoyceOS-AutoStart"
$Pyw = Join-Path $Root ".venv\Scripts\pythonw.exe"
$Boot = Join-Path $Root "tools\joyce_boot.py"
$Cmd = '"' + $Pyw + '" "' + $Boot + '"'

function Remove-Legacy {
  # Duong cu qua .vbs: Run key + 2 task. Don het de khong con duong nao 360 se tat ngam.
  Remove-ItemProperty -Path $RunKey -Name $RunName -ErrorAction SilentlyContinue
  & schtasks /delete /tn "JoyceOS-Boot" /f 2>$null | Out-Null
  & schtasks /delete /tn "JoyceOS-Watchdog" /f 2>$null | Out-Null
}

switch ($Action.ToLower()) {
  "install" {
    if (-not (Test-Path $Boot) -or -not (Test-Path $Pyw)) {
      Write-Host "Khong thay tools\joyce_boot.py hoac .venv\Scripts\pythonw.exe - chay setup.bat truoc."
      exit 1
    }
    Remove-Legacy
    & schtasks /create /tn $Task /sc minute /mo 5 /rl limited /f /tr $Cmd | Out-Null
    if ($LASTEXITCODE -ne 0) { Write-Host "Khong tao duoc task $Task."; exit 1 }
    Write-Host "Da bat tu khoi dong: task '$Task' 5 phut/lan -> pythonw tools\joyce_boot.py"
    Write-Host "  Mo may xong khoang 2-5 phut Joyce tu len + gui link moi qua Telegram."
    Write-Host "  Server chet giua ngay cung tu song lai. Nhat ky: server\watchdog.log"
    Write-Host "Go bo: joyce-autostart.bat uninstall hoac cong tac trong trang Cai dat"
  }
  "uninstall" {
    Remove-Legacy
    & schtasks /delete /tn $Task /f 2>$null | Out-Null
    Write-Host "Da tat tu khoi dong cung Windows (xoa task + Run key cu)."
  }
  default {
    & schtasks /query /tn $Task /fo list 2>$null | Out-Null
    if ($LASTEXITCODE -eq 0) {
      Write-Host "DANG bat tu khoi dong (task $Task)."
      & schtasks /query /tn $Task /v /fo list 2>$null | Select-String "Status|Last Run|Last Result|Next Run"
    } else {
      $reg = (Get-ItemProperty -Path $RunKey -Name $RunName -ErrorAction SilentlyContinue).$RunName
      if ($reg) { Write-Host "  !! Con co che CU qua .vbs (360 tat moi lan mo may). Chay 'joyce-autostart.bat install'." }
      Write-Host "CHUA bat tu khoi dong. Bat bang: joyce-autostart.bat install"
      Write-Host "hoac cong tac 'Tu bat Joyce' trong trang Cai dat"
    }
  }
}

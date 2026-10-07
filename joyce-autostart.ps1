# ============================================================
# JOYCE OS - tu khoi dong cung Windows (ban sao cua bin/joyce-autostart.sh ben Mac).
# Goi qua joyce-autostart.bat, dung goi truc tiep tru khi biet minh dang lam gi.
#
# Cach lam: ghi/xoa Run key HKCU "JoyceOS" - CUNG entry voi cong tac "Tu bat Joyce"
# trong trang Cai dat, nen bat o dau thi tat o dau cung duoc, khong the co hai
# co che chay song song. Lenh tro vao start-joyce-delayed.vbs: NGU 5 PHUT sau
# dang nhap roi moi goi start-joyce.vbs, de Windows/Ollama app khoi dong xong
# truoc (tranh tranh CPU luc logon). Server chay NEN, khong bat trinh duyet.
# Muon mo dashboard thi double-click "JOYCE OS.bat".
# ============================================================
param([string]$Action = "status")

$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$RunKey = "HKCU:\Software\Microsoft\Windows\CurrentVersion\Run"
$Name = "JoyceOS"
$Vbs = Join-Path $Root "start-joyce-delayed.vbs"
$Cmd = 'wscript.exe //nologo "' + $Vbs + '"'

switch ($Action.ToLower()) {
  "install" {
    if (-not (Test-Path $Vbs)) {
      Write-Host "Khong thay start-joyce-delayed.vbs canh script nay - dat joyce-autostart.ps1 o goc thu muc Joyce."
      exit 1
    }
    New-ItemProperty -Path $RunKey -Name $Name -Value $Cmd -PropertyType String -Force | Out-Null
    Write-Host "Da bat tu khoi dong cung Windows (tre 5 phut sau dang nhap)."
    Write-Host "Run key: $RunKey\$Name"
    Write-Host "Go bo: joyce-autostart.bat uninstall hoac cong tac trong trang Cai dat"
  }
  "uninstall" {
    Remove-ItemProperty -Path $RunKey -Name $Name -ErrorAction SilentlyContinue
    Write-Host "Da tat tu khoi dong cung Windows."
  }
  default {
    $cur = (Get-ItemProperty -Path $RunKey -Name $Name -ErrorAction SilentlyContinue).$Name
    if ($cur) {
      Write-Host "DANG bat tu khoi dong (Run key: $cur)"
    } else {
      Write-Host "CHUA bat tu khoi dong. Bat bang: joyce-autostart.bat install hoac cong tac trong trang Cai dat"
    }
  }
}

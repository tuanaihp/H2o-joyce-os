' ============================================
'  Joyce OS - WATCHDOG. Chay moi 5 phut qua Scheduled Task "JoyceOS-Watchdog".
'
'  Ba vai tro:
'   1) Du phong khoi dong: neu Relay (joyce-boot.vbs -> task JoyceOS-Boot) bi
'      giat, tick dau tien sau khi may da len >= 5 phut se tu goi server.
'   2) Tu song lai: server chet giua ngay ma khong phai do nguoi dung bam
'      stop-joyce.bat (khong co cu server\.joyce-paused) -> goi lai ngay.
'   3) Khong canh giac ao: uptime < 5 phut thi im, de cho cua Relay; nguoi dung
'      stop tay thi im vinh vien cho toi khi start-joyce chay lai.
'  An, khong cua so, tu ket thuc. Task bi xoa khi tat autostart.
' ============================================
On Error Resume Next

Set fso = CreateObject("Scripting.FileSystemObject")
root = fso.GetParentFolderName(WScript.ScriptFullName)

' Nguoi dung bam stop-joyce.bat -> co cu pause -> watchdog im, khong tu song lai.
If fso.FileExists(root & "\server\.joyce-paused") Then WScript.Quit

' May moi len < 5 phut: cua Relay (JoyceOS-Boot) se chay, watchdog nhung lao.
Set wmi = GetObject("winmgmts:\\.\root\cimv2")
Set os = wmi.ExecQuery("Select LastBootUpTime from Win32_OperatingSystem")
For Each o In os
  boot = o.LastBootUpTime
Next
If Not IsEmpty(boot) Then
  If DateDiff("s", WMIDateToDate(boot), Now) < 300 Then WScript.Quit
End If

' Port 7777 co ai nghe khong? (cau tra loi nao cung tinh la song, ke ca 401)
alive = False
Set http = CreateObject("MSXML2.ServerXMLHTTP.6.0")
http.setTimeouts 2000, 2000, 2000, 2000
http.Open "GET", "http://127.0.0.1:7777/", False
http.Send
If Err.Number = 0 Then alive = True
Err.Clear
On Error GoTo 0

' Server song: khong can dung day lai, chi xem tunnel co chet rieng khong roi thoat.
' LUU Y: truoc day o day co "If alive Then WScript.Quit" dat NGAY TREN khoi "If alive Then"
' ben duoi, nen ca nhanh va tunnel la code chet - khong lan nao chay. Gio gop lam mot.
If alive Then
  On Error Resume Next
  Set fso0 = CreateObject("Scripting.FileSystemObject")
  ' Chu co the TAT tunnel co chu dich (tools\tunnel-off.flag). Khong co kiem tra nay thi
  ' nguoi tu tay giet cloudflared de ngung phoi may ra Internet se bi watchdog bat lai o
  ' chu ky sau, kem mot link public moi gui thang qua Telegram.
  If Not fso0.FileExists(root & "\tools\tunnel-off.flag") Then
    Set sh0 = CreateObject("WScript.Shell")
    ' Loc theo CommandLine chua :7777 - cloudflared cua app khac (H2O Video Studio
    ' tunnel :5170) chay song song se bi tasklist/IMAGENAME nhan lam la tunnel Joyce,
    ' khien tunnel_notify khong bao gio duoc goi de mo tunnel moi.
    Dim cfJoyce : cfJoyce = False
    For Each cf In wmi.ExecQuery("Select CommandLine from Win32_Process where Name='cloudflared.exe'")
      If InStr(cf.CommandLine, "7777") > 0 Then cfJoyce = True
    Next
    If Not cfJoyce Then
      sh0.Run """" & root & "\.venv\Scripts\python.exe"" """ & root & "\tools\tunnel_notify.py""", 0, False
    End If
  End If

  ' Ollama: server song nhung nao local chet giua ngay (autostart hong, AV giet,
  ' updater tu tat ma khong bat lai) -> bat lai. Khong ngu gi nen khong so bi AV
  ' diet nhu vong cho cua start-joyce. Process nao ten co "ollama" thi khong
  ' spawn chong - de tick sau kiem lai.
  ollamaUp = False
  http.setTimeouts 1500, 1500, 1500, 1500
  http.Open "GET", "http://127.0.0.1:11434/api/tags", False
  http.Send
  ' VBScript "And" khong short-circuit: doc http.Status khi request loi se throw,
  ' nen phai long If - khong duoc gop dieu kien.
  If Err.Number = 0 Then
    If http.Status = 200 Then ollamaUp = True
  End If
  Err.Clear
  If Not ollamaUp Then
    Set sh2 = CreateObject("WScript.Shell")
    Dim oAll : oAll = sh2.Exec("cmd /c tasklist /NH").StdOut.ReadAll
    Dim oExe : oExe = sh2.ExpandEnvironmentStrings("%LOCALAPPDATA%") & "\Programs\Ollama\ollama.exe"
    If InStr(LCase(oAll), "ollama") = 0 And fso0.FileExists(oExe) Then
      sh2.Run "cmd /c set ""OLLAMA_MODELS=E:\Ollama\models"" && set ""OLLAMA_CONTEXT_LENGTH=16384"" && """ & oExe & """ serve >> """ & root & "\server\ollama.log"" 2>&1", 0, False
      Set olg = fso.OpenTextFile(root & "\server\watchdog.log", 8, True)
      olg.WriteLine Now & " ollama chet -> da spawn lai serve"
      olg.Close
    End If
  End If

  WScript.Quit
End If

' Server chet -> song lai. Ghi mot dong vao watchdog.log de con vet chan duoc.
CreateObject("WScript.Shell").Run _
  "wscript.exe //nologo """ & root & "\start-joyce.vbs""", 0, False
On Error Resume Next
Set lg = fso.OpenTextFile(root & "\server\watchdog.log", 8, True)
lg.WriteLine Now & " server chet -> da goi start-joyce.vbs"
lg.Close


Function WMIDateToDate(d)
  WMIDateToDate = DateSerial(Left(d,4), Mid(d,5,2), Mid(d,7,2)) + _
                  TimeSerial(Mid(d,9,2), Mid(d,11,2), Mid(d,13,2))
End Function

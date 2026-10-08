' ============================================
'  Joyce OS - BOOT RELAY. Chay tuc thi luc logon qua Run key, KHONG ngu.
'
'  May nay (360/Malwarebytes) diet cac process an ngu dai - start-joyce-delayed.vbs
'  ngu 300s tung bi giet cam giua chung nen Joyce khong bao gio toi. Cach moi:
'  script nay chi tao mot one-shot Scheduled Task "JoyceOS-Boot" dung 5 phut nua
'  roi THOAT NGAY. Do tre do Task Scheduler giu, khong con gi de giet.
'  Lo lech qua nua dem (khoi dong 23:5x): bo qua, JoyceOS-Watchdog 5 phut/lan lo.
' ============================================
On Error Resume Next

Set fso = CreateObject("Scripting.FileSystemObject")
root = fso.GetParentFolderName(WScript.ScriptFullName)

t = DateAdd("n", 5, Now)
If DateValue(t) = DateValue(Now) Then
  hh = Right("0" & Hour(t), 2)
  mm = Right("0" & Minute(t), 2)
  cmd = "schtasks /create /tn JoyceOS-Boot /sc once /st " & hh & ":" & mm & _
        " /f /tr ""wscript.exe //nologo \""" & root & "\start-joyce.vbs\"""""
  CreateObject("WScript.Shell").Run "cmd /c " & cmd, 0, True
End If

WScript.Quit

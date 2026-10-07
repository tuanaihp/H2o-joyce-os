' ============================================
'  Joyce OS - tu khoi dong TRE 5 PHUT sau khi dang nhap Windows.
'  Shortcut trong thu muc Startup tro vao file nay (khong phai start-joyce.vbs
'  truc tiep). Ly do cho 5 phut: ngay sau logon Windows/Ollama app/OneDrive
'  dang khoi dong ram ro - server bat dau luc nay de bi dung do CPU/disk.
'  wscript ngu la mot tien trinh an, khong cua so, khong ton gi.
'  Go bo autostart: joyce-autostart.bat uninstall
' ============================================
WScript.Sleep 300000

Set fso = CreateObject("Scripting.FileSystemObject")
root = fso.GetParentFolderName(WScript.ScriptFullName)
CreateObject("WScript.Shell").Run "wscript.exe //nologo """ & root & "\start-joyce.vbs""", 0, False

' ============================================
'  Joyce OS - chạy NGẦM (ẩn cửa sổ cmd)
'  Double-click file này (hoặc start-joyce.bat) để bật server ở chế độ nền.
'  Log ghi vào server\joyce.log. Dừng bằng stop-joyce.bat.
' ============================================
Set fso = CreateObject("Scripting.FileSystemObject")
root = fso.GetParentFolderName(WScript.ScriptFullName)
Set sh = CreateObject("WScript.Shell")

' QUAN TRỌNG: mọi lệnh đều cd /d vào root trước - KHÔNG dựa vào working directory
' kế thừa (CurrentDirectory không đáng tin tuỳ nơi gọi, từng làm bước stop chết
' im lặng với lỗi 'stop-joyce.bat is not recognized').

' Tắt instance cũ trước (ẩn, chờ xong). Output ghi server\stop-last.log để soi khi trục trặc.
' GỌI BẰNG ĐƯỜNG DẪN TUYỆT ĐỐI: tên trần "stop-joyce.bat" bị cmd từ chối tìm theo thư mục
' hiện tại khi môi trường có NoDefaultCurrentDirectoryInExePath (đường dẫn có "\" thì không sao).
sh.Run "cmd /c cd /d """ & root & """ && call """ & root & "\stop-joyce.bat"" > server\stop-last.log 2>&1", 0, True

' Gỡ cờ "người dùng chủ động dừng" - start-joyce chạy nghĩa là Joyce được phép sống,
' watchdog (joyce-watchdog.vbs) nhìn cờ này để biết có được tự khởi động lại không.
If fso.FileExists(root & "\server\.joyce-paused") Then fso.DeleteFile root & "\server\.joyce-paused", True

' Chạy server ẩn (0 = cửa sổ ẩn, False = không chờ). Output -> server\joyce.log
sh.Run "cmd /c cd /d """ & root & """ && .venv\Scripts\python.exe server\main.py > server\joyce.log 2>&1", 0, False

' Tunnel Cloudflare + gửi link mới vào Telegram (ẩn, tự thoát sau khi gửi).
' tools\tunnel_notify.py tự bỏ qua nếu cloudflared đã chạy sẵn.
sh.Run "cmd /c cd /d """ & root & """ && .venv\Scripts\python.exe tools\tunnel_notify.py > tools\tunnel-notify.log 2>&1", 0, False

' Ollama local (não miễn phí chạy offline): probe NHANH đúng 1 lần rồi spawn luôn,
' KHÔNG vòng ngủ dài - wscript ngủ 40s trong cửa sổ logon đúng dáng dropper nên 360
' từng diệt script giữa chừng (chết im, không tới được nhánh fallback). Nếu lượt
' này sót thì Watchdog 5 phút/tick sẽ bật lại - lớp đó không ngủ nên an toàn.
Dim http, ollamaUp, ollamaExe, olOut, olLog
ollamaUp = False
Set http = CreateObject("MSXML2.ServerXMLHTTP.6.0")
On Error Resume Next
http.setTimeouts 1500, 1500, 1500, 1500
http.Open "GET", "http://127.0.0.1:11434/api/tags", False
http.Send
If http.Status = 200 Then ollamaUp = True
On Error GoTo 0
If Not ollamaUp Then
  ollamaExe = sh.ExpandEnvironmentStrings("%LOCALAPPDATA%") & "\Programs\Ollama\ollama.exe"
  ' Tray app đang khởi động dở thì có process mà chưa mở port - đừng spawn chồng
  ' serve (hai cái đấu port), Watchdog sẽ lo nếu nó chết hẳn.
  olOut = sh.Exec("cmd /c tasklist /NH").StdOut.ReadAll
  Set olLog = fso.OpenTextFile(root & "\server\ollama.log", 8, True)
  If InStr(LCase(olOut), "ollama") = 0 And fso.FileExists(ollamaExe) Then
    olLog.WriteLine Now & " [boot] port 11434 chưa lên, không thấy process ollama -> spawn serve"
    ' Kho model ở E:\Ollama\models (ổ C: ít chỗ) + ngữ cảnh 16K (mặc định 4096 thì
    ' prompt Joyce bị 400). Set env trong lệnh, không dựa vào biến user.
    sh.Run "cmd /c set ""OLLAMA_MODELS=E:\Ollama\models"" && set ""OLLAMA_CONTEXT_LENGTH=16384"" && """ & ollamaExe & """ serve >> """ & root & "\server\ollama.log"" 2>&1", 0, False
  Else
    olLog.WriteLine Now & " [boot] port 11434 chưa lên nhưng ollama đang chạy -> để watchdog lo"
  End If
  olLog.Close
End If

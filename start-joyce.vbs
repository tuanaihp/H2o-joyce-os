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

' Ollama local (não miễn phí chạy offline): chỉ bật "ollama serve" khi port 11434
' chưa có ai nghe - nếu anh đã mở Ollama app bằng tay thì bước này tự bỏ qua,
' không spawn chồng process.
' Thử tới 4 lần, cách nhau 10s: lúc vừa logon Ollama app (Startup) có thể đang
' khởi động dở, hoặc auto-updater của nó vừa tự tắt app để nâng cấp (đã gặp:
' bản 0.34.2 -> 0.35.1 tự giết server lúc 5:50 sáng rồi không bật lại). Nếu
' hết 4 lần vẫn chết thì tự mở "ollama serve" headless, sau đó chờ nó lên tới
' 60s để Joyce kết nối ngay được thay vì phải bấm Kết nối tay.
Dim http, ollamaUp, ollamaTry
ollamaUp = False
Set http = CreateObject("MSXML2.ServerXMLHTTP.6.0")
For ollamaTry = 1 To 4
  On Error Resume Next
  http.setTimeouts 1500, 1500, 1500, 1500
  http.Open "GET", "http://127.0.0.1:11434/api/tags", False
  http.Send
  If http.Status = 200 Then ollamaUp = True
  On Error GoTo 0
  If ollamaUp Then Exit For
  WScript.Sleep 10000
Next
If Not ollamaUp Then
  ollamaExe = sh.ExpandEnvironmentStrings("%LOCALAPPDATA%") & "\Programs\Ollama\ollama.exe"
  ' Kho model đặt ở E:\Ollama\models (ổ C: ít chỗ) + khung ngữ cảnh 16K
  ' (mặc định Ollama chỉ 4096 - prompt Joyce vài nghìn token sẽ bị 400
  ' "exceeds the available context size"). Set env ngay trong lệnh để không
  ' phụ thuộc biến môi trường user có kịp nạp hay không.
  sh.Run "cmd /c set ""OLLAMA_MODELS=E:\Ollama\models"" && set ""OLLAMA_CONTEXT_LENGTH=16384"" && """ & ollamaExe & """ serve > """ & root & "\server\ollama.log"" 2>&1", 0, False
  ' Chờ serve sẵn sàng (tối đa 60s) trước khi script kết thúc.
  For ollamaTry = 1 To 12
    WScript.Sleep 5000
    On Error Resume Next
    http.setTimeouts 1500, 1500, 1500, 1500
    http.Open "GET", "http://127.0.0.1:11434/api/tags", False
    http.Send
    If http.Status = 200 Then ollamaUp = True
    On Error GoTo 0
    If ollamaUp Then Exit For
  Next
End If

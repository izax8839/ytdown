@echo off
chcp 65001 > nul
cd /d "%~dp0"

set "TARGET_DIR=%~dp0"
set "APP_PY=%TARGET_DIR%app.py"
set "ICON_FILE=%TARGET_DIR%icon.ico"
set "PYTHONW=%LOCALAPPDATA%\Programs\Python\Python312\pythonw.exe"
set "SHORTCUT=%USERPROFILE%\Desktop\YouTube 미디어 다운로더.lnk"

powershell -ExecutionPolicy Bypass -Command "$ws = New-Object -ComObject WScript.Shell; $s = $ws.CreateShortcut('%SHORTCUT%'); $s.TargetPath = '%PYTHONW%'; $s.Arguments = '`\"%APP_PY%`\"'; $s.WorkingDirectory = '%TARGET_DIR%'; $s.IconLocation = '%ICON_FILE%,0'; $s.Description = 'YouTube 영상 및 고음질 음원 다운로더'; $s.Save(); Write-Host '========================================================'; Write-Host ' 바탕화면에 [YouTube 미디어 다운로더] 바로가기 생성 완료!'; Write-Host '========================================================'"

pause

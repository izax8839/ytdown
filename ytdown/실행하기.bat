@echo off
chcp 65001 > nul
cd /d "%~dp0"

:: PATH 설정 갱신
set "PATH=%LOCALAPPDATA%\Programs\Python\Python312;%LOCALAPPDATA%\Programs\Python\Python312\Scripts;%LOCALAPPDATA%\Microsoft\WinGet\Packages\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-9.0.2-full_build\bin;%PATH%"

:: pythonw가 있으면 콘솔 창 없이 실행, 없으면 일반 python으로 실행
where pythonw >nul 2>&1
if %errorlevel% equ 0 (
    start "" pythonw app.py
) else (
    start "" python app.py
)

exit /b 0

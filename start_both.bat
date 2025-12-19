@echo off
REM start_both.bat - Windows version
REM Captures screen frames and logs keystrokes simultaneously

REM Clean up old files
if exist frame_timestamps_ms.txt del /q frame_timestamps_ms.txt
if exist keylog.csv del /q keylog.csv
if exist frames_with_keys.csv del /q frames_with_keys.csv

REM Clean up frames directory
if exist frames (
    del /q frames\*.png 2>nul
) else (
    mkdir frames
)

REM Start ffmpeg in background using PowerShell Start-Process (handles file output better than start /B)
REM Using gdigrab to capture desktop (Windows equivalent of avfoundation)
REM Use wrapper batch file to avoid PowerShell argument parsing issues
powershell -Command "$proc = Start-Process -FilePath '%~dp0start_ffmpeg.bat' -WorkingDirectory '%~dp0' -WindowStyle Hidden -PassThru; $proc.Id | Out-File -FilePath '%~dp0ffmpeg_pid.txt' -Encoding ASCII"

REM Run keylogger (foreground, blocks until ESC/Ctrl-C)
REM Use venv Python if it exists, otherwise use system Python
if exist venv\Scripts\python.exe (
    venv\Scripts\python.exe keylogger\keylogger.py
) else (
    python keylogger\keylogger.py
)

REM Cleanup: Kill ffmpeg process when keylogger exits
echo Stopping ffmpeg...
REM Kill ffmpeg directly (not the wrapper batch file)
taskkill /F /IM ffmpeg.exe >nul 2>&1
if exist ffmpeg_pid.txt del ffmpeg_pid.txt
echo Recording stopped.
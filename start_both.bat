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
powershell -Command "$proc = Start-Process -FilePath 'ffmpeg' -ArgumentList '-f','gdigrab','-framerate','30','-i','desktop','-filter_complex','settb=1/1000,setpts=RTCTIME/1000,mpdecimate,split=2[frames][ts];[frames]format=rgb24,scale=1920:1200[out]','-map','[out]','-vsync','passthrough','-frame_pts','0','frames\frame_%06d.png','-map','[ts]','-f','mkvtimestamp_v2','-y','frame_timestamps_ms.txt' -WindowStyle Hidden -PassThru; $proc.Id | Out-File -FilePath 'ffmpeg_pid.txt' -Encoding ASCII"

REM Run keylogger (foreground, blocks until ESC/Ctrl-C)
REM Use venv Python if it exists, otherwise use system Python
if exist venv\Scripts\python.exe (
    venv\Scripts\python.exe keylogger\keylogger.py
) else (
    python keylogger\keylogger.py
)

REM Cleanup: Kill ffmpeg process when keylogger exits
echo Stopping ffmpeg...
if exist ffmpeg_pid.txt (
    for /f %%i in (ffmpeg_pid.txt) do taskkill /F /PID %%i >nul 2>&1
    del ffmpeg_pid.txt
) else (
    taskkill /F /IM ffmpeg.exe >nul 2>&1
)
echo Recording stopped.
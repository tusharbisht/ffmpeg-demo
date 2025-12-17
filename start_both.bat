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

REM Start ffmpeg in background to capture Windows desktop and extract frames/timestamps
REM Using gdigrab to capture desktop (Windows equivalent of avfoundation)
start /B ffmpeg -f gdigrab -framerate 30 -i desktop -filter_complex "settb=1/1000,setpts=RTCTIME/1000,mpdecimate,split=2[frames][ts];[frames]format=rgb24,scale=1920:1200[out]" -map "[out]" -vsync passthrough -frame_pts 0 frames\frame_%%06d.png -map "[ts]" -f mkvtimestamp_v2 -y frame_timestamps_ms.txt 2> ffmpeg_error.log

REM Run keylogger (foreground, blocks until ESC/Ctrl-C)
REM Use venv Python if it exists, otherwise use system Python
if exist venv\Scripts\python.exe (
    venv\Scripts\python.exe keylogger\keylogger.py
) else (
    python keylogger\keylogger.py
)

REM Cleanup: Kill ffmpeg process when keylogger exits
echo Stopping ffmpeg...
taskkill /F /IM ffmpeg.exe >nul 2>&1
echo Recording stopped.
@echo off
REM Wrapper script for ffmpeg to run in background
REM Ensure we're in the correct directory
cd /d "%~dp0"
REM Run ffmpeg - convert RTCTIME (nanoseconds) to milliseconds
REM RTCTIME/1000000 gives milliseconds
ffmpeg -f gdigrab -framerate 30 -i desktop -filter_complex "settb=1/1000,setpts=RTCTIME/1000,mpdecimate=hi=64*12:lo=64*5:frac=0.33,split=2[frames][ts];[frames]format=yuv420p,scale=1920:1200[out]" -map "[out]" -vsync passthrough -frame_pts 0 -q:v 2 -threads 2 frames\frame_%%06d.jpg -map "[ts]" -f mkvtimestamp_v2 -flush_packets 1 -y frame_timestamps_ms.txt


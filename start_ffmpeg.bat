@echo off
REM Wrapper script for ffmpeg to run in background
ffmpeg -f gdigrab -framerate 30 -i desktop -filter_complex "settb=1/1000,setpts=RTCTIME/1000,mpdecimate,split=2[frames][ts];[frames]format=rgb24,scale=1920:1200[out]" -map "[out]" -vsync passthrough -frame_pts 0 frames\frame_%%06d.png -map "[ts]" -f mkvtimestamp_v2 -y frame_timestamps_ms.txt


@echo off
echo Test 4: Testing RTCTIME function...
ffmpeg -f gdigrab -framerate 30 -i desktop -t 3 -filter_complex "settb=1/1000,setpts=RTCTIME/1000,showinfo" -f null - -v verbose 2>&1 | findstr /C:"pts_time" /C:"RTCTIME" > rtctime_debug.txt

echo Check rtctime_debug.txt for RTCTIME values
pause
@echo off
echo Test 2: Checking [ts] stream output...
ffmpeg -f gdigrab -framerate 30 -i desktop -t 3 -filter_complex "settb=1/1000,setpts=RTCTIME/1000,mpdecimate,split=2[frames][ts];[frames]format=rgb24,scale=1920:1200[out]" -map "[ts]" -f null - -v verbose 2>&1 | findstr /C:"frame=" /C:"pts=" /C:"time=" > ts_stream_debug.txt

echo Check ts_stream_debug.txt for [ts] stream data
pause
@echo off
echo Testing ffmpeg timestamp output...
echo.

REM Test 1: Check if [ts] stream produces any output
echo Test 1: Running ffmpeg for 5 seconds to capture timestamps...
ffmpeg -f gdigrab -framerate 30 -i desktop -t 5 -filter_complex "settb=1/1000,setpts=RTCTIME/1000,mpdecimate,split=2[frames][ts];[frames]format=rgb24,scale=1920:1200[out]" -map "[out]" -vsync passthrough -frame_pts 0 test_frames\frame_%%06d.png -map "[ts]" -f mkvtimestamp_v2 test_timestamps.txt -v verbose 2> ffmpeg_debug.log

echo.
echo Check test_timestamps.txt for content
echo Check ffmpeg_debug.log for errors
pause
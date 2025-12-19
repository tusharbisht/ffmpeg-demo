@echo off
echo Test 3: Running ffmpeg in foreground (not background)...
ffmpeg -f gdigrab -framerate 30 -i desktop -t 5 -filter_complex "settb=1/1000,setpts=RTCTIME/1000,mpdecimate,split=2[frames][ts];[frames]format=rgb24,scale=1920:1200[out]" -map "[out]" -vsync passthrough -frame_pts 0 test_frames\frame_%%06d.png -map "[ts]" -f mkvtimestamp_v2 test_timestamps_foreground.txt

echo.
echo Check if test_timestamps_foreground.txt has content (foreground run)
pause
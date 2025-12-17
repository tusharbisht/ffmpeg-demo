!bash

rm frame_timestamps_ms.txt
rm keylog.csv
rm -y frames/*
rm -y frames_with_keys.csv
ffmpeg -f avfoundation -framerate 30 -i "1:none" -filter_complex "settb=1/1000,setpts=RTCTIME/1000,mpdecimate,split=2[frames][ts];[frames]format=rgb24,scale=1920:1200[out]" -map "[out]" -vsync passthrough -frame_pts 0 frames/frame_%06d.png -map "[ts]" -f mkvtimestamp_v2 frame_timestamps_ms.txt &

python3 keylogger/keylogger.py

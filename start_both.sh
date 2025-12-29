!bash

rm frame_timestamps_ms.txt
rm keylog.csv
rm -y frames/*
rm -y frames_with_keys.csv
ffmpeg -f avfoundation -framerate 30 -use_wallclock_as_timestamps 1 -i "1:none" -filter_complex "settb=1/1000,setpts=PTS*1000,split=2[frames][ts];[frames]format=yuv420p,scale=1920:1200[out]" -map "[out]" -vsync passthrough -frame_pts 0 -q:v 2 -threads 2 frames/frame_%06d.jpg -map "[ts]" -f mkvtimestamp_v2 frame_timestamps_ms.txt &

python3 keylogger/keylogger.py

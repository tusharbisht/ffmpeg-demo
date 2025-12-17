#!/usr/bin/env python3
# keylogger.py
# Records key events to keylog.csv with microsecond timestamps.
# Stop by pressing ESC (or Ctrl-C).

from pynput import keyboard
import time
import csv
import sys
import os

OUT = "keylog.csv"

def now_us():
    return time.time_ns() // 1000  # microseconds

# Header if file doesn't exist
if not os.path.exists(OUT):
    with open(OUT, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["ts_us","event","key","window"])

def on_press(key):
    try:
        kname = key.char
    except AttributeError:
        kname = str(key)
    ts = now_us()
    with open(OUT, "a", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([ts, "down", kname, ""])
    # Optional: stop on ESC
    if key == keyboard.Key.esc:
        print("ESC pressed — stopping.")
        return False

def on_release(key):
    try:
        kname = key.char
    except AttributeError:
        kname = str(key)
    ts = now_us()
    with open(OUT, "a", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([ts, "up", kname, ""])

if __name__ == "__main__":
    print("Starting keylogger. Press ESC to stop.")
    with keyboard.Listener(on_press=on_press, on_release=on_release) as listener:
        try:
            listener.join()
        except KeyboardInterrupt:
            print("Interrupted, exiting.")
            sys.exit(0)


#!/usr/bin/env python3
# keylogger.py
# Records key events to keylog.csv with 13-digit millisecond timestamps.
# Stop by pressing ESC (or Ctrl-C).

from pynput import keyboard
import time
import csv
import sys
import os

OUT = "keylog.csv"

def now_ms_13digits():
    """Return timestamp as milliseconds (13 digits for current epoch time)."""
    ms = time.time_ns() // 1_000_000  # nanoseconds to milliseconds
    return ms  # milliseconds since epoch (13 digits currently)

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
    ts = now_ms_13digits()
    with open(OUT, "a", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([ts, "down", kname, ""])
    # Optional: stop on ESC
    if key == keyboard.Key.esc:
        response = input("ESC pressed. Stop keylogger? (Y/n): ").strip().upper()
        if response in ("Y", "YES", ""):
            print("Stopping keylogger...")
            return False
        else:
            print("Continuing keylogger...")
            return True

def on_release(key):
    try:
        kname = key.char
    except AttributeError:
        kname = str(key)
    ts = now_ms_13digits()
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


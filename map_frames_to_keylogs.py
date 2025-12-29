#!/usr/bin/env python3
"""
Map recorded frames to their timestamps and nearby key events.

Usage:
  python3 map_frames_to_keylogs.py \
    --frames-dir frames \
    --timestamps frame_timestamps_ms.txt \
    --keylog keylog.csv \
    --window-ms 20 \
    --output frames_with_keys.csv
"""

import argparse
import csv
import glob
import os
from typing import List, Tuple


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Pair frames with timestamps and nearby key events."
    )
    parser.add_argument("--frames-dir", default="frames", help="Directory with frame JPEGs.")
    parser.add_argument(
        "--timestamps",
        default="frame_timestamps_ms.txt",
        help="ffmpeg mkvtimestamp_v2 output.",
    )
    parser.add_argument(
        "--keylog",
        default="keylogger/keylog.csv",
        help="CSV from keylogger.py.",
    )
    parser.add_argument(
        "--event-filter",
        choices=["down", "up", "both"],
        default="down",
        help="Which key events to consider for mapping (default: down).",
    )
    parser.add_argument(
        "--window-ms",
        type=float,
        default=20.0,
        help="Half-width window (ms). Used for window mode or max distance in nearest mode.",
    )
    parser.add_argument(
        "--output",
        default="frames_with_keys.csv",
        help="Output CSV mapping frames to events.",
    )
    parser.add_argument(
        "--mode",
        choices=["window", "nearest"],
        default="window",
        help=(
            "window: collect all events within +/- window-ms; "
            "nearest: pick the single closest event within window-ms."
        ),
    )
    parser.add_argument(
        "--exclusive-events",
        action="store_true",
        help=(
            "Consume events so each keylog entry maps to at most one frame. "
            "In window mode the first (earliest) frame whose window contains "
            "an event will claim it; in nearest mode the first frame that picks "
            "it as nearest consumes it."
        ),
    )
    parser.add_argument(
        "--ocr-csv",
        help=(
            "Optional OCR CSV (from validate_ocr_mapping.py) to do keylog→frame "
            "matching by typed-character deltas."
        ),
    )
    parser.add_argument(
        "--ocr-output",
        default="frames_to_keylog_via_ocr.csv",
        help="Output CSV when using --ocr-csv matching.",
    )
    return parser.parse_args()


def normalize_ts_to_us(raw: int) -> int:
    """Heuristically normalize a timestamp to microseconds."""
    if raw < 1_000_000_000_000:  # likely seconds
        return raw * 1_000_000
    if raw < 1_000_000_000_000_000:  # likely milliseconds
        return raw * 1_000
    return raw  # already microseconds


def load_frame_timestamps(path: str) -> List[int]:
    """Return list of timestamps in microseconds, skipping header lines."""
    ts_us: List[int] = []
    with open(path, "r") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            ts_us.append(normalize_ts_to_us(int(line)))
    return ts_us


def load_keylog(path: str, event_filter: str) -> List[Tuple[int, str, str]]:
    events: List[Tuple[int, str, str]] = []
    allowed = {"down", "up"} if event_filter == "both" else {event_filter}
    with open(path, newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            try:
                ts = int(row["ts_us"])
            except (KeyError, ValueError):
                continue
            etype = row.get("event", "")
            if etype not in allowed:
                continue
            events.append((ts, etype, row.get("key", "")))
    return events


def load_ocr_csv(path: str) -> dict:
    """
    Load OCR CSV produced by validate_ocr_mapping.py.
    Returns map of frame_file -> ocr_text string.
    """
    ocr_map = {}
    with open(path, newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            frame_file = row.get("frame_file")
            if not frame_file:
                continue
            ocr_raw = row.get("ocr_text", "")
            # restore newlines that were escaped as "\n" in the CSV
            ocr_map[frame_file] = ocr_raw.replace("\\n", "\n")
    return ocr_map


def newest_appended_char(prev_text: str, curr_text: str) -> str:
    """
    Compare last non-empty lines; return first newly appended char (lowercased)
    or "" if none.
    """
    def last_line(text: str) -> str:
        for l in reversed(text.splitlines()):
            if l.strip():
                return l
        return ""

    prev = last_line(prev_text)
    curr = last_line(curr_text)
    # find common prefix length
    prefix_len = 0
    for a, b in zip(prev, curr):
        if a == b:
            prefix_len += 1
        else:
            break
    appended = curr[prefix_len:]
    return appended[0].lower() if appended else ""


def chars_newly_appeared(prev_text: str, curr_text: str) -> List[str]:
    """
    Return list of characters that appear in curr_text but not in prev_text.
    Uses last non-empty line for comparison.
    """
    def last_line(text: str) -> str:
        for l in reversed(text.splitlines()):
            if l.strip():
                return l
        return ""
    
    prev = last_line(prev_text).lower()
    curr = last_line(curr_text).lower()
    
    # Count characters in each
    from collections import Counter
    prev_counts = Counter(prev)
    curr_counts = Counter(curr)
    
    # Find characters that increased in count
    newly_appeared = []
    for char, count in curr_counts.items():
        if char.isalnum() or char in ".,@":  # printable chars we care about
            if count > prev_counts.get(char, 0):
                # This char appeared or increased - add it once per increase
                increase = count - prev_counts.get(char, 0)
                newly_appeared.extend([char] * increase)
    
    return newly_appeared


def map_keylogs_with_ocr(
    frame_files: List[str],
    frame_ts_us: List[int],
    key_events: List[Tuple[int, str, str]],
    ocr_map: dict,
    output_path: str,
) -> None:
    """
    For each printable keylog event, find the earliest subsequent frame
    whose OCR shows that character newly appended (vs previous frame).
    Continue from last iteration position.
    """
    rows = []
    prev_ocr = ""
    # Build list of frames with their OCR texts for delta comparison
    frame_ocrs: List[Tuple[str, str]] = []  # (frame_file, ocr_text)
    for f in frame_files:
        frame_name = os.path.basename(f)
        ocr_text = ocr_map.get(frame_name, "")
        frame_ocrs.append((frame_name, ocr_text))
    
    frame_idx = 0
    n_ts = len(frame_ts_us)
    matched_keys = 0
    
    for ts_us, etype, key in key_events:
        if not key or len(key) != 1:
            continue
        k = key.lower()
        found = False
        # Search from current frame_idx position (continue from last iteration)
        search_idx = frame_idx
        
        while search_idx < len(frame_ocrs):
            frame_name, curr_ocr = frame_ocrs[search_idx]
            prev_ocr = frame_ocrs[search_idx - 1][1] if search_idx > 0 else ""
            
            # Check if character k newly appeared (wasn't in previous frame)
            # Use FULL OCR text (not just last line) for comparison
            prev_text = prev_ocr.lower()
            curr_text = curr_ocr.lower()
            
            # Character must be in current text but NOT in previous text
            if k in curr_text and k not in prev_text:
                # Guard against mismatch between number of frames and timestamps.
                ts_idx = search_idx if search_idx < n_ts else n_ts - 1
                ts_ms = frame_ts_us[ts_idx] / 1000.0
                diff_ms = ts_ms - (ts_us / 1000.0)
                rows.append(
                    [
                        frame_name,
                        key,
                        f"{ts_ms:.3f}",
                        f"{ts_us/1000.0:.3f}",
                        f"{diff_ms:.3f}",
                    ]
                )
                frame_idx = search_idx + 1  # Advance to next frame for next key search
                found = True
                matched_keys += 1
                break
            search_idx += 1
        # If not found, frame_idx stays where it was - next key will search from same position
        # But if we've exhausted all frames, we can't match any more keys
        if not found and search_idx >= len(frame_ocrs):
            # No more frames available - can't match remaining keys
            break
    
    print(f"OCR-based mapping: matched {matched_keys} out of {len([k for _, _, k in key_events if k and len(k) == 1])} printable keys")

    with open(output_path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(
            ["frame_file", "keylog_char", "frame_ts_ms", "keylog_ts_ms", "diff_ms"]
        )
        writer.writerows(rows)


def collect_events_for_frame(
    ts_us: int, events: List[Tuple[int, str, str]], half_window_us: float
) -> str:
    start = ts_us - half_window_us
    end = ts_us + half_window_us
    nearby = [
        f"{e_ts}:{etype}:{ekey}"
        for (e_ts, etype, ekey) in events
        if start <= e_ts <= end
    ]
    return ";".join(nearby)


def collect_events_for_frame_exclusive(
    ts_us: int, events: List[Tuple[int, str, str]], half_window_us: float
) -> str:
    """
    Like collect_events_for_frame but also CONSUMES matched events from the list.
    Because frames are processed in chronological order and we always remove
    matched events, each key event is assigned to the earliest frame whose
    +/- window includes it.
    """
    start = ts_us - half_window_us
    end = ts_us + half_window_us
    remaining: List[Tuple[int, str, str]] = []
    chosen = None
    for e_ts, etype, ekey in events:
        if chosen is None and start <= e_ts <= end:
            # First event in window wins for this frame.
            chosen = (e_ts, etype, ekey)
            # Do not add back to remaining -> consumed
        else:
            remaining.append((e_ts, etype, ekey))

    # Mutate original list in place so caller sees consumed events removed
    events[:] = remaining
    if chosen is None:
        return ""
    e_ts, etype, ekey = chosen
    return f"{e_ts}:{etype}:{ekey}"


def find_nearest_event(
    ts_us: int, events: List[Tuple[int, str, str]], max_distance_us: float
) -> Tuple[str, int]:
    """Return best event string and its index; empty string and -1 if none within distance."""
    best_idx = -1
    best_delta = max_distance_us + 1
    for idx, (e_ts, etype, ekey) in enumerate(events):
        delta = abs(e_ts - ts_us)
        if delta <= max_distance_us and delta < best_delta:
            best_delta = delta
            best_idx = idx
    if best_idx == -1:
        return "", -1
    e_ts, etype, ekey = events[best_idx]
    return f"{e_ts}:{etype}:{ekey}", best_idx


def main() -> None:
    args = parse_args()

    frame_files = sorted(glob.glob(os.path.join(args.frames_dir, "frame_*.jpg")))
    frame_ts_us = load_frame_timestamps(args.timestamps)

    if len(frame_files) != len(frame_ts_us):
        print(
            f"Warning: frame count ({len(frame_files)}) "
            f"!= timestamp count ({len(frame_ts_us)})."
        )

    key_events = load_keylog(args.keylog, args.event_filter)
    half_window_us = args.window_ms * 1000.0
    # Sort once so nearest search is deterministic; simple linear search is fine for small logs.
    key_events.sort(key=lambda x: x[0])

    # OCR-based mapping path
    if args.ocr_csv:
        ocr_map = load_ocr_csv(args.ocr_csv)
        map_keylogs_with_ocr(frame_files, frame_ts_us, key_events, ocr_map, args.ocr_output)
        print(f"Wrote OCR-based mapping to {args.ocr_output}")
        return

    with open(args.output, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["frame_file", "ts_ms", "ts_us", "key_events"])
        for idx, frame in enumerate(frame_files):
            # Guard against mismatched lengths: reuse last timestamp if needed.
            ts_us = frame_ts_us[idx] if idx < len(frame_ts_us) else frame_ts_us[-1]
            ts_ms = ts_us / 1000.0
            if args.mode == "window":
                if args.exclusive_events:
                    events_str = collect_events_for_frame_exclusive(
                        ts_us, key_events, half_window_us
                    )
                else:
                    events_str = collect_events_for_frame(
                        ts_us, key_events, half_window_us
                    )
            else:
                events_str, ev_idx = find_nearest_event(ts_us, key_events, half_window_us)
                if args.exclusive_events and ev_idx != -1:
                    key_events.pop(ev_idx)
            writer.writerow([os.path.basename(frame), f"{ts_ms:.3f}", ts_us, events_str])

    print(f"Wrote mapping to {args.output}")


if __name__ == "__main__":
    main()


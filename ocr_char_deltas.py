#!/usr/bin/env python3
"""
Scan frames, run OCR, and report which characters are newly appearing
compared to the previous frame's OCR text.

Usage:
  python3 ocr_char_deltas.py \
    --frames-dir frames \
    --output ocr_char_deltas.csv \
    --lang eng
"""

import argparse
import csv
import glob
import os
import string
from collections import Counter
from typing import List, Tuple, Optional

from PIL import Image
import pytesseract

PRINTABLE = set(string.ascii_letters + string.digits + string.punctuation + " ")


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="OCR per frame and detect newly appearing chars.")
    p.add_argument("--frames-dir", default="frames", help="Directory with frame_XXXXX.png images.")
    p.add_argument("--output", default="ocr_char_deltas.csv", help="Output CSV.")
    p.add_argument("--lang", default="eng", help="Tesseract language (default: eng).")
    p.add_argument(
        "--crop",
        help="Optional crop: x1,y1,x2,y2 (pixels) to focus on typed region.",
    )
    p.add_argument(
        "--threshold",
        type=int,
        help="Optional 0-255 luminance threshold; pixels above become white before OCR.",
    )
    return p.parse_args()


def parse_crop(crop_str: Optional[str]) -> Optional[Tuple[int, int, int, int]]:
    if not crop_str:
        return None
    parts = [int(p) for p in crop_str.split(",")]
    if len(parts) != 4:
        raise ValueError("crop must be x1,y1,x2,y2")
    return tuple(parts)  # type: ignore[return-value]


def apply_threshold(img: Image.Image, threshold: Optional[int]) -> Image.Image:
    if threshold is None:
        return img
    gray = img.convert("L")
    bw = gray.point(lambda p: 0 if p < threshold else 255, "1")
    return bw.convert("RGB")


def run_ocr(image_path: str, lang: str, crop_box, threshold: Optional[int]) -> str:
    img = Image.open(image_path)
    gray = img.convert("L")
    threshold = 100
    bw = gray.point(lambda p: 0 if p < threshold else 255, "1")
    img = bw.convert("RGB")
    if crop_box:
        img = img.crop(crop_box)
    config = (
        "--oem 3 --psm 7 "
        "-c tessedit_char_whitelist=abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789@._ "
        "-c load_system_dawg=0 -c load_freq_dawg=0"
    )
    return pytesseract.image_to_string(img, lang=lang, config=config)    


def newly_appeared_chars(prev: str, curr: str) -> List[str]:
    prev = prev.lower()
    curr = curr.lower()
    prev_counts = Counter(c for c in prev if c in PRINTABLE)
    curr_counts = Counter(c for c in curr if c in PRINTABLE)
    new_chars: List[str] = []
    for ch, cnt in curr_counts.items():
        inc = cnt - prev_counts.get(ch, 0)
        if inc > 0:
            new_chars.extend([ch] * inc)
    return new_chars


def main() -> None:
    args = parse_args()
    crop_box = parse_crop(args.crop)
    frames = sorted(glob.glob(os.path.join(args.frames_dir, "frame_*.png")))
    prev_text = ""

    with open(args.output, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["frame_file", "new_chars", "ocr_text"])

        for i, frame in enumerate(frames):
            text = run_ocr(frame, args.lang, crop_box, args.threshold)
            new_chars = newly_appeared_chars(prev_text, text)
            w.writerow([os.path.basename(frame), "".join(new_chars), text.replace("\n", "\\n")])
            prev_text = text

    print(f"Wrote OCR char deltas for {len(frames)} frames to {args.output}")


if __name__ == "__main__":
    main()
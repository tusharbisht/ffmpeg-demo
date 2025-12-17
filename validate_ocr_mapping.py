#!/usr/bin/env python3
"""
Validate frame↔keylog mapping using basic OCR.

Requires:
  - Pillow  (pip install pillow)
  - pytesseract  (pip install pytesseract)
  - Tesseract installed on the system (brew install tesseract on macOS).

Usage example:
  python3 validate_ocr_mapping.py \
    --frames-dir frames \
    --mapping-csv frames_with_keys.csv \
    --output-csv ocr_validation.csv
"""

import argparse
import csv
import os
import string
from collections import Counter
from typing import List, Tuple

from PIL import Image
import pytesseract


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run OCR on frames and compare text to mapped key events."
    )
    parser.add_argument(
        "--frames-dir",
        default="frames",
        help="Directory that contains frame_XXXXX.png images.",
    )
    parser.add_argument(
        "--mapping-csv",
        default="frames_with_keys.csv",
        help="CSV produced by map_frames_to_keylogs.py.",
    )
    parser.add_argument(
        "--output-csv",
        default="ocr_validation.csv",
        help="Where to write OCR vs keylog comparison.",
    )
    parser.add_argument(
        "--lang",
        default="eng",
        help="OCR language code for Tesseract (default: eng).",
    )
    parser.add_argument(
        "--crop",
        help="Optional crop in pixels: x1,y1,x2,y2. Limits OCR to typed region.",
    )
    parser.add_argument(
        "--threshold",
        type=int,
        help="Optional 0-255 luminance threshold; pixels above become white before OCR.",
    )
    return parser.parse_args()


PRINTABLE_KEYS = set(string.ascii_letters + string.digits + string.punctuation + " ")


def extract_expected_keys(key_events_field: str) -> List[str]:
    """
    Parse the key_events field (e.g. 'ts:down:a;ts:up:a') and
    return a list of printable key characters in order.
    """
    if not key_events_field:
        return []
    expected: List[str] = []
    for part in key_events_field.split(";"):
        if not part:
            continue
        # Format: ts:event:key
        pieces = part.split(":")
        if len(pieces) < 3:
            continue
        key = pieces[-1]
        # Skip special keys like "Key.shift"
        if len(key) == 1 and key in PRINTABLE_KEYS:
            expected.append(key)
    return expected


def parse_crop(crop_str: str):
    if not crop_str:
        return None
    try:
        parts = [int(p) for p in crop_str.split(",")]
        if len(parts) != 4:
            return None
        x1, y1, x2, y2 = parts
        return (x1, y1, x2, y2)
    except Exception:
        return None


def apply_threshold(img: Image.Image, threshold: int) -> Image.Image:
    if threshold is None:
        return img
    gray = img.convert("L")
    bw = gray.point(lambda p: 0 if p < threshold else 255, "1")
    return bw.convert("RGB")


def run_ocr(image_path: str, lang: str, crop_box, threshold: int) -> str:
    img = Image.open(image_path)
    if crop_box:
        img = img.crop(crop_box)
    img = apply_threshold(img, threshold)
    text = pytesseract.image_to_string(img, lang=lang)
    return text


def main() -> None:
    args = parse_args()
    crop_box = parse_crop(args.crop)
    threshold = args.threshold

    with open(args.mapping_csv, newline="") as f_in, open(
        args.output_csv, "w", newline=""
    ) as f_out:
        reader = csv.DictReader(f_in)
        fieldnames = [
            "frame_file",
            "ts_ms",
            "key_events",
            "expected_keys",
            "ocr_text",
            "all_expected_in_ocr",
            "missing_keys",
            "expected_len",
            "ocr_len",
            "delta_pass",
        ]
        writer = csv.DictWriter(f_out, fieldnames=fieldnames)
        writer.writeheader()

        total = 0
        with_expected = 0
        matches = 0
        mismatches = 0
        prev_counts: Counter[str] = Counter()
        prev_last_counts: Counter[str] = Counter()

        for row in reader:
            total += 1
            frame_file = row["frame_file"]
            ts_ms = row.get("ts_ms", "")
            key_events = row.get("key_events", "")
            expected_keys = extract_expected_keys(key_events)
            if expected_keys:
                with_expected += 1

            img_path = os.path.join(args.frames_dir, frame_file)
            if not os.path.exists(img_path):
                ocr_text = ""
                missing = expected_keys
                all_in = False if expected_keys else True
            else:
                ocr_text = run_ocr(img_path, args.lang, crop_box, threshold)
                ocr_lower = ocr_text.lower()
                lines = ocr_lower.splitlines()
                last_line = ""
                for l in reversed(lines):
                    if l.strip():
                        last_line = l
                        break
                last_counts = Counter(last_line)
                curr_counts = Counter(ocr_lower)
                # delta check: each expected char count must increase vs previous frame
                # AND its count must increase in the last non-empty line
                missing = []
                for k in expected_keys:
                    kc = k.lower()
                    total_delta = curr_counts.get(kc, 0) - prev_counts.get(kc, 0)
                    last_delta = last_counts.get(kc, 0) - prev_last_counts.get(kc, 0)
                    if total_delta <= 0 or last_delta <= 0:
                        missing.append(k)
                all_in = len(missing) == 0
                prev_counts = curr_counts
                prev_last_counts = last_counts

            if expected_keys:
                if all_in:
                    matches += 1
                    # Verbose log for every successful match with keylog
                    print(
                        f"[MATCH] {frame_file} ts_ms={ts_ms} "
                        f"expected='{''.join(expected_keys)}' (delta pass)"
                    )
                else:
                    mismatches += 1
                    print(
                        f"[MISMATCH] {frame_file} ts_ms={ts_ms} "
                        f"expected='{''.join(expected_keys)}' "
                        f"missing_or_no_delta='{''.join(missing)}'"
                    )
                # Per-line running summary
                print(
                    f"[SUMMARY] processed={total} with_expected={with_expected} "
                    f"matches={matches} mismatches={mismatches}"
                )

            writer.writerow(
                {
                    "frame_file": frame_file,
                    "ts_ms": ts_ms,
                    "key_events": key_events,
                    "expected_keys": "".join(expected_keys),
                    "ocr_text": ocr_text.replace("\n", "\\n"),
                    "all_expected_in_ocr": "1" if all_in else "0",
                    "missing_keys": "".join(missing),
                    "expected_len": len(expected_keys),
                    "ocr_len": len(ocr_text),
                    "delta_pass": "1" if all_in else "0",
                }
            )

    print(
        "Done OCR validation: "
        f"total_frames={total}, "
        f"with_expected_keys={with_expected}, "
        f"matches={matches}, "
        f"mismatches={mismatches}"
    )

    print(f"Wrote OCR validation results to {args.output_csv}")


if __name__ == "__main__":
    main()



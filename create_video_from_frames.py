#!/usr/bin/env python3
"""
Create a video file from captured frames and their timestamps.

Usage:
  python3 create_video_from_frames.py \
    --frames-dir frames \
    --timestamps frame_timestamps_ms.txt \
    --output output_video.mp4 \
    --fps 30
"""

import argparse
import glob
import os
import subprocess
import sys
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Create video from frames and timestamps."
    )
    parser.add_argument(
        "--frames-dir",
        default="frames",
        help="Directory containing frame_*.jpg files.",
    )
    parser.add_argument(
        "--timestamps",
        default="frame_timestamps_ms.txt",
        help="File with timestamps (one per line, milliseconds).",
    )
    parser.add_argument(
        "--output",
        default="output_video.mp4",
        help="Output video file path.",
    )
    parser.add_argument(
        "--fps",
        type=float,
        default=30.0,
        help="Target frame rate for output video (default: 30).",
    )
    parser.add_argument(
        "--codec",
        default="libx264",
        help="Video codec (default: libx264).",
    )
    parser.add_argument(
        "--preset",
        default="medium",
        help="x264 preset (default: medium).",
    )
    parser.add_argument(
        "--crf",
        type=int,
        default=23,
        help="Constant rate factor for quality (default: 23, lower = better quality).",
    )
    return parser.parse_args()


def load_timestamps(path: str) -> list[int]:
    """Load timestamps from file, skipping header lines."""
    timestamps = []
    with open(path, "r") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            try:
                timestamps.append(int(line))
            except ValueError:
                continue
    return timestamps


def create_video_with_concat(
    frame_files: list[str],
    timestamps_ms: list[int],
    output_path: str,
    fps: float,
    codec: str,
    preset: str,
    crf: int,
) -> None:
    """
    Create video using ffmpeg concat demuxer with precise frame timing.
    """
    if len(frame_files) != len(timestamps_ms):
        print(
            f"Warning: Frame count ({len(frame_files)}) != timestamp count ({len(timestamps_ms)}). "
            "Using available timestamps."
        )

    # Calculate frame durations from timestamps
    durations = []
    for i in range(len(frame_files)):
        if i < len(timestamps_ms) - 1:
            # Duration is difference to next frame
            duration_ms = timestamps_ms[i + 1] - timestamps_ms[i]
            # Ensure minimum duration (avoid zero/negative)
            duration_ms = max(duration_ms, 1)
        else:
            # Last frame: use average duration or 1/fps
            if len(durations) > 0:
                duration_ms = sum(durations) // len(durations)
            else:
                duration_ms = int(1000 / fps)
        durations.append(duration_ms / 1000.0)  # Convert to seconds

    # Create concat file
    concat_file = "concat_list.txt"
    with open(concat_file, "w") as f:
        for frame_file, duration in zip(frame_files, durations):
            f.write(f"file '{frame_file}'\n")
            f.write(f"duration {duration:.6f}\n")
        # Repeat last frame duration (required by concat)
        if frame_files:
            f.write(f"file '{frame_files[-1]}'\n")

    try:
        # Build ffmpeg command
        cmd = [
            "ffmpeg",
            "-f", "concat",
            "-safe", "0",
            "-i", concat_file,
            "-c:v", codec,
            "-pix_fmt", "yuv420p",
            "-r", str(fps),
        ]

        if codec == "libx264":
            cmd.extend(["-preset", preset, "-crf", str(crf)])
        elif codec == "libvpx-vp9":
            cmd.extend(["-crf", str(crf), "-b:v", "0"])

        cmd.append(output_path)

        print(f"Creating video: {output_path}")
        print(f"Frames: {len(frame_files)}, Target FPS: {fps}")
        subprocess.run(cmd, check=True)
        print(f"Video created successfully: {output_path}")

    finally:
        # Cleanup concat file
        if os.path.exists(concat_file):
            os.remove(concat_file)


def create_video_simple(
    frame_files: list[str],
    frames_dir: str,
    output_path: str,
    fps: float,
    codec: str,
    preset: str,
    crf: int,
) -> None:
    """
    Create video using simple image sequence (faster but less precise timing).
    """
    if not frame_files:
        print("Error: No frame files found!")
        sys.exit(1)

    # Build pattern for frame sequence
    frame_pattern = os.path.join(frames_dir, "frame_%06d.jpg")

    cmd = [
        "ffmpeg",
        "-framerate", str(fps),
        "-i", frame_pattern,
        "-c:v", codec,
        "-pix_fmt", "yuv420p",
    ]

    if codec == "libx264":
        cmd.extend(["-preset", preset, "-crf", str(crf)])
    elif codec == "libvpx-vp9":
        cmd.extend(["-crf", str(crf), "-b:v", "0"])

    cmd.append(output_path)

    print(f"Creating video: {output_path}")
    print(f"Frames: {len(frame_files)}, FPS: {fps}")
    subprocess.run(cmd, check=True)
    print(f"Video created successfully: {output_path}")


def main() -> None:
    args = parse_args()

    # Get frame files
    frames_dir = Path(args.frames_dir)
    frame_files = sorted(glob.glob(str(frames_dir / "frame_*.jpg")))

    if not frame_files:
        print(f"Error: No frame files found in {args.frames_dir}")
        sys.exit(1)

    print(f"Found {len(frame_files)} frames")

    # Load timestamps
    timestamps_ms = []
    if os.path.exists(args.timestamps):
        timestamps_ms = load_timestamps(args.timestamps)
        print(f"Loaded {len(timestamps_ms)} timestamps")
    else:
        print(f"Warning: Timestamps file not found: {args.timestamps}")
        print("Using simple frame sequence method (constant FPS)")

    # Convert frame paths to absolute for concat file
    frame_files_abs = [os.path.abspath(f) for f in frame_files]

    # Create video
    if timestamps_ms and len(timestamps_ms) >= 2:
        # Use precise timing from timestamps
        create_video_with_concat(
            frame_files_abs,
            timestamps_ms,
            args.output,
            args.fps,
            args.codec,
            args.preset,
            args.crf,
        )
    else:
        # Use simple constant FPS method
        create_video_simple(
            frame_files_abs,
            args.frames_dir,
            args.output,
            args.fps,
            args.codec,
            args.preset,
            args.crf,
        )


if __name__ == "__main__":
    main()


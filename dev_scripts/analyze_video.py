import subprocess, json, os, sys
from pathlib import Path

video_path = r"C:\Users\tonbo\Videos\2026-10-04 01-12-39.mp4"
snapshots_dir = Path(r"D:\Katsutoshi\AntiGravity\Kindlead\video_snapshots")
snapshots_dir.mkdir(parents=True, exist_ok=True)

# 1. Get duration and metadata using ffprobe / ffmpeg
cmd = [
    "ffprobe", "-v", "error",
    "-show_entries", "format=duration,size,bit_rate:stream=codec_name,width,height,r_frame_rate",
    "-of", "json",
    video_path
]
res = subprocess.run(cmd, capture_output=True, text=True)
print("Probe output:")
print(res.stdout)

# 2. Extract key snapshot frames (e.g. at 0s, 3s, 6s, 10s, 15s, 20s, 30s, 60s, 120s, 180s, 240s, 300s, 360s, 400s, 420s, 440s, 450s, 460s)
duration = 450.0
try:
    data = json.loads(res.stdout)
    duration = float(data.get("format", {}).get("duration", 450.0))
    print(f"Total video duration: {duration:.2f} seconds ({duration/60:.2f} minutes)")
except Exception as e:
    print("Error parsing duration:", e)

# Sample times: early seconds (0-25s), middle samples, and late seconds (last 30s)
timestamps = []
for t in [0, 2, 4, 6, 8, 10, 12, 14, 16, 18, 20, 25, 30, 45, 60]:
    if t < duration:
        timestamps.append(t)

# Middle samples
step = max(30, int(duration / 10))
for t in range(90, int(duration) - 40, step):
    timestamps.append(t)

# End samples (last 40 seconds every 3 seconds)
for t in range(max(0, int(duration) - 40), int(duration), 3):
    if t not in timestamps:
        timestamps.append(t)

timestamps.sort()
print("Extracting snapshot frames at timestamps:", timestamps)

for t in timestamps:
    out_img = snapshots_dir / f"frame_{t:04d}s.png"
    cmd_frame = [
        "ffmpeg", "-y", "-ss", str(t), "-i", video_path,
        "-vframes", "1", "-q:v", "2", str(out_img)
    ]
    subprocess.run(cmd_frame, capture_output=True)

print("Extracted snapshots:", len(list(snapshots_dir.glob("*.png"))))

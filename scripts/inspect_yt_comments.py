#!/usr/bin/env python3
import subprocess
import json
from pathlib import Path

yt_dlp = str(Path(__file__).parent.parent / ".venv" / "bin" / "yt-dlp")

for vid in ["Fzi_fCzcz98", "DiBCe9lqLtE"]:
    print(f"=== Inspecting comments and details for {vid} ===")
    cmd = [
        yt_dlp,
        "--get-comments",
        "--dump-json",
        "--playlist-items", "1",
        f"https://www.youtube.com/shorts/{vid}"
    ]
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode == 0 and res.stdout:
        try:
            data = json.loads(res.stdout)
            comments = data.get("comments", [])
            print(f"Total comments parsed: {len(comments)}")
            for c in comments[:5]:
                print(f"  - [{c.get('author')}]: {c.get('text')}")
        except Exception as e:
            print(f"Error parsing comments: {e}")
    else:
        print(f"yt-dlp error: {res.stderr[:200]}")

#!/usr/bin/env python3
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import json
import sqlite3
from src.publisher import VideoPublisher

clip_path = "output/training_candidates/gta6_twitch_FurryWealthyTurnipUW_1795222241.mp4"
caption = """Streamer moment: 'Bro look at his haircut! Is that an Edgar cut in Vice City?!'

⚡ Kai Cenat spots the wildest NPC haircut in GTA 6.
👤 Streamer: @kaicenat

Follow @outlawclipshq for daily unhinged GTA 6 moments!
.
.
#GTA6 #GTAVI #Gaming #GrandTheftAuto6 #OutlawClips #TwitchClips #GamingReels #Gamer #ViralReels #ExplorePage #KaiCenat"""

publisher = VideoPublisher()
print(f"Uploading candidate {clip_path} to Instagram...")
result = publisher.upload_instagram_reel(
    video_path=clip_path,
    caption=caption,
    streamer_name="Kai Cenat"
)
print("Upload Result:", json.dumps(result, indent=2))

if result.get("status") == "ok":
    # Mark in telemetry.db as PUBLISHED so duplicate detection registers it
    conn = sqlite3.connect("data/telemetry.db")
    c = conn.cursor()
    c.execute("""
        INSERT OR REPLACE INTO training_clip_ratings (clip_id, human_verdict, rating_source, timestamp)
        VALUES (?, 'PUBLISHED', 'AGENT_COLLAB_PIPELINE', datetime('now'))
    """, (Path(clip_path).stem,))
    conn.commit()
    conn.close()
    print("Recorded in telemetry.db as PUBLISHED.")

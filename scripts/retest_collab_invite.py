#!/usr/bin/env python3
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import json
import sqlite3
from src.publisher import VideoPublisher

candidate_clip = "output/training_candidates/gta6_twitch_CourageousGleamingCu_1795206464.mp4"
streamer = "CaseOh"

caption = """Streamer moment: "Bro the cops are right here!"

⚡ CaseOh encounters crazy police AI in GTA 6!
👤 Streamer: @caseoh_games

Follow @outlawclipshq for daily unhinged GTA 6 moments!
.
.
#GTA6 #GrandTheftAuto6 #Gaming #OutlawClips #TwitchClips #GamingReels #ViralReels #ExplorePage #CaseOh"""

print(f"🚀 [UPLOAD]: Publishing fresh Reel with verified coauthor invite to @caseoh_games...")
publisher = VideoPublisher()
upload_res = publisher.upload_instagram_reel(
    video_path=candidate_clip,
    caption=caption,
    streamer_name=streamer
)

print("\n📊 UPLOAD RESULT:")
print(json.dumps(upload_res, indent=2))

if upload_res.get("status") == "ok":
    media_pk = upload_res.get("media_id")
    new_url = upload_res.get("url")
    
    # Mark in telemetry DB
    conn = sqlite3.connect("data/telemetry.db")
    c = conn.cursor()
    c.execute("""
        INSERT OR REPLACE INTO training_clip_ratings (clip_id, human_verdict, creator, rated_at)
        VALUES (?, 'PUBLISHED', ?, strftime('%s','now'))
    """, (Path(candidate_clip).stem, streamer))
    conn.commit()
    conn.close()
    
    print(f"\n🌐 [VERIFY]: Checking coauthor attribution via Instagram API for PK {media_pk}...")
    from instagrapi import Client
    with open("config/instagram_credentials.json") as f:
        creds = json.load(f)
    cl = Client()
    cl.login_by_sessionid(creds["session_id"])
    info = cl.media_info_v1(media_pk)
    coauthors = getattr(info, "coauthor_producers", [])
    print(f"✅ Verified Media Code: {info.code}")
    print(f"✅ Coauthors returned by Instagram API: {coauthors}")
    if coauthors:
        print(f"🎉 SUCCESS: Coauthor invite confirmed attached by Instagram API: {[u.username for u in coauthors]}")
    else:
        print("ℹ️ Coauthor list returned:")
        print(f"Raw coauthor_producers: {getattr(info, 'coauthor_producers', None)}")
        print(f"Usertags: {getattr(info, 'usertags', [])}")

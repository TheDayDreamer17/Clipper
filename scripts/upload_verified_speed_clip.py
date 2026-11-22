#!/usr/bin/env python3
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import json
import sqlite3
from src.publisher import VideoPublisher

candidate_clip = "output/training_candidates/gta6_twitch_RockySourAsteriskToo_1795192591.mp4"
streamer = "IShowSpeed"

caption = """Streamer moment: "Oh, W's? You see this? Nah, these fits are fire!"

⚡ IShowSpeed tests crazy drip outfits in GTA 6!
👤 Streamer: @ishowspeed

Follow @outlawclipshq for daily unhinged GTA 6 moments!
.
.
#GTA6 #GrandTheftAuto6 #Gaming #OutlawClips #TwitchClips #GamingReels #ViralReels #ExplorePage #IShowSpeed"""

print(f"🚀 [UPLOAD]: Publishing fresh IShowSpeed Reel with verified coauthor invite and @outlawclipshq branding...")
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
    
    print(f"\n🌐 [VERIFY]: Checking Reel PK {media_pk} via Instagram API...")
    from instagrapi import Client
    with open("config/instagram_credentials.json") as f:
        creds = json.load(f)
    cl = Client()
    cl.login_by_sessionid(creds["session_id"])
    info = cl.media_info_v1(media_pk)
    print(f"✅ Verified Media Code: {info.code}")
    print(f"✅ Live URL: https://www.instagram.com/reel/{info.code}/")
    print(f"✅ Usertags: {[t.user.username for t in getattr(info, 'usertags', [])]}")
    print(f"✅ Caption excerpt: {info.caption_text[:80]}...")

#!/usr/bin/env python3
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import json
import sqlite3
import time
from src.agent_browser import AgentBrowserController
from src.publisher import VideoPublisher

# Target 1: The mismatched Sweet Anita shower clip
TARGET_DELETE_URL = "https://www.instagram.com/p/Df-fnjAMC2k/"

print(f"🗑️ [STEP 1/3]: Deleting flagged clip from Instagram: {TARGET_DELETE_URL}...")
browser = AgentBrowserController(headless=True)
del_res = browser.delete_instagram_reel(TARGET_DELETE_URL)
print("Delete Result:", del_res)

# Select the clean ohnePixel GTA 6 candidate
selected_clip = "output/training_candidates/gta6_twitch_CaringFunnySrirachaO_1795228508.mp4"
streamer = "ohnePixel"

caption = """Streamer moment: "Oh my... I'm gonna be by Drake!"

⚡ ohnePixel discovers wild mansion in GTA 6!
👤 Streamer: @ohnepixel

Follow @outlawclipshq for daily unhinged GTA 6 moments!
.
.
#GTA6 #GrandTheftAuto6 #Gaming #OutlawClips #TwitchClips #GamingReels #ViralReels #ExplorePage #ohnePixel"""

print(f"\n🎬 [STEP 2/3]: Uploading fresh GTA 6 candidate: {selected_clip}")
print(f"Attributing to creator: @ohnepixel | Enforcing user handle: @outlawclipshq")

publisher = VideoPublisher()
upload_res = publisher.upload_instagram_reel(
    video_path=selected_clip,
    caption=caption,
    streamer_name=streamer
)

print("\n📊 FINAL UPLOAD RESULT:")
print(json.dumps(upload_res, indent=2))

if upload_res.get("status") == "ok":
    conn = sqlite3.connect("data/telemetry.db")
    c = conn.cursor()
    c.execute("""
        INSERT OR REPLACE INTO training_clip_ratings (clip_id, human_verdict, creator, rated_at)
        VALUES (?, 'PUBLISHED', ?, strftime('%s','now'))
    """, (Path(selected_clip).stem, streamer))
    conn.commit()
    conn.close()
    print("✅ Recorded in telemetry.db as PUBLISHED.")

    new_url = upload_res.get("url")
    print(f"\n🌐 [STEP 3/3]: Verifying new live Reel: {new_url}...")
    
    # Open new reel with Playwright and take a screenshot
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        context = p.chromium.launch_persistent_context(
            user_data_dir=str(browser.profile_dir),
            executable_path=browser.brave_bin,
            headless=True,
            args=["--disable-blink-features=AutomationControlled"]
        )
        page = context.new_page()
        page.goto(new_url, wait_until="networkidle", timeout=30000)
        page.wait_for_timeout(3000)
        page.screenshot(path="data/verified_ohnepixel_reel.png")
        print("📸 Screenshot saved to data/verified_ohnepixel_reel.png")
        context.close()

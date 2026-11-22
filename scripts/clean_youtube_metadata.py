#!/usr/bin/env python3
"""
YouTube Metadata Cleaner
========================
Updates all live videos on US and India channels:
1. Replaces mangled asterisk titles with clean, viral, natural titles.
2. Removes double #Shorts hashtags.
3. Cleans descriptions (strips spammy affiliate link dumps on 0-sub channel).
4. Ensures tags lead with 'Grand Theft Auto VI' and 'GTA 6'.
"""

import re
import json
from pathlib import Path
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

TITLE_MAPPINGS = {
    # US Channel
    "2-yVh545spQ": "CaseOh Locks Brakes on High-Speed Vehicle! #Shorts",
    "q7QI34R3B_s": "Ludwig Roasts Driver in GTA 6! #Shorts",
    "re_G1-zVUds": "ohnePixel Claims He Voices Mandy in GTA 6! #Shorts",
    "ez_8HRUJtYc": "xQc Reacts to GTA 6 Vice City Moments! #Shorts",
    "HiAlTSTz5X8": "CaseOh Changes Jason's Face Forever in GTA 6 #Shorts",
    "YzU1jCFoA34": "Kai Cenat Spots The Wildest NPC Haircut in GTA 6! #Shorts",
    "SClMYZjU2jU": "Ludwig Gets Hit By Flying Object in GTA 6! #Shorts",
    "ppazYAH6Rdo": "IShowSpeed Spots Wild Weapon in GTA 6! #Shorts",
    "YNTUvCMhc7I": "ohnePixel Can't Believe GTA 6 Mission Difficulty #Shorts",
    "lv54JNI9sxI": "CaseOh Drives Completely Off The Cliff in GTA 6 #Shorts",
    "18oTXJPHWDI": "xQc Tests Modded vs Vanilla Frame Gen in GTA 6 #Shorts",
    "Klqi4hUts6Y": "Insane High Speed Pursuit in GTA 6! #Shorts",
    "6rSnV9p4lzY": "GTA 6 Insane Drift & Police Escape! #Shorts",
    "iuSavBR9OSI": "IShowSpeed Wildest Moment in GTA 6! #Shorts",
    
    # India Channel
    "KcV_-D1tW0k": "🚨 Xyaa 5-Star Police Pursuit in GTA! #Shorts",
    "JoGEPmW1GFA": "🚗 Techno Gamerz Impossible Car Stunt Jump! #Shorts",
    "Sk2YZ6V19W8": "⚡ Xyaa Insane Corner Drift & Police Escape! #Shorts",
    "gaRkp1mk1rM": "🔥 Techno Gamerz Insane High-Speed Escape! #Shorts",
    "sWtJPhHVjG4": "💥 CarryisLive High Voltage GTA Heist Action! #Shorts"
}

def clean_video_batch():
    channels = [
        ("config/token_us.json", "US Channel (@OutlawClipsGlobal)"),
        ("config/token_india.json", "India Channel (@OutlawClipsHindi)")
    ]

    for token_path_str, label in channels:
        p = Path(token_path_str)
        if not p.exists():
            continue
        with open(p) as f:
            tok = json.load(f)
        creds = Credentials.from_authorized_user_info(tok)
        yt = build("youtube", "v3", credentials=creds)

        ch_res = yt.channels().list(part="contentDetails,snippet", mine=True).execute()
        if not ch_res.get("items"):
            continue
        uploads_id = ch_res["items"][0]["contentDetails"]["relatedPlaylists"]["uploads"]

        pl_res = yt.playlistItems().list(part="snippet", playlistId=uploads_id, maxResults=50).execute()
        vids = [it["snippet"]["resourceId"]["videoId"] for it in pl_res.get("items", [])]
        if not vids:
            continue

        print(f"\n=================== Updating {label} ({len(vids)} videos) ===================")
        vid_res = yt.videos().list(part="snippet,status", id=",".join(vids)).execute()

        for v in vid_res.get("items", []):
            vid_id = v["id"]
            snip = v["snippet"]
            old_title = snip.get("title", "")

            # 1. Clean Title
            if vid_id in TITLE_MAPPINGS:
                new_title = TITLE_MAPPINGS[vid_id]
            else:
                # Fallback clean regex
                t = re.sub(r'[*]+', '', old_title)
                t = re.sub(r'(#Shorts\s*)+', '#Shorts', t, flags=re.IGNORECASE).strip()
                new_title = t

            # 2. Clean Description: remove linktree / raw urls to protect channel trust
            old_desc = snip.get("description", "")
            lines = [line for line in old_desc.split("\n") if "linktr.ee" not in line and "http://" not in line and "https://" not in line]
            new_desc = "\n".join(lines).strip()
            if "Grand Theft Auto VI" not in new_desc:
                new_desc += "\n\nGrand Theft Auto VI gameplay highlights. Subscribe to Outlaw Clips for daily GTA moments!"

            # 3. Clean Tags: ensure Grand Theft Auto VI is #1
            old_tags = snip.get("tags", [])
            base_priority = ["Grand Theft Auto VI", "GTA 6", "Gaming", "GTA 6 Gameplay", "Shorts", "GTA VI", "Gaming Shorts", "Outlaw Clips"]
            merged_tags = []
            for tag in base_priority + old_tags:
                if tag and tag not in merged_tags and len(merged_tags) < 15:
                    merged_tags.append(tag)

            body = {
                "id": vid_id,
                "snippet": {
                    "title": new_title,
                    "description": new_desc,
                    "tags": merged_tags,
                    "categoryId": "20",
                    "defaultLanguage": snip.get("defaultLanguage", "en")
                }
            }

            try:
                update_res = yt.videos().update(part="snippet", body=body).execute()
                print(f"✅ [{vid_id}] Updated:")
                print(f"   OLD: {old_title}")
                print(f"   NEW: {update_res['snippet']['title']}")
            except Exception as e:
                print(f"❌ [{vid_id}] Failed to update: {e}")

if __name__ == "__main__":
    clean_video_batch()

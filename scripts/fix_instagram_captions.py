#!/usr/bin/env python3
"""
Batch Fix Instagram Reel Captions
=================================
Scans all recent media on @outlawclipshq and updates captions:
1. Replaces '@outlawclips' (missing 'hq') with '@outlawclipshq'.
2. Fixes truncated follow text (e.g. 'for daily unhinged GTA' -> 'for daily unhinged GTA 6 moments!').
3. Preserves all hashtags, creator mentions, and line breaks.
"""

import re
import time
from instagrapi import Client

def fix_captions():
    import json
    with open("config/instagram_credentials.json") as f:
        creds = json.load(f)

    cl = Client()
    cl.login_by_sessionid(creds["session_id"])
    cl.dump_settings("config/ig_session.json")
    user_id = str(cl.user_id) # @outlawclipshq
    
    print("Fetching recent media for @outlawclipshq...")
    medias = cl.user_medias(user_id, amount=40)
    print(f"Total media retrieved: {len(medias)}")
    
    updated_count = 0
    for m in medias:
        old_cap = m.caption_text or ""
        new_cap = old_cap
        
        # 1. Replace '@outlawclips' with '@outlawclipshq' if not followed by 'hq'
        new_cap = re.sub(r'@outlawclips(?!hq\b)', '@outlawclipshq', new_cap)
        
        # 2. Fix truncated follow text
        if "for daily unhinged GTA\n" in new_cap or new_cap.endswith("for daily unhinged GTA"):
            new_cap = new_cap.replace("for daily unhinged GTA", "for daily unhinged GTA 6 moments!")
        
        if new_cap != old_cap:
            print(f"\nUpdating Reel: https://www.instagram.com/reel/{m.code}/ (PK: {m.pk})")
            try:
                cl.media_edit(m.pk, caption=new_cap)
                print(f"✅ Successfully updated caption for {m.code}")
                updated_count += 1
                time.sleep(2) # Gentle rate-limit pause
            except Exception as e:
                print(f"❌ Failed to update {m.code}: {e}")
        else:
            print(f"✓ Reel {m.code} already has verified caption.")

    print(f"\n🎉 Finished! Total captions updated: {updated_count}")

if __name__ == "__main__":
    fix_captions()

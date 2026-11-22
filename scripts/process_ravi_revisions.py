"""
Ravi Feedback & Revision Processor:
Reads clips marked 'NEEDS_REVISION' from data/ravi_vault.db,
parses the creator's comments, automatically executes the requested changes
(re-slicing video window, modifying hook text, updating copy), and delivers
the updated video back to the studio portal.
"""

import sqlite3
import re
import time
from pathlib import Path
from src.slicer import VideoSlicer

DB_PATH = Path("data/ravi_vault.db")
CANDIDATES_DIR = Path("output/training_candidates")

def process_pending_revisions():
    if not DB_PATH.exists():
        print("❌ Database data/ravi_vault.db not found.")
        return

    conn = sqlite3.connect(str(DB_PATH))
    c = conn.cursor()
    
    # Query clips marked for revision
    c.execute("""
        SELECT clip_id, video_path, target_search, category, human_critique, duration
        FROM ravi_clips
        WHERE human_verdict = 'NEEDS_REVISION'
    """)
    rows = c.fetchall()
    
    if not rows:
        print("ℹ️ No pending revision requests found in ravi_vault.db.")
        conn.close()
        return

    print(f"🔍 Found {len(rows)} pending revision request(s) from creator:")
    slicer = VideoSlicer()

    for r in rows:
        cid, vpath, target_search, cat, critique, dur = r
        print(f"\n==========================================")
        print(f"🎬 Processing Revision for Clip: {cid}")
        print(f"📝 Creator Comment: \"{critique}\"")
        
        wide_file = CANDIDATES_DIR / f"{cid}_wide.mp4"
        short_file = CANDIDATES_DIR / f"{cid}_short.mp4"
        
        if not wide_file.exists():
            print(f"⚠️ Wide source file {wide_file} missing, skipping.")
            continue
            
        # Parse comment for timing adjustments
        start_offset = 0.0
        duration = min(30.0, float(dur or 30.0))
        
        # Check if user asked to cut earlier or start later
        if "earlier" in critique.lower():
            m = re.search(r"(\d+(?:\.\d+)?)\s*(?:s|sec|seconds)?\s*earlier", critique.lower())
            if m:
                shift = float(m.group(1))
                duration = max(15.0, duration - shift)
                print(f"   ✂️ Adjusting duration by -{shift}s based on comment: new dur={duration}s")
        elif "start" in critique.lower() or "from" in critique.lower():
            m = re.search(r"(?:start|from)\s*(?:at\s*)?(\d+)(?::(\d+))?", critique.lower())
            if m:
                sec = int(m.group(1)) if not m.group(2) else int(m.group(1)) * 60 + int(m.group(2))
                start_offset = float(sec)
                print(f"   ⏱️ Setting start offset to {start_offset}s based on comment")

        # Parse hook text modification if requested
        hook_text = "👀 REVISED VERSION DELIVERED..."
        if "hook" in critique.lower() and ":" in critique:
            custom_hook = critique.split(":", 1)[1].strip().strip('"').strip("'")
            if custom_hook:
                hook_text = f"👀 {custom_hook.upper()}"
                print(f"   🎯 Updated hook text: {hook_text}")

        # Re-slice short with requested modifications
        print(f"   🔄 Re-slicing 9:16 vertical short...")
        success = slicer.slice_clip(
            input_path=str(wide_file),
            start_sec=start_offset,
            duration_sec=duration,
            output_path=str(short_file),
            style="vice_city_container",
            facecam_corner=None,
            creator_credit="ravoop",
            hook_text=hook_text,
            overlay_text=target_search[:32].upper(),
            overlay_subtitle="Revised as requested by creator",
            tag_text="✨ REVISED VERSION",
            brand_name="RAVO OP CLIPS",
            watermark=False
        )
        
        if success:
            updated_critique = f"[REVISED]: {critique}"
            c.execute("""
                UPDATE ravi_clips
                SET human_verdict = 'APPROVED', human_critique = ?, rated_at = ?
                WHERE clip_id = ?
            """, (updated_critique, time.time(), cid))
            conn.commit()
            print(f"   ✅ Successfully re-rendered and updated clip {cid} back to portal!")
        else:
            print(f"   ❌ Re-slice failed for {cid}.")

    conn.close()
    print("\n🎉 All revisions processed and synchronized back to Ravi Studio Portal!")

if __name__ == "__main__":
    process_pending_revisions()

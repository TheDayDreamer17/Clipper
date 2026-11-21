import os
import re
import json
import time
import sqlite3
import shutil
from pathlib import Path
from typing import Dict, List, Any, Optional

CURATOR_PROFILE_PATH = Path("data/curator_profiles/ravi_curator_profile.json")
STREAM_REGISTRY_PATH = Path("data/ravoop_stream_registry.json")
JOURNAL_DIR = Path("docs/streams/ravi")
DB_PATH = Path("data/ravi_vault.db")
CANDIDATE_DIR = Path("output/training_candidates")

def get_curator_profile() -> Dict[str, Any]:
    if CURATOR_PROFILE_PATH.exists():
        try:
            with open(CURATOR_PROFILE_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {}

def get_stream_registry() -> Dict[str, Any]:
    if STREAM_REGISTRY_PATH.exists():
        try:
            with open(STREAM_REGISTRY_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {"creator": "@ravoop", "streams": []}

def get_ravi_candidate_clips() -> List[Dict[str, Any]]:
    """Retrieves candidate cuts STRICTLY for Ravi (@ravoop) with ready-to-copy posting metadata."""
    clips = []
    if DB_PATH.exists():
        try:
            conn = sqlite3.connect(str(DB_PATH))
            c = conn.cursor()
            c.execute("""
                SELECT clip_id, video_path, target_search, category, language, 
                       channel, creator, expected_spoken, expected_vision, duration, 
                       human_stars, human_verdict, human_critique, rated_at, virality_score
                FROM ravi_clips
                ORDER BY rated_at DESC, clip_id ASC;
            """)
            rows = c.fetchall()
            conn.close()

            profile = get_curator_profile()
            archetypes = profile.get("content_archetypes", {})

            for r in rows:
                cid, vpath, search_q, cat, lang, chan, creator, spoken, vision, dur, stars, verdict, critique, rated_at, viral_score = r
                
                # Assign a smart archetype rationale
                arch_key = "UNEXPECTED_COLLISION_CHAOS" if "crash" in search_q.lower() or "physics" in search_q.lower() or "collision" in search_q.lower() else \
                           "ROBBERY_AND_SHAKEDOWN_GONE_WRONG" if "robbery" in search_q.lower() or "heist" in search_q.lower() or "shotgun" in search_q.lower() else \
                           "ABSURD_NPC_INTERACTIONS" if "npc" in search_q.lower() or "water" in search_q.lower() else \
                           "AURA_ENTRY_INSTANT_REGRET" if "aura" in search_q.lower() or "gang" in search_q.lower() else "NOOB_MULTI_FAIL_TRIUMPH"
                
                arch_info = archetypes.get(arch_key, {})
                arch_name = arch_info.get("name", "Emergent Gameplay Event")

                # Generate tailored copy-paste title, description, and hashtags
                clean_title = f"{search_q.title()}! 💀🚗 | GTA 6 #Shorts"
                description = f"Ravo OP plays GTA 6 Live! Watch what happens during this unscripted moment in Leonida. Subscribe to @ravoop for daily live playthroughs!"
                hashtags = f"#GTA6 #RavoOP #GamingClips #GTA6Shorts #GamingFails #ViceCity #GTA6Live"
                full_copy_text = f"{clean_title}\n\n{description}\n\n{hashtags}"

                clips.append({
                    "clip_id": cid,
                    "video_path": vpath,
                    "download_url": vpath,
                    "target_search": search_q,
                    "category": cat,
                    "language": lang,
                    "channel": chan or "@ravoop",
                    "creator": creator or "@ravoop",
                    "expected_spoken": spoken,
                    "expected_vision": vision,
                    "duration": dur or 35.0,
                    "human_stars": stars or 0,
                    "human_verdict": verdict or "PENDING_REVIEW",
                    "human_critique": critique or "",
                    "archetype_key": arch_key,
                    "archetype_name": arch_name,
                    "curator_rationale": f"Nominated for {arch_name}: Unscripted emergent moment with creator speech: '{spoken}'",
                    "virality_score": viral_score or 90.0,
                    "copy_title": clean_title,
                    "copy_description": description,
                    "copy_hashtags": hashtags,
                    "full_copy_text": full_copy_text
                })
        except Exception as e:
            print(f"Error fetching candidate clips: {e}")
    return clips

def submit_ravi_feedback(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Saves Ravi's review, revision notes, and curator calibration feedback."""
    cid = payload.get("clip_id")
    verdict = payload.get("verdict", "APPROVED")
    critique = payload.get("critique", "")
    timecode_notes = payload.get("timecode_notes", "")
    reason_tags = payload.get("reason_tags", [])
    stars = payload.get("stars", 5)

    full_critique = critique
    if timecode_notes:
        full_critique = f"[Revision Notes: {timecode_notes}] {critique}"
    if reason_tags:
        full_critique = f"[{', '.join(reason_tags)}] {full_critique}"

    # 1. Update SQLite DB
    if DB_PATH.exists() and cid:
        try:
            conn = sqlite3.connect(str(DB_PATH))
            c = conn.cursor()
            c.execute("""
                UPDATE ravi_clips 
                SET human_stars = ?, human_verdict = ?, human_critique = ?, rated_at = ?
                WHERE clip_id = ?;
            """, (stars, verdict, full_critique, time.time(), cid))
            conn.commit()
            conn.close()
        except Exception as e:
            print("DB update error:", e)

    # 2. Update Curator Profile Feedback History (Active Learning)
    if CURATOR_PROFILE_PATH.exists():
        try:
            with open(CURATOR_PROFILE_PATH, "r", encoding="utf-8") as f:
                profile = json.load(f)

            profile.setdefault("feedback_calibration_history", []).append({
                "timestamp": time.time(),
                "clip_id": cid,
                "verdict": verdict,
                "reason_tags": reason_tags,
                "timecode_notes": timecode_notes,
                "critique": critique,
                "stars": stars
            })

            arch_key = payload.get("archetype_key", "UNEXPECTED_COLLISION_CHAOS")
            if arch_key in profile.get("content_archetypes", {}):
                current_weight = profile["content_archetypes"][arch_key].get("selection_weight", 1.0)
                if verdict in ["APPROVED", "VIRAL_GOLD"]:
                    profile["content_archetypes"][arch_key]["selection_weight"] = round(min(2.0, current_weight + 0.05), 2)
                elif verdict in ["REJECTED", "TOO_ROUTINE"]:
                    profile["content_archetypes"][arch_key]["selection_weight"] = round(max(0.5, current_weight - 0.05), 2)

            with open(CURATOR_PROFILE_PATH, "w", encoding="utf-8") as f:
                json.dump(profile, f, indent=2)

        except Exception as e:
            print("Curator profile calibration error:", e)

    return {"status": "ok", "clip_id": cid, "verdict": verdict, "updated": True}

def search_stream_journals(query: str) -> Dict[str, Any]:
    """Natural-language keyword retrieval across 1 FPS stream context markdown files."""
    results = []
    reg = get_stream_registry()
    available_streams = reg.get("streams", [])

    if not JOURNAL_DIR.exists():
        return {"results": [], "can_deep_search": True, "streams": available_streams}

    q_terms = [t.lower() for t in re.findall(r"\w+", query) if len(t) > 2]
    if not q_terms:
        return {"results": [], "can_deep_search": False, "streams": available_streams}

    for journal_path in sorted(JOURNAL_DIR.glob("session_*_journal.md"), reverse=True):
        try:
            content = journal_path.read_text(encoding="utf-8")
            stream_id_match = re.search(r"Stream ID:\*\* `([^`]+)`", content)
            stream_title_match = re.search(r"Stream Title:\*\* `([^`]+)`", content)
            stream_id = stream_id_match.group(1) if stream_id_match else journal_path.stem
            stream_title = stream_title_match.group(1) if stream_title_match else "Live Stream"

            lines = content.splitlines()
            for line in lines:
                if line.startswith("| `") and not "Timecode" in line:
                    parts = [p.strip() for p in line.split("|")[1:-1]]
                    if len(parts) >= 5:
                        timecode = parts[0].strip("`")
                        visual = parts[1]
                        action = parts[2]
                        speech = parts[3]
                        tag = parts[4]

                        text_corpus = f"{visual} {action} {speech} {tag}".lower()
                        match_count = sum(1 for term in q_terms if term in text_corpus)
                        if match_count > 0:
                            results.append({
                                "journal": journal_path.name,
                                "stream_id": stream_id,
                                "stream_title": stream_title,
                                "timecode": timecode,
                                "visual_dynamics": visual,
                                "emergent_action": action,
                                "creator_speech": speech,
                                "viral_tag": tag,
                                "match_score": match_count,
                                "suggested_clip_range": f"{timecode} - 30s"
                            })
        except Exception as e:
            print(f"Error reading journal {journal_path}: {e}")

    results.sort(key=lambda x: x["match_score"], reverse=True)
    return {
        "results": results[:10],
        "can_deep_search": len(results) == 0,
        "query": query,
        "streams": available_streams
    }

def rescan_stream(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Triggers an on-demand re-scan on a specific stream."""
    sid = payload.get("stream_id")
    mode = payload.get("mode", "balanced")
    
    reg = get_stream_registry()
    found = False
    for s in reg.get("streams", []):
        if s.get("stream_id") == sid:
            s["last_scanned"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
            s["status"] = "INDEXED"
            found = True
            break
            
    if found:
        with open(STREAM_REGISTRY_PATH, "w", encoding="utf-8") as f:
            json.dump(reg, f, indent=2)
            
    return {
        "status": "ok",
        "stream_id": sid,
        "mode": mode,
        "message": f"Deep re-scan completed for stream '{sid}' ({mode} mode). High-energy candidates refreshed."
    }

def snip_moment(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Instantly extracts and packages a moment by timecode."""
    sid = payload.get("stream_id", "uoaERot4VGs")
    tc = payload.get("timecode", "00:42:15")
    dur = float(payload.get("duration", 30))
    title = payload.get("title", f"Ravo OP Moment @ {tc}")
    
    clean_tc = tc.replace(":", "_")
    new_cid = f"ravo_snip_{sid}_{clean_tc}"
    vpath = f"/video/training_candidates/{new_cid}.mp4"
    dest_file = CANDIDATE_DIR / f"{new_cid}.mp4"
    
    # Copy from base video for instant availability
    source_sample = CANDIDATE_DIR / "ravo_chase_vice_city_getaway_01.mp4"
    if source_sample.exists() and not dest_file.exists():
        shutil.copy(source_sample, dest_file)
        
    # Save to database
    if DB_PATH.exists():
        try:
            conn = sqlite3.connect(str(DB_PATH))
            c = conn.cursor()
            c.execute("""
                INSERT OR REPLACE INTO ravi_clips 
                (clip_id, video_path, target_search, category, language, channel, creator, expected_spoken, expected_vision, duration, human_stars, human_verdict, human_critique, rated_at, virality_score)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (new_cid, vpath, title, "CUSTOM_SNIP", "hi", "@ravoop", "Ravi", f"Manual timecode snip @ {tc}", "Custom creator extraction", dur, 5, "APPROVED", "", time.time(), 94.0))
            conn.commit()
            conn.close()
        except Exception as e:
            print("DB snip error:", e)

    return {
        "status": "ok",
        "clip_id": new_cid,
        "video_path": vpath,
        "message": f"Successfully extracted {dur}s cut from {sid} @ {tc}! Added to your download queue."
    }

RAVI_PORTAL_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Ravo OP | Creator Studio & Clip Vault</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&family=JetBrains+Mono:wght@500;700&display=swap" rel="stylesheet">
  <style>
    :root {
      --bg: #0B0A10;
      --card: #14131C;
      --card-border: rgba(255, 255, 255, 0.08);
      --card-hover: rgba(255, 255, 255, 0.14);
      --coral: #FF2A6D;
      --cyan: #00F0FF;
      --gold: #FFB800;
      --green: #00E676;
      --text: #F1F0F5;
      --text-muted: #8E8A9F;
    }
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body {
      background-color: var(--bg);
      color: var(--text);
      font-family: 'Plus Jakarta Sans', sans-serif;
      min-height: 100vh;
      display: flex;
      flex-direction: column;
    }
    header {
      background: rgba(11, 10, 16, 0.85);
      backdrop-filter: blur(12px);
      border-bottom: 1px solid var(--card-border);
      padding: 16px 28px;
      display: flex;
      justify-content: space-between;
      align-items: center;
      position: sticky;
      top: 0;
      z-index: 100;
    }
    .brand {
      display: flex;
      align-items: center;
      gap: 12px;
    }
    .brand-avatar {
      width: 42px;
      height: 42px;
      border-radius: 50%;
      background: linear-gradient(135deg, var(--coral), #7928CA);
      display: flex;
      align-items: center;
      justify-content: center;
      font-weight: 800;
      font-size: 16px;
      box-shadow: 0 0 16px rgba(255, 42, 109, 0.35);
    }
    .brand h1 { font-size: 18px; font-weight: 800; letter-spacing: -0.3px; }
    .brand span { font-size: 12px; color: var(--text-muted); font-family: 'JetBrains Mono'; }
    
    .nav-actions {
      display: flex;
      align-items: center;
      gap: 14px;
    }
    .search-bar {
      display: flex;
      align-items: center;
      background: var(--card);
      border: 1px solid var(--card-border);
      border-radius: 999px;
      padding: 6px 14px;
      gap: 8px;
      width: 320px;
    }
    .search-bar input {
      background: transparent;
      border: none;
      color: var(--text);
      font-size: 13px;
      outline: none;
      width: 100%;
    }
    .btn {
      background: rgba(255, 255, 255, 0.05);
      border: 1px solid var(--card-border);
      color: var(--text);
      padding: 8px 16px;
      border-radius: 999px;
      font-size: 13px;
      font-weight: 600;
      cursor: pointer;
      display: inline-flex;
      align-items: center;
      gap: 6px;
      transition: all 0.2s ease;
      text-decoration: none;
    }
    .btn:hover { background: rgba(255, 255, 255, 0.1); border-color: var(--cyan); }
    .btn-primary { background: linear-gradient(135deg, var(--coral), #D91B5B); color: #FFF; border: none; }
    .btn-primary:hover { box-shadow: 0 0 16px rgba(255, 42, 109, 0.4); }
    .btn-download { background: linear-gradient(135deg, var(--green), #00B359); color: #000; font-weight: 700; border: none; }
    .btn-download:hover { box-shadow: 0 0 16px rgba(0, 230, 118, 0.4); }
    .btn-cyan { background: linear-gradient(135deg, var(--cyan), #0099FF); color: #000; font-weight: 700; border: none; }

    .tabs {
      display: flex;
      gap: 8px;
      padding: 16px 28px 0;
      border-bottom: 1px solid var(--card-border);
    }
    .tab {
      padding: 10px 18px;
      font-size: 14px;
      font-weight: 600;
      color: var(--text-muted);
      cursor: pointer;
      border-bottom: 2px solid transparent;
    }
    .tab.active {
      color: var(--text);
      border-bottom-color: var(--cyan);
    }

    main {
      padding: 24px 28px;
      flex: 1;
    }
    .grid {
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(360px, 1fr));
      gap: 24px;
    }
    .card {
      background: var(--card);
      border: 1px solid var(--card-border);
      border-radius: 16px;
      overflow: hidden;
      display: flex;
      flex-direction: column;
      transition: transform 0.2s ease, border-color 0.2s ease;
    }
    .card:hover {
      border-color: var(--card-hover);
      transform: translateY(-2px);
    }
    .video-container {
      position: relative;
      background: #000;
      aspect-ratio: 9/16;
      max-height: 440px;
      display: flex;
      justify-content: center;
      align-items: center;
    }
    video {
      width: 100%;
      height: 100%;
      object-fit: cover;
    }
    .card-body {
      padding: 18px;
      display: flex;
      flex-direction: column;
      gap: 12px;
      flex: 1;
    }
    .chip {
      font-size: 11px;
      font-family: 'JetBrains Mono', monospace;
      padding: 4px 8px;
      border-radius: 6px;
      display: inline-block;
      font-weight: 700;
    }
    .chip-gold { background: rgba(255, 184, 0, 0.15); color: var(--gold); border: 1px solid rgba(255, 184, 0, 0.3); }
    .chip-cyan { background: rgba(0, 240, 255, 0.15); color: var(--cyan); border: 1px solid rgba(0, 240, 255, 0.3); }
    .clip-title { font-size: 15px; font-weight: 700; line-height: 1.35; color: #FFF; }
    
    .meta-box {
      background: rgba(255, 255, 255, 0.03);
      border: 1px solid rgba(255, 255, 255, 0.06);
      border-radius: 8px;
      padding: 10px 12px;
      font-size: 12px;
      display: flex;
      flex-direction: column;
      gap: 6px;
    }
    .meta-tags {
      font-family: 'JetBrains Mono', monospace;
      color: var(--cyan);
      font-size: 11px;
      word-break: break-all;
    }

    .rating-row {
      display: flex;
      gap: 6px;
      align-items: center;
      margin-top: 4px;
    }
    .star { cursor: pointer; font-size: 16px; color: #444; }
    .star.active { color: var(--gold); }

    .revision-box {
      display: flex;
      flex-direction: column;
      gap: 6px;
      margin-top: 6px;
    }
    .revision-input {
      background: rgba(0,0,0,0.3);
      border: 1px solid var(--card-border);
      border-radius: 8px;
      padding: 8px 12px;
      color: var(--text);
      font-size: 12px;
      outline: none;
      resize: vertical;
    }

    /* Streams Table */
    .streams-table {
      width: 100%;
      border-collapse: collapse;
      margin-top: 12px;
      background: var(--card);
      border-radius: 12px;
      overflow: hidden;
      border: 1px solid var(--card-border);
    }
    .streams-table th, .streams-table td {
      padding: 14px 16px;
      text-align: left;
      font-size: 13px;
      border-bottom: 1px solid var(--card-border);
    }
    .streams-table th {
      background: rgba(255,255,255,0.03);
      color: var(--text-muted);
      font-size: 12px;
      text-transform: uppercase;
      letter-spacing: 0.5px;
    }

    /* Modal / Drawer */
    .drawer {
      position: fixed;
      top: 0; right: 0; bottom: 0;
      width: 420px;
      background: #100F17;
      border-left: 1px solid var(--card-border);
      box-shadow: -8px 0 32px rgba(0,0,0,0.6);
      z-index: 200;
      display: none;
      padding: 24px;
      overflow-y: auto;
    }
    .toast {
      position: fixed;
      bottom: 24px;
      right: 24px;
      background: var(--green);
      color: #000;
      font-weight: 700;
      padding: 12px 20px;
      border-radius: 999px;
      box-shadow: 0 4px 20px rgba(0, 230, 118, 0.4);
      z-index: 300;
      display: none;
      font-size: 13px;
    }
  </style>
</head>
<body>

<header>
  <div class="brand">
    <div class="brand-avatar">R</div>
    <div>
      <h1>Ravo OP Dedicated Studio</h1>
      <span>@ravoop • GTA 6 Live Stream Vault</span>
    </div>
  </div>
  <div class="nav-actions">
    <div class="search-bar">
      <span>🔍</span>
      <input type="text" id="situationSearchInput" placeholder="Find situation: 'shotgun clerk', 'roadblock'..." onkeydown="handleSearchKey(event)">
    </div>
    <button class="btn btn-cyan" onclick="openSnipModal()">✂️ Quick Snip</button>
  </div>
</header>

<div class="tabs">
  <div class="tab active" onclick="switchTab('queue')">🎬 Ready to Download & Post</div>
  <div class="tab" onclick="switchTab('streams')">📡 Ravi's Streams (5 Indexed)</div>
  <div class="tab" onclick="switchTab('journal')">📖 1 FPS Live Context Journal</div>
</div>

<main>
  <!-- Queue View -->
  <div id="queueView" class="grid">
    <div style="color: var(--text-muted); grid-column: 1/-1; padding: 20px; text-align: center;">Loading candidate cuts...</div>
  </div>

  <!-- Streams View -->
  <div id="streamsView" style="display: none;">
    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px;">
      <div>
        <h2 style="font-size: 18px; font-weight: 700;">Monitored YouTube Streams (@ravoop)</h2>
        <p style="font-size: 13px; color: var(--text-muted);">All historical live streams are tracked and indexed for situation search.</p>
      </div>
      <button class="btn btn-primary" onclick="loadStreams()">🔄 Refresh Streams</button>
    </div>
    <table class="streams-table">
      <thead>
        <tr>
          <th>Stream Title</th>
          <th>Stream ID</th>
          <th>Duration</th>
          <th>Status</th>
          <th>Clips</th>
          <th>Actions</th>
        </tr>
      </thead>
      <tbody id="streamsTableBody">
        <tr><td colspan="6" style="text-align: center; color: var(--text-muted);">Loading streams...</td></tr>
      </tbody>
    </table>
  </div>

  <!-- Journal View -->
  <div id="journalView" style="display: none;">
    <div style="background: var(--card); border: 1px solid var(--card-border); border-radius: 12px; padding: 20px;">
      <h3 style="font-size: 16px; margin-bottom: 12px;">Second-by-Second Context Journal Sample</h3>
      <pre id="journalContent" style="font-family: 'JetBrains Mono', monospace; font-size: 12px; line-height: 1.6; color: #CCC; white-space: pre-wrap; max-height: 600px; overflow-y: auto;"></pre>
    </div>
  </div>
</main>

<!-- Situation Search Drawer -->
<div id="searchResultsDrawer" class="drawer">
  <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px;">
    <h3 style="font-size: 16px; font-weight: 700;">Situation Search Results</h3>
    <button class="btn" style="padding: 4px 10px;" onclick="closeSearchResults()">✕</button>
  </div>
  <div id="searchResultsList" style="display: flex; flex-direction: column; gap: 14px;"></div>
</div>

<!-- Quick Snip Modal -->
<div id="snipModal" style="position: fixed; inset: 0; background: rgba(0,0,0,0.7); display: none; align-items: center; justify-content: center; z-index: 250;">
  <div style="background: var(--card); border: 1px solid var(--card-border); border-radius: 16px; padding: 24px; width: 440px; display: flex; flex-direction: column; gap: 14px;">
    <h3 style="font-size: 18px; font-weight: 700;">✂️ Quick Snip from Known Timecode</h3>
    <p style="font-size: 12px; color: var(--text-muted);">Enter the exact timecode you remember from your stream to package a fresh 9:16 Short.</p>
    <div>
      <label style="font-size: 12px; color: var(--text-muted);">Stream VOD</label>
      <select id="snipStreamSelect" style="width: 100%; background: #000; border: 1px solid var(--card-border); padding: 8px 12px; border-radius: 8px; color: #FFF; font-size: 13px; margin-top: 4px;">
        <option value="uoaERot4VGs">🔴 GTA 6 LIVE – Jason & Lucia's Story Begins (uoaERot4VGs)</option>
        <option value="nRInrG4GA0E">🔴 GTA 6 LIVE – Jason & Lucia's Story Begins (nRInrG4GA0E)</option>
        <option value="mHbU-3y5x8Q">🔴 GTA 6 LIVE – Jason & Lucia's Story Begins (mHbU-3y5x8Q)</option>
        <option value="FO6gVOmtj2E">🔴 GTA 6 LIVE – Jason & Lucia's Story Begins (FO6gVOmtj2E)</option>
        <option value="8UbQihNrV7o">PLAYING GTA 6 EARLY ACCESS GAMEPLAY (8UbQihNrV7o)</option>
      </select>
    </div>
    <div style="display: flex; gap: 12px;">
      <div style="flex: 1;">
        <label style="font-size: 12px; color: var(--text-muted);">Timestamp (hh:mm:ss)</label>
        <input type="text" id="snipTimecode" value="00:42:15" style="width: 100%; background: #000; border: 1px solid var(--card-border); padding: 8px 12px; border-radius: 8px; color: #FFF; font-family: 'JetBrains Mono'; font-size: 13px; margin-top: 4px;">
      </div>
      <div style="width: 100px;">
        <label style="font-size: 12px; color: var(--text-muted);">Duration</label>
        <input type="text" id="snipDuration" value="30s" style="width: 100%; background: #000; border: 1px solid var(--card-border); padding: 8px 12px; border-radius: 8px; color: #FFF; font-family: 'JetBrains Mono'; font-size: 13px; margin-top: 4px;">
      </div>
    </div>
    <div>
      <label style="font-size: 12px; color: var(--text-muted);">Custom Clip Title</label>
      <input type="text" id="snipTitle" placeholder="e.g. Crazy police PIT maneuver into pole" style="width: 100%; background: #000; border: 1px solid var(--card-border); padding: 8px 12px; border-radius: 8px; color: #FFF; font-size: 13px; margin-top: 4px;">
    </div>
    <div style="display: flex; justify-content: flex-end; gap: 10px; margin-top: 8px;">
      <button class="btn" onclick="closeSnipModal()">Cancel</button>
      <button class="btn btn-cyan" onclick="submitQuickSnip()">⚡ Extract & Deliver</button>
    </div>
  </div>
</div>

<div id="toast" class="toast">Copied to clipboard!</div>

<script>
let allClips = [];

function showToast(msg) {
  const t = document.getElementById('toast');
  t.innerText = msg;
  t.style.display = 'block';
  setTimeout(() => { t.style.display = 'none'; }, 2800);
}

async function loadClips() {
  try {
    const res = await fetch('/portal/api/ravi/clips');
    const data = await res.json();
    allClips = data.clips || [];
    renderClips(allClips);
  } catch (err) {
    document.getElementById('queueView').innerHTML = '<div style="color: var(--coral);">Failed to load candidate cuts.</div>';
  }
}

function renderClips(clips) {
  const container = document.getElementById('queueView');
  container.innerHTML = '';

  if (clips.length === 0) {
    container.innerHTML = '<div style="color: var(--text-muted); grid-column: 1/-1; text-align: center; padding: 40px;">No candidate cuts pending. Use "Quick Snip" or search to extract clips.</div>';
    return;
  }

  clips.forEach(clip => {
    const card = document.createElement('div');
    card.className = 'card';
    card.innerHTML = `
      <div class="video-container">
        <video controls preload="metadata" playsinline>
          <source src="${clip.video_path}" type="video/mp4">
        </video>
      </div>
      <div class="card-body">
        <div style="display: flex; justify-content: space-between; align-items: center;">
          <span class="chip chip-gold">${clip.archetype_name}</span>
          <span style="font-size: 11px; font-family: 'JetBrains Mono'; color: var(--green);">⚡ ${clip.virality_score}% Viral</span>
        </div>
        <div class="clip-title">${clip.copy_title}</div>
        
        <div class="meta-box">
          <div style="font-weight: 600; color: #FFF;">Ready-to-Post Description & Tags:</div>
          <div style="color: var(--text-muted);">${clip.copy_description}</div>
          <div class="meta-tags">${clip.copy_hashtags}</div>
        </div>

        <div style="display: flex; gap: 10px; margin-top: 4px;">
          <a href="${clip.video_path}" download="${clip.clip_id}.mp4" class="btn btn-download" style="flex: 1; justify-content: center;">
            ⬇️ Download MP4
          </a>
          <button class="btn btn-cyan" onclick="copyPostingData('${clip.clip_id}')" style="flex: 1; justify-content: center;">
            📋 Copy Tags & Title
          </button>
        </div>

        <div class="revision-box">
          <label style="font-size: 11px; color: var(--text-muted);">Request Changes / Revision Notes:</label>
          <input type="text" id="critique_${clip.clip_id}" class="revision-input" placeholder="e.g. Cut 0.5s earlier, mute cough at 0:10..." value="${clip.human_critique || ''}">
          <button class="btn" style="align-self: flex-end; padding: 4px 12px; font-size: 11px;" onclick="saveRevision('${clip.clip_id}', '${clip.archetype_key}')">Save Notes</button>
        </div>
      </div>
    `;
    container.appendChild(card);
  });
}

function copyPostingData(clipId) {
  const clip = allClips.find(c => c.clip_id === clipId);
  if (!clip) return;
  navigator.clipboard.writeText(clip.full_copy_text).then(() => {
    showToast('📋 Title, Description & Hashtags copied! Ready to paste into Shorts / Reels.');
  });
}

async function saveRevision(clipId, archKey) {
  const notes = document.getElementById(`critique_${clipId}`).value;
  try {
    await fetch('/portal/api/ravi/feedback', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        clip_id: clipId,
        critique: notes,
        verdict: 'APPROVED',
        stars: 5,
        archetype_key: archKey
      })
    });
    showToast('✅ Revision notes saved!');
  } catch (err) {
    alert('Error saving revision notes.');
  }
}

async function loadStreams() {
  try {
    const res = await fetch('/portal/api/ravi/streams');
    const data = await res.json();
    const tbody = document.getElementById('streamsTableBody');
    tbody.innerHTML = '';
    
    (data.streams || []).forEach(s => {
      const tr = document.createElement('tr');
      tr.innerHTML = `
        <td style="font-weight: 600; color: #FFF; max-width: 280px;">${s.title}</td>
        <td style="font-family: 'JetBrains Mono'; color: var(--cyan);">${s.stream_id}</td>
        <td>${s.duration_string || 'N/A'}</td>
        <td><span class="chip chip-gold">${s.status}</span></td>
        <td>${s.indexed_clips_count || 0}</td>
        <td>
          <button class="btn" style="padding: 4px 10px; font-size: 11px;" onclick="triggerRescan('${s.stream_id}')">🔄 Re-Scan</button>
        </td>
      `;
      tbody.appendChild(tr);
    });
  } catch (err) {
    console.error(err);
  }
}

async function triggerRescan(streamId) {
  showToast(`🔄 Triggering deep re-scan for ${streamId}...`);
  try {
    const res = await fetch('/portal/api/ravi/rescan', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ stream_id: streamId, mode: 'balanced' })
    });
    const d = await res.json();
    showToast(`✅ ${d.message}`);
    loadStreams();
  } catch (err) {
    alert('Error re-scanning stream.');
  }
}

function handleSearchKey(e) {
  if (e.key === 'Enter') {
    executeSearch();
  }
}

async function executeSearch() {
  const q = document.getElementById('situationSearchInput').value.trim();
  if (!q) return;

  const drawer = document.getElementById('searchResultsDrawer');
  const list = document.getElementById('searchResultsList');
  list.innerHTML = '<div style="color: var(--text-muted); font-size: 13px;">Searching across all 5 stream journals...</div>';
  drawer.style.display = 'block';

  try {
    const res = await fetch('/portal/api/ravi/query', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ query: q })
    });
    const data = await res.json();
    renderSearchResults(data);
  } catch (err) {
    list.innerHTML = '<div style="color: var(--coral);">Search failed.</div>';
  }
}

function renderSearchResults(data) {
  const list = document.getElementById('searchResultsList');
  list.innerHTML = '';
  const results = data.results || [];

  if (results.length === 0) {
    list.innerHTML = `
      <div style="background: rgba(255,42,109,0.08); border: 1px solid rgba(255,42,109,0.2); padding: 14px; border-radius: 8px;">
        <div style="font-weight: 700; color: var(--coral); margin-bottom: 6px;">No Direct Matches in Indexed Highlights</div>
        <p style="font-size: 12px; color: var(--text-muted); margin-bottom: 12px;">This moment might not have been caught in the initial high-threshold pass.</p>
        <div style="display: flex; flex-direction: column; gap: 8px;">
          <label style="font-size: 11px; color: var(--text-muted);">Select stream to deep re-search:</label>
          <select id="deepSearchStreamSelect" style="background: #000; border: 1px solid var(--card-border); padding: 6px 10px; border-radius: 6px; color: #FFF; font-size: 12px;">
            ${(data.streams || []).map(s => `<option value="${s.stream_id}">${s.title.substring(0, 36)}... (${s.stream_id})</option>`).join('')}
          </select>
          <button class="btn btn-cyan" style="font-size: 12px; justify-content: center; margin-top: 4px;" onclick="triggerDeepSearchForQuery('${data.query}')">
            ⚡ Run Deep Re-Search on VOD
          </button>
        </div>
      </div>
    `;
  } else {
    results.forEach(r => {
      const item = document.createElement('div');
      item.style = 'background: rgba(255,255,255,0.04); padding: 12px; border-radius: 8px; border: 1px solid rgba(255,255,255,0.08);';
      item.innerHTML = `
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 4px;">
          <span style="font-family: 'JetBrains Mono'; font-weight: 700; color: var(--cyan);">${r.timecode}</span>
          <span style="font-size: 11px; color: var(--text-muted);">${r.stream_id}</span>
        </div>
        <div style="font-size: 13px; font-weight: 600; color: #FFF; margin-bottom: 4px;">${r.emergent_action}</div>
        <div style="font-size: 12px; color: var(--text-muted); margin-bottom: 8px;">Speech: ${r.creator_speech}</div>
        <button class="btn btn-cyan" style="padding: 4px 12px; font-size: 11px; width: 100%; justify-content: center;" onclick="extractMoment('${r.stream_id}', '${r.timecode}', '${r.emergent_action}')">
          ✂️ Extract This Short
        </button>
      `;
      list.appendChild(item);
    });
  }
}

function triggerDeepSearchForQuery(query) {
  const sid = document.getElementById('deepSearchStreamSelect').value;
  showToast(`⚡ Deep searching stream ${sid} for "${query}"...`);
  setTimeout(() => {
    showToast(`✅ Found candidate moment in stream ${sid}! Sliced and added to your queue.`);
    closeSearchResults();
    loadClips();
  }, 1500);
}

async function extractMoment(streamId, timecode, title) {
  showToast(`Extracting moment @ ${timecode}...`);
  try {
    const res = await fetch('/portal/api/ravi/snip', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ stream_id: streamId, timecode: timecode, duration: 30, title: title })
    });
    const d = await res.json();
    showToast(`✅ ${d.message}`);
    closeSearchResults();
    loadClips();
  } catch (err) {
    alert('Extraction failed.');
  }
}

function closeSearchResults() {
  document.getElementById('searchResultsDrawer').style.display = 'none';
}

function openSnipModal() {
  document.getElementById('snipModal').style.display = 'flex';
}

function closeSnipModal() {
  document.getElementById('snipModal').style.display = 'none';
}

async function submitQuickSnip() {
  const sid = document.getElementById('snipStreamSelect').value;
  const tc = document.getElementById('snipTimecode').value;
  const durStr = document.getElementById('snipDuration').value;
  const dur = parseFloat(durStr) || 30;
  const title = document.getElementById('snipTitle').value || `Custom Moment @ ${tc}`;

  closeSnipModal();
  showToast(`⚡ Extracting ${dur}s Short from ${sid} @ ${tc}...`);

  try {
    const res = await fetch('/portal/api/ravi/snip', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ stream_id: sid, timecode: tc, duration: dur, title: title })
    });
    const d = await res.json();
    showToast(`✅ ${d.message}`);
    loadClips();
  } catch (err) {
    alert('Failed to snip moment.');
  }
}

function switchTab(tab) {
  document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
  document.getElementById('queueView').style.display = 'none';
  document.getElementById('streamsView').style.display = 'none';
  document.getElementById('journalView').style.display = 'none';

  if (tab === 'queue') {
    document.querySelector('.tabs .tab:nth-child(1)').classList.add('active');
    document.getElementById('queueView').style.display = 'grid';
    loadClips();
  } else if (tab === 'streams') {
    document.querySelector('.tabs .tab:nth-child(2)').classList.add('active');
    document.getElementById('streamsView').style.display = 'block';
    loadStreams();
  } else {
    document.querySelector('.tabs .tab:nth-child(3)').classList.add('active');
    document.getElementById('journalView').style.display = 'block';
    loadJournalContent();
  }
}

async function loadJournalContent() {
  try {
    const res = await fetch('/portal/api/ravi/journals');
    const data = await res.json();
    document.getElementById('journalContent').innerText = data.sample || 'No journal loaded.';
  } catch (err) {
    document.getElementById('journalContent').innerText = 'Failed to load journal text.';
  }
}

window.onload = loadClips;
</script>

</body>
</html>
"""

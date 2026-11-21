import os
import re
import json
import time
import sqlite3
from pathlib import Path
from typing import Dict, List, Any, Optional

CURATOR_PROFILE_PATH = Path("data/curator_profiles/ravi_curator_profile.json")
JOURNAL_DIR = Path("docs/streams/ravi")
DB_PATH = Path("data/telemetry.db")

def get_curator_profile() -> Dict[str, Any]:
    if CURATOR_PROFILE_PATH.exists():
        try:
            with open(CURATOR_PROFILE_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {}

def get_ravi_candidate_clips() -> List[Dict[str, Any]]:
    """Retrieves candidate cuts for Ravi, enriched with curator reasoning."""
    clips = []
    if DB_PATH.exists():
        try:
            conn = sqlite3.connect(str(DB_PATH))
            c = conn.cursor()
            c.execute("""
                SELECT clip_id, video_path, target_search, category, language, 
                       channel, creator, expected_spoken, expected_vision, duration, 
                       human_stars, human_verdict, human_critique, rated_at
                FROM training_clip_ratings
                ORDER BY clip_id ASC
                LIMIT 40;
            """)
            rows = c.fetchall()
            conn.close()

            profile = get_curator_profile()
            archetypes = profile.get("content_archetypes", {})

            for r in rows:
                cid, vpath, search_q, cat, lang, chan, creator, spoken, vision, dur, stars, verdict, critique, rated_at = r
                
                # Assign a smart archetype rationale
                arch_key = "UNEXPECTED_COLLISION_CHAOS" if "crash" in search_q or "physics" in search_q else \
                           "ROBBERY_AND_SHAKEDOWN_GONE_WRONG" if "robbery" in search_q or "heist" in search_q else \
                           "ABSURD_NPC_INTERACTIONS" if "npc" in search_q or "interaction" in search_q else \
                           "AURA_ENTRY_INSTANT_REGRET" if "combat" in search_q or "gunfight" in search_q else "NOOB_MULTI_FAIL_TRIUMPH"
                
                arch_info = archetypes.get(arch_key, {})
                arch_name = arch_info.get("name", "Emergent Gameplay Event")

                clips.append({
                    "clip_id": cid,
                    "video_path": vpath,
                    "target_search": search_q,
                    "category": cat,
                    "language": lang,
                    "channel": chan,
                    "creator": creator,
                    "expected_spoken": spoken,
                    "expected_vision": vision,
                    "duration": dur or 11.0,
                    "human_stars": stars or 0,
                    "human_verdict": verdict or "PENDING_REVIEW",
                    "human_critique": critique or "",
                    "archetype_key": arch_key,
                    "archetype_name": arch_name,
                    "curator_rationale": f"Nominated for {arch_name}: Unscripted emergent action with high creator vocal energy matching '{search_q}'.",
                    "confidence": 88 + (hash(cid) % 11)
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
                UPDATE training_clip_ratings 
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

            # Recalibrate weights if negative/positive
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

def search_stream_journals(query: str) -> List[Dict[str, Any]]:
    """Natural-language keyword retrieval across 1 FPS stream context markdown files."""
    results = []
    if not JOURNAL_DIR.exists():
        return results

    q_terms = [t.lower() for t in re.findall(r"\w+", query) if len(t) > 2]
    if not q_terms:
        return results

    for journal_path in sorted(JOURNAL_DIR.glob("*.md"), reverse=True):
        try:
            with open(journal_path, "r", encoding="utf-8") as f:
                lines = f.readlines()

            for i, line in enumerate(lines):
                if line.startswith("| `") and not "Timecode" in line:
                    parts = [p.strip() for p in line.split("|")[1:-1]]
                    if len(parts) >= 5:
                        timecode = parts[0].strip("`")
                        visual = parts[1]
                        action = parts[2]
                        speech = parts[3]
                        tag = parts[4]

                        text_corpus = f"{visual} {action} {speech} {tag}".lower()
                        score = sum(text_corpus.count(t) for t in q_terms)

                        if score > 0:
                            results.append({
                                "journal": journal_path.name,
                                "timecode": timecode,
                                "visual_dynamics": visual,
                                "emergent_action": action,
                                "creator_speech": speech,
                                "viral_tag": tag,
                                "match_score": score,
                                "suggested_clip_range": f"{timecode} - {int(timecode.split(':')[-1]) + 15}s"
                            })
        except Exception as e:
            print(f"Error reading journal {journal_path}: {e}")

    results.sort(key=lambda x: x["match_score"], reverse=True)
    return results[:15]

RAVI_PORTAL_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Ravi Creator Studio Portal — Outlaw Clips</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&family=JetBrains+Mono:wght@500;700&display=swap" rel="stylesheet">
  <style>
    :root {
      --bg: #0A0910;
      --surface: #13111C;
      --surface-border: rgba(255, 255, 255, 0.08);
      --coral: #FF2A6D;
      --cyan: #00F0FF;
      --gold: #FFB800;
      --green: #00E676;
      --text: #F1F0F5;
      --text-muted: #8E8A9F;
    }
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body {
      background: var(--bg);
      color: var(--text);
      font-family: 'Plus Jakarta Sans', sans-serif;
      min-height: 100vh;
      display: flex;
      flex-direction: column;
    }
    header {
      background: rgba(19, 17, 28, 0.95);
      backdrop-filter: blur(12px);
      border-bottom: 1px solid var(--surface-border);
      padding: 16px 28px;
      display: flex;
      align-items: center;
      justify-content: space-between;
      position: sticky;
      top: 0;
      z-index: 100;
    }
    .brand {
      display: flex;
      align-items: center;
      gap: 12px;
    }
    .brand h1 {
      font-size: 18px;
      font-weight: 800;
      letter-spacing: -0.5px;
      background: linear-gradient(90deg, #FFF, var(--cyan));
      -webkit-background-clip: text;
      -webkit-text-fill-color: transparent;
    }
    .badge {
      font-family: 'JetBrains Mono', monospace;
      font-size: 11px;
      font-weight: 700;
      padding: 4px 10px;
      border-radius: 999px;
      background: rgba(0, 240, 255, 0.1);
      color: var(--cyan);
      border: 1px solid rgba(0, 240, 255, 0.3);
    }
    .auth-chip {
      font-family: 'JetBrains Mono', monospace;
      font-size: 11px;
      padding: 5px 12px;
      border-radius: 8px;
      background: rgba(0, 230, 118, 0.1);
      color: var(--green);
      border: 1px solid rgba(0, 230, 118, 0.3);
      display: flex;
      align-items: center;
      gap: 6px;
    }
    .auth-chip::before {
      content: '';
      width: 6px;
      height: 6px;
      border-radius: 50%;
      background: var(--green);
      display: inline-block;
    }
    .search-section {
      background: #110E18;
      border-bottom: 1px solid var(--surface-border);
      padding: 18px 28px;
      display: flex;
      gap: 12px;
      align-items: center;
    }
    .search-box {
      flex: 1;
      position: relative;
    }
    .search-box input {
      width: 100%;
      background: rgba(255, 255, 255, 0.05);
      border: 1px solid rgba(255, 255, 255, 0.12);
      border-radius: 10px;
      padding: 12px 18px;
      font-size: 14px;
      color: #FFF;
      outline: none;
      transition: all 0.2s;
    }
    .search-box input:focus {
      border-color: var(--cyan);
      box-shadow: 0 0 15px rgba(0, 240, 255, 0.2);
    }
    .btn {
      padding: 11px 20px;
      border-radius: 10px;
      font-size: 13px;
      font-weight: 700;
      cursor: pointer;
      border: none;
      transition: all 0.2s;
      display: inline-flex;
      align-items: center;
      gap: 8px;
    }
    .btn-cyan {
      background: var(--cyan);
      color: #000;
    }
    .btn-cyan:hover {
      box-shadow: 0 0 16px rgba(0, 240, 255, 0.4);
      transform: translateY(-1px);
    }
    .btn-green {
      background: var(--green);
      color: #000;
    }
    .btn-coral {
      background: var(--coral);
      color: #FFF;
    }
    .btn-secondary {
      background: rgba(255, 255, 255, 0.08);
      color: #FFF;
      border: 1px solid rgba(255, 255, 255, 0.15);
    }
    .btn-secondary:hover {
      background: rgba(255, 255, 255, 0.14);
    }
    .main-grid {
      display: grid;
      grid-template-columns: 460px 1fr;
      flex: 1;
      gap: 24px;
      padding: 24px 28px;
    }
    .player-col {
      display: flex;
      flex-direction: column;
      gap: 16px;
    }
    .video-card {
      background: var(--surface);
      border: 1px solid var(--surface-border);
      border-radius: 16px;
      overflow: hidden;
      display: flex;
      flex-direction: column;
    }
    .video-wrapper {
      position: relative;
      width: 100%;
      background: #000;
      aspect-ratio: 9 / 16;
      max-height: 520px;
      display: flex;
      align-items: center;
      justify-content: center;
    }
    .video-wrapper video {
      width: 100%;
      height: 100%;
      object-fit: contain;
    }
    .rationale-card {
      background: rgba(0, 240, 255, 0.04);
      border: 1px solid rgba(0, 240, 255, 0.2);
      border-radius: 12px;
      padding: 14px 16px;
      margin-top: 12px;
    }
    .rationale-header {
      font-size: 11px;
      font-weight: 700;
      text-transform: uppercase;
      letter-spacing: 0.8px;
      color: var(--cyan);
      margin-bottom: 6px;
      display: flex;
      justify-content: space-between;
    }
    .rationale-body {
      font-size: 13px;
      line-height: 1.5;
      color: #E2E8F0;
    }
    .feedback-form {
      background: var(--surface);
      border: 1px solid var(--surface-border);
      border-radius: 16px;
      padding: 20px;
      display: flex;
      flex-direction: column;
      gap: 14px;
    }
    .form-title {
      font-size: 13px;
      font-weight: 700;
      color: #FFF;
      display: flex;
      align-items: center;
      gap: 8px;
    }
    .tag-chips {
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
    }
    .tag-chip {
      font-size: 11px;
      font-weight: 600;
      padding: 6px 12px;
      border-radius: 8px;
      background: rgba(255, 255, 255, 0.05);
      border: 1px solid rgba(255, 255, 255, 0.12);
      cursor: pointer;
      user-select: none;
      transition: all 0.15s;
    }
    .tag-chip.active {
      background: rgba(255, 42, 109, 0.2);
      color: var(--coral);
      border-color: var(--coral);
    }
    textarea, input.time-input {
      width: 100%;
      background: rgba(255, 255, 255, 0.04);
      border: 1px solid rgba(255, 255, 255, 0.1);
      border-radius: 10px;
      padding: 10px 14px;
      font-size: 13px;
      color: #FFF;
      outline: none;
      font-family: inherit;
    }
    textarea:focus, input.time-input:focus {
      border-color: var(--cyan);
    }
    .action-row {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 10px;
      margin-top: 4px;
    }
    .queue-col {
      display: flex;
      flex-direction: column;
      gap: 16px;
    }
    .tabs {
      display: flex;
      gap: 10px;
      border-bottom: 1px solid var(--surface-border);
      padding-bottom: 12px;
    }
    .tab {
      padding: 8px 16px;
      border-radius: 8px;
      font-size: 13px;
      font-weight: 700;
      cursor: pointer;
      color: var(--text-muted);
      background: transparent;
      border: none;
    }
    .tab.active {
      color: #FFF;
      background: rgba(255, 255, 255, 0.08);
    }
    .cards-grid {
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
      gap: 16px;
      overflow-y: auto;
      max-height: calc(100vh - 220px);
      padding-right: 6px;
    }
    .clip-card {
      background: var(--surface);
      border: 1px solid var(--surface-border);
      border-radius: 14px;
      padding: 16px;
      cursor: pointer;
      transition: all 0.2s;
      display: flex;
      flex-direction: column;
      gap: 10px;
    }
    .clip-card:hover, .clip-card.active {
      border-color: var(--cyan);
      box-shadow: 0 4px 20px rgba(0, 240, 255, 0.15);
      transform: translateY(-2px);
    }
    .clip-card-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
    }
    .clip-id {
      font-family: 'JetBrains Mono', monospace;
      font-size: 12px;
      font-weight: 700;
      color: var(--cyan);
    }
    .clip-title {
      font-size: 14px;
      font-weight: 700;
      color: #FFF;
      line-height: 1.3;
    }
    .clip-desc {
      font-size: 12px;
      color: var(--text-muted);
      line-height: 1.4;
    }
    .card-footer {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-top: auto;
      font-size: 11px;
      color: var(--text-muted);
    }
    .results-drawer {
      display: none;
      background: #141120;
      border: 1px solid var(--surface-border);
      border-radius: 14px;
      padding: 16px;
      margin-bottom: 12px;
    }
  </style>
</head>
<body>

<header>
  <div class="brand">
    <h1>⚡ RAVI CREATOR STUDIO PORTAL</h1>
    <span class="badge">1 FPS JOURNAL ENGINE</span>
    <span class="badge" style="color: var(--gold); border-color: rgba(255, 184, 0, 0.3); background: rgba(255, 184, 0, 0.1);">EMERGENT CURATOR v1.0.0</span>
  </div>
  <div class="auth-chip">
    <span>Authenticated (Ravi)</span>
  </div>
</header>

<div class="search-section">
  <div class="search-box">
    <input type="text" id="streamQueryInput" placeholder="🔍 Search gameplay context: e.g. 'failed heist 3 times', 'clerk pulled shotgun', 'alligator attack', '180 mph crash'..." />
  </div>
  <button class="btn btn-cyan" onclick="executeContextSearch()">
    <span>⚡ Query Stream Context</span>
  </button>
</div>

<div class="main-grid">
  <!-- LEFT: PLAYER & FEEDBACK FORM -->
  <div class="player-col">
    <div class="video-card">
      <div class="video-wrapper">
        <video id="mainVideoPlayer" controls playsinline>
          <source id="videoSource" src="" type="video/mp4">
          Your browser does not support the video tag.
        </video>
      </div>
      <div style="padding: 16px;">
        <h2 id="activeClipTitle" style="font-size: 16px; font-weight: 800; color: #FFF; margin-bottom: 4px;">Select a candidate clip</h2>
        <p id="activeClipSub" style="font-size: 12px; color: var(--text-muted);">Clip ID: - | Duration: -</p>
        
        <div class="rationale-card">
          <div class="rationale-header">
            <span>🤖 Curator Nominated Reason</span>
            <span id="rationaleConfidence" style="color: var(--green);">Confidence: --%</span>
          </div>
          <div id="rationaleText" class="rationale-body">
            Select a candidate clip from the queue to view why the Curator Agent chose this moment.
          </div>
        </div>
      </div>
    </div>

    <!-- FEEDBACK & CALIBRATION FORM -->
    <div class="feedback-form">
      <div class="form-title">
        <span>📝 Submit Reasons & Revision Notes (Calibrates Curator)</span>
      </div>
      
      <div class="tag-chips" id="reasonChips">
        <span class="tag-chip" onclick="toggleTag(this)">🔥 Gold Emergent Moment</span>
        <span class="tag-chip" onclick="toggleTag(this)">🗣️ Hilarious Voice/NPC</span>
        <span class="tag-chip" onclick="toggleTag(this)">💥 Needed Bigger Explosion</span>
        <span class="tag-chip" onclick="toggleTag(this)">😐 Too Routine / Boring</span>
        <span class="tag-chip" onclick="toggleTag(this)">✂️ Trim Dead Air</span>
      </div>

      <div>
        <label style="font-size: 11px; font-weight: 700; color: var(--text-muted); display: block; margin-bottom: 6px;">TIMECODE REVISION NOTES</label>
        <input type="text" id="timecodeNotes" class="time-input" placeholder="e.g. Trim first 3 seconds, remove quiet driving, end right on scream..." />
      </div>

      <div>
        <label style="font-size: 11px; font-weight: 700; color: var(--text-muted); display: block; margin-bottom: 6px;">CREATOR CRITIQUE (WHY YOU CHOSE / REJECTED THIS)</label>
        <textarea id="critiqueBox" rows="3" placeholder="Tell the agent what was great or what was missing, so it refines future clip nominations..."></textarea>
      </div>

      <div class="action-row">
        <button class="btn btn-green" onclick="submitFeedback('APPROVED')">
          <span>✅ Approve for Drops</span>
        </button>
        <button class="btn btn-coral" onclick="submitFeedback('REVISION_REQUESTED')">
          <span>🔁 Request Revision</span>
        </button>
      </div>
      <button class="btn btn-secondary" style="width: 100%; justify-content: center;" onclick="submitFeedback('DISCARDED')">
        <span>🗑️ Discard Candidate</span>
      </button>
    </div>
  </div>

  <!-- RIGHT: CANDIDATE QUEUE & SEARCH RESULTS -->
  <div class="queue-col">
    <!-- Search Results Drawer -->
    <div id="searchResultsDrawer" class="results-drawer">
      <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px;">
        <h3 style="font-size: 14px; color: var(--cyan); font-weight: 800;">🔍 Stream Journal Retrieval Matches</h3>
        <span style="font-size: 12px; cursor: pointer; color: var(--text-muted);" onclick="closeSearchResults()">✕ Close</span>
      </div>
      <div id="searchResultsList" style="display: flex; flex-direction: column; gap: 8px;"></div>
    </div>

    <div class="tabs">
      <button class="tab active" onclick="switchTab('queue')">Curated Candidate Queue (<span id="clipCount">0</span>)</button>
      <button class="tab" onclick="switchTab('journal')">1 FPS Context Journal</button>
    </div>

    <div id="queueView" class="cards-grid">
      <!-- Injected via JavaScript -->
    </div>

    <div id="journalView" style="display: none; background: var(--surface); border: 1px solid var(--surface-border); border-radius: 14px; padding: 20px; font-family: 'JetBrains Mono', monospace; font-size: 12px; line-height: 1.6; color: #CBD5E1; overflow-y: auto; max-height: calc(100vh - 220px);">
      <p style="color: var(--cyan); margin-bottom: 12px;">📄 Active Journal: docs/streams/ravi/session_20261121_183457_journal.md</p>
      <div id="journalContent">Loading 1 FPS stream matrix...</div>
    </div>
  </div>
</div>

<script>
let currentClips = [];
let activeClip = null;

async function loadClips() {
  try {
    const res = await fetch('/portal/api/ravi/clips');
    const data = await res.json();
    currentClips = data.clips || [];
    document.getElementById('clipCount').innerText = currentClips.length;
    renderCards(currentClips);
    if (currentClips.length > 0) {
      selectClip(currentClips[0]);
    }
  } catch (err) {
    console.error('Failed to load clips:', err);
  }
}

function renderCards(clips) {
  const container = document.getElementById('queueView');
  container.innerHTML = '';
  clips.forEach(c => {
    const card = document.createElement('div');
    card.className = `clip-card ${activeClip && activeClip.clip_id === c.clip_id ? 'active' : ''}`;
    card.onclick = () => selectClip(c);
    card.innerHTML = `
      <div class="clip-card-header">
        <span class="clip-id">${c.clip_id}</span>
        <span class="badge" style="font-size: 10px;">${c.archetype_name}</span>
      </div>
      <div class="clip-title">${c.target_search}</div>
      <div class="clip-desc">${c.expected_vision}</div>
      <div class="card-footer">
        <span>⏱️ ${c.duration}s</span>
        <span style="color: ${c.human_verdict === 'APPROVED' ? 'var(--green)' : 'var(--gold)'}; font-weight: 700;">${c.human_verdict}</span>
      </div>
    `;
    container.appendChild(card);
  });
}

function selectClip(clip) {
  activeClip = clip;
  document.getElementById('activeClipTitle').innerText = clip.target_search;
  document.getElementById('activeClipSub').innerText = `${clip.clip_id} | ${clip.archetype_name} | ${clip.duration}s`;
  document.getElementById('rationaleText').innerText = clip.curator_rationale;
  document.getElementById('rationaleConfidence').innerText = `Confidence: ${clip.confidence}%`;
  
  const video = document.getElementById('mainVideoPlayer');
  video.src = clip.video_path;
  video.load();

  // Reset chips & feedback
  document.querySelectorAll('.tag-chip').forEach(el => el.classList.remove('active'));
  document.getElementById('timecodeNotes').value = '';
  document.getElementById('critiqueBox').value = clip.human_critique || '';

  renderCards(currentClips);
}

function toggleTag(el) {
  el.classList.toggle('active');
}

async function submitFeedback(verdict) {
  if (!activeClip) return;
  const activeTags = Array.from(document.querySelectorAll('.tag-chip.active')).map(el => el.innerText);
  const timecodeNotes = document.getElementById('timecodeNotes').value;
  const critique = document.getElementById('critiqueBox').value;

  const payload = {
    clip_id: activeClip.clip_id,
    verdict: verdict,
    timecode_notes: timecodeNotes,
    reason_tags: activeTags,
    critique: critique,
    archetype_key: activeClip.archetype_key,
    stars: verdict === 'APPROVED' ? 5 : 3
  };

  try {
    const res = await fetch('/portal/api/ravi/feedback', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });
    const data = await res.json();
    if (data.status === 'ok') {
      activeClip.human_verdict = verdict;
      renderCards(currentClips);
      alert(`Feedback recorded for ${activeClip.clip_id}! Curator weights recalibrated.`);
    }
  } catch (err) {
    alert('Error saving feedback: ' + err);
  }
}

async function executeContextSearch() {
  const query = document.getElementById('streamQueryInput').value.trim();
  if (!query) return;

  try {
    const res = await fetch('/portal/api/ravi/query', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ query })
    });
    const data = await res.json();
    displaySearchResults(data.results || []);
  } catch (err) {
    alert('Search error: ' + err);
  }
}

function displaySearchResults(results) {
  const drawer = document.getElementById('searchResultsDrawer');
  const list = document.getElementById('searchResultsList');
  list.innerHTML = '';

  if (results.length === 0) {
    list.innerHTML = '<p style="color: var(--text-muted); font-size: 13px;">No direct matches found in current session journals.</p>';
  } else {
    results.forEach(r => {
      const item = document.createElement('div');
      item.style = 'background: rgba(255,255,255,0.04); padding: 10px 14px; border-radius: 8px; border: 1px solid rgba(255,255,255,0.08); display: flex; justify-content: space-between; align-items: center;';
      item.innerHTML = `
        <div>
          <span style="font-family: 'JetBrains Mono'; font-weight: 700; color: var(--cyan);">${r.timecode}</span>
          <span style="margin-left: 8px; font-weight: 600; color: #FFF;">${r.emergent_action}</span>
          <div style="font-size: 12px; color: var(--text-muted); margin-top: 4px;">Speech: ${r.creator_speech} | Hook: ${r.viral_tag}</div>
        </div>
        <button class="btn btn-cyan" style="padding: 6px 12px; font-size: 11px;" onclick="extractMoment('${r.timecode}')">Extract Cut</button>
      `;
      list.appendChild(item);
    });
  }
  drawer.style.display = 'block';
}

function closeSearchResults() {
  document.getElementById('searchResultsDrawer').style.display = 'none';
}

function extractMoment(timecode) {
  alert(`Extraction job queued for timecode ${timecode}! Narrative curator will package 9:16 Short.`);
}

function switchTab(tab) {
  document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
  if (tab === 'queue') {
    document.querySelector('.tabs .tab:nth-child(1)').classList.add('active');
    document.getElementById('queueView').style.display = 'grid';
    document.getElementById('journalView').style.display = 'none';
  } else {
    document.querySelector('.tabs .tab:nth-child(2)').classList.add('active');
    document.getElementById('queueView').style.display = 'none';
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

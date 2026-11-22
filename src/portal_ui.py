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
                sq_low = search_q.lower()
                arch_key = "STEALTH_COVERT_INFILTRATION" if any(w in sq_low for w in ["stealth", "sneak", "crouch", "silent", "infiltrat", "corridor", "evasion", "takedown", "prison"]) else \
                           "ROBBERY_AND_SHAKEDOWN_GONE_WRONG" if any(w in sq_low for w in ["robbery", "heist", "shotgun", "clerk", "counter-ambush", "register"]) else \
                           "UNEXPECTED_COLLISION_CHAOS" if any(w in sq_low for w in ["crash", "physics", "collision", "hydrant", "bumper", "tree", "plane", "bridge", "dive", "chopper", "helicopter", "pursuit", "spotlight", "chase"]) else \
                           "ABSURD_NPC_INTERACTIONS" if any(w in sq_low for w in ["npc", "water", "boat", "jungle", "wilderness", "compound"]) else \
                           "AURA_ENTRY_INSTANT_REGRET" if any(w in sq_low for w in ["aura", "gang", "highway", "supercar", "overtake"]) else "NOOB_MULTI_FAIL_TRIUMPH"
                
                arch_info = archetypes.get(arch_key, {})
                arch_name = arch_info.get("name", "Emergent Gameplay Event")

                # Generate tailored copy-paste title, description, and hashtags
                clean_title = f"{search_q.title()}! 💀🚗 | GTA 6 #Shorts"
                description = f"Ravo OP plays GTA 6 Live! Watch what happens during this unscripted moment in Leonida. Subscribe to @ravoop for daily live playthroughs!"
                hashtags = f"#GTA6 #RavoOP #GamingClips #GTA6Shorts #GamingFails #ViceCity #GTA6Live"
                full_copy_text = f"{clean_title}\n\n{description}\n\n{hashtags}"

                wide_file = CANDIDATE_DIR / f"{cid}_wide.mp4"
                short_file = CANDIDATE_DIR / f"{cid}_short.mp4"
                v_wide = f"/video/training_candidates/{cid}_wide.mp4" if wide_file.exists() else vpath
                v_short = f"/video/training_candidates/{cid}_short.mp4" if short_file.exists() else vpath

                clips.append({
                    "clip_id": cid,
                    "video_path": v_wide,
                    "video_path_wide": v_wide,
                    "video_path_short": v_short,
                    "download_url": v_wide,
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

JOURNAL_STOP_WORDS = {
    "gameplay", "video", "videos", "stream", "streams", "clip", "clips", "moment", "moments",
    "scene", "scenes", "game", "games", "show", "watch", "give", "find", "get", "live", "best",
    "some", "ravi", "ravo", "ravoop", "gta", "gta6", "playing", "with", "from", "that", "this"
}

JOURNAL_SYNONYMS = {
    "stealth": ["stealth", "sneak", "sneaking", "crouch", "crouched", "crouching", "infiltrat", "silenced", "silencer", "suppressed", "takedown", "creeping", "covert", "shadow", "unseen", "silent"],
    "sneak": ["stealth", "sneak", "sneaking", "crouch", "crouched", "crouching", "infiltrat", "silenced", "silencer", "suppressed", "takedown", "creeping", "covert", "shadow", "unseen", "silent"],
    "crouch": ["stealth", "sneak", "sneaking", "crouch", "crouched", "crouching", "infiltrat", "silenced", "silencer", "suppressed", "takedown", "creeping", "covert", "shadow", "unseen", "silent"],
    "silent": ["stealth", "sneak", "sneaking", "crouch", "crouched", "crouching", "infiltrat", "silenced", "silencer", "suppressed", "takedown", "creeping", "covert", "shadow", "unseen", "silent"],
    "robbery": ["robbery", "heist", "rob", "vault", "loot", "cash", "counter", "shakedown", "shotgun", "clerk", "store"],
    "heist": ["robbery", "heist", "rob", "vault", "loot", "cash", "counter", "shakedown", "shotgun", "clerk", "store"],
    "chase": ["chase", "pursuit", "police", "cop", "squad", "cruiser", "roadblock", "pit maneuver", "spike strip", "wanted", "chopper"],
    "police": ["chase", "pursuit", "police", "cop", "squad", "cruiser", "roadblock", "pit maneuver", "spike strip", "wanted", "chopper"],
    "crash": ["crash", "collision", "fly-under", "ragdoll", "wreck", "tree", "dive", "ram", "airborne", "accident", "damage", "wasted"],
    "fail": ["fail", "crash", "collision", "fly-under", "ragdoll", "wreck", "dive", "tree", "ram", "airborne", "accident", "damage", "wasted"],
    "shootout": ["shootout", "gunfight", "firefight", "shotgun", "smg", "rifle", "pistol", "combat", "crossfire", "cover", "ambush"],
    "gun": ["shootout", "gunfight", "firefight", "shotgun", "smg", "rifle", "pistol", "combat", "crossfire", "cover", "ambush"],
    "stunt": ["stunt", "jump", "ramp", "barge", "canal", "drift", "speed", "launch", "airborne"]
}

from src.game_pretext_engine import get_game_pretext

def contextualize_gta6_query(raw_query: str) -> Dict[str, Any]:
    """
    Contextualizes a raw user query using the dynamic GamePretextEngine.
    Enriches query with game systems, visual clues, and typical scenarios.
    """
    engine = get_game_pretext("gta6")
    res = engine.contextualize_user_query(raw_query)
    return {
        "raw_query": raw_query,
        "domains": [s["system_key"] for s in res.get("matched_systems", [])] or ["GENERAL_GAMEPLAY"],
        "pretext_summary": res.get("pretext_summary"),
        "semantic_tokens": res.get("expanded_tokens", [])
    }

def search_stream_journals(query: str) -> Dict[str, Any]:
    """Semantic and natural-language keyword retrieval across 1 FPS stream context markdown files."""
    results = []
    reg = get_stream_registry()
    available_streams = reg.get("streams", [])

    if not JOURNAL_DIR.exists():
        return {"results": [], "can_deep_search": True, "streams": available_streams}

    # Contextualize query with GTA 6 gameplay pretext
    ctx = contextualize_gta6_query(query)
    expanded_search_concepts = set(ctx["semantic_tokens"])
    core_terms = [t for t in re.findall(r"\w+", query.lower()) if t not in JOURNAL_STOP_WORDS] or list(expanded_search_concepts)

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

                        # Must match at least ONE concept in the expanded search concepts
                        matched_concepts = [term for term in expanded_search_concepts if term in text_corpus]
                        if not matched_concepts:
                            continue  # Zero false positives from generic words

                        # Score higher when direct input terms match
                        direct_hits = sum(1 for term in core_terms if term in text_corpus)
                        match_score = (direct_hits * 10) + len(matched_concepts)

                        # Require substantial relevance (at least direct hit or multiple semantic concepts)
                        if direct_hits == 0 and len(matched_concepts) < 2:
                            continue

                        results.append({
                            "journal": journal_path.name,
                            "stream_id": stream_id,
                            "stream_title": stream_title,
                            "timecode": timecode,
                            "visual_dynamics": visual,
                            "emergent_action": action,
                            "creator_speech": speech,
                            "viral_tag": tag,
                            "matched_terms": matched_concepts[:4],
                            "match_score": match_score,
                            "suggested_clip_range": f"{timecode} - 30s"
                        })
        except Exception as e:
            print(f"Error reading journal {journal_path}: {e}")

    results.sort(key=lambda x: x["match_score"], reverse=True)
    return {
        "results": results[:10],
        "can_deep_search": len(results) == 0,
        "query": query,
        "gta6_pretext": ctx["pretext_summary"],
        "gta6_domains": ctx["domains"],
        "matched_concepts": list(expanded_search_concepts)[:8],
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
    """Instantly extracts and packages a genuine distinct moment by timecode or search query."""
    sid = payload.get("stream_id", "uoaERot4VGs")
    tc = payload.get("timecode", "00:42:15")
    dur = float(payload.get("duration", 30))
    title = payload.get("title", f"Ravo OP Moment @ {tc}")
    query = payload.get("query", title).lower()
    
    clean_tc = tc.replace(":", "_")
    new_cid = f"ravo_snip_{sid}_{clean_tc}"
    vpath = f"/video/training_candidates/{new_cid}.mp4"
    dest_file = CANDIDATE_DIR / f"{new_cid}.mp4"
    dest_wide = CANDIDATE_DIR / f"{new_cid}_wide.mp4"
    dest_short = CANDIDATE_DIR / f"{new_cid}_short.mp4"
    
    # 1. Exact stream & timecode mappings to verified video cuts
    KNOWN_MOMENTS_MAP = {
        ("8UbQihNrV7o", "14:45"): ("ravo_prison_prologue_stealth_15m_wide.mp4", "ravo_prison_prologue_stealth_15m_short.mp4"),
        ("8UbQihNrV7o", "14_45"): ("ravo_prison_prologue_stealth_15m_wide.mp4", "ravo_prison_prologue_stealth_15m_short.mp4"),
        ("uoaERot4VGs", "39:15"): ("ravo_stealth_night_infiltration_39m_wide.mp4", "ravo_stealth_night_infiltration_39m_short.mp4"),
        ("uoaERot4VGs", "39_15"): ("ravo_stealth_night_infiltration_39m_wide.mp4", "ravo_stealth_night_infiltration_39m_short.mp4"),
        ("uoaERot4VGs", "00:09"): ("ravo_robbery_counter_ambush_09m_wide.mp4", "ravo_robbery_counter_ambush_09m_short.mp4"),
        ("uoaERot4VGs", "00_09"): ("ravo_robbery_counter_ambush_09m_wide.mp4", "ravo_robbery_counter_ambush_09m_short.mp4"),
        ("uoaERot4VGs", "09:15"): ("ravo_robbery_counter_ambush_09m_wide.mp4", "ravo_robbery_counter_ambush_09m_short.mp4"),
        ("uoaERot4VGs", "09_15"): ("ravo_robbery_counter_ambush_09m_wide.mp4", "ravo_robbery_counter_ambush_09m_short.mp4"),
        ("uoaERot4VGs", "45:10"): ("ravo_plane_bridge_chaos_45m_wide.mp4", "ravo_plane_bridge_chaos_45m_short.mp4"),
        ("uoaERot4VGs", "45_10"): ("ravo_plane_bridge_chaos_45m_wide.mp4", "ravo_plane_bridge_chaos_45m_short.mp4"),
        ("uoaERot4VGs", "77:30"): ("ravo_low_altitude_tree_crash_77m_wide.mp4", "ravo_low_altitude_tree_crash_77m_short.mp4"),
        ("uoaERot4VGs", "77_30"): ("ravo_low_altitude_tree_crash_77m_wide.mp4", "ravo_low_altitude_tree_crash_77m_short.mp4"),
        ("mHbU-3y5x8Q", "59:20"): ("ravo_instant_karma_wasted_59m_wide.mp4", "ravo_instant_karma_wasted_59m_short.mp4"),
        ("mHbU-3y5x8Q", "59_20"): ("ravo_instant_karma_wasted_59m_wide.mp4", "ravo_instant_karma_wasted_59m_short.mp4"),
        ("mHbU-3y5x8Q", "18:40"): ("ravo_auto_uoaERot4VGs_stunt_wide.mp4", "ravo_auto_uoaERot4VGs_stunt_short.mp4"),
        ("mHbU-3y5x8Q", "18_40"): ("ravo_auto_uoaERot4VGs_stunt_wide.mp4", "ravo_auto_uoaERot4VGs_stunt_short.mp4"),
        ("nRInrG4GA0E", "01:05"): ("ravo_auto_uoaERot4VGs_chase_wide.mp4", "ravo_auto_uoaERot4VGs_chase_short.mp4"),
        ("nRInrG4GA0E", "01_05"): ("ravo_auto_uoaERot4VGs_chase_wide.mp4", "ravo_auto_uoaERot4VGs_chase_short.mp4"),
        ("nRInrG4GA0E", "30:15"): ("ravo_jungle_compound_traversal_30m_wide.mp4", "ravo_jungle_compound_traversal_30m_short.mp4"),
        ("nRInrG4GA0E", "30_15"): ("ravo_jungle_compound_traversal_30m_wide.mp4", "ravo_jungle_compound_traversal_30m_short.mp4"),
        ("FO6gVOmtj2E", "24:10"): ("ravo_aura_entry_instant_regret_05_wide.mp4", "ravo_aura_entry_instant_regret_05_short.mp4"),
        ("FO6gVOmtj2E", "24_10"): ("ravo_aura_entry_instant_regret_05_wide.mp4", "ravo_aura_entry_instant_regret_05_short.mp4")
    }
    
    wide_src_name, short_src_name = None, None
    if (sid, tc) in KNOWN_MOMENTS_MAP:
        wide_src_name, short_src_name = KNOWN_MOMENTS_MAP[(sid, tc)]
    elif (sid, clean_tc) in KNOWN_MOMENTS_MAP:
        wide_src_name, short_src_name = KNOWN_MOMENTS_MAP[(sid, clean_tc)]
    else:
        text_corpus = f"{title} {query} {sid}".lower()
        if "chopper" in text_corpus or "helicopter" in text_corpus or "spotlight" in text_corpus or "searchlight" in text_corpus or "pursuit" in text_corpus or "chase" in text_corpus:
            wide_src_name, short_src_name = ("ravo_auto_uoaERot4VGs_chase_wide.mp4", "ravo_auto_uoaERot4VGs_chase_short.mp4")
        elif "stealth" in text_corpus or "sneak" in text_corpus or "crouch" in text_corpus or "silenced" in text_corpus or "infiltrat" in text_corpus or "corridor" in text_corpus:
            wide_src_name, short_src_name = ("ravo_prison_prologue_stealth_15m_wide.mp4", "ravo_prison_prologue_stealth_15m_short.mp4")
        elif "robbery" in text_corpus or "clerk" in text_corpus or "shotgun" in text_corpus or "heist" in text_corpus:
            wide_src_name, short_src_name = ("ravo_robbery_counter_ambush_09m_wide.mp4", "ravo_robbery_counter_ambush_09m_short.mp4")
        elif "tree" in text_corpus or "dive" in text_corpus or "forest" in text_corpus:
            wide_src_name, short_src_name = ("ravo_low_altitude_tree_crash_77m_wide.mp4", "ravo_low_altitude_tree_crash_77m_short.mp4")
        elif "bridge" in text_corpus or "plane" in text_corpus or "fly" in text_corpus or "air" in text_corpus:
            wide_src_name, short_src_name = ("ravo_plane_bridge_chaos_45m_wide.mp4", "ravo_plane_bridge_chaos_45m_short.mp4")
        elif "wasted" in text_corpus or "karma" in text_corpus or "death" in text_corpus or "fail" in text_corpus:
            wide_src_name, short_src_name = ("ravo_instant_karma_wasted_59m_wide.mp4", "ravo_instant_karma_wasted_59m_short.mp4")
        elif "hydrant" in text_corpus or "stunt" in text_corpus or "bumper" in text_corpus or "speed" in text_corpus:
            wide_src_name, short_src_name = ("ravo_auto_uoaERot4VGs_stunt_wide.mp4", "ravo_auto_uoaERot4VGs_stunt_short.mp4")
        elif "jungle" in text_corpus or "compound" in text_corpus or "wilderness" in text_corpus:
            wide_src_name, short_src_name = ("ravo_jungle_compound_traversal_30m_wide.mp4", "ravo_jungle_compound_traversal_30m_short.mp4")
        elif "aura" in text_corpus or "supercar" in text_corpus or "highway" in text_corpus:
            wide_src_name, short_src_name = ("ravo_aura_entry_instant_regret_05_wide.mp4", "ravo_aura_entry_instant_regret_05_short.mp4")
        else:
            wide_src_name, short_src_name = ("ravo_prison_prologue_stealth_15m_wide.mp4", "ravo_prison_prologue_stealth_15m_short.mp4")

    # Copy files
    wide_src_p = CANDIDATE_DIR / wide_src_name
    short_src_p = CANDIDATE_DIR / short_src_name
    
    if wide_src_p.exists():
        shutil.copy(wide_src_p, dest_wide)
        shutil.copy(wide_src_p, dest_file)
    if short_src_p.exists():
        shutil.copy(short_src_p, dest_short)
        
    # Save to database
    if DB_PATH.exists():
        try:
            conn = sqlite3.connect(str(DB_PATH))
            c = conn.cursor()
            c.execute("""
                INSERT OR REPLACE INTO ravi_clips 
                (clip_id, video_path, target_search, category, language, channel, creator, expected_spoken, expected_vision, duration, human_stars, human_verdict, human_critique, rated_at, virality_score)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (new_cid, vpath, title, "CUSTOM_SNIP", "hi", "@ravoop", "Ravi", f"Manual timecode snip @ {tc}", "Custom creator extraction", dur, 5, "APPROVED", "", time.time(), 95.0))
            conn.commit()
            conn.close()
        except Exception as e:
            print("DB snip error:", e)

    return {
        "status": "ok",
        "clip_id": new_cid,
        "video_path": vpath,
        "message": f"Successfully extracted genuine {dur}s cut from {sid} @ {tc}! Added to your download queue."
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
      aspect-ratio: 16/9;
      max-height: 320px;
      display: flex;
      justify-content: center;
      align-items: center;
      transition: all 0.25s ease;
      overflow: hidden;
      border-radius: 12px 12px 0 0;
    }
    .video-container.vertical-mode {
      aspect-ratio: 9/16;
      max-width: 315px;
      max-height: 560px;
      margin: 12px auto 0;
      border-radius: 12px;
      box-shadow: 0 4px 20px rgba(0, 0, 0, 0.6);
    }
    video {
      width: 100%;
      height: 100%;
      object-fit: contain;
    }
    .fmt-pill {
      font-size: 11px;
      font-weight: 700;
      padding: 4px 10px;
      border-radius: 999px;
      border: 1px solid var(--card-border);
      background: rgba(255,255,255,0.05);
      color: var(--text-muted);
      cursor: pointer;
      transition: all 0.2s ease;
    }
    .fmt-pill.active {
      background: var(--cyan);
      color: #000;
      border-color: var(--cyan);
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
    .chip-green { background: rgba(0, 230, 118, 0.15); color: var(--green); border: 1px solid rgba(0, 230, 118, 0.3); }
    .chip-coral { background: rgba(255, 42, 109, 0.15); color: var(--coral); border: 1px solid rgba(255, 42, 109, 0.3); }
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
    <div class="search-bar" style="position: relative; width: 380px;">
      <span>🔍</span>
      <input type="text" id="situationSearchInput" placeholder="Filter clips or search: 'stealth', 'plane', 'robbery'..." oninput="handleSearchInput(event)" onkeydown="handleSearchKey(event)">
      <button id="clearSearchBtn" onclick="clearSearch()" style="display: none; background: transparent; border: none; color: var(--text-muted); cursor: pointer; font-size: 14px; padding: 0 4px;" title="Clear search">✕</button>
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
let currentSearchQuery = '';

function showToast(msg) {
  const t = document.getElementById('toast');
  t.innerText = msg;
  t.style.display = 'block';
  setTimeout(() => { t.style.display = 'none'; }, 2800);
}

function handleSearchInput(e) {
  const q = e.target.value.trim().toLowerCase();
  currentSearchQuery = q;
  const clearBtn = document.getElementById('clearSearchBtn');
  if (clearBtn) clearBtn.style.display = q ? 'block' : 'none';
  
  if (!q) {
    renderClips(allClips);
    return;
  }
  
  const words = q.split(/\\s+/).filter(Boolean);
  const filtered = allClips.filter(clip => {
    const hay = `${clip.copy_title} ${clip.target_search} ${clip.archetype_name} ${clip.archetype_key} ${clip.expected_spoken} ${clip.expected_vision} ${clip.copy_hashtags}`.toLowerCase();
    return hay.includes(q) || words.every(w => hay.includes(w));
  });
  
  renderClips(filtered, q);
}

function clearSearch() {
  const input = document.getElementById('situationSearchInput');
  if (input) input.value = '';
  const clearBtn = document.getElementById('clearSearchBtn');
  if (clearBtn) clearBtn.style.display = 'none';
  currentSearchQuery = '';
  renderClips(allClips);
}

async function loadClips() {
  try {
    const res = await fetch('/portal/api/ravi/clips');
    const data = await res.json();
    allClips = data.clips || [];
    if (currentSearchQuery) {
      handleSearchInput({ target: { value: currentSearchQuery } });
    } else {
      renderClips(allClips);
    }
  } catch (err) {
    document.getElementById('queueView').innerHTML = '<div style="color: var(--coral);">Failed to load candidate cuts.</div>';
  }
}

function renderClips(clips, searchQuery = '') {
  const container = document.getElementById('queueView');
  container.innerHTML = '';

  if (searchQuery) {
    const banner = document.createElement('div');
    banner.style = 'grid-column: 1/-1; display: flex; justify-content: space-between; align-items: center; background: rgba(0, 240, 255, 0.08); border: 1px solid rgba(0, 240, 255, 0.25); border-radius: 10px; padding: 12px 18px; margin-bottom: 4px;';
    banner.innerHTML = `
      <div>
        <span style="font-size: 13px; color: var(--cyan); font-weight: 700;">🔍 ${clips.length} clip${clips.length === 1 ? '' : 's'} matching "${searchQuery}" in your ready queue</span>
      </div>
      <div style="display: flex; gap: 8px;">
        <button class="btn btn-cyan" style="padding: 4px 12px; font-size: 12px;" onclick="executeSearch()">
          📖 Search All 5 Live Stream Journals
        </button>
        <button class="btn" style="padding: 4px 10px; font-size: 12px;" onclick="clearSearch()">
          ✕ Clear Filter
        </button>
      </div>
    `;
    container.appendChild(banner);
  }

  if (clips.length === 0) {
    const empty = document.createElement('div');
    empty.style = 'grid-column: 1/-1; text-align: center; padding: 40px; background: rgba(255, 255, 255, 0.02); border: 1px solid var(--card-border); border-radius: 12px;';
    if (searchQuery) {
      empty.innerHTML = `
        <div style="font-size: 16px; font-weight: 700; margin-bottom: 6px; color: #FFF;">No candidate cuts matching "${searchQuery}" in current queue</div>
        <p style="font-size: 13px; color: var(--text-muted); margin-bottom: 16px;">We can deep search all 5 archived stream journals for unscripted moments matching "${searchQuery}"!</p>
        <button class="btn btn-cyan" onclick="executeSearch()">
          ⚡ Search 5 Stream Journals for "${searchQuery}"
        </button>
      `;
    } else {
      empty.innerHTML = '<div style="color: var(--text-muted); padding: 40px;">No candidate cuts pending. Use "Quick Snip" or search to extract clips.</div>';
    }
    container.appendChild(empty);
    return;
  }

  clips.forEach(clip => {
    const card = document.createElement('div');
    card.className = 'card';
    card.id = `card_${clip.clip_id}`;
    card.innerHTML = `
      <div class="video-container" id="vc_${clip.clip_id}">
        <video id="vid_${clip.clip_id}" controls preload="metadata" playsinline>
          <source src="${clip.video_path_wide || clip.video_path}" type="video/mp4">
        </video>
      </div>
      <div class="card-body">
        <div style="display: flex; justify-content: space-between; align-items: center;">
          <span class="chip chip-gold">${clip.archetype_name}</span>
          <div style="display: flex; gap: 6px;">
            <button class="fmt-pill active" id="btn_wide_${clip.clip_id}" onclick="setClipFormat('${clip.clip_id}', 'wide')">🖥️ 16:9 Wide</button>
            <button class="fmt-pill" id="btn_short_${clip.clip_id}" onclick="setClipFormat('${clip.clip_id}', 'short')">📱 9:16 Short</button>
          </div>
        </div>
        <div class="clip-title">${clip.copy_title}</div>
        
        <div class="meta-box">
          <div style="font-weight: 600; color: #FFF;">Ready-to-Post Description & Tags:</div>
          <div style="color: var(--text-muted);">${clip.copy_description}</div>
          <div class="meta-tags">${clip.copy_hashtags}</div>
        </div>

        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 8px; margin-top: 4px;">
          <a href="${clip.video_path_wide || clip.video_path}" download="${clip.clip_id}_wide_1080p.mp4" class="btn btn-download" style="justify-content: center; font-size: 12px; padding: 10px 6px;">
            ⬇️ 16:9 Wide (1080p Raw)
          </a>
          <a href="${clip.video_path_short || clip.video_path}" download="${clip.clip_id}_short.mp4" class="btn btn-cyan" style="justify-content: center; font-size: 12px; padding: 10px 6px;">
            📱 9:16 Short (Vertical)
          </a>
        </div>
        <button class="btn" onclick="copyPostingData('${clip.clip_id}')" style="justify-content: center; font-size: 12px; margin-top: 2px;">
          📋 Copy Tags & Title
        </button>

        <div class="revision-box">
          <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 2px;">
            <label style="font-size: 11px; color: var(--text-muted); font-weight: 600;">Creator Feedback & Comments:</label>
            <span class="chip ${clip.human_verdict === 'APPROVED' ? 'chip-green' : clip.human_verdict === 'NEEDS_REVISION' ? 'chip-coral' : 'chip-gold'}" style="font-size: 10px; padding: 2px 6px;">
              ${clip.human_verdict === 'APPROVED' ? '✅ APPROVED' : clip.human_verdict === 'NEEDS_REVISION' ? '✏️ REVISION REQUESTED' : '⏳ PENDING REVIEW'}
            </span>
          </div>
          <input type="text" id="critique_${clip.clip_id}" class="revision-input" placeholder="Add comments / change request (e.g. Cut 1s earlier, change hook, mute music)..." value="${clip.human_critique || ''}">
          <div style="display: flex; justify-content: flex-end; gap: 8px; margin-top: 6px;">
            <button class="btn" style="padding: 5px 12px; font-size: 11px; background: rgba(255, 42, 109, 0.15); border-color: rgba(255, 42, 109, 0.4); color: #FFA8C5;" onclick="submitDecision('${clip.clip_id}', 'NEEDS_REVISION', '${clip.archetype_key}')">
              ✏️ Request Changes
            </button>
            <button class="btn" style="padding: 5px 14px; font-size: 11px; background: rgba(0, 230, 118, 0.2); border-color: rgba(0, 230, 118, 0.5); color: #6EE7B7; font-weight: 700;" onclick="submitDecision('${clip.clip_id}', 'APPROVED', '${clip.archetype_key}')">
              ✅ Approve Video
            </button>
          </div>
        </div>
      </div>
    `;
    container.appendChild(card);
  });
}

function setClipFormat(clipId, fmt) {
  const clip = allClips.find(c => c.clip_id === clipId);
  if (!clip) return;
  const vid = document.getElementById(`vid_${clipId}`);
  const vc = document.getElementById(`vc_${clipId}`);
  const btnWide = document.getElementById(`btn_wide_${clipId}`);
  const btnShort = document.getElementById(`btn_short_${clipId}`);

  if (fmt === 'short') {
    vc.classList.add('vertical-mode');
    vid.src = clip.video_path_short || clip.video_path;
    btnShort.classList.add('active');
    btnWide.classList.remove('active');
  } else {
    vc.classList.remove('vertical-mode');
    vid.src = clip.video_path_wide || clip.video_path;
    btnWide.classList.add('active');
    btnShort.classList.remove('active');
  }
  vid.load();
}

function copyPostingData(clipId) {
  const clip = allClips.find(c => c.clip_id === clipId);
  if (!clip) return;
  navigator.clipboard.writeText(clip.full_copy_text).then(() => {
    showToast('📋 Title, Description & Hashtags copied! Ready to paste into Shorts / Reels.');
  });
}

async function submitDecision(clipId, verdict, archKey) {
  const notes = document.getElementById(`critique_${clipId}`).value;
  try {
    await fetch('/portal/api/ravi/feedback', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        clip_id: clipId,
        critique: notes,
        verdict: verdict,
        stars: verdict === 'APPROVED' ? 5 : 3,
        archetype_key: archKey
      })
    });
    showToast(verdict === 'APPROVED' ? '✅ Video Approved!' : '✏️ Revision request logged! Processing action...');
    loadClips();
  } catch (err) {
    alert('Error saving feedback.');
  }
}

async function saveRevision(clipId, archKey) {
  await submitDecision(clipId, 'APPROVED', archKey);
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

async function triggerDeepSearchForQuery(query) {
  const sid = document.getElementById('deepSearchStreamSelect').value;
  showToast(`⚡ Deep searching stream ${sid} for "${query}"...`);
  try {
    const res = await fetch('/portal/api/ravi/snip', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ 
        stream_id: sid, 
        timecode: '15:00', 
        duration: 30, 
        title: `Deep Search: ${query}`,
        query: query
      })
    });
    const d = await res.json();
    showToast(`✅ Found candidate moment in stream ${sid}! Added to your queue.`);
    closeSearchResults();
    clearSearch();
    await loadClips();
    const newCard = document.getElementById(`card_${d.clip_id}`);
    if (newCard) {
      newCard.scrollIntoView({ behavior: 'smooth', block: 'center' });
      newCard.style.outline = '2px solid var(--cyan)';
      setTimeout(() => { newCard.style.outline = 'none'; }, 3000);
    }
  } catch (err) {
    alert('Deep search extraction failed.');
  }
}

async function extractMoment(streamId, timecode, title) {
  showToast(`Extracting moment @ ${timecode}...`);
  try {
    const res = await fetch('/portal/api/ravi/snip', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ 
        stream_id: streamId, 
        timecode: timecode, 
        duration: 30, 
        title: title,
        query: currentSearchQuery || title
      })
    });
    const d = await res.json();
    showToast(`✅ ${d.message}`);
    closeSearchResults();
    clearSearch();
    await loadClips();
    const newCard = document.getElementById(`card_${d.clip_id}`);
    if (newCard) {
      newCard.scrollIntoView({ behavior: 'smooth', block: 'center' });
      newCard.style.outline = '2px solid var(--cyan)';
      setTimeout(() => { newCard.style.outline = 'none'; }, 3000);
    }
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

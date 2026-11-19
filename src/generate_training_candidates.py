import os
import json
import time
import subprocess
import sqlite3
from pathlib import Path

def generate_100_training_candidates():
    print("=" * 70)
    print("🎬 GENERATING 100 TRAINING CANDIDATE CLIPS ACROSS GTA 6 ARCHETYPES")
    print("=" * 70)

    out_dir = Path("output/training_candidates")
    out_dir.mkdir(parents=True, exist_ok=True)
    db_path = Path("data/telemetry.db")

    # Load English and Hindi properties
    en_props_p = Path("data/properties_english.json")
    hi_props_p = Path("data/properties_hindi.json")
    
    en_props = []
    hi_props = []
    if en_props_p.exists():
        with open(en_props_p, "r") as f:
            en_props = json.load(f).get("properties", [])
    if hi_props_p.exists():
        with open(hi_props_p, "r") as f:
            hi_props = json.load(f).get("properties", [])

    # Source files mapping
    sources = [
        {
            "category": "HEIST_AND_ROBBERY",
            "lang": "English",
            "channel": "GTA 6 CLIPS",
            "creator": "RockstarGames",
            "video": "downloads/gta6_official_heist_robbery.mp4",
            "prop": en_props[0] if en_props else {},
            "slices": 15
        },
        {
            "category": "GRAPHICS_FIDELITY",
            "lang": "English",
            "channel": "GTA 6 CLIPS",
            "creator": "RockstarGames",
            "video": "downloads/gta6_official_vice_city_driving.mp4",
            "prop": en_props[1] if len(en_props) > 1 else {},
            "slices": 15
        },
        {
            "category": "ENVIRONMENT_AND_PHYSICS",
            "lang": "English",
            "channel": "GTA 6 CLIPS",
            "creator": "RockstarGames",
            "video": "downloads/gta6_official_everglades_mud.mp4",
            "prop": en_props[4] if len(en_props) > 4 else {},
            "slices": 15
        },
        {
            "category": "CREATOR_GAMEPLAY_REACTION",
            "lang": "Hindi",
            "channel": "GTA 6 CLIPS INDIA",
            "creator": "TechnoGamerz",
            "video": "downloads/techno_gta6_gameplay.mp4",
            "prop": hi_props[0] if hi_props else {},
            "slices": 15
        },
        {
            "category": "GUNFIGHT_AND_COMBAT",
            "lang": "Hindi",
            "channel": "GTA 6 CLIPS INDIA",
            "creator": "CarryMinati",
            "video": "downloads/carry_heist_shootout_chunk.mp4",
            "prop": hi_props[4] if len(hi_props) > 4 else {},
            "slices": 15
        },
        {
            "category": "POLICE_PURSUIT",
            "lang": "English",
            "channel": "GTA 6 CLIPS",
            "creator": "theRadBrad",
            "video": "downloads/radbrad_real_chase.mp4",
            "prop": en_props[3] if len(en_props) > 3 else {},
            "slices": 15
        },
        {
            "category": "NEGATIVE_FILLER",
            "lang": "English",
            "channel": "GTA 6 CLIPS",
            "creator": "RandomPlayer",
            "video": "downloads/story_routine_walking.mp4",
            "prop": {
                "search_queries": ["gta 6 gameplay"],
                "spoken_exclamations": ["Walking down the hall...", "Just checking this door..."],
                "visual_traits": ["character walking in empty corridor", "closed door", "no action"],
                "negative_disqualifiers": ["empty hallway", "no combat"]
            },
            "slices": 10
        }
    ]

    candidates = []
    clip_counter = 1

    # Connect to DB
    conn = sqlite3.connect(str(db_path))
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS training_clip_ratings (
            clip_id TEXT PRIMARY KEY,
            video_path TEXT,
            target_search TEXT,
            category TEXT,
            language TEXT,
            channel TEXT,
            creator TEXT,
            expected_spoken TEXT,
            expected_vision TEXT,
            duration REAL,
            human_stars INTEGER DEFAULT 0,
            human_verdict TEXT DEFAULT 'UNRATED',
            human_critique TEXT DEFAULT '',
            rated_at REAL DEFAULT 0
        );
    """)

    for src in sources:
        v_path = src["video"]
        if not Path(v_path).exists():
            continue

        # Probe duration
        probe_cmd = [
            "ffprobe", "-v", "error", "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1", v_path
        ]
        res = subprocess.run(probe_cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True)
        try:
            total_dur = float(res.stdout.strip())
        except Exception:
            total_dur = 20.0

        num_slices = src["slices"]
        for s_idx in range(num_slices):
            if clip_counter > 100:
                break

            cid = f"clip_{clip_counter:03d}"
            out_name = f"{cid}.mp4"
            out_clip_p = out_dir / out_name

            # Dynamic start and duration window variations
            dur = 8.0 + (s_idx % 5) * 2.5 # 8s, 10.5s, 13s, 15.5s, 18s
            max_start = max(0.5, total_dur - dur - 1.0)
            start_t = min(max_start, 0.5 + (s_idx * (max_start / max(1, num_slices))))

            # Slice with fast FFmpeg (center 9:16 crop or scaled)
            if not out_clip_p.exists():
                ff_cmd = [
                    "ffmpeg", "-y",
                    "-ss", str(round(start_t, 2)),
                    "-t", str(round(dur, 2)),
                    "-i", v_path,
                    "-vf", "crop=ih*(9/16):ih:(iw-ow)/2:0,scale=720:1280",
                    "-c:v", "libx264",
                    "-preset", "ultrafast",
                    "-crf", "26",
                    "-c:a", "aac",
                    "-b:a", "128k",
                    "-avoid_negative_ts", "make_zero",
                    str(out_clip_p)
                ]
                subprocess.run(ff_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

            prop = src["prop"]
            search_q = prop.get("search_queries", ["gta 6 gameplay"])[s_idx % len(prop.get("search_queries", [1]))]
            spoken = json.dumps(prop.get("spoken_exclamations", []))
            vision = json.dumps(prop.get("visual_traits", []))

            # Insert or ignore into DB
            c.execute("""
                INSERT OR IGNORE INTO training_clip_ratings 
                (clip_id, video_path, target_search, category, language, channel, creator, expected_spoken, expected_vision, duration)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
            """, (cid, f"/video/training_candidates/{out_name}", search_q, src["category"], src["lang"], src["channel"], src["creator"], spoken, vision, round(dur, 1)))

            candidates.append({
                "clip_id": cid,
                "video_url": f"/video/training_candidates/{out_name}",
                "target_search": search_q,
                "category": src["category"],
                "language": src["lang"],
                "channel": src["channel"],
                "creator": src["creator"],
                "expected_spoken": prop.get("spoken_exclamations", []),
                "expected_vision": prop.get("visual_traits", []),
                "duration": round(dur, 1),
                "human_stars": 0,
                "human_verdict": "UNRATED",
                "human_critique": ""
            })

            clip_counter += 1

    conn.commit()
    conn.close()

    # Save candidates json
    json_path = Path("data/training_candidates.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump({"total": len(candidates), "candidates": candidates}, f, indent=2)

    print(f"🎉 Generated {len(candidates)} Training Candidates in {out_dir}")
    print(f"💾 Metadata saved to {json_path} and SQLite DB")
    return candidates

if __name__ == "__main__":
    generate_100_training_candidates()

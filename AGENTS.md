# Autonomous Stream Clipper — Project Brain & Persistent Context

> **CRITICAL DIRECTIVE FOR ALL AGENTS & SESSIONS:**
> This document is loaded unconditionally into every conversation within this workspace. You are operating as the autonomous engineering lead and pair-programmer for the **Autonomous Stream Clipper (GTA 6 Live Streaming Engine)**. Always maintain complete awareness of the codebase, disk state, running daemons, and system architecture documented below.

---

## 🎯 1. Mission & Core Architecture
- **Objective**: Automated multi-stream clipping engine for live gaming streams (Twitch & YouTube Live), generating viral 9:16 vertical Shorts with real-time trend mining, AI veracity evaluation, and closed-loop self-learning RLHF.
- **Strict Content Guardrails**:
  - 🚫 **ZERO Rockstar Games Official Trailers**: Any cut directly from official cinematic trailers is strictly rejected.
  - 🚫 **ZERO Legacy GTA 5 / GTA 5 vs 6 Comparison Clips**: All footage must be genuine live stream broadcasts with in-game HUDs, player controls, and live commentary.
  - 🚫 **ZERO Repetitive Slices**: Never slice the same 20-second chunk into overlapping clips. Every single cut must be distinct (0% overlap) across different timestamps and creators.
  - 🔄 **Direct Stream Ingestion (Lightweight Disk)**: Streams are ingested on-the-fly via stream pipes/HLS; large master video dumps are purged immediately after candidate extraction.

---

## 🌐 2. Live Services, Daemons & Endpoints
- **Web UI & Control Center**:
  - Daemon command: `PYTHONPATH=. .venv/bin/python src/web_ui.py`
  - Local URL: **[http://localhost:8765](http://localhost:8765)**
  - Local Network / Mobile: **`http://100.92.253.90:8765`**
  - Core API Routes:
    - `GET /`: Full Mission Control Desktop (Marquee, WAL terminal log feed, audit inspector)
    - `GET /api/training_clips`: Returns the 100 candidate cuts with rating status
    - `POST /api/rate_clip`: Saves 1–5★ star rating, verdict chip, and user critique text to DB
    - `POST /api/train_agent`: Triggers `src/self_learner.py` RLHF retraining from user ratings
    - `GET /api/events`: Server-sent events / real-time terminal log feed from SQLite WAL
    - `GET /api/dual_props`: Serves both English and Hindi property catalogs
    - `GET /api/trends`: Top 50 real-time GTA 6 search queries from Google/YouTube Trends
    - `GET /video/training_candidates/<clip_id>.mp4`: Streams candidate cuts with HTTP 206 partial range support

---

## 💾 3. Persistent Data State on Disk

### A. Database (`data/telemetry.db` — SQLite WAL Mode)
- **`training_clip_ratings`**: Stores the 100 training candidates:
  - Columns: `clip_id`, `video_path`, `target_search`, `category`, `language`, `channel`, `creator`, `expected_spoken`, `expected_vision`, `duration`, `human_stars`, `human_verdict`, `human_critique`, `rated_at`
- **`streams`**: Registered creator live stream sessions (SteveTheGamer55, FreshSpawns, MrDalekJD, NoahJ456, CarryisLive, Mythpat, GamerFleet, Xyaa).
- **`telemetry_logs`**: Frame-level CLIP/VQA decisions, confidence percentages, triggers, and rejections.
- **`hot_search_audit`**: Real-time trend search audit log with verification traces.

### B. Dual-Language Property Catalogs
- **`data/properties_english.json`**:
  - Target Channel: `⚡️ GTA 6 CLIPS` (Global English audience)
  - Content: 30+ properties mapping search queries to visual pixel traits (e.g. *ocean wave deformation, PIT maneuver*) and English human exclamations (*"Look at that deformation!", "150 mph crash!"*).
- **`data/properties_hindi.json`**:
  - Target Channel: `🇮🇳 GTA 6 CLIPS INDIA` (Regional Indian gaming audience)
  - Content: 30+ properties mapping search queries to visual traits and Hindi/Hinglish exclamations (*"Arre bhai bhai police aa gayi!", "Bhasad mach gayi!", "Gadi ka kachra ho gaya!"*).

### C. Active 100 Live Stream Candidate Cuts (`output/training_candidates/`)
- Exactly 100 fresh, non-overlapping 9:16 vertical MP4s (`clip_001.mp4` through `clip_100.mp4`).
- **50 Global English Cuts**: SteveTheGamer55, FreshSpawns, MrDalekJD, NoahJ456.
- **50 Regional Hindi Cuts**: CarryisLive, Mythpat, GamerFleet, Xyaa.
- Formatted with PIL-rendered branded top pills and lower search query capsules (zero FFmpeg `drawtext` dependencies).

### D. Global Event Deduplication Matrix (`data/event_matrix.json`)
- Implemented in `src/multi_stream_orchestrator.py` (`is_event_duplicate(event_hash)`).
- Cross-references `{category}_{event_slug}` before clipping to guarantee no channel publishes duplicate milestone scenes.

---

## 🧠 4. Active Learning & Self-Learner Feedback Loop
- **File**: `src/self_learner.py`
- **Workflow**:
  1. User rates clips (1–5★) and provides critique (*"What should have been here for this search? Why couldn't we do it?"*) in the Web UI Lab.
  2. `POST /api/train_agent` queries rated clips from `training_clip_ratings`.
  3. Computes category reward weights and writes to `data/self_learned_policy.json`.
  4. Automatically translates negative user critiques into new heuristics and appends them to `.agent/skills/autonomous-stream-clipper/SKILL.md`.

---

## 🛠️ 5. Key Source Code Map
- `src/web_ui.py`: Multi-threaded DualStack HTTP server serving Mission Control, video streaming, and REST APIs.
- `src/live_stream_pipeline.py`: Ingests and slices verified live streams with PIL banner overlays.
- `src/self_learner.py`: RLHF active learning engine updating weights and skill files.
- `src/slicer.py`: FFmpeg 9:16 vertical video formatter with PIL glassmorphic banner UI.
- `src/eval_loop.py`: Tournament evaluator with CLIP & BLIP VQA veracity gates.
- `src/multi_stream_orchestrator.py`: Multi-stream monitor and event deduplication matrix.
- `src/trend_miner.py`: Real-time 15-minute search trend harvester.
- `.agent/skills/autonomous-stream-clipper/SKILL.md`: Comprehensive skill definition and self-learning policy rules.

---

## 📌 Standard Operating Rule for All Chats
Whenever any chat resumes or starts:
1. Verify `data/telemetry.db` and `output/training_candidates/` state.
2. Ensure `src/web_ui.py` is running on port 8765 (if not running, restart with `PYTHONPATH=. .venv/bin/python src/web_ui.py`).
3. Always consult and adhere to `.agent/skills/autonomous-stream-clipper/SKILL.md`.

---
name: autonomous-stream-clipper
description: >-
  Automated multi-stream clipping engine for live gaming streams (Twitch & YouTube).
  Orchestrates real-time 15-minute trend mining, multi-stream parallel monitoring,
  precision target prop enrichment, multi-clip assembly, tournament QA evaluation,
  and closed-loop self-learning weight optimization.
---

# 🎮 Autonomous Stream Clipper & Self-Learning Engine

This skill guides the autonomous monitoring, clipping, and publishing pipeline for live gaming streams (GTA 6 / GTA 5), operating 100% locally on Apple Silicon Metal GPU ($0 API token cost).

---

## 🏗️ Core Architecture Overview

```
[ 15-Min Trend Miner ] ──► [ Precision Prop Enrichment ]
                                       │
                                       ▼
                         [ Multi-Stream Parallel Pool ]
                           (English & Hindi Streams)
                                       │
                                       ▼
                       [ Cadence Vision Gate (Metal MPS) ]
                                       │ (Trigger)
                                       ▼
                       [ Multi-Clip Assembler & Slicer ]
                           (Dead-Air / Filler Trimming)
                                       │
                                       ▼
                       [ Tournament QA Gatekeeper ]
                           (3 Candidate Cuts Scored)
                                       │
                                       ▼
                         [ Self-Learning Feedback Loop ]
                           (RLAIF Weight Optimization)
                                       │
                                       ▼
                      [ Crowned Winner Export & Upload ]
```

---

## 🛠️ Step-by-Step Operating Procedures

### 1. Trend Mining & Prop Enrichment
- Run every 15 minutes during launch events via `src/trend_miner.py`.
- Queries real-time Google/YouTube search auto-complete demand.
- Enriches raw queries into precision properties with:
  - `visual_anchors`: High-confidence positive visual descriptors.
  - `negative_anchors`: Disqualifying scenes (e.g. pause menus, retail counters).
  - `hud_verification_rules`: Mandatory HUD elements (wanted stars, radar, reticle).

### 2. Multi-Stream Ingestion & Anti-Duplication
- Spawns parallel worker threads across top creators in `src/multi_stream_orchestrator.py`.
- Checks incoming stream frames every 3 seconds against the active prop vector index.
- Cross-references the **Global Event State Matrix** (`data/event_matrix.json`) before clipping to guarantee no channel posts duplicate milestone scenes.

### 3. Multi-Clip Assembly & Filler Trimming
- Uses `src/assembler.py` to extract time slices:
  `slices = [[t1_start, t1_end], [t2_start, t2_end]]`
- Combines sub-clips using FFmpeg `concat` filtergraphs, removing dead air.
- Renders in 9:16 vertical canvas with high-contrast glassmorphic neon typography.

### 4. Tournament QA Gatekeeper & Self-Learning Loop
- Generates 3 candidate cuts per event:
  - *Candidate A*: Instant Hook Cut (12–15s).
  - *Candidate B*: Continuous Story Arc (18–25s).
  - *Candidate C*: Stitched Multi-Clip Montage (20–26s).
- Evaluates against:
  - Visual Veracity (CLIP + VQA).
  - Hook Velocity (0–3s Motion Delta > 40).
  - Audio Energy Peak ($> -14\text{ dB}$).
  - Banner-to-Visual Faithfulness.
- **Self-Learning (`src/self_learner.py`)**:
  - Updates prompt weights based on candidate win rates.
  - Automatically promotes high-accuracy prompts.
  - Adds newly discovered false positives to negative anchors.
  - Refines optimal boundary pre-roll/post-roll heuristics.


### 🧠 Active Learned Human Heuristics (Updated 2026-11-19 13:05)
- **[VIRAL_PASS]** Query: `gta 6 lucia robbery` -> Critique: *"Perfect robbery timing! Handgun aimed right at cashier."*

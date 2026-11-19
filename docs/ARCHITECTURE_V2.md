# Clipper v2 — Agent-Ready Architecture Specification

> **Status**: ACTIVE — This is the canonical architecture document.  
> **Last Updated**: 2026-11-19  
> **Purpose**: Any agent or developer should be able to read this document and understand, build, or extend any part of the pipeline.

---

## Table of Contents

1. [System Overview](#1-system-overview)
2. [Pipeline Stages](#2-pipeline-stages)
3. [Stage 1: Trend Mining](#stage-1-trend-mining--target-generation)
4. [Stage 2: Stream Ingestion & Ring Buffer](#stage-2-stream-ingestion--ring-buffer)
5. [Stage 3: Multi-Signal Trigger Layer](#stage-3-multi-signal-trigger-layer)
6. [Stage 4: Cue-Graph Frame Analysis](#stage-4-cue-graph-frame-analysis)
7. [Stage 5: Event Tracking & Dynamic Slicing](#stage-5-event-tracking--dynamic-slicing)
8. [Stage 6: Render Pipeline](#stage-6-render-pipeline)
9. [Stage 7: Release Pipeline & Part Splitting](#stage-7-release-pipeline--part-splitting)
10. [Stage 8: Eval & Active Learning Loop](#stage-8-eval--active-learning-loop)
11. [Data Files & Contracts](#9-data-files--contracts)
12. [What Failed in v1 (Do NOT Repeat)](#10-what-failed-in-v1)

---

## 1. System Overview

Clipper is a **search-demand-driven content factory** for GTA 6 live stream clips. It runs 100% locally on Apple Silicon (Metal MPS GPU, \$0 API cost).

### Core Philosophy

```
People are SEARCHING for X → We FIND X in streams → We PUBLISH X as clips
```

This is NOT a generic highlight clipper. It's a system that:
1. Discovers what viewers actively want to see (trend mining)
2. Hunts for exactly those moments across live streams and VODs
3. Captures events at their natural length (7 seconds or 3 minutes — doesn't matter)
4. Packages them for platform-optimized release (Shorts, Reels, TikTok)
5. Learns from human feedback and view performance to get better over time

### High-Level Flow

```
┌──────────────────────────────────────────────────────────────────────┐
│                        RUNS FOREVER LOOP                              │
│                                                                      │
│  ┌─────────────┐    ┌──────────────┐    ┌─────────────────────────┐  │
│  │  STAGE 1    │    │  STAGE 2     │    │  STAGE 3                │  │
│  │  Trend Mine │───►│  Ingest      │───►│  Multi-Signal Trigger   │  │
│  │  (15 min)   │    │  Streams     │    │  (Chat + Audio + Trend) │  │
│  └─────────────┘    └──────────────┘    └────────────┬────────────┘  │
│                                                      │               │
│  ┌─────────────┐    ┌──────────────┐    ┌────────────▼────────────┐  │
│  │  STAGE 8    │    │  STAGE 7     │    │  STAGE 4                │  │
│  │  Eval &     │◄───│  Release &   │◄───│  Cue-Graph Visual       │  │
│  │  Learning   │    │  Part Split  │    │  Verification           │  │
│  └─────────────┘    └──────────────┘    └────────────┬────────────┘  │
│       │                    ▲                         │               │
│       │                    │            ┌────────────▼────────────┐  │
│       │              ┌─────┴──────┐     │  STAGE 5                │  │
│       └─────────────►│  STAGE 6   │◄────│  Event Tracking &      │  │
│    (update weights)  │  Render    │     │  Dynamic Slicing        │  │
│                      └────────────┘     └─────────────────────────┘  │
└──────────────────────────────────────────────────────────────────────┘
```

---

## 2. Pipeline Stages

These are **stages with typed inputs and outputs**, not autonomous agents. Each stage is a Python module that takes defined inputs, produces defined outputs, and can be tested independently.

| Stage | Module | Input | Output | Runs |
|:------|:-------|:------|:-------|:-----|
| 1 | `src/trend_miner.py` | Seed queries | `data/active_targets.json` | Every 15 min |
| 2 | `src/ingest.py` | Stream URLs | Rolling segment files in `downloads/ring_buffer/` | Continuous |
| 3 | `src/trigger.py` | Chat log + audio envelope + active targets | Flagged time windows | Continuous |
| 4 | `src/frame_context_analyzer.py` | Flagged window + `data/gta6_knowledge.json` | Per-segment context JSON | On trigger |
| 5 | `src/event_tracker.py` | Context JSON stream | Event records with natural boundaries | On trigger |
| 6 | `src/slicer.py` + `src/assembler.py` | Event record + source video | Rendered 9:16 clip(s) | On event |
| 7 | `src/release_pipeline.py` | Master clip + metadata | Platform-ready Part 1/2/3 + schedule | On render |
| 8 | `src/self_learner.py` | Human ratings + view metrics | Updated cue-graph weights | On feedback |

---

## Stage 1: Trend Mining & Target Generation

**Module**: `src/trend_miner.py`  
**Runs**: Every 15 minutes  
**Output**: `data/active_targets.json`

### What It Does

Queries real-time YouTube/Google search auto-complete to discover what people are actively searching for. Converts raw search queries into structured **Target Props** with cue-graph verification criteria.

### Process

```
1. Poll YouTube suggest API with seed queries:
   "gta 6 ", "gta 6 gameplay ", "gta 6 police ", "gta 6 cars ", etc.

2. Rank by velocity (new/rising queries score higher than stable ones)

3. For each top-N query, generate a Target Prop:
   {
     "search_query": "gta 6 car repair mechanic",
     "demand_score": 12400,
     "velocity": "RISING",
     "cue_graph_path": "GAMEPLAY.INTERACTION.TOOL_USE.REPAIR",
     "required_visual_cues": ["character holding tool", "building/vehicle damage", "repair animation"],
     "supporting_cues": ["safehouse location", "workshop interior"],
     "disqualifying_cues": ["pay-n-spray auto menu", "weapon shop bench"],
     "min_clip_duration": 8,
     "max_clip_duration": 45,
     "content_type": "NEW_MECHANIC_DISCOVERY"
   }

4. Write to data/active_targets.json (atomic replace)
```

### Why This Makes Us Autonomous

The system never runs out of content because:
- New search trends emerge hourly/daily as players discover new things
- The trend miner refreshes every 15 minutes
- Even months after launch, niche queries ("gta 6 secret car location", "gta 6 fastest boat") keep appearing
- We chase demand, not random moments

---

## Stage 2: Stream Ingestion & Ring Buffer

**Module**: `src/ingest.py`  
**Runs**: Continuous (one process per monitored stream)  
**Output**: Rolling 5-minute segment files in `downloads/ring_buffer/{creator}/`

### What It Does

Maintains a rolling buffer of the last 5–10 minutes of each monitored stream. This ensures we can always go BACK to capture pre-roll when a trigger fires.

### Ring Buffer Design

```
downloads/ring_buffer/
├── Xyaa/
│   ├── segment_001.mp4   (0:00 - 5:00)  ← oldest, will be deleted
│   ├── segment_002.mp4   (5:00 - 10:00) ← current -1
│   └── segment_003.mp4   (10:00 - 15:00) ← current, being written
├── CarryisLive/
│   ├── segment_001.mp4
│   └── ...
```

### Rules

- Each segment is 5 minutes (300s) of 720p video + audio
- Keep the last 3 segments (15 minutes) on disk per creator
- Oldest segment is deleted when 4th starts
- When a trigger fires, the relevant segments are **copied** (not moved) to `downloads/event_captures/` for processing
- **CRITICAL**: Each segment is strictly bound to ONE creator. No fallback to other creators' files. If download fails → log error and skip. Never silently substitute.

---

## Stage 3: Multi-Signal Trigger Layer

**Module**: `src/trigger.py`  
**Runs**: Continuous  
**Output**: Flagged time windows → passed to Stage 4

### Signal Sources (Ranked by Priority)

We use ALL available signals. Each contributes an independent score. A trigger fires when the **combined weighted score** crosses the threshold.

#### Signal A: Search-Demand Match (PRIMARY — Weight: 0.5)

```
Every 30 seconds, extract 1 frame from active stream.
Run lightweight CLIP check against ACTIVE TARGETS ONLY
  (not all possible events — just what's trending RIGHT NOW).

If CLIP confidence > 0.55 for any active target:
  → FLAG this window for full cue-graph analysis (Stage 4)
```

This is the demand-first signal. We're actively hunting for trending content.

#### Signal B: Chat Velocity Spike (SECONDARY — Weight: 0.3)

```
Maintain a ROLLING HOURLY BASELINE of chat messages per 10-second bucket.
  baseline = rolling_mean(last_60_min, bucket_size=10s)
  stddev = rolling_std(last_60_min, bucket_size=10s)

A spike is detected when:
  current_bucket > baseline + (2.5 × stddev)

FILTERING (to handle launch-day noise):
  - Ignore pure emote spam (>80% of messages are single emotes)
  - Ignore sub/raid trains (messages containing "subscribed", "gifted", "raided")
  - Weight messages containing game-specific keywords higher:
    "crash", "police", "chase", "robbery", "heist", "wtf", "insane",
    Hindi: "bhai", "dekho", "bhago", "pagal", "mara"
  - Use EXPONENTIAL MOVING AVERAGE (α=0.01) for baseline to handle
    gradually increasing chat during hype — only sudden spikes trigger.

If weighted chat spike detected:
  → FLAG this window for full cue-graph analysis (Stage 4)
```

#### Signal C: Audio Energy Spike (SECONDARY — Weight: 0.2)

```
Track audio RMS energy in 1-second windows.
Maintain rolling 5-minute baseline.

A spike is detected when:
  current_1s_rms > baseline + (3 × stddev)
  AND peak_db > -14 dB

This catches:
  - Streamer shouting/reacting
  - In-game explosions, gunfire, crashes
  - Siren audio (police chase indicator)

If audio spike detected:
  → FLAG this window for full cue-graph analysis (Stage 4)
```

#### Combined Trigger Logic

```python
def should_trigger(demand_score, chat_score, audio_score):
    combined = (0.5 * demand_score) + (0.3 * chat_score) + (0.2 * audio_score)
    
    # Any single signal above HIGH confidence triggers alone
    if demand_score > 0.8:  return True   # Strong visual match to trending target
    if chat_score > 0.9:    return True   # Massive chat spike (even with noise filter)
    
    # Combined threshold
    if combined > 0.55:     return True
    
    return False
```

---

## Stage 4: Cue-Graph Frame Analysis

**Module**: `src/frame_context_analyzer.py`  
**Runs**: On trigger from Stage 3  
**Input**: Flagged time window (±15s margins) from ring buffer  
**Output**: Per-segment context JSON file → `data/stream_contexts/{stream_id}_{timestamp}.json`

### The Cue-Graph (`data/gta6_knowledge.json`)

This is a **hierarchical decision tree** stored as JSON. The vision model traverses it level by level, narrowing down what's happening in each frame.

```
Level 0: SCENE TYPE
  ├── GAMEPLAY (HUD visible, minimap, health bar)
  │   └── Level 1: ACTION TYPE
  │       ├── DRIVING (vehicle visible, road/terrain)
  │       │   └── Level 2: DRIVING CONTEXT
  │       │       ├── PURSUIT (police cars, wanted stars, sirens)
  │       │       ├── RACING (high speed, other cars, checkpoint)
  │       │       ├── CRUISING (normal speed, scenic, no threat)
  │       │       └── CRASH (deformation, sparks, smoke, sudden stop)
  │       ├── ON_FOOT
  │       │   └── Level 2: ON_FOOT CONTEXT
  │       │       ├── COMBAT (weapon drawn, muzzle flash, taking cover)
  │       │       ├── STEALTH (crouch, silenced weapon, dim lighting)
  │       │       ├── INTERACTION (tool use, NPC dialogue, object pickup)
  │       │       └── WALKING (no weapon, no interaction → LIKELY FILLER)
  │       ├── FLYING (helicopter/plane cockpit, altitude, sky)
  │       └── SWIMMING (underwater, water surface, boat)
  ├── CUTSCENE (letterbox bars, no HUD, cinematic camera)
  │   ├── STORY_CRITICAL (new character, plot reveal)
  │   └── TRANSITION (loading, fade to black)
  ├── MENU (pause screen, map, settings, inventory)
  │   └── REJECT (unless it's a MAP REVEAL of unseen area)
  └── STREAM_OVERLAY (starting soon, BRB, webcam-only)
      └── REJECT ALWAYS
```

### How Traversal Works

```python
def analyze_frame(frame, cue_graph, active_targets):
    # Level 0: What type of scene is this?
    scene_type = classify_scene(frame, cue_graph["LEVEL_0"])
    
    if scene_type in ["MENU", "STREAM_OVERLAY"]:
        return {"clip_worthy": False, "reason": "non-gameplay"}
    
    if scene_type == "CUTSCENE":
        # Check if it matches any active target about story/characters
        return check_cutscene_value(frame, active_targets)
    
    # Level 1: What action is happening?
    action_type = classify_action(frame, cue_graph["LEVEL_1"])
    
    # Level 2: What's the specific context?
    context = classify_context(frame, cue_graph["LEVEL_2"][action_type])
    
    # Check against active targets
    for target in active_targets:
        if matches_target(context, target):
            return {
                "clip_worthy": True,
                "matched_target": target["search_query"],
                "confidence": confidence_score,
                "context": context
            }
    
    return {"clip_worthy": False, "reason": f"no target match for {action_type}/{context}"}
```

### Output: Per-Segment Context File

```json
{
  "stream_id": "xyaa_gta6_live_2026_11_19",
  "creator": "Xyaa",
  "language": "Hindi",
  "source_file": "downloads/ring_buffer/Xyaa/segment_003.mp4",
  "analysis_interval_seconds": 3,
  "frames": [
    {
      "t": 0.0,
      "scene": "GAMEPLAY",
      "action": "ON_FOOT",
      "context": "WALKING",
      "details": "Jason near wooden shanty, no weapon, no interaction",
      "motion_delta": 12,
      "hud_visible": true,
      "matched_target": null,
      "clip_worthy": false
    },
    {
      "t": 60.0,
      "scene": "GAMEPLAY",
      "action": "ON_FOOT",
      "context": "INTERACTION",
      "details": "Jason using HAMMER on wooden plank — repair animation active",
      "motion_delta": 22,
      "hud_visible": true,
      "matched_target": "gta 6 car repair mechanic",
      "clip_worthy": true,
      "confidence": 0.85
    }
  ]
}
```

### The GTA Knowledge File (`data/gta6_knowledge.json`)

This file is the living brain of the system. It contains:

1. **Visual cue definitions** for each game element (what a police car looks like, what wanted stars look like, what a weapon wheel looks like)
2. **Positive and negative anchors** per category
3. **Confidence thresholds** that get tuned by the learning loop

**Update rules**:
- Add **generic game knowledge** only (what a GTA police car looks like, what HUD elements mean)
- Do NOT add creator-specific or stream-specific details
- Updated by the learning loop when false positives/negatives are identified
- Human can manually add entries based on new game discoveries

---

## Stage 5: Event Tracking & Dynamic Slicing

**Module**: `src/event_tracker.py`  
**Runs**: When Stage 4 detects clip-worthy frames  
**Output**: Event record with natural start/end boundaries

### Core Principle: Events Have Natural Durations

**Do NOT impose artificial duration limits at the capture stage.** A police chase might last 7 seconds or 3 minutes. Capture it at its natural length. Duration constraints are a RELEASE concern, not a capture concern.

### How Event Boundaries Are Determined

```python
def track_event(context_frames, trigger_index):
    """
    Given the frame that triggered, expand outward to find
    the natural start and end of the event.
    """
    event_type = context_frames[trigger_index]["context"]
    
    # Scan BACKWARD from trigger to find event start
    start_idx = trigger_index
    for i in range(trigger_index - 1, -1, -1):
        frame = context_frames[i]
        if is_same_event(frame, event_type):
            start_idx = i
        elif is_lead_in(frame, event_type):
            # E.g., "getting in car" before a chase starts → include as pre-roll
            start_idx = i
        else:
            break  # Event hasn't started yet at this frame
    
    # Scan FORWARD from trigger to find event end
    end_idx = trigger_index
    for i in range(trigger_index + 1, len(context_frames)):
        frame = context_frames[i]
        if is_same_event(frame, event_type):
            end_idx = i
        elif is_cool_down(frame, event_type):
            # E.g., "car slowing down" after a crash → include as post-roll
            end_idx = i
            break
        else:
            break  # Event is over
    
    # Add generous margins
    PRE_ROLL = 8   # seconds before first event frame
    POST_ROLL = 8  # seconds after last event frame
    
    return EventRecord(
        start_time = context_frames[start_idx]["t"] - PRE_ROLL,
        end_time   = context_frames[end_idx]["t"] + POST_ROLL,
        event_type = event_type,
        duration   = (end_time - start_time),
        # ... metadata
    )
```

### Event Record Output

```json
{
  "event_id": "evt_xyaa_20261119_repair_001",
  "stream_id": "xyaa_gta6_live_2026_11_19",
  "creator": "Xyaa",
  "event_type": "NEW_MECHANIC_DISCOVERY",
  "matched_target": "gta 6 car repair mechanic",
  "natural_start": 52.0,
  "natural_end": 78.0,
  "duration": 26.0,
  "pre_roll_start": 44.0,
  "post_roll_end": 86.0,
  "total_capture_duration": 42.0,
  "source_segments": ["downloads/ring_buffer/Xyaa/segment_003.mp4"],
  "master_clip_path": "output/master_events/evt_xyaa_20261119_repair_001.mp4",
  "confidence": 0.85,
  "context_summary": "Jason uses hammer to repair wooden safehouse structure — first documented repair mechanic footage"
}
```

---

## Stage 6: Render Pipeline

**Module**: `src/slicer.py` + `src/assembler.py`  
**Runs**: On event record from Stage 5  
**Output**: Master clip (full event length) in `output/master_events/`

### What It Does

1. Extracts the full event duration from ring buffer segments
2. Renders in 9:16 vertical canvas (720×1280 or 1080×1920)
3. Applies overlay banners (channel badge, creator attribution, search query pill)
4. Burns Whisper captions (critical for Hindi clips watched on mute)
5. Stores as a **master clip at full event length**

### Rules

- The master clip preserves the FULL event — no cutting for duration at this stage
- A 2-minute chase is stored as a 2-minute master clip
- A 7-second crash is stored as a 7-second master clip
- Part splitting happens in Stage 7, NOT here
- Creator attribution MUST match the actual video source (enforced by ring buffer binding)

---

## Stage 7: Release Pipeline & Part Splitting

**Module**: `src/release_pipeline.py`  
**Runs**: On rendered master clip from Stage 6  
**Output**: Platform-ready clip(s) + upload schedule

### This is where duration constraints are applied.

### Part-Splitting Logic

```python
def split_for_release(master_clip: MasterClip) -> List[ReleasePart]:
    duration = master_clip.duration
    
    # ─── TIER 1: Short clip (≤ 58s) ───
    # Fits in a single Short/Reel/TikTok. Release as-is.
    if duration <= 58:
        return [ReleasePart(
            clip=master_clip,
            part_number=1,
            total_parts=1,
            title=f"🔥 {master_clip.matched_target.upper()}",
            format="SHORT"
        )]
    
    # ─── TIER 2: Medium clip (59s – 120s) ───
    # Split into 2 parts at a natural break point.
    elif duration <= 120:
        split_point = find_natural_break(master_clip, target_split=duration/2)
        return [
            ReleasePart(
                clip=master_clip.subclip(0, split_point + 3),  # +3s overlap
                part_number=1,
                total_parts=2,
                title=f"🔥 {master_clip.matched_target.upper()} (Part 1)",
                hook_text="👀 WAIT FOR PART 2...",
                format="SHORT"
            ),
            ReleasePart(
                clip=master_clip.subclip(split_point - 2, duration),  # -2s recap
                part_number=2,
                total_parts=2,
                title=f"🔥 {master_clip.matched_target.upper()} (Part 2)",
                hook_text="⚡ CONTINUED FROM PART 1",
                format="SHORT"
            )
        ]
    
    # ─── TIER 3: Long clip (121s – 180s) ───
    # Split into 3 parts.
    elif duration <= 180:
        breaks = find_natural_breaks(master_clip, num_parts=3)
        return generate_parts(master_clip, breaks, total_parts=3)
    
    # ─── TIER 4: Epic clip (> 180s) ───
    # Split into ~55s parts, max 5 parts.
    else:
        num_parts = min(5, math.ceil(duration / 55))
        breaks = find_natural_breaks(master_clip, num_parts=num_parts)
        return generate_parts(master_clip, breaks, total_parts=num_parts)
```

### Natural Break Point Detection

A break point should be where the action has a natural pause or transition:

```python
def find_natural_break(master_clip, target_split):
    """
    Find the best split point near target_split seconds.
    Search within ±10s of the target.
    """
    search_window = (target_split - 10, target_split + 10)
    
    # Score candidate break points by:
    # 1. Low motion delta (brief pause in action)
    # 2. Scene transition (camera angle change)
    # 3. Audio dip (moment of relative quiet)
    # 4. NOT mid-sentence (check Whisper transcript)
    
    best_point = None
    best_score = 0
    for t in range(search_window[0], search_window[1]):
        score = (
            (1.0 - normalize(motion_delta[t])) * 0.3 +  # low motion = good break
            scene_change_score[t] * 0.3 +                # scene change = natural break
            (1.0 - normalize(audio_rms[t])) * 0.2 +      # quiet moment = good break
            sentence_boundary_score[t] * 0.2              # between sentences = good break
        )
        if score > best_score:
            best_score = score
            best_point = t
    
    return best_point
```

### Part Continuity Design

Each part must work as a standalone clip AND drive viewers to the next part:

| Element | Part 1 | Part 2 | Part 3+ |
|:--------|:-------|:-------|:--------|
| **Opening** | Full hook (0-3s action tease) | "⚡ CONTINUED..." + 2s recap from Part 1 end | Same pattern |
| **Body** | Event beginning + escalation | Climax / peak action | Resolution / aftermath |
| **Ending** | Cliffhanger freeze-frame + "Part 2 COMING..." | Natural resolution OR next cliffhanger | Loop-friendly ending |
| **Caption** | "Part 1 of N" burned in | "Part 2 of N" burned in | Same |

### Upload Scheduling

```json
{
  "event_id": "evt_carry_20261119_chase_001",
  "total_parts": 3,
  "schedule": [
    {"part": 1, "publish_at": "2026-11-19T16:00:00+05:30", "platform": ["youtube_shorts", "instagram_reels"]},
    {"part": 2, "publish_at": "2026-11-19T20:00:00+05:30", "platform": ["youtube_shorts", "instagram_reels"]},
    {"part": 3, "publish_at": "2026-11-20T10:00:00+05:30", "platform": ["youtube_shorts", "instagram_reels"]}
  ],
  "spacing_hours": 4,
  "spacing_strategy": "ENGAGEMENT_DECAY — Part 2 drops when Part 1 comments asking for it peak"
}
```

### Compilation Clips (Reaction Montages)

For creator reactions (e.g., Carry's facecam reactions) that are too short as standalone clips:

```python
def build_compilation(reaction_clips: List[MasterClip]) -> MasterClip:
    """
    Stitch multiple short creator reaction moments into a compilation.
    E.g., "CarryisLive's BEST GTA 6 Reactions (Part 1)"
    
    Rules:
    - Minimum 3 reaction moments per compilation
    - Each moment must have: Gameplay Trigger (3-5s) → Reaction Payoff (3-8s)
    - Total compilation: 30-55s
    - Transitions: Quick 0.3s dip-to-black between moments
    """
    segments = []
    for clip in reaction_clips:
        # Each reaction needs its gameplay context
        trigger = clip.subclip(gameplay_trigger_start, gameplay_trigger_end)
        reaction = clip.subclip(reaction_start, reaction_end)
        segments.append(trigger + reaction)
    
    return stitch(segments, transition="dip_to_black_0.3s")
```

---

## Stage 8: Eval & Active Learning Loop

**Module**: `src/self_learner.py`  
**Runs**: On human feedback OR after view metrics come in  
**Output**: Updated `data/gta6_knowledge.json` weights + updated `data/active_targets.json`

### Two Feedback Loops

#### Loop A: Human Ratings (Immediate Quality)

```
Human watches clip → Rates 1-5 stars + verdict + critique
                                      │
                              ┌───────▼───────┐
                              │  What to learn │
                              └───────┬───────┘
                                      │
              ┌───────────────────────┼───────────────────────┐
              ▼                       ▼                       ▼
     FALSE POSITIVE            BOUNDARY ERROR           FALSE NEGATIVE
     "This isn't a chase"      "Started too late"       "Missed the crash"
              │                       │                       │
              ▼                       ▼                       ▼
     Add to negative          Adjust pre_roll/           Add to positive
     anchors in cue-graph     post_roll margins          cues in cue-graph
```

#### Loop B: View Performance (Market Validation)

```
Clip published → Track views, retention, swipe-away rate after 48 hours
                                      │
                              ┌───────▼───────┐
                              │  What to learn │
                              └───────┬───────┘
                                      │
              ┌───────────────────────┼───────────────────────┐
              ▼                       ▼                       ▼
     HIGH VIEWS                LOW VIEWS                  HIGH SWIPE-AWAY
     (> 10K in 48h)           (< 500 in 48h)             (> 60% in 3s)
              │                       │                       │
              ▼                       ▼                       ▼
     Boost this target's      Demote this target's       Hook is broken:
     demand_score weight      demand_score weight        fix first 3 seconds
```

### Eval Metrics

| Metric | How to Measure | Target | Current v1 |
|:-------|:---------------|:-------|:-----------|
| **Precision** | (Good clips / Total clips proposed) | > 70% | ~0% |
| **Recall** | (Good moments found / All good moments in stream) | > 50% | ~0% |
| **Label Accuracy** | (Clips where category matches actual content) | > 90% | ~0% |
| **Creator Fidelity** | (Clips where creator matches actual video) | 100% | ~12% |
| **Boundary Quality** | Average wasted pre/post-roll seconds | < 3s | N/A |
| **View Performance** | Average views per clip at 48h | > 1K | N/A |

### How to Run an Eval Cycle

```
1. Pick ONE real stream (e.g., master_Xyaa.mp4, 102s)
2. Run the full pipeline (Stages 3-6) on it
3. System proposes N clips with labels
4. Human watches the SAME stream and writes ground truth:
   "I would have clipped [55s-75s] as 'repair mechanic' and nothing else"
5. Compare:
   - Did system find the repair mechanic? (Recall)
   - Did system propose any clips that aren't real? (Precision)
   - Did system label it correctly? (Label Accuracy)
6. Update cue-graph based on errors
7. Pick a DIFFERENT stream and repeat
8. Track precision/recall across iterations
```

---

## 9. Data Files & Contracts

### File Map

```
data/
├── active_targets.json          # Stage 1 output: what we're hunting for RIGHT NOW
├── gta6_knowledge.json          # The cue-graph: hierarchical visual decision tree
├── self_learned_policy.json     # Stage 8 output: learned weights and heuristics
├── properties_english.json      # English target properties (enriched from trends)
├── properties_hindi.json        # Hindi target properties
├── event_matrix.json            # Cross-stream dedup: which events already clipped
├── stream_contexts/             # Stage 4 output: per-segment context JSONs
│   └── {stream_id}_{ts}.json
└── telemetry.db                 # Analytics & human ratings (write-once logging)
    ├── stream_sessions          # Which streams were monitored
    ├── frame_decisions          # Per-frame trigger/reject decisions
    └── training_clip_ratings    # Human star ratings + critiques

output/
├── master_events/               # Stage 6 output: full-length rendered clips
│   └── evt_{creator}_{date}_{type}_{id}.mp4
├── release_parts/               # Stage 7 output: platform-ready split parts
│   ├── evt_{id}_part1.mp4
│   ├── evt_{id}_part2.mp4
│   └── evt_{id}_metadata.json
└── compilations/                # Reaction montage compilations
    └── comp_{creator}_{date}.mp4

downloads/
├── ring_buffer/                 # Stage 2: rolling 5-min segments per creator
│   ├── Xyaa/
│   ├── CarryisLive/
│   └── .../
└── event_captures/              # Copies of segments used for event processing
```

### Data Contracts (Typed Interfaces Between Stages)

```python
# Stage 1 → Stage 3
@dataclass
class ActiveTarget:
    search_query: str
    demand_score: int
    velocity: str  # "RISING" | "STABLE" | "DECLINING"
    cue_graph_path: str  # e.g., "GAMEPLAY.DRIVING.PURSUIT"
    required_visual_cues: List[str]
    disqualifying_cues: List[str]
    min_clip_duration: int
    max_clip_duration: int

# Stage 3 → Stage 4
@dataclass
class FlaggedWindow:
    stream_id: str
    creator: str
    start_time: float
    end_time: float
    trigger_source: str  # "DEMAND_MATCH" | "CHAT_SPIKE" | "AUDIO_SPIKE" | "COMBINED"
    trigger_confidence: float
    source_segments: List[Path]

# Stage 4 → Stage 5
@dataclass
class FrameContext:
    t: float
    scene: str
    action: str
    context: str
    details: str
    motion_delta: float
    hud_visible: bool
    matched_target: Optional[str]
    clip_worthy: bool
    confidence: float

# Stage 5 → Stage 6
@dataclass
class EventRecord:
    event_id: str
    stream_id: str
    creator: str
    event_type: str
    matched_target: str
    natural_start: float
    natural_end: float
    duration: float  # Can be 7s or 180s — no artificial limit
    source_segments: List[Path]
    confidence: float

# Stage 6 → Stage 7
@dataclass
class MasterClip:
    event_id: str
    file_path: Path
    duration: float
    creator: str
    language: str
    matched_target: str
    event_type: str

# Stage 7 output
@dataclass
class ReleasePart:
    event_id: str
    part_number: int
    total_parts: int
    file_path: Path
    duration: float
    title: str
    hook_text: str
    platform_targets: List[str]
    publish_at: datetime
```

---

## 10. What Failed in v1 (Do NOT Repeat)

> [!CAUTION]
> These are the five v1 anti-patterns. If you catch yourself doing any of these, STOP.

### Anti-Pattern 1: Pre-Fabricated Labels
**v1 did**: Hardcoded `(0, 11, "POLICE_PURSUIT", ...)` tuples BEFORE looking at the video.  
**v2 rule**: Labels are ALWAYS derived from actual frame analysis. The vision model tells us what it sees; we don't tell it what to see.

### Anti-Pattern 2: Fixed-Duration Blind Slicing
**v1 did**: Every clip was exactly 11 seconds, generated by arithmetic `(N*11, (N+1)*11)`.  
**v2 rule**: Events have natural durations. Capture the full event. Duration constraints are a release-stage concern.

### Anti-Pattern 3: Silent Fallback Substitution
**v1 did**: When a creator's stream download failed, silently used `carry_live_sample.mp4.mkv` for all creators.  
**v2 rule**: If a source file is missing → log error → skip that creator. NEVER substitute one creator's footage under another's name.

### Anti-Pattern 4: Metadata Without Verification
**v1 did**: Said "police chase" in metadata without checking if police were visible in any frame.  
**v2 rule**: Every label passes through the cue-graph. Required cues MUST be confirmed in actual frames before the label is applied.

### Anti-Pattern 5: Training on Garbage Data
**v1 did**: Asked for human ratings on 100 clips that were all sliced from the wrong video with fake labels.  
**v2 rule**: Only run eval/training on clips that passed through the real pipeline. Garbage in → garbage out applies to learning loops too.

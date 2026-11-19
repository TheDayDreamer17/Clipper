# ⚡️ Production Agentic Swarm & Multi-Stream Clipping Engine Architecture

> **System Overview**: An autonomous, distributed 7-agent swarm designed for high-velocity live gaming streams (Twitch & YouTube) targeting the GTA 6 launch. The system ingests search demand in real time, monitors multi-lingual livestreams, filters out copyright-restricted creators, validates narrative coherence in pixels with local vision models (BLIP + CLIP), applies dual-channel branding, and stages viral 9:16 shorts for review and upload.

---

## 1. System Topology & Data Flow

```
┌────────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                                   ⚡️ ANTIGRAVITY AGENT SWARM TOPOLOGY                                   │
└────────────────────────────────────────────────────────────────────────────────────────────────────────┘

  [1. TrendScoutAgent]
         │ (High-velocity YouTube / Google Trends)
         ▼
  [Target Props & Demand DB] (data/telemetry.db - SQLite WAL)
         │
         ▼
  [2. StreamDiscoveryAgent] ──► [Copyright & Rights Shield] (Blacklist non-consenting creators)
         │
         ├───► Global (English & Non-Indian) ──► Target Channel: "⚡️ GTA 6 CLIPS"
         └───► Regional (Hindi / Indic)       ──► Target Channel: "🇮🇳 GTA 6 CLIPS INDIA"
         │
         ├──────────────────────────────────────────┐
         ▼                                          ▼
  [3. YouTubeStreamWatcher]                  [4. TwitchStreamWatcher]
  • Stream chunk buffer & VOD ingest         • Live manifest & Twitch User Clips API
         │                                          │
         └────────────────────┬─────────────────────┘
                              ▼
                 [5. NarrativeGuardrailAgent]
                 • Pre-Cut: BLIP/CLIP Vision & Audio Peak QA
                 • Buffer Check: Action begins + ends with ±3.0s headroom
                 • Loopback: Rejects & instructs Watcher to re-slice if broken
                              │
                              ▼ (Approved Candidate)
                 [6. BrandingCompositorAgent]
                 • 9:16 Vertical Smart Crop & Ambient Blurred Background (1080x1920)
                 • Brand Stamps: (⚡️ GTA 6 CLIPS or 🇮🇳 GTA 6 CLIPS INDIA)
                 • Dynamic Overlay: 3s Animated Hook & Outro Subscription CTA
                              │
                              ▼
                 [7. PublishStagingAgent]
                 • Human-in-the-Loop Web UI Staging (1-Click Approval)
                 • SEO Generator: Viral Title, Hashtags & Channel Routing
                 • Automated Dispatcher: Ready for API Upload once credentials set
```

---

## 2. The 7 Autonomous Agents & Responsibilities

### 1. `TrendScoutAgent` (`trend_scout`)
- **Mission**: Mine real-time user search demand to guide what clips should be extracted.
- **Cadence**: Every 15 minutes across 16 primary seed vectors.
- **Operations**:
  - Fetches top autocomplete search queries from YouTube and Google search endpoints.
  - Clusters raw queries into structured gameplay archetypes (`HEIST_AND_ROBBERY`, `VEHICLE_PURSUIT`, `GRAPHICS_FIDELITY`, `PHYSICS_DEFORMATION`, `STORY_MISSION_ARC`).
  - Synthesizes top 50 active target props into SQLite `telemetry.db`.

### 2. `StreamDiscoveryAgent` (`stream_discovery`)
- **Mission**: Ingest top-ranking livestreams and eliminate legal/copyright risk before compute is spent.
- **Dual-Language Routing**:
  - **Regional (Hindi / Indic)**: e.g., @TechnoGamerz, @CarryMinati $\rightarrow$ Routed to **`GTA 6 CLIPS INDIA`**.
  - **Global (English / International)**: e.g., @RockstarGames, @theRadBrad, @PewDiePie $\rightarrow$ Routed to **`GTA 6 CLIPS`**.
- **Copyright & Rights Shield**:
  - Scans streamer channel bio, video descriptions, and pinned chat bot announcements against strict regex:
    ```python
    COPYRIGHT_PATTERNS = [
        r"no\s+re-?uploads?",
        r"do\s+not\s+(clip|share|repost)",
        r"clips?\s+not\s+allowed",
        r"all\s+rights\s+reserved",
        r"copyright\s+strike",
        r"strictly\s+prohibited"
    ]
    ```
  - If a creator states content sharing or re-uploading is forbidden, they are flagged `STATUS = 'BLACKLISTED_COPYRIGHT'` and skipped entirely.

### 3. `YouTubeStreamWatcher` (`yt_watcher`)
- **Mission**: Ingest live YouTube streams and detect peak clip moments.
- **Operations**:
  - Parses live HLS manifest streams (1080p60).
  - Evaluates rolling audio RMS loudness and visual optical flow delta ($>32.0\text{ px/frame}$).
  - Extracts candidate clip timestamp windows and forwards packets to `NarrativeGuardrailAgent`.

### 4. `TwitchStreamWatcher` (`twitch_watcher`)
- **Mission**: Dual monitoring of live Twitch feeds and organic viewer clips.
- **Operations**:
  - Queries Twitch GQL / Clips API to harvest clips already made by organic viewers during high-traffic stream moments.
  - Calculates view-velocity score: $\text{VPS} = \frac{\Delta \text{Views}}{\Delta \text{Minutes}}$.
  - Dispatches high-velocity clips to `NarrativeGuardrailAgent` for brand compliance and quality scoring.

### 5. `NarrativeGuardrailAgent` (`narrative_guardrail`)
- **Mission**: Reject hallucinations and low-value filler ("Fail Fast, Learn Fast").
- **Operations**:
  - **Headroom Buffer**: Enforces $+2.5\text{s}$ pre-roll and $+3.0\text{s}$ post-roll buffer around action so scenes never start or cut abruptly.
  - **Multi-Frame Vision QA**: Extracts 8 equidistant frames across candidate video; generates frame captions using Salesforce BLIP; computes zero-shot prompt alignment using OpenAI CLIP ViT-B/32 on local GPU (Apple Silicon MPS / CUDA).
  - **Truth in Pixels**: Verifies that claimed objects (e.g. tanks, police cars, robberies) actually exist in pixels.
  - **Closed-Loop Retry**: If the action cuts prematurely or a hook is missing, returns a `RETRY` packet to the watcher agent with adjusted timestamp offsets.

### 6. `BrandingCompositorAgent` (`branding_compositor`)
- **Mission**: Transform 16:9 gameplay into premium, platform-optimized 9:16 vertical shorts (1080x1920).
- **Operations**:
  - **Ambient Blurred Background**: Darkened, blurred 9:16 background (`boxblur=30:5`, `brightness=-0.30`) with a centered 16:9 gameplay window bounded by a 3px border.
  - **Channel Brand Stamp**: Top-left badge (`⚡️ GTA 6 CLIPS` or `🇮🇳 GTA 6 CLIPS INDIA`).
  - **Creator Attribution**: Top-right attribution capsule (`VIA @creator`).
  - **Animated Attention Hook**: Displayed from $t=0.0\text{s}$ to $t=3.0\text{s}$ (`enable='between(t,0,3.0)'`).
  - **Outro Subscription CTA**: Displayed during final 2.5 seconds (`enable='gte(t,DURATION-2.5)'`).
  - **Audio Sync Fix**: Enforces `-avoid_negative_ts make_zero -async 1` to guarantee iOS/macOS Safari audio/video synchronization.

### 7. `PublishStagingAgent` (`publish_staging`)
- **Mission**: Human-in-the-loop review staging and upload dispatching.
- **Operations**:
  - Surfaces rendered shorts on the hosted Web UI control center.
  - Synthesizes platform-ready metadata: High-CTR YouTube Shorts / Reels title, SEO hashtags, description, and creator credits.
  - Stages for 1-click publishing or automated API dispatch (YouTube Data API v3, TikTok Content Posting API).

---

## 3. Technology Stack & Operational Architecture

| Subsystem | Technology | Purpose |
|---|---|---|
| **Runtime & Language** | Python 3.14 / macOS Darwin / MPS GPU | Local, zero-cloud-token compute pipeline |
| **Vision & AI Models** | `Salesforce/blip-image-captioning-base` + `openai/clip-vit-base-patch32` | $0-cost local multi-frame narrative truth evaluation |
| **Video Processing** | FFmpeg 7.x (`libx264`, `aac`, complex filtergraphs) | 1080x1920 vertical composition with timed overlays |
| **Telemetry & Storage** | SQLite in WAL (Write-Ahead Log) mode | Concurrent multi-agent telemetry and decision logging |
| **Server & Networking** | Python `ThreadingHTTPServer` on `tcp46` (IPv4 & IPv6 Dual-Stack) | Accessible via localhost, LAN, and Tailscale cellular mobile |
| **Frontend UI** | Vanilla HTML5 / CSS3 / ES6 (No external JS frameworks) | Lightweight, glassmorphic real-time control center |

---

## 4. Key Questions & Review Prompts for External Models

If you are sharing this plan with another AI model (e.g., Claude 3.5 Sonnet, GPT-4o, OpenAI o1), here are targeted review prompts to ask:

```text
Please review this production architecture for an autonomous multi-stream clipping engine and evaluate:

1. ARCHITECTURAL ROBUSTNESS:
   - Does the 7-agent division of concerns follow solid distributed systems principles?
   - Are there any single points of failure (SPOFs) or potential bottlenecks when monitoring 10+ concurrent livestreams?

2. GUARDRAIL & COMPLIANCE MECHANISMS:
   - Is the regex-based Copyright & Rights Shield sufficient to prevent DMCA strikes, or should it be augmented with heuristic API checks or YouTube Content ID audio probing?
   - How can the ±3.0s buffer headroom and BLIP/CLIP closed-loop retry mechanism be optimized to minimize re-slicing latency?

3. SCALABILITY & CONCURRENCY:
   - In SQLite WAL mode, will concurrent writes from 7 agents cause database lock contention under heavy burst loads?
   - What queuing system (e.g. Redis, Celery, or asyncio queues) would you recommend if scaling this engine to 100+ streams across multiple worker machines?

4. CONTENT ENGAGEMENT:
   - Are the dual-channel branding strategies (Global "GTA 6 CLIPS" vs Regional "GTA 6 CLIPS INDIA") and timed overlays (3s animated hook + 2.5s outro CTA) optimal for maximizing retention on YouTube Shorts and TikTok?
```

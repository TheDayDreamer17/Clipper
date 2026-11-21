# 📋 Outlaw Clips — Project Roadmap & Task Tracker

> **Last Updated**: November 21, 2026  
> **Mission Control Portal**: [http://localhost:3000](http://localhost:3000)

---

## 1. 🛡️ Instagram Account Restoration & Compliance (`@outlawclipshq`)

- [x] **Full Profile Audit**: Audited all Reels on `@outlawclipshq` and identified root causes (Duplicate files, Burst Velocity, Sensitive title keywords).
- [x] **Remove Flagged Duplicate Reel**: Deleted Reel 1 ([`Df_W18CM6sY`](https://www.instagram.com/reel/Df_W18CM6sY/)) via persistent Agent Brave Browser to eliminate the "Unoriginal Content" duplicate penalty.
- [x] **Upload Verified Reel with Collaborator Invite**: Successfully uploaded fresh candidate [Kai Cenat Edgar Cut Reel](https://www.instagram.com/reel/Df_-OHUMv0Y/) (`Df_-OHUMv0Y`) with:
  - Meta Originality Collaborator Tag: `@kaicenat`
  - Sanitized Caption: 0 sensitive words, 11 hashtags, verified `@outlawclipshq` handle.
  - Video Specs: 1080x1920 (9:16), 30s duration, clean audio.
- [x] **Persistent Agent Browser Authentication**: Verified Brave profile (`~/.clipper_browser_profile`) logged in to Instagram & YouTube Studio. Live session synced to `config/instagram_credentials.json`.
- [ ] **Submit Appeal Request**: Open Instagram on mobile $\to$ `Settings and privacy` $\to$ `Account Status` $\to$ `Recommendation Guidelines` $\to$ tap **Request a Review**. *(User Action)*
- [ ] **Monitor Appeal Resolution**: Track restoration of Explore and Recommendation distribution (typically 24–48 hours).

---

## 2. 🚦 Pre-Flight Guardrails & Safety Architecture

- [x] **Instagram Pre-Flight Engine** (`src/instagram_guardrail.py`):
  - [x] **SHA-256 Digital Fingerprinting**: Prevents identical video files or clip IDs from ever posting twice.
  - [x] **Anti-Spam Rate Limiting**: Enforces strict **2.5-hour cooldown** between Reel dispatches to prevent burst-velocity bot flags.
  - [x] **Aspect Ratio & Specs Validator**: Rejects non-vertical (9:16) clips, durations outside 5–90s, and silent videos.
  - [x] **Caption Hygiene**: Strips raw external URLs and enforces verified handle `@outlawclipshq`.
  - [x] **Official Collaborator & Creator Usertagging**: Added `config/creator_handles.json` mapping. Auto-attributes creator tags on every new Reel upload (`src/publisher.py`) to bypass Meta's 2024 aggregator penalty.
- [x] **Qwen-2.5 Local SLM Contextual Sanitizer** (`src/seo_engine.py`):
  - [x] 2-Tier defense-in-depth: Qwen-2.5-1.5B running on Apple Silicon Metal evaluates context and internet slang (English + Hindi/Hinglish).
  - [x] Dynamic asterisk auto-masking (`ass` $\to$ `a**`, `booty` $\to$ `b**ty`, `bitch` $\to$ `b*tch`, `fuck` $\to$ `f*ck`).
- [x] **Integrated Dispatch Gates**: Fully wired into `src/publisher.py` and `src/autonomous_daemon.py`.

---

## 3. 📊 Mission Control Social Analytics Dashboard

- [x] **Social Analytics Engine** (`src/social_analytics.py`):
  - [x] Real-time YouTube Data API v3 integration for **US Global** channel (`@OutlawClipsGlobal`).
  - [x] Real-time YouTube Data API v3 integration for **India** channel (`@OutlawClipsHindi`).
  - [x] Instagram profile metrics integration (`@outlawclipshq`).
  - [x] In-memory **10-minute TTL caching** to conserve daily Google API quota.
- [x] **Web Portal Header Banner** (`src/web_ui.py`):
  - [x] Render live channel cards on `http://localhost:3000` with subscriber counts, lifetime views, live Shorts counts, and direct links.
  - [x] Endpoint `/api/analytics` active with auto-refresh every 60 seconds.
- [ ] **Advanced Analytics Enhancements**:
  - [ ] Add 7-day view growth velocity sparklines.
  - [ ] Add Shorts retention curve & like-to-view ratio indicators.

---

## 4. 🌐 Persistent Agent Browser (Reboot-Proof)

- [x] **Playwright Core Integration**: Installed and configured `playwright-1.65.2` in `.venv`.
- [x] **Persistent Disk Profile**: Configured `~/.clipper_browser_profile/` targeting `/Applications/Brave Browser.app`.
- [x] **1-Time Setup Completed** (`src/agent_browser_setup.py`):
  - [x] Authenticated 2 Google Accounts (YouTube Studio Global & India).
  - [x] Authenticated 1 Instagram Account (`@outlawclipshq`).
  - [x] Session tokens and cookies saved permanently to local SSD.
- [x] **Controller Framework** (`src/agent_browser.py`):
  - [x] Headless and headful execution modes.
  - [x] Automated YouTube Studio video title & description editor.
  - [x] Automated Instagram Reel management methods.
- [ ] **Browser Automation Workflows**:
  - [ ] Automated YouTube Studio copyright & monetization claim checker.
  - [ ] Automated pinned comment publisher via browser agent.

---

## 5. 🎮 Continuous Multi-Stream Clipping & Auto-Pilot

- [x] **Expanded Creator Discovery**: Active 35+ creator monitoring roster (Kai Cenat, IShowSpeed, CaseOh, Ludwig, CarryisLive, Dynamo, Mortal, Scout, Techno Gamerz, Xyaa).
- [x] **Dense Mosaic Dynamic Censor**: Batched 48-frame PyTorch scanning with 32px broadcast mosaic and dynamic emblem logo sizing.
- [x] **Pure GTA 6 Game Locking**: Scrapers, trend miners, and pipelines locked strictly to **Grand Theft Auto VI** (purged all GTA 5 / Los Santos fallback queries).
- [ ] **Autonomous Dispatch Monitoring**: Monitor next scheduled drops:
  - YouTube Global: Next drop in 6h window.
  - YouTube India: Next drop in 6h window.
  - Instagram Reels: Next drop following 2.5h cooldown.



---

## 6. 👤 Single-Creator Dedicated Studio & Narrative Brain (Ravi Setup)

Architecture for dedicated single-player end-to-end playthrough analysis, multi-format content generation (Shorts + Long-form), dedicated creator portal, and comedic meme curation.

### A. 🖥️ Dedicated Creator Portal & Feedback Loop
- [ ] **Creator Review Portal UI** (`/portal/ravi`):
  - [ ] Dedicated web interface for Ravi to review generated Shorts, Reels, and Long-form cuts.
  - [ ] Integrated revision request system: timecoded commentary (*"make this shorter"*, *"trim the first 3 seconds"*, *"change banner hook"*).
  - [ ] Interactive Stream Natural Language Query: prompt bar allowing the creator to request specific moments (*"Get me the clip where I failed the heist 3 times"*, *"Find my fastest sports car drift"*).
- [ ] **Direct Multi-Channel Dispatch**:
  - [ ] Telegram Bot delivery webhook with inline approve / request-edit buttons.
  - [ ] Automatic syncing between Telegram actions and the Web Portal review queue.

### B. 🧠 Dense Gameplay Logging Engine (60-Frame Semantic Journal)
- [ ] **Stream Perception Worker** (`src/creator_journal_engine.py`):
  - [ ] Continuous windowed frame analysis (every 60 frames / ~2 sec) using Vision SLM + CLIP + OCR HUD parser.
  - [ ] Structured session markdown journal (`docs/streams/ravi/session_{date}_journal.md`) tracking:
    - **Mission State Machine**: `MISSION_START`, `CHECKPOINT`, `MISSION_FAILED`, `MISSION_PASSED`, `FREE_ROAM`.
    - **Telemetry & Physics Events**: Collision spikes, top-speed cruising, weapon crosshair hits, player death ragdoll.
    - **Audio Energy & Emotion**: Screams, laughter, frustration sighs, long silences (dead air).

### C. 🎬 Narrative Director & Meme Curation Agent (`src/narrative_curator.py`)
- [ ] **Multi-Format Assembly Engine**:
  - [ ] **Long-Form Walkthroughs (16:9 4K/1080p)**: Auto-stitches complete story arcs (`MISSION_START` -> `MISSION_PASSED`) trimming out tedious dead travel while preserving cutscenes and story dialogue.
  - [ ] **Short-Form Viral Moments (9:16 Shorts/Reels)**: Auto-cuts punchy 15–45s vertical clips optimized for retention.
- [ ] **Comedic & Meme Pattern Synthesizer**:
  - [ ] **"The Noob Arc" (Failure Montage -> Climax)**: Detects repeated `MISSION_FAILED` loops on the same checkpoint. Cuts rapid comedic failure cuts with meme SFX (fart sound, sad trombone, 'directed by robert b weide'), resolving into the final victory.
  - [ ] **"Heavy Driver" vs. "Traffic God"**:
    - *Smooth Operator*: High-speed city driving with 0 collisions over 20s -> pair with phonk / cool aura audio.
    - *Heavy Driver Meme*: Streamer claims driving confidence -> immediate catastrophic collision chain -> meme punchline audio.
  - [ ] **"Aura Entry vs. Instant Regret"**: Slow-motion cinematic zoom/letterbox of confident combat walk-in (Bollywood / Salman Khan / Sigma walk vibe), abruptly cut to instant ragdoll death with comedic cutoff audio.
  - [ ] **SEO & Search-Trend Aligned Guides**: Matches gameplay moments against trending Google/YouTube searches (e.g. *"How to escape 5-star police in Vice City"*, *"Hidden weapon location"*).

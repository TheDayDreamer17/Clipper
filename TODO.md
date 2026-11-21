# 📋 Outlaw Clips — Project Roadmap & Task Tracker

> **Last Updated**: November 21, 2026  
> **Mission Control Portal**: [http://localhost:3000](http://localhost:3000)

---

## 1. 🛡️ Instagram Account Restoration & Compliance (`@outlawclipshq`)

- [x] **Full Profile Audit**: Audited all Reels on `@outlawclipshq` and identified root causes (Duplicate files, Burst Velocity, Sensitive title keywords).
- [x] **Remove Flagged Duplicate & Un-collaborated Reels**: Deleted flagged Reels ([`Df_W18CM6sY`](https://www.instagram.com/reel/Df_W18CM6sY/), [`Df-fnjAMC2k`](https://www.instagram.com/reel/Df-fnjAMC2k/), [`DgADFcXMb2H`](https://www.instagram.com/reel/DgADFcXMb2H/), [`DgAF9dwMI6D`](https://www.instagram.com/reel/DgAF9dwMI6D/), [`Df-QHOrszIG`](https://www.instagram.com/reel/Df-QHOrszIG/)) via persistent Agent Brave Browser to clean the grid of un-attributed media.
- [x] **Upload Verified Reels with Collaborator Invites & Fixed Account Branding**:
  - [x] [CaseOh GTA 6 Police Reel](https://www.instagram.com/reel/DgAHnPBsRp-/) (`DgAHnPBsRp-`): Co-Author `@caseoh_games` (`55153794944`), `FOLLOW @OUTLAWCLIPSHQ` pill.
  - [x] [IShowSpeed GTA 6 Drip Reel](https://www.instagram.com/reel/DgAN8BhMxnS/) (`DgAN8BhMxnS`): Co-Author `@ishowspeed` (`1541770582`), `FOLLOW @OUTLAWCLIPSHQ` pill, mapped handle `@ishowspeed`.
- [x] **Overlay Generator & Asset Pipeline Upgrade**:
  - Hardcoded middle divider updated to `FOLLOW @OUTLAWCLIPSHQ` in `src/slicer.py`.
  - Dynamic streamer attribution mapping via `config/creator_handles.json`.
  - Purged all 60 stale pre-rendered overlay assets from `data/brand_assets/`.
  - Fixed residual `@OutlawClips` text in `src/web_ui.py` to `@outlawclipshq`.
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

### A. 🖥️ Dedicated Creator Portal & Feedback Loop (`/portal/ravi`)
- [ ] **Creator Review Portal UI** (`/portal/ravi` in `src/web_ui.py`):
  - [ ] Dedicated route with lightweight PIN/token authentication.
  - [ ] Interactive video player with timestamped feedback input (*"make this shorter"*, *"trim 3s from start"*, *"swap to phonk BGM"*).
  - [ ] **Curator Rationale & Feedback Reason Submission**:
    - Displays why the curator nominated this clip (*"Nominated because: Unscripted armed clerk counter-ambush during robbery [Confidence: 94%]"*).
    - Structured "Reasons to Choose / Reject" feedback form (tag pills: *"Too routine"*, *"NPC dialogue hilarious"*, *"Unexpected twist was gold"*, *"Needs louder punchline"*) + freeform critique that directly recalibrates the Curator Profile.
  - [ ] Natural Language Clip Retrieval Bar: search bar querying the stream journal (*"get me the clip where I failed the bank heist 3 times"*, *"find my top speed drift through Vice Beach"*).
  - [ ] Bidirectional Telegram Bot Sync: Approve/revision buttons sync state between Telegram and `/portal/ravi`.

### B. 🧠 Dense Gameplay Logging Engine (Continuous 1 FPS Streaming Pipeline)
- [ ] **Stream Perception Worker** (`src/creator_journal_engine.py`):
  - [ ] **Real-Time 1 FPS Direct Stream Pipe**: Inspects 1 frame per second (`fps=1`) directly from live streams (or VOD replays) via FFmpeg pipe without saving large master video dumps.
  - [ ] Uses local Vision SLM + CLIP + OCR HUD parser to classify in-game states and actions for every single second.
  - [ ] Emits a persistent chronological context journal (`docs/streams/ravi/session_{date}_journal.md`) recording:
    - **Second-by-Second Telemetry**: `t=00:01:24`, HUD state, mission banner text, speedometer reading, minimap threat indicators.
    - **Mission State Machine**: `MISSION_START`, `CHECKPOINT`, `MISSION_FAILED`, `MISSION_PASSED`, `FREE_ROAM`.
    - **Physical & Combat Events**: Collision impacts, weapon firing, police wanted star escalations, player death/ragdoll.
    - **Audio Energy & Emotion**: Spoken exclamations, screams, laughter, frustration sighs, dead air silences.
  - [ ] **Context Query API**: Serves full second-by-second context to the portal search bar for natural-language retrieval.

### C. 🎵 Curated SFX & Meme Asset Library (`assets/sfx/`)
- [ ] **Pre-bundled Audio Library**:
  - [ ] `assets/sfx/bollywood_aura/`: Hero walk-in BGMs (Salman Khan entry style, KGF/Vikram bass drops, Sigma phonk).
  - [ ] `assets/sfx/comedic_fail/`: Fart sounds, sad trombone, squeaky toy, 'Directed by Robert B. Weide', record scratch.
  - [ ] `assets/sfx/heavy_driver/`: High-energy driving phonk, tire screeches, catastrophic crash impact boom.
  - [ ] `assets/sfx/punchline_accents/`: Anime 'wow', dramatic reverb thud, 'bruh' sound effect.

### D. 🎬 Narrative Director & Dual-Format Viral Engine (`src/narrative_curator.py`)
- [ ] **Dual-Format Output with Viral-Worthy Gate**:
  - [ ] **Short-Form Viral Moments (9:16 Shorts/Reels)**: 15–45s punchy vertical edits.
    - *"The Noob Arc"*: Multi-failure loops cut with comedic SFX resolving into final triumph.
    - *"Heavy Driver Meme"*: Overconfident driving banter cut into instant multi-car pileup.
    - *"Aura Entry vs. Instant Regret"*: Slow-mo cinematic letterboxed walk-in sharply cut to ragdoll death with comedic timing.
  - [ ] **Long-Form Episodic Walkthroughs (16:9 4K/1080p)**: Mission-by-mission complete story walkthroughs (`MISSION_START` -> `MISSION_PASSED`) with cutscenes and story dialogue intact and dead travel fast-forwarded.
  - [ ] **Extended Viral Activities (>60s)**: Any high-energy activity lasting beyond the 45s short threshold (e.g. 5-star military survival marathon, elaborate boat chases) packaged into 2–5 min dedicated showcase cuts if `viral_score >= 80`.

### E. 🎭 Emergent Gameplay Curator Profile (`data/curator_profiles/ravi_curator_profile.json`)
- [ ] **Unusual & Out-of-the-Ordinary Archetype Detectors**:
  - [ ] **"Accidental Chaos & Instant Karma"**: Routine crash leading to unexpected chain reaction (secondary explosions, hit NPC landing on moving truck, instant karma ragdoll).
  - [ ] **"Robbery & Rent Collection Gone Wrong"**: Intended shakedown meeting unexpected resistance (clerk pulling a shotgun, undercover cop behind door, empty register).
  - [ ] **"Bizarre NPC Anomalies"**: Bizarre open-world pedestrian interactions (wildlife bursting into urban shops, NPCs stealing streamer's getaway car, hilarious bystander commentary).
- [ ] **Continuous Closed-Loop Calibration Engine**:
  - [ ] Updates category selection weights and appends learned heuristic rules to the curator profile whenever Ravi submits his reasons for choosing or rejecting clips in `/portal/ravi`.


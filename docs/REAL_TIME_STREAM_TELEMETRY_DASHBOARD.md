# 📊 Real-Time Stream Telemetry & Observability Dashboard

> **Purpose:** Live audit trail tracking all streams, detected game moments, rejection causes, and tournament QA evaluations.  
> **Last Generated:** 2026-11-18 09:21:49  
> **Storage Engine:** SQLite WAL Mode (`data/telemetry.db`)

---
## 📈 High-Level Statistical Summary

| Metric | Count / Value | Operational Meaning |
| :--- | :---: | :--- |
| **Active Stream Workers** | **9 Channels** | Concurrent live monitoring agents |
| **Total Cadence Frames Checked** | **22 Frames** | Evaluated every 3 seconds |
| **High-Confidence Event Triggers** | **9 Triggers** | Crossed model threshold for clipping |
| **Filtered Out (Rejections)** | **13 Frames** | Dead air / false positive prevention |
| **Crowned Viral Shorts** | **3 Videos** | Passed Tournament QA Gatekeeper |

---
## 📡 Active Monitored Streams

| Session ID | Creator Name | Platform | Language | Status | Source URL |
| :--- | :--- | :---: | :---: | :---: | :--- |
| `sess_techno_gamerz_1794970186` | **Techno Gamerz** | `YOUTUBE` | `https://www.youtube.com/watch?v=fcexQBagpc4` | 🟢 `ACTIVE` | [Watch Stream](Hindi) |
| `sess_theradbrad_1794970186` | **theRadBrad** | `YOUTUBE` | `https://www.youtube.com/watch?v=kCU9NEbxj_4` | 🟢 `ACTIVE` | [Watch Stream](English) |
| `sess_gta_series_videos_1794970186` | **GTA Series Videos** | `YOUTUBE` | `https://www.youtube.com/watch?v=x1MoTocndkY` | 🟢 `ACTIVE` | [Watch Stream](English) |
| `sess_theradbrad_1794973762` | **theRadBrad** | `YOUTUBE` | `https://www.youtube.com/watch?v=kCU9NEbxj_4` | 🟢 `ACTIVE` | [Watch Stream](English) |
| `sess_techno_gamerz_1794973762` | **Techno Gamerz** | `YOUTUBE` | `https://www.youtube.com/watch?v=fcexQBagpc4` | 🟢 `ACTIVE` | [Watch Stream](Hindi) |
| `sess_gta_series_videos_1794973762` | **GTA Series Videos** | `YOUTUBE` | `https://www.youtube.com/watch?v=x1MoTocndkY` | 🟢 `ACTIVE` | [Watch Stream](English) |
| `sess_gta_series_videos_1794973893` | **GTA Series Videos** | `YOUTUBE` | `https://www.youtube.com/watch?v=x1MoTocndkY` | 🟢 `ACTIVE` | [Watch Stream](English) |
| `sess_theradbrad_1794973893` | **theRadBrad** | `YOUTUBE` | `https://www.youtube.com/watch?v=kCU9NEbxj_4` | 🟢 `ACTIVE` | [Watch Stream](English) |
| `sess_techno_gamerz_1794973893` | **Techno Gamerz** | `YOUTUBE` | `https://www.youtube.com/watch?v=fcexQBagpc4` | 🟢 `ACTIVE` | [Watch Stream](Hindi) |

---
## 🛑 Diagnostic Audit: Where Did We Go Wrong? (Top Rejection Causes)

Understanding why potential clips are rejected allows us to fine-tune prompts and filters in real time:

| Rejection Reason / Filter Trigger | Frames Dropped | Diagnostic Meaning & Mitigation |
| :--- | :---: | :--- |
| `Confidence < 45.0% threshold` | **6** | Filtered to prevent false positive or low retention clip |
| `Negative Anchor: third person camera hovering b` | **3** | Filtered to prevent false positive or low retention clip |
| `Negative Anchor: active 3D in-game camera drivi` | **3** | Filtered to prevent false positive or low retention clip |
| `Deduplication: POLICE_PURSUIT_police_pursuit already published` | **1** | Filtered to prevent false positive or low retention clip |

---
## 🏆 Tournament Event Provenance & Output Audit

| Creator | Event / Scenario | Window | Winning Cut | Score | QA Status | Output Short Link | Rejection Notes / Tuning |
| :--- | :--- | :---: | :--- | :---: | :---: | :--- | :--- |
| **Techno Gamerz** | `In-Car Cockpit Driving with Steering Wheel & Dashboard Toggle` | `0s-20s` | `Candidate B: Full Arc (20s)` | **84.8/100** (🔥 VIRAL BREAKOUT) | ✅ PASS | [`techno_gamerz_-_in-car_cockpit_driving_with_steering_wheel_&_dashboard_toggle_WINNER_9x16.mp4`](output/tournament_winners/techno_gamerz_-_in-car_cockpit_driving_with_steering_wheel_&_dashboard_toggle_WINNER_9x16.mp4) | *Tournament Winner passed QA* |
| **GTA Series Videos** | `Complete Character Artwork Rotation (Michael, Franklin, Trevor, Bikini Girl)` | `0s-20s` | `Candidate A: Fast Climax (14s)` | **88.3/100** (🔥 VIRAL BREAKOUT) | ✅ PASS | [`gta_series_videos_-_complete_character_artwork_rotation_(michael,_franklin,_trevor,_bikini_girl)_WINNER_9x16.mp4`](output/tournament_winners/gta_series_videos_-_complete_character_artwork_rotation_(michael,_franklin,_trevor,_bikini_girl)_WINNER_9x16.mp4) | *Tournament Winner passed QA* |
| **theRadBrad** | `Los Santos High-Speed 3-Star Police Pursuit with Cruisers & Sirens` | `0s-20s` | `Candidate B: Full Arc (20s)` | **78.2/100** (⚡ HIGH RETENTION) | ✅ PASS | [`theradbrad_-_los_santos_high-speed_3-star_police_pursuit_with_cruisers_&_sirens_WINNER_9x16.mp4`](output/tournament_winners/theradbrad_-_los_santos_high-speed_3-star_police_pursuit_with_cruisers_&_sirens_WINNER_9x16.mp4) | *Tournament Winner passed QA* |

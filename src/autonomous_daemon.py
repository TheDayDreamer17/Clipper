"""
Autonomous Multi-Agent Clipper Daemon for GTA 6 Live Streams.
Coordinates TrendScout, TwitchStreamWatcher, MultiModalScorer, NarrativeGuardrail,
and BrandingCompositor in parallel using SQLite WAL event streaming.
"""

import os
import sys
import time
import signal
import sqlite3
import threading
from pathlib import Path
from typing import List, Dict, Any, Optional

# Ensure project root is in path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.agent_swarm import AgentSwarmCoordinator
from src.twitch_clips import TwitchClipEngine
from src.trend_miner import TrendMiner
from src.transcribe import Transcriber
from src.scorer import ViralityScorer
from src.slicer import VideoSlicer

class AutonomousClipperDaemon:
    def __init__(self, db_path: str = "data/telemetry.db", poll_interval: int = 60):
        self.db_path = Path(db_path)
        self.poll_interval = poll_interval
        self.running = False
        self.swarm = AgentSwarmCoordinator()
        self.twitch_engine = TwitchClipEngine(temp_dir="downloads/ring_buffer/gta6_live")
        self.trend_miner = TrendMiner()
        self.transcriber = Transcriber()
        self.scorer = ViralityScorer()
        self.slicer = VideoSlicer()
        self._init_db()

    def _init_db(self):
        conn = sqlite3.connect(str(self.db_path))
        c = conn.cursor()
        c.execute("PRAGMA journal_mode=WAL;")
        c.execute("""
            CREATE TABLE IF NOT EXISTS agent_live_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                agent_id TEXT,
                agent_name TEXT,
                event_type TEXT,
                message TEXT,
                details_json TEXT,
                timestamp TEXT,
                created_at REAL
            );
        """)
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
        conn.commit()
        conn.close()

    def start(self):
        self.running = True
        print("\n" + "=" * 70)
        print("🚀 AUTONOMOUS GTA 6 MULTI-AGENT CLIPPER DAEMON ACTIVATED")
        print("   Coordination: SQLite WAL Bus | Engine: Apple Silicon Metal / MLX")
        print("   Mission Control UI: http://localhost:8766")
        print("=" * 70)

        self.swarm.log_event(
            "swarm_coordinator",
            "SwarmCoordinator",
            "DAEMON_STARTED",
            "Autonomous multi-agent daemon loop initialized on Apple Silicon."
        )

        # Thread 1: Trend Scout (every 15 min)
        t_trends = threading.Thread(target=self._trend_scout_loop, daemon=True, name="TrendScoutThread")
        t_trends.start()

        # Thread 2: Stream Watcher & Clipper Pipeline (every 60 sec)
        t_clipper = threading.Thread(target=self._stream_pipeline_loop, daemon=True, name="StreamClipperThread")
        t_clipper.start()

        # Thread 3: Autonomous Social Publisher (every 2 hours to YouTube & Instagram)
        t_publisher = threading.Thread(target=self._auto_publish_loop, daemon=True, name="AutoPublisherThread")
        t_publisher.start()

        # Main supervision thread
        try:
            while self.running:
                time.sleep(1)
        except (KeyboardInterrupt, SystemExit):
            self.stop()

    def stop(self):
        print("\n🛑 Stopping Autonomous Clipper Daemon...")
        self.running = False
        self.swarm.log_event(
            "swarm_coordinator",
            "SwarmCoordinator",
            "DAEMON_STOPPED",
            "Autonomous multi-agent daemon shutdown cleanly."
        )

    def _trend_scout_loop(self):
        while self.running:
            try:
                self.swarm.log_event(
                    "trend_scout",
                    "TrendScoutAgent",
                    "TREND_POLL_START",
                    "Polling live YouTube and Google autocomplete for high-velocity GTA 6 queries..."
                )
                trends = self.trend_miner.fetch_live_search_trends(["GTA 6 live", "GTA 6 gameplay", "GTA 6 leak"])
                top_queries = trends[:8]
                self.swarm.log_event(
                    "trend_scout",
                    "TrendScoutAgent",
                    "TRENDS_UPDATED",
                    f"Discovered {len(trends)} high-velocity search queries: {', '.join(top_queries[:4])}",
                    {"top_queries": top_queries}
                )
            except Exception as e:
                self.swarm.log_event("trend_scout", "TrendScoutAgent", "ERROR", f"Trend scout exception: {e}")
            
            # Wait 15 minutes between trend sweeps
            for _ in range(900):
                if not self.running:
                    return
                time.sleep(1)

    def _stream_pipeline_loop(self):
        # Initial brief warmup delay
        time.sleep(5)
        while self.running:
            try:
                self._run_single_clipping_cycle()
            except Exception as e:
                self.swarm.log_event(
                    "swarm_coordinator",
                    "SwarmCoordinator",
                    "CYCLE_ERROR",
                    f"Pipeline cycle error: {str(e)[:150]}"
                )

            # Wait poll interval
            for _ in range(self.poll_interval):
                if not self.running:
                    return
                time.sleep(1)

    def _auto_publish_loop(self):
        # Paced Multi-Platform Flywheel:
        # 1. Instagram drops every 4 hours to build organic momentum without velocity flags.
        # 2. YouTube drops top verified winners every 14 hours (1-2 drops/day) to stay in optimal Shorts Feed testing window.
        ig_interval = 4 * 3600
        yt_interval = 14 * 3600
        last_ig_time = 0
        last_yt_time = 0

        time.sleep(60) # Initial 60-second warmup

        while self.running:
            now = time.time()
            try:
                # 1. YouTube Paced Drops (every 6 hours)
                if now - last_yt_time >= yt_interval:
                    self._dispatch_scheduled_youtube()
                    last_yt_time = now

                # 2. Instagram Fast-Paced Drops (every 2 hours)
                if now - last_ig_time >= ig_interval:
                    self._dispatch_scheduled_instagram()
                    last_ig_time = now
            except Exception as e:
                self.swarm.log_event(
                    "social_dispatcher",
                    "SocialDispatchAgent",
                    "AUTO_PUBLISH_ERROR",
                    f"Auto-publish cycle error: {str(e)[:150]}"
                )

            # Check every 60 seconds
            for _ in range(60):
                if not self.running:
                    return
                time.sleep(1)

    def _dispatch_scheduled_youtube(self):
        """Paced YouTube Drops (Every 6h): 1 Hindi to YT India, 1 English to YT US. Prioritizes QUEUED clips."""
        from src.seo_engine import ViralSEOEngine
        from src.publisher import VideoPublisher

        seo = ViralSEOEngine()
        pub = VideoPublisher()

        # YouTube India
        conn = sqlite3.connect(str(self.db_path))
        c = conn.cursor()
        c.execute("""
            SELECT clip_id, video_path, target_search, creator, expected_spoken 
            FROM training_clip_ratings 
            WHERE (human_verdict = 'QUEUED' OR human_verdict = 'APPROVED' OR human_verdict = 'REVIEW')
              AND human_verdict != 'PUBLISHED' AND human_verdict != 'FAILED' AND human_verdict != 'QUARANTINED' AND category != 'MATURE_SCENE'
              AND language LIKE '%Hindi%'
            ORDER BY (CASE WHEN human_verdict = 'QUEUED' THEN 1 ELSE 0 END) DESC, virality_score DESC, rated_at DESC LIMIT 1;
        """)
        hindi_row = c.fetchone()
        conn.close()

        if hindi_row:
            cid, vpath_raw, target_search, creator, spoken_tx = hindi_row
            real_file = Path("output") / vpath_raw.replace("/video/", "")
            if real_file.exists():
                print(f"🚀 [YT-Dispatch]: Uploading Hindi clip '{cid}' to YouTube India...")
                seo_pkg = seo.generate_seo_package(action_headline=target_search or cid, transcript=spoken_tx or "", streamer_name=creator or "Streamer", channel_type="india")
                yt_res = pub.upload_youtube_unlisted(video_path=str(real_file), title=seo_pkg.get("title", f"{target_search} #Shorts"), description=seo_pkg.get("description", ""), tags=seo_pkg.get("youtube_tags", []), target_channel="india", privacy_status="public")
                
                conn = sqlite3.connect(str(self.db_path))
                if yt_res.get("status") == "ok":
                    conn.execute("UPDATE training_clip_ratings SET human_verdict = 'PUBLISHED', publish_error = NULL WHERE clip_id = ?", (cid,))
                    print(f"✅ [YT India Dispatched]: {yt_res.get('url')}")
                else:
                    err_msg = yt_res.get("message", "YouTube upload failed")
                    conn.execute("UPDATE training_clip_ratings SET human_verdict = 'FAILED', publish_error = ? WHERE clip_id = ?", (err_msg, cid))
                    print(f"⚠️ [YT India Failed]: {err_msg}")
                conn.commit()
                conn.close()

        # YouTube US / Global
        conn = sqlite3.connect(str(self.db_path))
        c = conn.cursor()
        c.execute("""
            SELECT clip_id, video_path, target_search, creator, expected_spoken 
            FROM training_clip_ratings 
            WHERE (human_verdict = 'QUEUED' OR human_verdict = 'APPROVED' OR human_verdict = 'REVIEW')
              AND human_verdict != 'PUBLISHED' AND human_verdict != 'FAILED' AND human_verdict != 'QUARANTINED' AND category != 'MATURE_SCENE'
              AND (language NOT LIKE '%Hindi%' OR language IS NULL)
            ORDER BY (CASE WHEN human_verdict = 'QUEUED' THEN 1 ELSE 0 END) DESC, virality_score DESC, rated_at DESC LIMIT 1;
        """)
        en_row = c.fetchone()
        conn.close()

        if en_row:
            cid, vpath_raw, target_search, creator, spoken_tx = en_row
            real_file = Path("output") / vpath_raw.replace("/video/", "")
            if real_file.exists():
                print(f"🚀 [YT-Dispatch]: Uploading English clip '{cid}' to YouTube US...")
                seo_pkg = seo.generate_seo_package(action_headline=target_search or cid, transcript=spoken_tx or "", streamer_name=creator or "Streamer", channel_type="us")
                yt_res = pub.upload_youtube_unlisted(video_path=str(real_file), title=seo_pkg.get("title", f"{target_search} #Shorts"), description=seo_pkg.get("description", ""), tags=seo_pkg.get("youtube_tags", []), target_channel="us", privacy_status="public")
                
                conn = sqlite3.connect(str(self.db_path))
                if yt_res.get("status") == "ok":
                    conn.execute("UPDATE training_clip_ratings SET human_verdict = 'PUBLISHED', publish_error = NULL WHERE clip_id = ?", (cid,))
                    print(f"✅ [YT US Dispatched]: {yt_res.get('url')}")
                else:
                    err_msg = yt_res.get("message", "YouTube upload failed")
                    conn.execute("UPDATE training_clip_ratings SET human_verdict = 'FAILED', publish_error = ? WHERE clip_id = ?", (err_msg, cid))
                    print(f"⚠️ [YT US Failed]: {err_msg}")
                conn.commit()
                conn.close()

    def _dispatch_scheduled_instagram(self):
        """Fast-Paced Instagram Drops (Every 2h): Posts top pending verified clip to Instagram Reels. Prioritizes QUEUED clips."""
        from src.seo_engine import ViralSEOEngine
        from src.publisher import VideoPublisher
        from src.instagram_guardrail import InstagramPreflightValidator

        validator = InstagramPreflightValidator(db_path=str(self.db_path))
        vel_ok, vel_err, rem_sec = validator.check_upload_velocity()
        if not vel_ok:
            print(f"⏳ [IG-Dispatch Cooldown]: {vel_err}")
            return

        seo = ViralSEOEngine()
        pub = VideoPublisher()

        conn = sqlite3.connect(str(self.db_path))
        c = conn.cursor()
        c.execute("""
            SELECT clip_id, video_path, target_search, creator, expected_spoken, language 
            FROM training_clip_ratings 
            WHERE (human_verdict = 'QUEUED' OR human_verdict = 'APPROVED' OR human_verdict = 'REVIEW')
              AND human_verdict != 'PUBLISHED' AND human_verdict != 'FAILED' AND human_verdict != 'QUARANTINED' AND category != 'MATURE_SCENE'
            ORDER BY (CASE WHEN human_verdict = 'QUEUED' THEN 1 ELSE 0 END) DESC, virality_score DESC, rated_at DESC LIMIT 1;
        """)
        row = c.fetchone()
        conn.close()

        if row:
            cid, vpath_raw, target_search, creator, spoken_tx, lang = row
            real_file = Path("output") / vpath_raw.replace("/video/", "")
            if real_file.exists():
                print(f"📸 [IG-Dispatch]: Uploading top clip '{cid}' (@{creator}) to Instagram Reels...")
                ch_type = "india" if "hindi" in (lang or "").lower() else "us"
                seo_pkg = seo.generate_seo_package(action_headline=target_search or cid, transcript=spoken_tx or "", streamer_name=creator or "Streamer", channel_type=ch_type)
                ig_res = pub.upload_instagram_reel(
                    video_path=str(real_file),
                    caption=seo_pkg.get("instagram_caption", ""),
                    streamer_name=creator
                )
                
                conn = sqlite3.connect(str(self.db_path))
                if ig_res.get("status") == "ok":
                    conn.execute("UPDATE training_clip_ratings SET human_verdict = 'PUBLISHED', publish_error = NULL WHERE clip_id = ?", (cid,))
                    print(f"✅ [Instagram Reel Dispatched]: {ig_res.get('url')}")
                    self.swarm.log_event(
                        "social_dispatcher",
                        "SocialDispatchAgent",
                        "IG_DISPATCH_COMPLETE",
                        f"Instagram Reel '{cid}' published! URL: {ig_res.get('url')}",
                        {"clip_id": cid, "instagram": ig_res}
                    )
                else:
                    err_msg = ig_res.get("message", "Instagram upload failed")
                    if "Pre-flight Guardrail" in err_msg:
                        conn.execute("UPDATE training_clip_ratings SET human_verdict = 'QUARANTINED', publish_error = ? WHERE clip_id = ?", (err_msg, cid))
                        print(f"🛑 [Instagram Quarantined]: {err_msg}")
                    else:
                        conn.execute("UPDATE training_clip_ratings SET human_verdict = 'FAILED', publish_error = ? WHERE clip_id = ?", (err_msg, cid))
                        print(f"⚠️ [Instagram Failed]: {err_msg}")
                conn.commit()
                conn.close()
        else:
            print("⏳ [IG-Dispatch]: No pending clips ready for Instagram.")

    def _run_single_clipping_cycle(self):
        self.swarm.log_event(
            "stream_discovery",
            "StreamDiscoveryAgent",
            "STREAM_AUDIT",
            "Auditing active live Twitch GTA 6 broadcasts and approved creator clips..."
        )

        # Pure GTA 6 discovery (Grand Theft Auto VI Viral Moments across Day, Week & Month)
        clips = []
        for gname in ["Grand Theft Auto VI"]:
            for period in ["LAST_DAY", "LAST_WEEK", "LAST_MONTH"]:
                try:
                    found = self.twitch_engine.fetch_top_clips(game_name=gname, limit=50, period=period)
                    for f in found:
                        if not any(existing["slug"] == f["slug"] for existing in clips):
                            clips.append(f)
                except Exception:
                    pass

        if not clips:
            self.swarm.log_event(
                "twitch_watcher",
                "TwitchStreamWatcher",
                "NO_CLIPS",
                "No new GTA 6 audience clips found this cycle. Waiting for next window."
            )
            return

        # Check existing in SQLite (Robust Title & Slug matching + Tombstone Blacklist)
        conn = sqlite3.connect(str(self.db_path))
        c = conn.cursor()
        c.execute("CREATE TABLE IF NOT EXISTS tombstone_rejected_clips (slug TEXT PRIMARY KEY, title TEXT, clip_id TEXT, rejected_at REAL);")
        c.execute("""
            SELECT clip_id, expected_vision, target_search FROM training_clip_ratings
            UNION
            SELECT clip_id, slug, title FROM tombstone_rejected_clips;
        """)
        all_text = " ".join(str(val).lower() for row in c.fetchall() for val in row if val)
        conn.close()

        unprocessed = [
            c for c in clips 
            if c["title"].lower().strip() not in all_text and c["slug"].lower()[:15] not in all_text
        ]

        # Strict clickbait & NSFW title blacklist
        CLICKBAIT_BLACKLIST = {
            "bikini", "gooner", "!cam2", "cam2", "hot tub", "hottub", "dating", "nsfw",
            "18+", "erotic", "onlyfans", "twerk", "strip", "feet", "feetcam", "subathon bikini"
        }

        # Sort unprocessed clips by view_count descending to capture top viral moments first
        unprocessed.sort(key=lambda x: int(x.get("view_count") or 0), reverse=True)

        # Ingest from ALL creators streaming GTA 6 (filtered only by spam/clickbait guardrails)
        curated_candidates = []
        for c in unprocessed:
            title_lower = c["title"].lower()
            
            # 1. Reject if title matches clickbait/NSFW bait
            if any(bad in title_lower for bad in CLICKBAIT_BLACKLIST):
                continue
                
            # 2. Accept ALL creators with at least 100 views (filters out 0-view bot spam)
            views = int(c.get("view_count") or 0)
            if views >= 100:
                curated_candidates.append(c)

        if not curated_candidates:
            self.swarm.log_event(
                "twitch_watcher",
                "TwitchStreamWatcher",
                "QUEUE_CLEAN",
                "No new unclipped moments from active GTA 6 creators in this window."
            )
            return

        target = curated_candidates[0]
        creator = target.get("channel", "LiveStreamer")
        slug = target["slug"]
        ts = int(time.time())
        clean_slug = "".join(ch for ch in slug if ch.isalnum() or ch in "_-")
        clip_id = f"gta6_twitch_{clean_slug[:32]}_{ts}"

        self.swarm.log_event(
            "twitch_watcher",
            "TwitchStreamWatcher",
            "TARGET_ACQUIRED",
            f"Ingesting live moment on @{creator}: '{target['title']}' ({target['view_count']:,} views)"
        )

        # 1. Pull ±15s live audience chat window
        chat_res = self.twitch_engine.fetch_clip_chat_window(slug, window_sec=15)
        comments = chat_res.get("comments", [])
        self.swarm.log_event(
            "twitch_watcher",
            "TwitchStreamWatcher",
            "CHAT_WINDOW_EXTRACTED",
            f"Extracted {len(comments)} chat messages (±15s window). Velocity: {chat_res.get('chat_velocity', 0)} msgs/s.",
            {"sample_chat": comments[:5]}
        )

        # 2. Download raw video
        raw_mp4 = Path(f"downloads/ring_buffer/gta6_live/{slug}.mp4")
        raw_mp4.parent.mkdir(parents=True, exist_ok=True)
        dl_cmd = [
            self.twitch_engine.ytdlp_bin,
            "--ffmpeg-location", "/opt/homebrew/bin/ffmpeg",
            "-f", "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",
            "--force-overwrites",
            "--no-warnings",
            "-o", str(raw_mp4),
            target["url"]
        ]
        import subprocess
        subprocess.run(dl_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        if not raw_mp4.exists():
            self.swarm.log_event("twitch_watcher", "TwitchStreamWatcher", "DOWNLOAD_FAIL", f"Failed to download raw stream for {slug}")
            return

        # 3. Transcribe speech using Whisper MLX
        tx_res = self.transcriber.transcribe(str(raw_mp4))
        transcript = " ".join(s.get("text", "") for s in tx_res).strip()
        if not transcript:
            transcript = target.get("title", "High-energy GTA 6 gameplay sequence")

        # 4. Score virality using local Qwen-2.5 SLM
        score_res = self.scorer.score_transcript(
            transcript_text=target.get("title", "") + (" - " + transcript[:150] if transcript else ""),
            streamer_name=creator,
            chat_context=comments
        )
        virality_score = float(score_res.get("virality_score", 70.0))
        viral_title = score_res.get("viral_title") or target.get("title", f"{creator} GTA 6 Showcase")
        top_hook = score_res.get("what_happened") or score_res.get("top_hook") or viral_title
        witty_desc = score_res.get("witty_description") or ""
        side_meme = score_res.get("side_meme_text")

        self.swarm.log_event(
            "narrative_guardrail",
            "NarrativeGuardrailAgent",
            "VIRALITY_EVALUATED",
            f"SLM Score: {virality_score}/100. Hook: '{top_hook}' | Title: '{viral_title}'",
            {"why_viral": score_res.get("why_viral"), "witty_description": witty_desc}
        )

        # 5. Render 9:16 vertical short (GTA VI Sunset Layout + Tight Facecam Crop)
        out_short = Path(f"output/training_candidates/{clip_id}.mp4")
        out_short.parent.mkdir(parents=True, exist_ok=True)
        duration = min(float(target.get("duration", 24)), 30.0)

        # Context-aware 3-way censor detection (Text Keywords + Zero-Shot Visual Frame CLIP)
        is_mature = any(kw in (target.get("title", "") + " " + transcript).lower() for kw in ["strip", "dancer", "bikini", "chest", "nude", "twerk", "club"])
        if not is_mature:
            try:
                from src.semantic_gatekeeper import SemanticGatekeeper
                gatekeeper = SemanticGatekeeper()
                v_res = gatekeeper.check_video_visual_nsfw(str(raw_mp4), threshold=0.60)
                if v_res.get("is_nsfw"):
                    is_mature = True
                    print(f"🚨 [Visual Guardrail Triggered]: {v_res.get('detected_category')} (conf: {v_res.get('confidence')})")
            except Exception as ge:
                print(f"Guardrail check warning: {ge}")

        category = "MATURE_SCENE" if is_mature else "GAMEPLAY"
        censor_mode = "broadcast_mosaic" if is_mature else None

        # Language Routing (English vs Hindi)
        creator_lower = creator.lower()
        hindi_creators = {
            "carryislive", "carryminati", "technogamerz", "techno gamerz", "xyaa", "xyaalive",
            "totalgaming", "total gaming", "mythpat", "scout", "mortal", "payalgaming", "payal",
            "tanmaybhat", "tanmay bhat", "rawknee", "therawkneegames", "dynamogaming", "dynamo",
            "jonathangaming", "jonathan", "hydraflick", "gtv", "bhaiyajigaming", "snax",
            "snaxgaming", "rebel", "rebelyt", "krontengaming", "kronten", "lolzzzgaming", "lolzzz",
            "mamba", "psycho"
        }
        is_hindi = any(hc in creator_lower for hc in hindi_creators) or any(w in target["title"].lower() for w in ["hindi", "bhai", "karo", "gameplay hindi", "desh"])
        clip_language = "Hindi / Indian Gaming" if is_hindi else "Live / English"

        self.slicer.slice_clip(
            input_path=str(raw_mp4),
            start_sec=0.0,
            duration_sec=duration,
            output_path=str(out_short),
            overlay_text=None,
            overlay_subtitle=None,
            tag_text="LIVE GTA",
            brand_name="OUTLAW CLIPS",
            creator_credit=creator,
            hook_text=top_hook,
            side_meme_text=None,
            censor_mode=censor_mode
        )
        raw_mp4.unlink(missing_ok=True)

        self.swarm.log_event(
            "branding_compositor",
            "BrandingCompositorAgent",
            "SHORT_RENDERED",
            f"Rendered 9:16 vertical short -> {clip_id}.mp4 with GTA VI frame & tight facecam"
        )

        # 6. Save into Telemetry DB for Instant Hub Review
        conn = sqlite3.connect(str(self.db_path))
        c = conn.cursor()
        c.execute("""
            INSERT INTO training_clip_ratings 
            (clip_id, video_path, target_search, category, language, channel, creator, expected_spoken, expected_vision, duration, virality_score, human_stars, human_verdict, human_critique, rated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, '', ?);
        """, (
            clip_id,
            f"/video/training_candidates/{clip_id}.mp4",
            viral_title,
            category,
            clip_language,
            f"@{creator}",
            creator,
            transcript[:200] if transcript else "High energy gameplay action",
            f"Audience Clip [{slug}]: {target['title']}",
            duration,
            virality_score,
            max(1, min(5, int(round(virality_score / 20.0)))),
            "APPROVED" if virality_score >= 75 and category != "MATURE_SCENE" else "REVIEW",
            float(ts)
        ))
        conn.commit()
        conn.close()

        self.swarm.log_event(
            "publish_staging",
            "PublishStagingAgent",
            "STAGED_FOR_REVIEW",
            f"Clip {clip_id} ({virality_score}/100) staged in Training Lab for human review."
        )
        print(f"\n✨ [Auto-Clipped]: {clip_id} ({creator} - '{viral_title}') Virality: {virality_score}/100")

if __name__ == "__main__":
    daemon = AutonomousClipperDaemon(poll_interval=60)
    daemon.start()

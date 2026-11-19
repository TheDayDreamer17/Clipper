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
        print("   Mission Control UI: http://localhost:8765")
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

    def _run_single_clipping_cycle(self):
        self.swarm.log_event(
            "stream_discovery",
            "StreamDiscoveryAgent",
            "STREAM_AUDIT",
            "Auditing active live Twitch GTA 6 broadcasts and audience clips..."
        )

        clips = self.twitch_engine.fetch_top_clips(game_name="Grand Theft Auto VI", limit=6)
        if not clips:
            self.swarm.log_event(
                "twitch_watcher",
                "TwitchStreamWatcher",
                "NO_CLIPS",
                "No new audience clips found this cycle. Waiting for next window."
            )
            return

        # Check existing in SQLite (Robust Title & Slug matching)
        conn = sqlite3.connect(str(self.db_path))
        c = conn.cursor()
        c.execute("SELECT clip_id, expected_vision, target_search FROM training_clip_ratings;")
        all_text = " ".join(str(val).lower() for row in c.fetchall() for val in row if val)
        conn.close()

        unprocessed = [
            c for c in clips 
            if c["title"].lower().strip() not in all_text and c["slug"].lower()[:15] not in all_text
        ]

        if not unprocessed:
            self.swarm.log_event(
                "twitch_watcher",
                "TwitchStreamWatcher",
                "QUEUE_CLEAN",
                f"All {len(clips)} active top audience clips already processed in telemetry."
            )
            return

        target = unprocessed[0]
        creator = target.get("channel", "LiveStreamer")
        slug = target["slug"]
        ts = int(time.time())
        clean_slug = "".join(ch for ch in slug if ch.isalnum())[:20]
        clip_id = f"gta6_twitch_{clean_slug}_{ts}"

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

        # 4. Score virality with Qwen-2.5 SLM + ±15s Chat Context + Sarcastic Copywriter
        score_res = self.scorer.score_transcript(transcript, streamer_name=creator, chat_context=comments)
        virality_score = score_res.get("virality_score", 70)
        viral_title = score_res.get("viral_title", target["title"])
        top_hook = score_res.get("top_hook") or "BRO REALLY THOUGHT HE WAS SLICK"
        witty_desc = score_res.get("witty_description") or ""
        side_meme = score_res.get("side_meme_text")

        self.swarm.log_event(
            "narrative_guardrail",
            "NarrativeGuardrailAgent",
            "VIRALITY_EVALUATED",
            f"SLM Score: {virality_score}/100. Hook: '{top_hook}' | Title: '{viral_title}'",
            {"why_viral": score_res.get("why_viral"), "witty_description": witty_desc}
        )

        # 5. Render 9:16 vertical short (Sleek Frosted Glass & Sarcastic Top Hook)
        out_short = Path(f"output/training_candidates/{clip_id}.mp4")
        out_short.parent.mkdir(parents=True, exist_ok=True)
        duration = min(float(target.get("duration", 24)), 30.0)

        # Context-aware 3-way censor detection (8-Bit Mosaic / Naughty Meme / Outlaw Brand Stamp)
        is_mature = any(kw in (target.get("title", "") + " " + transcript).lower() for kw in ["strip", "dancer", "bikini", "chest", "nude", "twerk", "club"])
        censor_mode = "round_robin" if is_mature else None

        self.slicer.slice_clip(
            input_path=str(raw_mp4),
            start_sec=0.0,
            duration_sec=duration,
            output_path=str(out_short),
            overlay_text=top_hook,
            overlay_subtitle=None,
            tag_text="LIVE GTA 6",
            brand_name="OUTLAW CLIPS",
            creator_credit=creator,
            hook_text=None,
            side_meme_text=side_meme,
            censor_mode=censor_mode
        )
        raw_mp4.unlink(missing_ok=True)

        self.swarm.log_event(
            "branding_compositor",
            "BrandingCompositorAgent",
            "SHORT_RENDERED",
            f"Rendered 9:16 vertical short -> {clip_id}.mp4 with dynamic subtitle sync"
        )

        # 6. Save into Telemetry DB
        conn = sqlite3.connect(str(self.db_path))
        c = conn.cursor()
        c.execute("""
            INSERT INTO training_clip_ratings 
            (clip_id, video_path, target_search, category, language, channel, creator, expected_spoken, expected_vision, duration, human_stars, human_verdict, human_critique, rated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, 'UNRATED', '', ?);
        """, (
            clip_id,
            f"/video/training_candidates/{clip_id}.mp4",
            "gta 6 live audience clip",
            "LIVE_GTA6_TWITCH",
            "Live / English",
            f"@{creator}",
            creator,
            transcript[:200],
            f"Audience Clip [{slug}]: {target['title']}",
            duration,
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

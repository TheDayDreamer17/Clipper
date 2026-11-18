import sqlite3
import time
from pathlib import Path
from typing import Dict, List, Any, Optional

class TelemetryTracker:
    """
    Real-time Telemetry, Observability & Analytics Logger.
    Uses SQLite WAL mode for safe multi-worker concurrent logging.
    Auto-compiles statistical audit dashboards for live tuning.
    """
    def __init__(self, db_path: str = "data/telemetry.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _get_conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path), timeout=10.0)
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA synchronous=NORMAL;")
        return conn

    def _init_db(self):
        with self._get_conn() as conn:
            conn.execute("""
            CREATE TABLE IF NOT EXISTS stream_sessions (
                session_id TEXT PRIMARY KEY,
                creator_name TEXT,
                platform TEXT,
                stream_url TEXT,
                language TEXT,
                started_at REAL,
                status TEXT
            );
            """)
            conn.execute("""
            CREATE TABLE IF NOT EXISTS frame_decisions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT,
                timestamp_sec REAL,
                detected_prop TEXT,
                confidence REAL,
                decision TEXT,  -- 'TRIGGER', 'INSPECT', 'REJECT'
                rejection_reason TEXT,
                logged_at REAL
            );
            """)
            conn.execute("""
            CREATE TABLE IF NOT EXISTS tournament_events (
                event_id TEXT PRIMARY KEY,
                session_id TEXT,
                creator_name TEXT,
                event_type TEXT,
                timestamp_window TEXT,
                winner_candidate TEXT,
                virality_score REAL,
                quality_tier TEXT,
                veracity_passed INTEGER,
                hook_velocity REAL,
                output_path TEXT,
                rejection_notes TEXT,
                created_at REAL
            );
            """)

    def register_stream(self, session_id: str, creator_name: str, platform: str, stream_url: str, language: str = "en"):
        with self._get_conn() as conn:
            conn.execute("""
            INSERT OR REPLACE INTO stream_sessions (session_id, creator_name, platform, stream_url, language, started_at, status)
            VALUES (?, ?, ?, ?, ?, ?, 'ACTIVE')
            """, (session_id, creator_name, platform, stream_url, language, time.time()))

    def log_frame_decision(self, session_id: str, timestamp_sec: float, detected_prop: str, confidence: float, decision: str, rejection_reason: Optional[str] = None):
        with self._get_conn() as conn:
            conn.execute("""
            INSERT INTO frame_decisions (session_id, timestamp_sec, detected_prop, confidence, decision, rejection_reason, logged_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (session_id, timestamp_sec, detected_prop, confidence, decision, rejection_reason or "", time.time()))

    def log_tournament_event(self, event_id: str, session_id: str, creator_name: str, event_type: str, timestamp_window: str, winner_candidate: str, virality_score: float, quality_tier: str, veracity_passed: bool, hook_velocity: float, output_path: str, rejection_notes: str = ""):
        with self._get_conn() as conn:
            conn.execute("""
            INSERT OR REPLACE INTO tournament_events (event_id, session_id, creator_name, event_type, timestamp_window, winner_candidate, virality_score, quality_tier, veracity_passed, hook_velocity, output_path, rejection_notes, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (event_id, session_id, creator_name, event_type, timestamp_window, winner_candidate, virality_score, quality_tier, 1 if veracity_passed else 0, hook_velocity, output_path, rejection_notes, time.time()))

    def export_dashboard_markdown(self, output_file: str = "docs/REAL_TIME_STREAM_TELEMETRY_DASHBOARD.md") -> Path:
        """
        Exports a high-visibility statistical dashboard for the user to review what was clipped,
        why candidates won or failed, and where rejections occurred.
        """
        out_p = Path(output_file)
        out_p.parent.mkdir(parents=True, exist_ok=True)

        with self._get_conn() as conn:
            cursor = conn.cursor()
            
            # 1. Total Metrics
            cursor.execute("SELECT COUNT(*) FROM stream_sessions;")
            total_streams = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM frame_decisions;")
            total_frames = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM frame_decisions WHERE decision = 'TRIGGER';")
            total_triggers = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM frame_decisions WHERE decision = 'REJECT';")
            total_rejections = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM tournament_events;")
            total_clips_crowned = cursor.fetchone()[0]

            # 2. Streams Monitored
            cursor.execute("SELECT session_id, creator_name, platform, stream_url, language, status FROM stream_sessions;")
            streams = cursor.fetchall()

            # 3. Top Rejection Reasons (Where did we go wrong?)
            cursor.execute("""
            SELECT rejection_reason, COUNT(*) as cnt 
            FROM frame_decisions 
            WHERE decision = 'REJECT' AND rejection_reason != ''
            GROUP BY rejection_reason 
            ORDER BY cnt DESC LIMIT 10;
            """)
            rejection_stats = cursor.fetchall()

            # 4. Crowned Tournament Events
            cursor.execute("""
            SELECT event_id, creator_name, event_type, timestamp_window, winner_candidate, virality_score, quality_tier, veracity_passed, hook_velocity, output_path, rejection_notes
            FROM tournament_events
            ORDER BY created_at DESC;
            """)
            events = cursor.fetchall()

        # Build Markdown Document
        lines = [
            "# 📊 Real-Time Stream Telemetry & Observability Dashboard\n",
            "> **Purpose:** Live audit trail tracking all streams, detected game moments, rejection causes, and tournament QA evaluations.  ",
            f"> **Last Generated:** {time.strftime('%Y-%m-%d %H:%M:%S')}  ",
            "> **Storage Engine:** SQLite WAL Mode (`data/telemetry.db`)\n",
            "---",
            "## 📈 High-Level Statistical Summary\n",
            "| Metric | Count / Value | Operational Meaning |",
            "| :--- | :---: | :--- |",
            f"| **Active Stream Workers** | **{total_streams} Channels** | Concurrent live monitoring agents |",
            f"| **Total Cadence Frames Checked** | **{total_frames:,} Frames** | Evaluated every 3 seconds |",
            f"| **High-Confidence Event Triggers** | **{total_triggers} Triggers** | Crossed model threshold for clipping |",
            f"| **Filtered Out (Rejections)** | **{total_rejections:,} Frames** | Dead air / false positive prevention |",
            f"| **Crowned Viral Shorts** | **{total_clips_crowned} Videos** | Passed Tournament QA Gatekeeper |\n",
            "---",
            "## 📡 Active Monitored Streams\n",
            "| Session ID | Creator Name | Platform | Language | Status | Source URL |",
            "| :--- | :--- | :---: | :---: | :---: | :--- |"
        ]

        for s in streams:
            lines.append(f"| `{s[0]}` | **{s[1]}** | `{s[2].upper()}` | `{s[3]}` | 🟢 `{s[5]}` | [Watch Stream]({s[4]}) |")

        lines.extend([
            "\n---",
            "## 🛑 Diagnostic Audit: Where Did We Go Wrong? (Top Rejection Causes)\n",
            "Understanding why potential clips are rejected allows us to fine-tune prompts and filters in real time:\n",
            "| Rejection Reason / Filter Trigger | Frames Dropped | Diagnostic Meaning & Mitigation |",
            "| :--- | :---: | :--- |"
        ] )

        for r in rejection_stats:
            lines.append(f"| `{r[0]}` | **{r[1]}** | Filtered to prevent false positive or low retention clip |")

        lines.extend([
            "\n---",
            "## 🏆 Tournament Event Provenance & Output Audit\n",
            "| Creator | Event / Scenario | Window | Winning Cut | Score | QA Status | Output Short Link | Rejection Notes / Tuning |",
            "| :--- | :--- | :---: | :--- | :---: | :---: | :--- | :--- |"
        ])

        for e in events:
            v_badge = "✅ PASS" if e[7] == 1 else "❌ VERACITY_FAIL"
            out_file = Path(e[9]).name if e[9] else "N/A"
            lines.append(
                f"| **{e[1]}** | `{e[2]}` | `{e[3]}` | `{e[4]}` | **{e[5]}/100** ({e[6]}) | "
                f"{v_badge} | [`{out_file}`]({e[9]}) | *{e[10] or 'Clean Cut'}* |"
            )

        with open(out_p, "w", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")

        return out_p

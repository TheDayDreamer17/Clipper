import sys
import re
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional, List
import json

class StreamJournal:
    """
    Maintains a live, timestamped Markdown context log for a monitored stream.
    Named after the video title, with URL on Line 1, ts-based event logs,
    and a structured compilation mapping table.
    """
    def __init__(
        self,
        stream_id: str,
        video_title: str,
        video_url: str = "https://youtube.com",
        streamer_name: str = "Creator",
        platform: str = "YouTube",
        language: str = "English",
        config_path: str = "config/game_properties.json",
        journals_dir: str = "docs/streams"
    ):
        self.stream_id = stream_id
        self.video_title = video_title
        self.video_url = video_url
        self.streamer_name = streamer_name
        self.platform = platform
        self.language = language
        self.journals_dir = Path(journals_dir)
        self.journals_dir.mkdir(parents=True, exist_ok=True)
        
        # Sanitize filename based on video title
        safe_title = re.sub(r'[^a-zA-Z0-9_\- ]', '', video_title).strip().replace(' ', '_')
        if not safe_title:
            safe_title = stream_id
        self.journal_file = self.journals_dir / f"{safe_title}.md"
        
        # Load GTA 6 property checklist
        self.config_path = Path(config_path)
        self.properties = {}
        if self.config_path.exists():
            with open(self.config_path, "r", encoding="utf-8") as f:
                self.properties = json.load(f).get("properties", {})

        # Checklist states
        self.checklist = {
            pid: {
                "name": pdata["name"],
                "category": pdata.get("category", ""),
                "extracted": False,
                "timestamp": None
            }
            for pid, pdata in self.properties.items()
        }

        # Rolling buffer for low-priority traversal segments
        self.pending_routine_segments: List[Dict[str, Any]] = []
        self.timeline_entries: List[str] = []
        self.extracted_results: List[Dict[str, Any]] = []

        self._initialize_or_load()

    def _format_time(self, seconds: float) -> str:
        mins = int(seconds // 60)
        secs = int(seconds % 60)
        return f"{mins:02d}:{secs:02d}"

    def _initialize_or_load(self):
        """Creates new Markdown document or loads existing one."""
        if not self.journal_file.exists():
            self._render_markdown()

    def _render_markdown(self):
        """Renders the entire Markdown document to disk adhering to user specification."""
        extracted_count = len(self.extracted_results)
        total_count = len(self.checklist)

        lines = [
            f"URL: {self.video_url}\n",
            f"# {self.video_title}\n",
            f"- **Streamer / Channel:** {self.streamer_name}",
            f"- **Platform:** {self.platform}",
            f"- **Language:** {self.language}",
            f"- **Stream ID:** `{self.stream_id}`",
            f"- **Target Moments Captured:** `{extracted_count}`\n",
            "---",
            "## ⏱️ Real-Time Stream Context Timeline\n",
        ]

        if not self.timeline_entries:
            lines.append("*(Stream monitoring initiated — waiting for first gameplay events...)*\n")
        else:
            for entry in self.timeline_entries:
                lines.append(entry)

        lines.extend([
            "\n---",
            "## 🎯 Results & Relevant Compilation Mapping\n",
            "| In-Game Event Category | Timestamp Window | Dynamic Duration | Output Clip Path | Channel Destination |",
            "| :--- | :--- | :--- | :--- | :--- |"
        ])

        if not self.extracted_results:
            lines.append("| *(No clips extracted yet)* | - | - | - | - |")
        else:
            for res in self.extracted_results:
                lines.append(
                    f"| **{res['category']}** | `{res['timestamp']}` | {res['duration']}s | "
                    f"`{res['clip_path']}` | {res['channel']} |"
                )

        with open(self.journal_file, "w", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")

    def _flush_pending_routine(self):
        """Collapses consecutive low-priority segments into a single concise summary."""
        if not self.pending_routine_segments:
            return

        start_time = self._format_time(self.pending_routine_segments[0]["start_sec"])
        end_time = self._format_time(self.pending_routine_segments[-1]["end_sec"])
        count = len(self.pending_routine_segments)

        activities = [s["action_summary"] for s in self.pending_routine_segments if s.get("action_summary")]
        sample_activity = activities[0] if activities else "General open-world traversal"
        
        entry = f"- **ts {start_time} - {end_time}**: (Collapsed {count} segments): {sample_activity} without major trigger events."
        self.timeline_entries.append(entry)
        self.pending_routine_segments.clear()

    def record_window(
        self,
        start_sec: float,
        end_sec: float,
        visual_state: str,
        action_summary: str,
        matched_property: Optional[str] = None,
        clip_path: Optional[str] = None,
        channel_dest: str = "English Channel"
    ):
        """
        Records an evaluated chunk with dynamic duration.
        """
        start_str = self._format_time(start_sec)
        end_str = self._format_time(end_sec)
        dur = int(round(end_sec - start_sec))

        if matched_property:
            self._flush_pending_routine()

            prop_name = matched_property
            if matched_property in self.checklist:
                prop_name = self.checklist[matched_property]["name"]
                self.checklist[matched_property]["extracted"] = True
                self.checklist[matched_property]["timestamp"] = f"{start_str} - {end_str}"

            timeline_line = f"- **ts {start_str} - {end_str}**: **[{prop_name}]** {action_summary} ({visual_state})."
            self.timeline_entries.append(timeline_line)

            if clip_path:
                self.extracted_results.append({
                    "category": prop_name,
                    "timestamp": f"ts {start_str} - {end_str}",
                    "duration": dur,
                    "clip_path": clip_path,
                    "channel": channel_dest
                })
        else:
            self.pending_routine_segments.append({
                "start_sec": start_sec,
                "end_sec": end_sec,
                "visual_state": visual_state,
                "action_summary": action_summary
            })
            if len(self.pending_routine_segments) >= 3:
                self._flush_pending_routine()

        self._render_markdown()

    def finalize(self):
        """Flushes any remaining routine segments at stream end."""
        self._flush_pending_routine()
        self._render_markdown()

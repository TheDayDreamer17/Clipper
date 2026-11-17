import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional, List
import json

class StreamJournal:
    """
    Maintains a live, timestamped Markdown context log for a monitored stream.
    Tracks in-game events, matched GTA 6 target properties, and performs
    rolling summarization of low-priority traversal segments so the user
    has a complete semantic index of the entire stream without watching it.
    """
    def __init__(
        self,
        stream_id: str,
        streamer_name: str,
        platform: str = "Twitch",
        config_path: str = "config/game_properties.json",
        journals_dir: str = "docs/streams"
    ):
        self.stream_id = stream_id
        self.streamer_name = streamer_name
        self.platform = platform
        self.journals_dir = Path(journals_dir)
        self.journals_dir.mkdir(parents=True, exist_ok=True)
        self.journal_file = self.journals_dir / f"{stream_id}_journal.md"
        
        # Load GTA 6 property checklist
        self.config_path = Path(config_path)
        self.properties = {}
        if self.config_path.exists():
            with open(self.config_path, "r", encoding="utf-8") as f:
                self.properties = json.load(f).get("properties", {})

        # Checklist states: property_id -> {"name": str, "extracted": bool, "timestamp": str}
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
        """Renders the entire Markdown document to disk."""
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        extracted_count = sum(1 for item in self.checklist.values() if item["extracted"])
        total_count = len(self.checklist)

        lines = [
            f"# 🎮 Live Stream Context Journal: {self.streamer_name}",
            f"> **Stream ID:** `{self.stream_id}`  ",
            f"> **Platform:** {self.platform}  ",
            f"> **Created:** {now_str}  ",
            f"> **Target Properties Captured:** `{extracted_count} / {total_count}`\n",
            "---",
            "## 🎯 GTA 6 In-Game Target Checklist\n",
        ]

        for pid, data in sorted(self.checklist.items()):
            if data["extracted"]:
                lines.append(f"- [x] **{pid} ({data['name']})** — Captured @ `{data['timestamp']}`")
            else:
                lines.append(f"- [ ] **{pid} ({data['name']})** — *{data['category']}*")

        lines.extend([
            "\n---",
            "## ⏱️ Real-Time Stream Context Timeline\n",
            "| Time Window | In-Game Activity & Visual State | Classification | Action Taken |",
            "| :--- | :--- | :--- | :--- |",
        ])

        for entry in self.timeline_entries:
            lines.append(entry)

        with open(self.journal_file, "w", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")

    def _flush_pending_routine(self):
        """Collapses consecutive low-priority segments into a single concise summary."""
        if not self.pending_routine_segments:
            return

        start_time = self._format_time(self.pending_routine_segments[0]["start_sec"])
        end_time = self._format_time(self.pending_routine_segments[-1]["end_sec"])
        count = len(self.pending_routine_segments)

        # Synthesize summary
        activities = [s["action_summary"] for s in self.pending_routine_segments if s.get("action_summary")]
        sample_activity = activities[0] if activities else "General traversal & camera motion"
        
        entry = (
            f"| `{start_time} - {end_time}` | "
            f"*{sample_activity}* (Collapsed {count} routine segments) | "
            f"`ROUTINE_TRAVERSAL` | 📝 Logged (Skipped Clip) |"
        )
        self.timeline_entries.append(entry)
        self.pending_routine_segments.clear()

    def record_window(
        self,
        start_sec: float,
        end_sec: float,
        visual_state: str,
        action_summary: str,
        matched_property: Optional[str] = None,
        clip_path: Optional[str] = None
    ):
        """
        Records an evaluated 30s chunk.
        If it matches a target property, flushes routine queue and marks extracted.
        If it's low priority, queues it for rolling summarization.
        """
        start_str = self._format_time(start_sec)
        end_str = self._format_time(end_sec)

        if matched_property and matched_property in self.checklist:
            # High priority match!
            self._flush_pending_routine()

            prop_data = self.checklist[matched_property]
            prop_data["extracted"] = True
            prop_data["timestamp"] = f"{start_str} - {end_str}"

            clip_name = Path(clip_path).name if clip_path else "Extracted"
            entry = (
                f"| `{start_str} - {end_str}` | "
                f"**{visual_state}** — {action_summary} | "
                f"🔥 **{matched_property}: {prop_data['name']}** | "
                f"✂️ Extracted (`{clip_name}`) |"
            )
            self.timeline_entries.append(entry)
        else:
            # Low priority / routine activity
            self.pending_routine_segments.append({
                "start_sec": start_sec,
                "end_sec": end_sec,
                "visual_state": visual_state,
                "action_summary": action_summary
            })
            # Collapse every 3 routine segments (~90 seconds)
            if len(self.pending_routine_segments) >= 3:
                self._flush_pending_routine()

        self._render_markdown()

    def finalize(self):
        """Flushes any remaining routine segments at stream end."""
        self._flush_pending_routine()
        self._render_markdown()

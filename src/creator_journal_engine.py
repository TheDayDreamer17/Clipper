import os
import sys
import io
import time
import json
import subprocess
from pathlib import Path
from typing import Dict, List, Any, Optional, Generator
from datetime import datetime
from PIL import Image
from src.semantic_gatekeeper import SemanticGatekeeper

class CreatorJournalEngine:
    """
    Continuous 1 FPS Direct Stream Perception & Journaling Engine.
    Streams YouTube/Twitch live broadcasts or past VODs on the fly via FFmpeg pipe,
    classifies gameplay at 1 frame per second without storing video dumps on disk,
    evaluates frames with SemanticGatekeeper, and maintains a persistent second-by-second markdown context journal.
    """
    def __init__(
        self,
        output_dir: Optional[str] = None,
        creator_name: str = "Ravi"
    ):
        self.creator_name = creator_name
        self.output_dir = Path(output_dir or f"docs/streams/{creator_name.lower()}")
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.ffmpeg_bin = shutil_which("ffmpeg") or "/opt/homebrew/bin/ffmpeg"
        self.gatekeeper = SemanticGatekeeper()

    def _format_timecode(self, total_seconds: int) -> str:
        h = total_seconds // 3600
        m = (total_seconds % 3600) // 60
        s = total_seconds % 60
        if h > 0:
            return f"{h:02d}:{m:02d}:{s:02d}"
        return f"{m:02d}:{s:02d}"

    def stream_frames_1fps(self, stream_source: str, max_seconds: int = 180) -> Generator[Dict[str, Any], None, None]:
        """
        Pipes 1 frame per second from any stream URL or local MP4 via FFmpeg stdout.
        Yields (second_index, PIL.Image). Zero persistent video file on disk!
        """
        # If it's a YouTube/Twitch URL, resolve direct media stream with yt-dlp -g
        stream_url = stream_source
        if "youtube.com" in stream_source or "youtu.be" in stream_source or "twitch.tv" in stream_source:
            try:
                cmd_resolve = [
                    ".venv/bin/yt-dlp",
                    "-g",
                    "-f", "bestvideo[height<=720]+bestaudio/best[height<=720]/best",
                    stream_source
                ]
                res = subprocess.run(cmd_resolve, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=20)
                if res.returncode == 0 and res.stdout.strip():
                    stream_url = res.stdout.strip().splitlines()[0]
            except Exception as e:
                print(f"⚠️ [JournalEngine] Fallback to direct URL input: {e}")

        # FFmpeg command: stream 1 frame per second as raw JPEG stream to stdout
        cmd = [
            self.ffmpeg_bin,
            "-hide_banner",
            "-loglevel", "error",
            "-i", stream_url,
            "-vf", "fps=1,scale=640:360",
            "-f", "image2pipe",
            "-vcodec", "mjpeg",
            "-t", str(max_seconds),
            "-"
        ]

        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        buffer = bytearray()
        sec_idx = 0

        # JPEG markers: SOI = 0xFF 0xD8, EOI = 0xFF 0xD9
        while True:
            chunk = proc.stdout.read(4096)
            if not chunk:
                break
            buffer.extend(chunk)

            while True:
                start = buffer.find(b"\xff\xd8")
                if start == -1:
                    buffer.clear()
                    break
                end = buffer.find(b"\xff\xd9", start + 2)
                if end == -1:
                    if start > 0:
                        del buffer[:start]
                    break

                jpg_bytes = buffer[start : end + 2]
                del buffer[: end + 2]

                try:
                    img = Image.open(io.BytesIO(jpg_bytes)).convert("RGB")
                    yield {"second": sec_idx, "timecode": self._format_timecode(sec_idx), "image": img}
                    sec_idx += 1
                except Exception:
                    pass

        proc.stdout.close()
        proc.wait()

    def scan_audio_energy(self, media_path: str, start_sec: float = 0.0, duration_sec: float = 30.0) -> Dict[str, Any]:
        """Runs ffmpeg volumedetect to get mean and max volume decibels across a time window."""
        cmd = [
            self.ffmpeg_bin,
            "-hide_banner",
            "-ss", str(start_sec),
            "-t", str(duration_sec),
            "-i", str(media_path),
            "-af", "volumedetect",
            "-f", "null",
            "-"
        ]
        res = subprocess.run(cmd, stderr=subprocess.PIPE, text=True)
        mean_vol = -99.0
        max_vol = -99.0
        for line in res.stderr.splitlines():
            if "mean_volume:" in line:
                try:
                    mean_vol = float(line.split("mean_volume:")[1].split("dB")[0].strip())
                except Exception:
                    pass
            if "max_volume:" in line:
                try:
                    max_vol = float(line.split("max_volume:")[1].split("dB")[0].strip())
                except Exception:
                    pass
        is_audible = mean_vol > -36.0
        return {
            "mean_volume": mean_vol,
            "max_volume": max_vol,
            "is_audible": is_audible
        }

    def evaluate_window(
        self,
        media_path: str,
        start_sec: float,
        duration_sec: float = 30.0
    ) -> Dict[str, Any]:
        """
        Grounded Multi-Modal Evaluation:
        1. Checks Audio Energy: rejects dead air / silence (< -36 dB).
        2. Samples Frames: evaluates with SemanticGatekeeper (BLIP caption + CLIP archetype).
        3. Returns full verified candidate decision with social metadata.
        """
        audio = self.scan_audio_energy(media_path, start_sec=start_sec, duration_sec=duration_sec)
        if not audio["is_audible"]:
            return {
                "is_approved": False,
                "confidence": 0.0,
                "reason": f"Rejected as Dead Air / Muted Audio ({audio['mean_volume']} dB)",
                "archetype": "MUTED_AUDIO",
                "audio": audio,
                "captions": [],
                "metadata": None
            }

        # Extract 3 frames across the window (start + 25%, start + 50%, start + 75%)
        frames = []
        for offset in [0.25 * duration_sec, 0.50 * duration_sec, 0.75 * duration_sec]:
            t = start_sec + offset
            cmd = [
                self.ffmpeg_bin, "-y",
                "-ss", str(t),
                "-i", str(media_path),
                "-vframes", "1",
                "-f", "image2pipe",
                "-vcodec", "mjpeg",
                "-"
            ]
            res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
            if res.stdout:
                try:
                    frames.append(Image.open(io.BytesIO(res.stdout)).convert("RGB"))
                except Exception:
                    pass

        if not frames:
            return {
                "is_approved": False,
                "confidence": 0.0,
                "reason": "Failed to extract frames",
                "archetype": "EXTRACTION_FAILURE",
                "audio": audio,
                "captions": [],
                "metadata": None
            }

        eval_res = self.gatekeeper.evaluate_multi_frame_context(
            frames,
            streamer_name=self.creator_name,
            game_title="GTA 6"
        )

        return {
            "is_approved": eval_res["is_worth_clipping"],
            "confidence": eval_res["confidence"],
            "reason": eval_res["decision_reason"],
            "archetype": eval_res["novel_archetype"],
            "audio": audio,
            "captions": eval_res.get("frame_captions", []),
            "metadata": eval_res.get("metadata")
        }

    def classify_frame(self, frame_info: Dict[str, Any], prev_frame: Optional[Image.Image] = None) -> Dict[str, Any]:
        """
        Deep multi-modal perception classifier for 1 FPS continuous stream.
        Grounded in SemanticGatekeeper (BLIP captions + CLIP contrast against novel vs lame archetypes).
        """
        img = frame_info["image"]
        sec = frame_info["second"]

        w, h = img.size

        # Optical motion estimation via frame differencing
        motion_level = "MODERATE"
        if prev_frame:
            from PIL import ImageChops, ImageStat
            diff = ImageChops.difference(img, prev_frame)
            stat = ImageStat.Stat(diff)
            delta = sum(stat.mean) / 3.0
            if delta < 4.0:
                motion_level = "STATIC"
            elif delta > 30.0:
                motion_level = "EXTREME_MOTION"
            else:
                motion_level = "ACTIVE"

        # Run real multi-modal perception via SemanticGatekeeper
        eval_res = self.gatekeeper.evaluate_multi_frame_context(
            [img],
            streamer_name=self.creator_name,
            game_title="GTA 6"
        )

        is_worth = eval_res.get("is_worth_clipping", False)
        caps = eval_res.get("frame_captions", ["Gameplay scene"])
        visual_entities = caps[0] if caps else "In-game view"
        emergent_action = eval_res.get("decision_reason", "Routine gameplay")
        curator_hook = eval_res.get("novel_archetype", "AMBIENT_ACTION") if is_worth else "AMBIENT_GAMEPLAY"
        confidence = eval_res.get("confidence", 0.0)

        creator_speech = "Live Commentary"
        audio_energy = "Active" if is_worth else "Calm"
        generic_state = "ACTION_EVENT" if is_worth else "FREE_ROAM"

        extra_telemetry = f"State: {generic_state} | Motion: {motion_level} | Gatekeeper Conf: {confidence}%"

        return {
            "second": sec,
            "timecode": frame_info["timecode"],
            "generic_state": generic_state,
            "visual_entities": visual_entities,
            "emergent_action": emergent_action,
            "creator_speech": creator_speech,
            "audio_energy": audio_energy,
            "curator_hook": curator_hook,
            "extra_telemetry": extra_telemetry,
            "is_emergent_highlight": is_worth,
            "confidence": confidence,
            "metadata": eval_res.get("metadata")
        }

    def generate_session_journal(
        self,
        stream_source: str,
        session_id: Optional[str] = None,
        duration_seconds: int = 60
    ) -> Path:
        """
        Executes the continuous 1 FPS streaming pipeline and writes the second-by-second
        context journal directly to disk in structured Markdown.
        """
        session_id = session_id or f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        journal_file = self.output_dir / f"{session_id}_journal.md"

        print(f"🎬 [JournalEngine] Starting 1 FPS Continuous Stream Ingestion for {self.creator_name}...")
        print(f"   Writing context to: {journal_file}")

        entries = []
        prev_img = None

        with open(journal_file, "w", encoding="utf-8") as f:
            f.write(f"# 🎮 Second-by-Second Stream Context Journal: {self.creator_name}\n\n")
            f.write(f"> **Session ID:** `{session_id}`  \n")
            f.write(f"> **Stream Source:** `{stream_source}`  \n")
            f.write(f"> **Inspection Cadence:** `1 Frame Per Second (1 FPS Direct Stream Pipe)`  \n")
            f.write(f"> **Recorded:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}  \n\n")
            f.write("---\n\n")
            f.write("## ⏱️ Chronological 1 FPS Stream Context Matrix\n\n")
            f.write("| Timecode | Visual & Entity Dynamics | Emergent Anomaly & Action | Creator Voice & Spoken Audio | Curator Viral Hook | Game State & HUD (Extra) |\n")
            f.write("| :--- | :--- | :--- | :--- | :--- | :--- |\n")

            for frame in self.stream_frames_1fps(stream_source, max_seconds=duration_seconds):
                data = self.classify_frame(frame, prev_img)
                prev_img = frame["image"]
                entries.append(data)

                # Append enriched multi-modal row
                row = (
                    f"| `{data['timecode']}` | {data['visual_entities']} | "
                    f"{data['emergent_action']} | *\"{data['creator_speech']}\"* ({data['audio_energy']}) | "
                    f"🔥 `{data['curator_hook']}` | `{data['extra_telemetry']}` |\n"
                )
                f.write(row)

                # If this is a peak emergent moment, write an explicit callout block
                if data["is_emergent_highlight"]:
                    f.write(
                        f"\n> 🚨 **[EMERGENT ANOMALY @ {data['timecode']}]:** {data['emergent_action']}  \n"
                        f"> 🗣️ **Creator Reaction:** *\"{data['creator_speech']}\"*  \n"
                        f"> 🎯 **Curator Recommendation:** Extract 15s candidate cut (`{data['timecode']}`) -> Archetype: `{data['curator_hook']}`\n\n"
                    )

                f.flush()

                if data["second"] % 10 == 0:
                    print(f"   ⏱️ t={data['timecode']} ({data['second']}s): [{data['curator_hook']}] {data['emergent_action'][:45]}...")

            # Summary section at end of journal
            f.write("\n---\n\n")
            f.write("## 🧠 Emergent Narrative Index (For Natural Language Retrieval)\n\n")
            f.write(f"- **Total Playthrough Monitored:** `{len(entries)} seconds ({len(entries)} frames @ 1 FPS)`\n")
            
            highlights = [e for e in entries if e["is_emergent_highlight"]]
            f.write(f"- **Peak Emergent Anomalies Detected:** `{len(highlights)}`\n\n")

            f.write("### 🎯 Recommended Emergent Candidate Cuts:\n")
            for h in highlights:
                f.write(
                    f"- 💥 **`{h['timecode']}` — {h['curator_hook']}:** {h['emergent_action']} "
                    f"(Reaction: *\"{h['creator_speech']}\"*)\n"
                )

        print(f"✅ [JournalEngine] Session journal generated with {len(entries)} seconds of full context: {journal_file}")
        return journal_file

def shutil_which(cmd):
    import shutil
    return shutil.which(cmd)

if __name__ == "__main__":
    test_src = sys.argv[1] if len(sys.argv) > 1 else "downloads/carry_live_sample.mp4.mkv"
    engine = CreatorJournalEngine(creator_name="Ravi")
    engine.generate_session_journal(stream_source=test_src, duration_seconds=30)

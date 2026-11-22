import os
import sys
import time
import json
import sqlite3
import subprocess
from pathlib import Path
from typing import List, Dict, Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.creator_journal_engine import CreatorJournalEngine
from src.slicer import VideoSlicer

DB_PATH = Path("data/ravi_vault.db")
REGISTRY_PATH = Path("data/ravoop_stream_registry.json")
OUT_DIR = Path("output/training_candidates")
JOURNAL_DIR = Path("docs/streams/ravi")

class RavoopAutoPipeline:
    """
    Autonomous Stream Monitor & Ingestion Engine for Ravi (@ravoop).
    Continuously monitors Ravi's YouTube live channel, discovers new streams,
    evaluates audio loudness and visual interactions via SemanticGatekeeper,
    generates grounded context journals, extracts top dual-format clips (16:9 Wide + 9:16 Short),
    and inserts them directly into the dedicated Ravi Vault database.
    """
    def __init__(self):
        self.channel_url = "https://www.youtube.com/@ravoop"
        self.state_file = Path("data/ravoop_processed_streams.json")
        self.processed_ids = self._load_processed()
        OUT_DIR.mkdir(parents=True, exist_ok=True)
        JOURNAL_DIR.mkdir(parents=True, exist_ok=True)
        self.journal_engine = CreatorJournalEngine(creator_name="Ravi")
        self.slicer = VideoSlicer()
        self._init_db()

    def _init_db(self):
        if DB_PATH.exists():
            try:
                conn = sqlite3.connect(str(DB_PATH))
                c = conn.cursor()
                c.execute("""
                    CREATE TABLE IF NOT EXISTS ravi_clips (
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
                        human_stars INTEGER,
                        human_verdict TEXT,
                        human_critique TEXT,
                        rated_at REAL,
                        virality_score REAL DEFAULT 0.0
                    );
                """)
                conn.commit()
                conn.close()
            except Exception as e:
                print(f"DB Init Error: {e}")

    def _load_processed(self) -> set:
        if self.state_file.exists():
            try:
                with open(self.state_file, "r") as f:
                    return set(json.load(f))
            except Exception:
                pass
        return set()

    def _save_processed(self):
        try:
            self.state_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.state_file, "w") as f:
                json.dump(list(self.processed_ids), f, indent=2)
        except Exception as e:
            print(f"Error saving processed streams: {e}")

    def fetch_recent_streams(self) -> List[Dict[str, Any]]:
        """Scrapes the streams tab of @ravoop via yt-dlp."""
        cmd = [
            "./.venv/bin/yt-dlp",
            "--flat-playlist",
            "--print", "%(id)s\t%(duration)s\t%(title)s",
            f"{self.channel_url}/streams"
        ]
        try:
            res = subprocess.run(cmd, capture_output=True, text=True, check=True)
            streams = []
            for line in res.stdout.strip().splitlines():
                if "\t" in line:
                    parts = line.split("\t", 2)
                    if len(parts) >= 3:
                        sid, dur_str, title = parts[0].strip(), parts[1].strip(), parts[2].strip()
                        dur = float(dur_str) if dur_str != "NA" and dur_str.replace(".", "", 1).isdigit() else 1800.0
                        streams.append({"id": sid, "title": title, "duration": dur})
            return streams
        except Exception as e:
            print(f"Error fetching live streams: {e}. Falling back to registered streams cache.")
            try:
                if REGISTRY_PATH.exists():
                    with open(REGISTRY_PATH, "r", encoding="utf-8") as f:
                        reg = json.load(f)
                    return [
                        {"id": s["stream_id"], "title": s["title"], "duration": float(s.get("duration_sec", 1800.0))}
                        for s in reg.get("streams", [])
                    ]
            except Exception:
                pass
            return []

    def find_audio_energy_peaks(self, stream_url: str, dur: float, top_k: int = 5) -> List[int]:
        """Downloads lightweight audio track and finds loudest action timestamps across stream."""
        audio_tmp = Path(f"/tmp/stream_{int(time.time())}_audio.webm")
        try:
            dl_cmd = ["./.venv/bin/yt-dlp", "-f", "251/ba/b", "-o", str(audio_tmp), stream_url]
            subprocess.run(dl_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=120, check=True)
            if not audio_tmp.exists():
                return [int(dur * f) for f in [0.25, 0.45, 0.65]]

            # Sweep in 90-second increments
            step = 90
            candidates = []
            for sec in range(120, int(dur) - 60, step):
                cmd = ["ffmpeg", "-ss", str(sec), "-t", "10", "-i", str(audio_tmp), "-af", "volumedetect", "-f", "null", "-"]
                res = subprocess.run(cmd, capture_output=True, text=True)
                mean_vol = -99.0
                for line in res.stderr.splitlines():
                    if "mean_volume:" in line:
                        try:
                            mean_vol = float(line.split("mean_volume:")[1].replace("dB", "").strip())
                        except Exception:
                            pass
                candidates.append((sec, mean_vol))

            candidates.sort(key=lambda x: x[1], reverse=True)
            peaks = [c[0] for c in candidates[:top_k]]
            audio_tmp.unlink(missing_ok=True)
            return sorted(peaks) if peaks else [int(dur * f) for f in [0.25, 0.45, 0.65]]
        except Exception as e:
            print(f"Error finding audio energy peaks: {e}")
            audio_tmp.unlink(missing_ok=True)
            return [int(dur * f) for f in [0.25, 0.45, 0.65]]

    def process_and_dispatch_cycle(self):
        """Runs one grounded check and harvest cycle using SemanticGatekeeper & Audio Volumedetect."""
        streams = self.fetch_recent_streams()
        print(f"📡 Found {len(streams)} live streams on {self.channel_url}")

        for s in streams:
            sid = s["id"]
            if sid in self.processed_ids:
                continue

            print(f"🎬 New stream detected: {s['title']} ({sid})! Processing autonomous grounded evaluation...")
            stream_url = f"https://www.youtube.com/watch?v={sid}"
            dur = max(60.0, float(s.get("duration", 1800.0)))

            # Discover real action peaks across the stream via full-stream audio volume energy sweep
            print(f"   🎧 Running full-stream audio energy sweep to pinpoint loudest action peaks...")
            test_offsets = self.find_audio_energy_peaks(stream_url, dur, top_k=6)
            print(f"   🎯 Identified {len(test_offsets)} action peak offsets: {test_offsets}")

            approved_moments = []

            for offset in test_offsets:
                m_str = f"{offset // 3600:02d}:{(offset % 3600) // 60:02d}:{offset % 60:02d}"
                m_end = f"{(offset + 35) // 3600:02d}:{((offset + 35) % 3600) // 60:02d}:{(offset + 35) % 60:02d}"
                sec_range = f"*{m_str}-{m_end}"
                cid = f"ravo_auto_{sid}_{offset}"
                wide_path = OUT_DIR / f"{cid}_wide.mp4"
                short_path = OUT_DIR / f"{cid}_short.mp4"

                try:
                    # 1. Download candidate 35s chunk for multi-modal evaluation
                    dl_cmd = [
                        "./.venv/bin/yt-dlp",
                        "--download-sections", sec_range,
                        "-f", "bv*[height<=1440]+ba/bv*+ba/best",
                        "--merge-output-format", "mp4",
                        "-o", str(wide_path),
                        stream_url
                    ]
                    subprocess.run(dl_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
                    if not wide_path.exists():
                        continue

                    # 2. Grounded Multi-Modal Gatekeeper Evaluation
                    eval_res = self.journal_engine.evaluate_window(str(wide_path), start_sec=0.0, duration_sec=30.0)
                    print(f"   🔍 t={m_str}: Approved={eval_res['is_approved']} | Archetype={eval_res['archetype']} | Vol={eval_res['audio']['mean_volume']}dB")

                    if not eval_res["is_approved"]:
                        print(f"   ❌ Rejected candidate at {m_str}: {eval_res['reason']}")
                        wide_path.unlink(missing_ok=True)
                        continue

                    # 3. Format Headless High-Craft 9:16 Short (Vice City Container + Audio Normalization)
                    meta = eval_res.get("metadata") or {}
                    title = meta.get("youtube_title") or f"Ravo OP {eval_res['archetype'].title()} #Shorts"
                    tag_line = f"🔥 {eval_res['archetype'].upper()[:25]}"

                    self.slicer.slice_clip(
                        input_path=str(wide_path),
                        start_sec=0.0,
                        duration_sec=30.0,
                        output_path=str(short_path),
                        style="vice_city_container",
                        facecam_corner=None,  # Headless stream (no webcam)
                        creator_credit="ravoop",
                        hook_text=f"👀 WAIT FOR THE ACTION...",
                        overlay_text=title[:32].upper(),
                        overlay_subtitle=eval_res['reason'][:36],
                        tag_text=tag_line,
                        brand_name="RAVO OP CLIPS",
                        watermark=False
                    )

                    # 4. Save into Ravi Vault DB
                    conn = sqlite3.connect(str(DB_PATH))
                    c = conn.cursor()
                    vpath = f"/video/training_candidates/{cid}_wide.mp4"
                    c.execute("""
                        INSERT OR REPLACE INTO ravi_clips 
                        (clip_id, video_path, target_search, category, language, channel, creator, expected_spoken, expected_vision, duration, human_stars, human_verdict, human_critique, rated_at, virality_score)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (cid, vpath, title, eval_res["archetype"], "hi", "@ravoop", "Ravi", "Live Voice Commentary", eval_res["reason"], 30.0, 5, "APPROVED", "", time.time(), eval_res["confidence"]))
                    conn.commit()
                    conn.close()

                    approved_moments.append({
                        "cid": cid,
                        "timecode": m_str,
                        "title": title,
                        "archetype": eval_res["archetype"],
                        "confidence": eval_res["confidence"]
                    })
                    print(f"   ✅ [Grounded Approval]: Saved verified clip {cid} to Ravi Studio!")

                    # Stop after harvesting 3 high-quality moments from this stream
                    if len(approved_moments) >= 3:
                        break

                except Exception as e:
                    print(f"Error evaluating moment {cid}: {e}")

            # Update Stream Registry
            self._update_registry(sid, s["title"], s["duration"], len(approved_moments))
            self.processed_ids.add(sid)
            self._save_processed()

    def _update_registry(self, sid: str, title: str, duration: float, clip_count: int):
        try:
            reg = {}
            if REGISTRY_PATH.exists():
                with open(REGISTRY_PATH, "r", encoding="utf-8") as f:
                    reg = json.load(f)
            streams = reg.get("streams", [])
            existing = next((s for s in streams if s.get("stream_id") == sid), None)
            if existing:
                existing["indexed_clips_count"] = existing.get("indexed_clips_count", 0) + clip_count
                existing["last_scanned"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
            else:
                streams.insert(0, {
                    "stream_id": sid,
                    "title": title,
                    "url": f"https://www.youtube.com/watch?v={sid}",
                    "duration_sec": int(duration),
                    "duration_string": f"{int(duration)//3600:02d}:{(int(duration)%3600)//60:02d}:{int(duration)%60:02d}",
                    "status": "INDEXED",
                    "journal_file": f"session_{sid}_journal.md",
                    "indexed_clips_count": clip_count,
                    "last_scanned": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
                })
            reg["streams"] = streams
            with open(REGISTRY_PATH, "w", encoding="utf-8") as f:
                json.dump(reg, f, indent=2)
        except Exception as e:
            print(f"Error updating registry: {e}")

    def run_forever(self, interval_sec: int = 600):
        print(f"🚀 Ravo OP Autonomous Ingestion Daemon Active. Polling {self.channel_url} every {interval_sec}s...")
        while True:
            try:
                self.process_and_dispatch_cycle()
            except Exception as e:
                print(f"Cycle Exception: {e}")
            time.sleep(interval_sec)

if __name__ == "__main__":
    pipeline = RavoopAutoPipeline()
    pipeline.run_forever()

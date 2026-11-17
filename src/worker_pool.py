import time
from pathlib import Path
from typing import List, Dict, Any, Optional
from concurrent.futures import ThreadPoolExecutor
import subprocess

from src.matcher import TopicMatcher
from src.slicer import VideoSlicer
from src.transcribe import Transcriber

class AudioStreamListener:
    """
    Audio-first stream inspector.
    Downloads ONLY audio chunks (~1 MB per minute) to preserve bandwidth and RAM.
    Video is only retrieved when a high-confidence topic match is triggered.
    """
    def __init__(
        self,
        stream_url: str,
        stream_name: str,
        transcriber: Transcriber,
        matcher: TopicMatcher,
        slicer: VideoSlicer,
        output_dir: str = "output",
        temp_dir: str = "downloads"
    ):
        self.stream_url = stream_url
        self.stream_name = stream_name
        self.transcriber = transcriber
        self.matcher = matcher
        self.slicer = slicer
        self.output_dir = Path(output_dir)
        self.temp_dir = Path(temp_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.temp_dir.mkdir(parents=True, exist_ok=True)
        self.ytdlp_bin = "/Users/vismaythaker/workspace/projects/Clipper/.venv/bin/yt-dlp"

    def inspect_window(self, start_sec: int, window_sec: int = 60) -> Optional[Dict[str, Any]]:
        """
        Pulls a lightweight audio-only chunk (~1 MB), transcribes it,
        and triggers video rendering ONLY if a hot topic is matched.
        """
        end_sec = start_sec + window_sec
        audio_chunk = self.temp_dir / f"{self.stream_name}_audio_{start_sec}_{end_sec}.m4a"

        # 1. Download audio-only slice (~1 MB)
        cmd = [
            self.ytdlp_bin,
            "--ffmpeg-location", "/opt/homebrew/bin/ffmpeg",
            "--download-sections", f"*{start_sec}-{end_sec}",
            "-f", "bestaudio[ext=m4a]/bestaudio/ba",
            "--force-overwrites",
            "--no-warnings",
            "-o", str(audio_chunk),
            self.stream_url
        ]

        res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if not audio_chunk.exists() or audio_chunk.stat().st_size == 0:
            return None

        # 2. Fast transcription on Metal GPU
        segments = self.transcriber.transcribe(str(audio_chunk))
        
        # Clean up temporary audio chunk immediately to keep RAM/SSD clean
        audio_chunk.unlink(missing_ok=True)

        # 3. Match against 20 Content Buckets
        for seg in segments:
            matches = self.matcher.scan_segment(seg["text"])
            if matches:
                top_match = matches[0]
                print(f"\n🚨 [MATCH FOUND in {self.stream_name}] @ {start_sec + seg['start']:.1f}s")
                print(f"   Category: {top_match['category']} | Triggers: {top_match['matched_keywords']}")
                print(f"   Speech: \"{seg['text']}\"")
                
                # 4. Trigger video download & render ONLY for this specific moment
                self._render_matched_clip(
                    exact_start=max(0, start_sec + seg["start"] - 5.0),
                    duration=min(45.0, (seg["end"] - seg["start"]) + 20.0),
                    topic_id=top_match["topic_id"]
                )
                return top_match

        return None

    def _render_matched_clip(self, exact_start: float, duration: float, topic_id: str):
        """
        Downloads ONLY the high-res video slice for the matched moment and formats to 9:16.
        """
        end_time = exact_start + duration
        video_temp = self.temp_dir / f"matched_{self.stream_name}_{int(exact_start)}.mp4"
        output_short = self.output_dir / f"{self.stream_name}_{topic_id}_{int(exact_start)}_9x16.mp4"

        print(f"📥 Pulling video slice [{exact_start:.1f}s to {end_time:.1f}s] for render...")
        cmd = [
            self.ytdlp_bin,
            "--ffmpeg-location", "/opt/homebrew/bin/ffmpeg",
            "--download-sections", f"*{int(exact_start)}-{int(end_time)}",
            "-f", "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",
            "--force-overwrites",
            "--no-warnings",
            "-o", str(video_temp),
            self.stream_url
        ]
        subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        if video_temp.exists():
            print(f"🎨 Rendering 9:16 vertical video -> {output_short}")
            self.slicer.slice_clip(
                input_path=str(video_temp),
                start_sec=0.0,
                duration_sec=duration,
                output_path=str(output_short),
                style="blur_bg"
            )
            # Remove raw video slice after short is generated
            video_temp.unlink(missing_ok=True)
            print(f"🎉 Completed Short: {output_short.name} ({output_short.stat().st_size / (1024*1024):.2f} MB)")


class StreamWorkerPool:
    """
    Multi-stream concurrency manager.
    Monitors multiple streams simultaneously in parallel threads.
    """
    def __init__(self, max_workers: int = 4):
        self.max_workers = max_workers
        self.transcriber = Transcriber(model_name="mlx-community/whisper-large-v3-turbo")
        self.matcher = TopicMatcher()
        self.slicer = VideoSlicer()

    def monitor_streams(self, stream_targets: List[Dict[str, str]], inspect_seconds: int = 180):
        """
        Dispatches concurrent listeners for each stream.
        stream_targets: [{'name': 'TechnoGamerz', 'url': '...'}, ...]
        """
        print("=" * 65)
        print(f"📡 Multi-Stream Worker Pool Activated ({len(stream_targets)} streams | {self.max_workers} threads)")
        print("=" * 65)

        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = []
            for target in stream_targets:
                listener = AudioStreamListener(
                    stream_url=target["url"],
                    stream_name=target["name"],
                    transcriber=self.transcriber,
                    matcher=self.matcher,
                    slicer=self.slicer
                )
                print(f"🧵 Spawning worker for: {target['name']}")
                futures.append(executor.submit(listener.inspect_window, start_sec=inspect_seconds, window_sec=60))

            for f in futures:
                f.result()
        print("\n✅ Multi-Stream batch inspection finished.")

import subprocess
from pathlib import Path
from typing import Optional

class StreamIngester:
    def __init__(self, output_dir: Optional[str] = None):
        self.output_dir = Path(output_dir or "downloads")
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def _to_seconds(self, time_str: str) -> int:
        """Converts HH:MM:SS or MM:SS or seconds string to integer seconds."""
        parts = time_str.split(":")
        if len(parts) == 3:
            return int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
        elif len(parts) == 2:
            return int(parts[0]) * 60 + int(parts[1])
        return int(float(time_str))

    def download_clip_sample(
        self,
        url: str,
        output_name: Optional[str] = None,
        start_time: str = "00:03:00",
        duration_sec: int = 90,
        force: bool = False
    ) -> Optional[Path]:
        """
        Uses yt-dlp and ffmpeg to grab a concise sample segment
        without downloading a 10-hour full stream.
        """
        import time
        if not output_name:
            output_name = f"gta6_live_{int(time.time())}.mp4"

        target_path = self.output_dir / output_name
        if not force and target_path.exists() and target_path.stat().st_size > 100000:
            print(f"⚡ Chunk already cached on disk: {target_path}")
            return target_path
        start_s = self._to_seconds(start_time)
        end_s = start_s + duration_sec
        section_spec = f"*{start_s}-{end_s}"
        
        # yt-dlp with --download-sections "*start-end"
        cmd = [
            "/Users/vismaythaker/workspace/projects/Clipper/.venv/bin/yt-dlp",
            "--ffmpeg-location", "/opt/homebrew/bin/ffmpeg",
            "--extractor-args", "youtube:player_client=android,web",
            "--download-sections", section_spec,
            "-f", "b/best[height<=720]/bestvideo+bestaudio/best",
            "--force-overwrites",
            "-o", str(target_path),
            url
        ]

        print(f"Executing: yt-dlp download range [{start_s}s to {end_s}s]...")
        res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        
        if target_path.exists():
            return target_path
        
        print(f"Download output: {res.stdout[-300:] if res.stdout else ''}")
        print(f"Download error note: {res.stderr[-300:] if res.stderr else ''}")
        return None

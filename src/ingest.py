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
        output_name: str = "sample.mp4",
        start_time: str = "00:03:00",
        duration_sec: int = 90
    ) -> Optional[Path]:
        """
        Uses yt-dlp and ffmpeg to grab a concise sample segment
        without downloading a 10-hour full stream.
        """
        target_path = self.output_dir / output_name
        start_s = self._to_seconds(start_time)
        end_s = start_s + duration_sec
        section_spec = f"*{start_s}-{end_s}"
        
        # yt-dlp with --download-sections "*start-end"
        cmd = [
            "/Users/vismaythaker/workspace/projects/Clipper/.venv/bin/yt-dlp",
            "--ffmpeg-location", "/opt/homebrew/bin/ffmpeg",
            "--download-sections", section_spec,
            "-f", "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",
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

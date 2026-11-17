import subprocess
import shutil
from pathlib import Path
from typing import Optional

class VideoSlicer:
    def __init__(self, ffmpeg_bin: Optional[str] = None):
        self.ffmpeg_bin = ffmpeg_bin or shutil.which("ffmpeg") or "/opt/homebrew/bin/ffmpeg"

    def slice_clip(
        self,
        input_path: str,
        start_sec: float,
        duration_sec: float,
        output_path: str,
        style: str = "blur_bg"
    ) -> bool:
        """
        Slices a video window and formats it into a 9:16 (1080x1920) vertical video.
        Styles:
          - 'blur_bg': Retains entire 16:9 gameplay in center with blurred matching background.
          - 'center_crop': Direct 9:16 center crop (zoomed in).
        """
        start_sec = max(0.0, start_sec)
        
        if style == "blur_bg":
            # 16:9 gameplay centered (1080x608), blurred background filling 1080x1920
            filter_complex = (
                "[0:v]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,boxblur=25:5[bg];"
                "[0:v]scale=1080:608[fg];"
                "[bg][fg]overlay=(W-w)/2:(H-h)/2[outv]"
            )
            cmd = [
                self.ffmpeg_bin,
                "-y",
                "-ss", str(start_sec),
                "-t", str(duration_sec),
                "-i", input_path,
                "-filter_complex", filter_complex,
                "-map", "[outv]",
                "-map", "0:a?",
                "-c:v", "libx264",
                "-preset", "veryfast",
                "-crf", "22",
                "-c:a", "aac",
                "-b:a", "192k",
                "-ar", "44100",
                "-avoid_negative_ts", "make_zero",
                "-async", "1",
                output_path
            ]
        else:
            # Direct Center Crop
            filter_str = "crop=ih*(9/16):ih:(iw-ow)/2:0,scale=1080:1920"
            cmd = [
                self.ffmpeg_bin,
                "-y",
                "-ss", str(start_sec),
                "-t", str(duration_sec),
                "-i", input_path,
                "-vf", filter_str,
                "-map", "0:v:0",
                "-map", "0:a?",
                "-c:v", "libx264",
                "-preset", "veryfast",
                "-crf", "22",
                "-c:a", "aac",
                "-b:a", "192k",
                "-ar", "44100",
                "-avoid_negative_ts", "make_zero",
                "-async", "1",
                output_path
            ]

        res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        return res.returncode == 0

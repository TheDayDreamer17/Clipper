import subprocess
import shutil
import tempfile
from pathlib import Path
from typing import Optional
from PIL import Image, ImageDraw, ImageFont

class VideoSlicer:
    """
    FFmpeg 9:16 Vertical Video Formatter with:
    - 16:9 centered gameplay with blurred background filling 1080x1920
    - Audio sync & positive PTS fix for macOS QuickTime/Safari
    - Dynamic duration rounding (e.g. 22s -> 25s)
    - Modern Glassmorphic Viral Banner UI (Neon Pill Badge, Cyan Glow, Drop Shadows)
    """
    def __init__(self, ffmpeg_bin: Optional[str] = None):
        self.ffmpeg_bin = ffmpeg_bin or shutil.which("ffmpeg") or "/opt/homebrew/bin/ffmpeg"
        self.font_path = "/System/Library/Fonts/Supplemental/Arial Bold.ttf"
        if not Path(self.font_path).exists():
            self.font_path = "/Library/Fonts/Arial Unicode.ttf"

    def round_duration(self, raw_duration: float, step: int = 5, min_sec: int = 15, max_sec: int = 60) -> int:
        """Rounds a duration up to the nearest clean 5s window."""
        rounded = int(step * round(raw_duration / step))
        if rounded < raw_duration:
            rounded += step
        return max(min_sec, min(max_sec, rounded))

    def create_text_banner_image(
        self,
        title: str,
        subtitle: Optional[str] = None,
        tag_text: str = "🔥 GTA SHOWCASE",
        output_png: Optional[Path] = None
    ) -> Path:
        """
        Renders a sleek, modern glassmorphic viral short banner:
        - Floating neon pink pill badge
        - Electric cyan glowing container border
        - High-contrast bold white title + drop shadow
        - Cyan/Gold accent subtitle
        """
        if not output_png:
            output_png = Path(tempfile.gettempdir()) / f"viral_banner_{abs(hash(title)) % 100000}.png"

        img = Image.new("RGBA", (1080, 1920), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)

        # 1. Main Glassmorphic Container (y=180 to y=330)
        pill_box = [(70, 180), (1010, 330)]
        # Glowing cyan outline
        draw.rounded_rectangle([(66, 176), (1014, 334)], radius=28, outline=(0, 240, 255, 140), width=3)
        # Translucent dark body
        draw.rounded_rectangle(pill_box, radius=24, fill=(12, 16, 24, 230))

        # 2. Category Pill Badge (floating on top-left of container)
        badge_box = [(110, 162), (360, 204)]
        draw.rounded_rectangle(badge_box, radius=12, fill=(255, 0, 128, 255)) # Vibrant Neon Pink

        # Load fonts
        try:
            badge_font = ImageFont.truetype(self.font_path, 22)
            main_font = ImageFont.truetype(self.font_path, 38)
            sub_font = ImageFont.truetype(self.font_path, 25)
        except Exception:
            badge_font = main_font = sub_font = ImageFont.load_default()

        # Render Pill Badge Text
        draw.text((235, 183), tag_text, font=badge_font, fill=(255, 255, 255, 255), anchor="mm")

        # Render Main Title (with shadow)
        title_y = 244 if subtitle else 255
        draw.text((542, title_y + 2), title.upper(), font=main_font, fill=(0, 0, 0, 220), anchor="mm")
        draw.text((540, title_y), title.upper(), font=main_font, fill=(255, 255, 255, 255), anchor="mm")

        # Render Subtitle if present
        if subtitle:
            draw.text((542, 292), subtitle.upper(), font=sub_font, fill=(0, 0, 0, 200), anchor="mm")
            draw.text((540, 290), subtitle.upper(), font=sub_font, fill=(0, 240, 255, 255), anchor="mm") # Electric Cyan

        img.save(output_png)
        return output_png

    def slice_clip(
        self,
        input_path: str,
        start_sec: float,
        duration_sec: float,
        output_path: str,
        style: str = "blur_bg",
        overlay_text: Optional[str] = None,
        overlay_subtitle: Optional[str] = None,
        tag_text: str = "🔥 GTA SHOWCASE"
    ) -> bool:
        """
        Slices a video window and formats it into a 9:16 (1080x1920) vertical video.
        """
        start_sec = max(0.0, start_sec)
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        
        banner_png = None
        if overlay_text:
            banner_png = self.create_text_banner_image(overlay_text, overlay_subtitle, tag_text=tag_text)

        if style == "blur_bg":
            # 16:9 gameplay centered (1080x608), blurred background filling 1080x1920
            if banner_png:
                filter_complex = (
                    "[0:v]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,boxblur=25:5[bg];"
                    "[0:v]scale=1080:608[fg];"
                    "[bg][fg]overlay=(W-w)/2:(H-h)/2[base];"
                    "[base][1:v]overlay=0:0[outv]"
                )
                cmd = [
                    self.ffmpeg_bin,
                    "-y",
                    "-ss", str(start_sec),
                    "-t", str(duration_sec),
                    "-i", input_path,
                    "-i", str(banner_png),
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
            filter_str = "crop=ih*(9/16):ih:(iw-ow)/2:0,scale=1080:1920"
            cmd = [
                self.ffmpeg_bin,
                "-y",
                "-ss", str(start_sec),
                "-t", str(duration_sec),
                "-i", input_path,
                "-vf", filter_str,
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

        res = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return res.returncode == 0 and Path(output_path).exists()

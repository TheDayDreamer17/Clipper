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
        candidate_fonts = [
            "/System/Library/Fonts/Supplemental/Arial Black.ttf",
            "/System/Library/Fonts/Supplemental/Impact.ttf",
            "/System/Library/Fonts/Supplemental/Futura.ttc",
            "/System/Library/Fonts/HelveticaNeue.ttc"
        ]
        self.font_path = next((f for f in candidate_fonts if Path(f).exists()), "/System/Library/Fonts/Helvetica.ttc")
        self.impact_font = "/System/Library/Fonts/Supplemental/Impact.ttf" if Path("/System/Library/Fonts/Supplemental/Impact.ttf").exists() else self.font_path
        self.arial_black_font = "/System/Library/Fonts/Supplemental/Arial Black.ttf" if Path("/System/Library/Fonts/Supplemental/Arial Black.ttf").exists() else self.font_path

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
        Renders a top-tier modern viral creator banner:
        - Floating high-impact category sticker (Cyber Yellow / Warning Red / Neon Pink)
        - Punchy, multi-directional shadowed Impact headline with smart wrapping (no edge cutoff)
        - Lower safe-zone hook capsule (y=1350) positioned right below the gameplay window
        - 100% transparent background outside the sticker elements
        """
        import textwrap
        if not output_png:
            output_png = Path(tempfile.gettempdir()) / f"viral_banner_{abs(hash(title)) % 100000}.png"

        img = Image.new("RGBA", (1080, 1920), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)

        # 1. Floating Category Tag Sticker (centered at x=540, y=230)
        tag_font_size = 30
        try:
            font_tag = ImageFont.truetype(self.arial_black_font, tag_font_size)
        except Exception:
            font_tag = ImageFont.load_default()

        tag_bbox = draw.textbbox((0, 0), tag_text.upper(), font=font_tag)
        tag_w = tag_bbox[2] - tag_bbox[0]
        tag_h = tag_bbox[3] - tag_bbox[1]

        pad_x, pad_y = 24, 10
        pill_box = [(540 - tag_w // 2 - pad_x, 230 - pad_y), (540 + tag_w // 2 + pad_x, 230 + tag_h + pad_y)]
        
        # Color match badge: Yellow for alerts/physics, Pink for characters, Red for wanted/combat
        badge_bg = (255, 221, 0, 255) # Cyber Yellow default
        badge_text_color = (0, 0, 0, 255)
        if any(w in tag_text.upper() for w in ["WANTED", "POLICE", "PURSUIT", "DANGER", "COMBAT", "SHOOTOUT"]):
            badge_bg = (255, 20, 60, 255) # Warning Red
            badge_text_color = (255, 255, 255, 255)
        elif any(w in tag_text.upper() for w in ["ARTWORK", "CHARACTER", "LEAK", "VIRAL"]):
            badge_bg = (255, 0, 128, 255) # Neon Pink
            badge_text_color = (255, 255, 255, 255)

        draw.rounded_rectangle(pill_box, radius=14, fill=badge_bg)
        draw.text((540, 230 + tag_h // 2), tag_text.upper(), font=font_tag, fill=badge_text_color, anchor="mm")

        # 2. Main Title (Impact Font with multi-line auto-wrap & 3D drop shadow)
        clean_title = title.upper().replace("_", " ")
        lines = textwrap.wrap(clean_title, width=22)
        if not lines:
            lines = [clean_title]

        title_font_size = 66 if len(lines) == 1 else 54
        line_height = 72 if len(lines) == 1 else 60
        try:
            font_title = ImageFont.truetype(self.impact_font, title_font_size)
        except Exception:
            font_title = ImageFont.load_default()

        # Center multi-line block vertically in top area (y=320 to 450)
        start_y = 350 - ((len(lines) - 1) * line_height) // 2
        for idx, line in enumerate(lines):
            curr_y = start_y + (idx * line_height)
            # Multi-directional drop shadow
            for dx, dy in [(0, 5), (3, 3), (-3, 3), (0, -2), (2, 0), (-2, 0)]:
                draw.text((540 + dx, curr_y + dy), line, font=font_title, fill=(0, 0, 0, 240), anchor="mm")
            # Crisp white foreground
            draw.text((540, curr_y), line, font=font_title, fill=(255, 255, 255, 255), anchor="mm")

        # 3. Subtitle / Hook Capsule (Placed in LOWER SAFE ZONE at y=1350, right below the 1080x608 gameplay window)
        if subtitle:
            sub_y = 1350
            try:
                font_sub = ImageFont.truetype(self.arial_black_font, 26)
            except Exception:
                font_sub = ImageFont.load_default()

            sub_bbox = draw.textbbox((0, 0), subtitle.upper(), font=font_sub)
            sub_w = sub_bbox[2] - sub_bbox[0]
            sub_h = sub_bbox[3] - sub_bbox[1]
            sub_box = [(540 - sub_w // 2 - 20, sub_y - 10), (540 + sub_w // 2 + 20, sub_y + sub_h + 10)]
            # Glassmorphic dark card with neon cyan border
            draw.rounded_rectangle(sub_box, radius=12, fill=(15, 23, 42, 230), outline=(0, 240, 255, 200), width=2)
            draw.text((540, sub_y + sub_h // 2), subtitle.upper(), font=font_sub, fill=(0, 240, 255, 255), anchor="mm")

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
            # 16:9 gameplay centered (1080x608), darkened blurred background filling 1080x1920
            # with crisp 3px accent borders framing the gameplay window
            if banner_png:
                filter_complex = (
                    "[0:v]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,boxblur=30:5,eq=brightness=-0.30:contrast=1.15[bg];"
                    "[0:v]scale=1080:608,drawbox=x=0:y=0:w=1080:h=3:color=white@0.5:t=fill,drawbox=x=0:y=605:w=1080:h=3:color=white@0.5:t=fill[fg];"
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
                    "[0:v]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,boxblur=30:5,eq=brightness=-0.30:contrast=1.15[bg];"
                    "[0:v]scale=1080:608,drawbox=x=0:y=0:w=1080:h=3:color=white@0.5:t=fill,drawbox=x=0:y=605:w=1080:h=3:color=white@0.5:t=fill[fg];"
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

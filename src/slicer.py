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
        brand_name: str = "GTA 6 CLIPS",
        creator_credit: Optional[str] = None,
        output_png: Optional[Path] = None
    ) -> Path:
        """
        Renders a top-tier modern viral creator banner:
        - Brand Stamp (Top Left: ⚡️ GTA 6 CLIPS or 🇮🇳 GTA 6 CLIPS INDIA)
        - Creator Attribution (Top Right: VIA @creator)
        - Floating high-impact category sticker (Cyber Yellow / Warning Red / Neon Pink)
        - Punchy, multi-directional shadowed Impact headline with smart wrapping
        - Lower safe-zone hook capsule (y=1350) positioned right below gameplay window
        """
        import textwrap
        if not output_png:
            output_png = Path(tempfile.gettempdir()) / f"viral_banner_{abs(hash(title + brand_name)) % 100000}.png"

        img = Image.new("RGBA", (1080, 1920), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)

        try:
            font_brand = ImageFont.truetype(self.arial_black_font, 24)
            font_credit = ImageFont.truetype(self.arial_black_font, 20)
            font_tag = ImageFont.truetype(self.arial_black_font, 28)
            font_sub = ImageFont.truetype(self.arial_black_font, 26)
        except Exception:
            font_brand = font_credit = font_tag = font_sub = ImageFont.load_default()

        # 1. Top Brand Stamp (Top Left: x=70, y=90)
        is_india = "INDIA" in brand_name.upper()
        brand_icon = "🇮🇳 " if is_india else "⚡️ "
        full_brand_text = f"{brand_icon}{brand_name.upper()}"
        b_bbox = draw.textbbox((0, 0), full_brand_text, font=font_brand)
        bw, bh = b_bbox[2] - b_bbox[0], b_bbox[3] - b_bbox[1]
        brand_box = [(70 - 16, 90 - 8), (70 + bw + 16, 90 + bh + 8)]
        brand_border = (255, 140, 0, 220) if is_india else (0, 240, 255, 200)
        draw.rounded_rectangle(brand_box, radius=10, fill=(15, 23, 42, 230), outline=brand_border, width=2)
        draw.text((70, 90 + bh // 2), full_brand_text, font=font_brand, fill=(255, 255, 255, 255), anchor="lm")

        # 2. Creator Attribution Badge (Top Right: x=1010 - cw, y=90)
        if creator_credit:
            credit_text = f"VIA @{creator_credit.lstrip('@')}"
            c_bbox = draw.textbbox((0, 0), credit_text, font=font_credit)
            cw, ch = c_bbox[2] - c_bbox[0], c_bbox[3] - c_bbox[1]
            credit_box = [(1010 - cw - 16, 90 - 8), (1010 + 16, 90 + ch + 8)]
            draw.rounded_rectangle(credit_box, radius=10, fill=(0, 0, 0, 210), outline=(255, 255, 255, 90), width=1)
            draw.text((1010 - cw, 90 + ch // 2), credit_text, font=font_credit, fill=(210, 210, 210, 240), anchor="lm")

        # 3. Floating Category Tag Sticker (centered at x=540, y=230)
        tag_bbox = draw.textbbox((0, 0), tag_text.upper(), font=font_tag)
        tag_w = tag_bbox[2] - tag_bbox[0]
        tag_h = tag_bbox[3] - tag_bbox[1]

        pad_x, pad_y = 24, 10
        pill_box = [(540 - tag_w // 2 - pad_x, 230 - pad_y), (540 + tag_w // 2 + pad_x, 230 + tag_h + pad_y)]
        
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

        # 4. Main Title (Impact Font with multi-line auto-wrap & 3D drop shadow)
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

        start_y = 350 - ((len(lines) - 1) * line_height) // 2
        for idx, line in enumerate(lines):
            curr_y = start_y + (idx * line_height)
            for dx, dy in [(0, 5), (3, 3), (-3, 3), (0, -2), (2, 0), (-2, 0)]:
                draw.text((540 + dx, curr_y + dy), line, font=font_title, fill=(0, 0, 0, 240), anchor="mm")
            draw.text((540, curr_y), line, font=font_title, fill=(255, 255, 255, 255), anchor="mm")

        # 5. Subtitle / Hook Capsule (Placed in LOWER SAFE ZONE at y=1350)
        if subtitle:
            sub_y = 1350
            sub_bbox = draw.textbbox((0, 0), subtitle.upper(), font=font_sub)
            sub_w = sub_bbox[2] - sub_bbox[0]
            sub_h = sub_bbox[3] - sub_bbox[1]
            sub_box = [(540 - sub_w // 2 - 20, sub_y - 10), (540 + sub_w // 2 + 20, sub_y + sub_h + 10)]
            draw.rounded_rectangle(sub_box, radius=12, fill=(15, 23, 42, 230), outline=(0, 240, 255, 200), width=2)
            draw.text((540, sub_y + sub_h // 2), subtitle.upper(), font=font_sub, fill=(0, 240, 255, 255), anchor="mm")

        img.save(output_png)
        return output_png

    def create_hook_overlay_image(self, hook_text: str = "👀 WAIT TILL THE END...", output_png: Optional[Path] = None) -> Path:
        """Renders the first 3-second attention-grabbing hook badge (y=585, just above gameplay)."""
        if not output_png:
            output_png = Path(tempfile.gettempdir()) / f"hook_badge_{abs(hash(hook_text)) % 100000}.png"

        img = Image.new("RGBA", (1080, 1920), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)

        try:
            font_hook = ImageFont.truetype(self.impact_font, 48)
        except Exception:
            font_hook = ImageFont.load_default()

        h_bbox = draw.textbbox((0, 0), hook_text.upper(), font=font_hook)
        hw, hh = h_bbox[2] - h_bbox[0], h_bbox[3] - h_bbox[1]
        hook_box = [(540 - hw // 2 - 24, 585 - 12), (540 + hw // 2 + 24, 585 + hh + 12)]
        draw.rounded_rectangle(hook_box, radius=14, fill=(255, 221, 0, 250), outline=(0, 0, 0, 220), width=3)
        draw.text((540, 585 + hh // 2), hook_text.upper(), font=font_hook, fill=(0, 0, 0, 255), anchor="mm")

        img.save(output_png)
        return output_png

    def create_outro_cta_image(self, brand_name: str = "GTA 6 CLIPS", output_png: Optional[Path] = None) -> Path:
        """Renders the final 2.5-second call-to-action subscribe card (y=1500)."""
        if not output_png:
            output_png = Path(tempfile.gettempdir()) / f"cta_badge_{abs(hash(brand_name)) % 100000}.png"

        img = Image.new("RGBA", (1080, 1920), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)

        try:
            font_cta = ImageFont.truetype(self.impact_font, 42)
        except Exception:
            font_cta = ImageFont.load_default()

        cta_text = f"🔴 SUBSCRIBE TO @{brand_name.replace(' ', '')}"
        c_bbox = draw.textbbox((0, 0), cta_text.upper(), font=font_cta)
        cw, ch = c_bbox[2] - c_bbox[0], c_bbox[3] - c_bbox[1]
        cta_box = [(540 - cw // 2 - 24, 1500 - 12), (540 + cw // 2 + 24, 1500 + ch + 12)]
        draw.rounded_rectangle(cta_box, radius=14, fill=(15, 23, 42, 240), outline=(255, 20, 60, 220), width=3)
        draw.text((540, 1500 + ch // 2), cta_text.upper(), font=font_cta, fill=(255, 255, 255, 255), anchor="mm")

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
        tag_text: str = "🔥 GTA SHOWCASE",
        brand_name: str = "GTA 6 CLIPS",
        creator_credit: Optional[str] = None,
        hook_text: Optional[str] = "👀 WAIT TILL THE END..."
    ) -> bool:
        """
        Slices a video window and formats it into a 9:16 (1080x1920) vertical video.
        Composites:
        1. Darkened ambient blurred 9:16 background with 3px framed gameplay
        2. Channel Brand Stamp (GTA 6 CLIPS / GTA 6 CLIPS INDIA) + Creator Attribution
        3. First 3-second animated attention hook (between(t, 0, 3.0))
        4. Final 2.5-second call-to-action subscribe prompt (gte(t, duration - 2.5))
        """
        start_sec = max(0.0, start_sec)
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        
        banner_png = None
        if overlay_text:
            banner_png = self.create_text_banner_image(
                title=overlay_text,
                subtitle=overlay_subtitle,
                tag_text=tag_text,
                brand_name=brand_name,
                creator_credit=creator_credit
            )

        hook_png = None
        if hook_text and duration_sec >= 5.0:
            hook_png = self.create_hook_overlay_image(hook_text)

        cta_png = None
        if duration_sec >= 8.0:
            cta_png = self.create_outro_cta_image(brand_name)

        if style == "blur_bg":
            inputs = ["-i", input_path]
            filter_chain = [
                "[0:v]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,boxblur=30:5,eq=brightness=-0.30:contrast=1.15[bg]",
                "[0:v]scale=1080:608,drawbox=x=0:y=0:w=1080:h=3:color=white@0.5:t=fill,drawbox=x=0:y=605:w=1080:h=3:color=white@0.5:t=fill[fg]",
                "[bg][fg]overlay=(W-w)/2:(H-h)/2[stage0]"
            ]

            curr_stream = "stage0"
            curr_idx = 1
            if banner_png:
                inputs.extend(["-i", str(banner_png)])
                filter_chain.append(f"[{curr_stream}][{curr_idx}:v]overlay=0:0[stage{curr_idx}]")
                curr_stream = f"stage{curr_idx}"
                curr_idx += 1

            if hook_png:
                inputs.extend(["-i", str(hook_png)])
                filter_chain.append(f"[{curr_stream}][{curr_idx}:v]overlay=0:0:enable=\x27between(t,0,3.0)\x27[stage{curr_idx}]")
                curr_stream = f"stage{curr_idx}"
                curr_idx += 1

            if cta_png:
                cta_start = max(3.5, duration_sec - 2.5)
                inputs.extend(["-i", str(cta_png)])
                filter_chain.append(f"[{curr_stream}][{curr_idx}:v]overlay=0:0:enable=\x27gte(t,{cta_start})\x27[outv]")
            else:
                last_step = filter_chain[-1]
                filter_chain[-1] = last_step[:last_step.rfind("[")] + "[outv]"

            filter_complex = ";".join(filter_chain)
            cmd = [
                self.ffmpeg_bin,
                "-y",
                "-ss", str(start_sec),
                "-t", str(duration_sec),
                *inputs,
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

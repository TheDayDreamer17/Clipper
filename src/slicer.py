import subprocess
import shutil
import tempfile
from pathlib import Path
from typing import Optional, Tuple, List
import random
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
        self._censor_counter = 0

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
        tag_text: str = "LIVE GTA 6",
        brand_name: str = "OUTLAW CLIPS",
        creator_credit: Optional[str] = None,
        chat_reaction: Optional[str] = None,
        side_meme_text: Optional[str] = None,
        output_png: Optional[Path] = None
    ) -> Path:
        """
        Renders the GTA VI Vice City Neon Sunset Stream Package Theme:
        - Sunset Coral & Midnight Purple glassmorphic color palette
        - Dedicated vector icon box (Instagram / Live broadcast glyph - 100% font-independent)
        - Floating sarcastic hook headline with dark 3D halo drop shadow
        - Optional Remotion-style side meme sticker badge (e.g. "I CAN DO THIS ALL DAY")
        - Lower live audience chat / notification ticker bar (like GFXCRATE reference)
        """
        import textwrap
        import re

        if not output_png:
            output_png = Path(tempfile.gettempdir()) / f"viral_banner_{abs(hash(title + brand_name)) % 100000}.png"

        img = Image.new("RGBA", (1080, 1920), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)

        # Fonts
        try:
            font_pill = ImageFont.truetype(self.arial_black_font, 22)
            font_title = ImageFont.truetype(self.impact_font, 54)
            font_sub = ImageFont.truetype(self.arial_black_font, 20)
            font_gem = ImageFont.truetype(self.arial_black_font, 18)
            font_badge = ImageFont.truetype(self.arial_black_font, 16)
        except Exception:
            font_pill = font_title = font_sub = font_gem = font_badge = ImageFont.load_default()

        # --- 1. TOP HEADER PILL (Vice City Sunset Glassmorphic Bar: y=85 to 145) ---
        clean_creator = (creator_credit or brand_name).lstrip("@").strip().upper()
        pill_label = f"GTA VI  •  @{clean_creator}"
        p_bbox = draw.textbbox((0, 0), pill_label, font=font_pill)
        text_w = p_bbox[2] - p_bbox[0]
        pw = text_w + 120
        ph = 56
        pill_x1 = 540 - pw // 2
        pill_y1 = 85
        pill_x2 = 540 + pw // 2
        pill_y2 = pill_y1 + ph

        # Dark midnight purple base with glowing sunset coral border (#FF4571)
        draw.rounded_rectangle([(pill_x1, pill_y1), (pill_x2, pill_y2)], radius=28, fill=(24, 7, 36, 230), outline=(255, 69, 113, 220), width=2)
        # Subtle top fuchsia highlight stripe
        draw.line([(pill_x1 + 30, pill_y1 + 2), (pill_x2 - 30, pill_y1 + 2)], fill=(255, 120, 160, 160), width=1)

        # Dedicated Left Icon Box (Sunset gradient button)
        icon_box_x1 = pill_x1 + 8
        icon_box_y1 = pill_y1 + 8
        icon_box_x2 = icon_box_x1 + 44
        icon_box_y2 = pill_y2 - 8
        draw.rounded_rectangle([(icon_box_x1, icon_box_y1), (icon_box_x2, icon_box_y2)], radius=14, fill=(255, 69, 113, 255))

        # Draw crisp mathematical vector glyph inside icon box (Instagram Camera Glyph)
        cam_x1, cam_y1 = icon_box_x1 + 10, icon_box_y1 + 10
        cam_x2, cam_y2 = icon_box_x2 - 10, icon_box_y2 - 10
        draw.rounded_rectangle([(cam_x1, cam_y1), (cam_x2, cam_y2)], radius=5, outline=(255, 255, 255, 255), width=2)
        lens_cx = (cam_x1 + cam_x2) // 2
        lens_cy = (cam_y1 + cam_y2) // 2
        draw.ellipse([(lens_cx - 4, lens_cy - 4), (lens_cx + 4, lens_cy + 4)], outline=(255, 255, 255, 255), width=2)
        draw.ellipse([(cam_x2 - 4, cam_y1 + 2), (cam_x2 - 2, cam_y1 + 4)], fill=(255, 255, 255, 255))

        # Pill creator text
        draw.text((icon_box_x2 + 18, pill_y1 + ph // 2), pill_label, font=font_pill, fill=(255, 255, 255, 255), anchor="lm")

        # --- 2. FLOATING WITTY HOOK BANNER (y=230 to y=450) ---
        clean_headline = re.sub(r'[\U00010000-\U0010ffff]', '', title).strip().upper()
        clean_headline = re.sub(r'[^\w\s\?\!\:\-\'\"]', '', clean_headline)
        if not clean_headline:
            clean_headline = "BRO REALLY THOUGHT HE WAS SLICK"

        wrap_w = 17 if side_meme_text else 20
        lines = textwrap.wrap(clean_headline, width=wrap_w)
        line_height = 68
        total_h = len(lines) * line_height
        box_pad = 28
        h_box_y1 = 250 - box_pad
        h_box_y2 = 250 + total_h + box_pad

        h_box_x2 = 840 if side_meme_text else 990
        text_cx = 465 if side_meme_text else 540

        # Draw Vice City Sunset Glass Backdrop Panel
        draw.rounded_rectangle([(90, h_box_y1), (h_box_x2, h_box_y2)], radius=20, fill=(20, 6, 32, 225), outline=(255, 176, 116, 160), width=2)
        draw.line([(110, h_box_y1), (h_box_x2 - 20, h_box_y1)], fill=(255, 69, 113, 240), width=3)

        start_y = 250 + (line_height // 2)
        for idx, line in enumerate(lines):
            curr_y = start_y + (idx * line_height)
            for dx, dy in [(-3, -3), (-3, 3), (3, -3), (3, 3), (0, 4), (0, -2), (3, 0), (-3, 0)]:
                draw.text((text_cx + dx, curr_y + dy), line, font=font_title, fill=(0, 0, 0, 255), anchor="mm")
            draw.text((text_cx, curr_y), line, font=font_title, fill=(255, 255, 255, 255), anchor="mm")

        # --- OPTIONAL FLOATING SIDE MEME BADGE (e.g. "I CAN DO THIS ALL DAY") ---
        if side_meme_text:
            badge_cx, badge_cy, badge_r = 940, (h_box_y1 + h_box_y2) // 2, 85
            # Outer neon glow rings
            draw.ellipse([(badge_cx - badge_r - 6, badge_cy - badge_r - 6), (badge_cx + badge_r + 6, badge_cy + badge_r + 6)], outline=(255, 69, 113, 140), width=3)
            draw.ellipse([(badge_cx - badge_r, badge_cy - badge_r), (badge_cx + badge_r, badge_cy + badge_r)], fill=(24, 7, 36, 245), outline=(0, 240, 255, 240), width=3)

            # Top mini pill tag inside badge: "MEME"
            pill_m_w, pill_m_h = 48, 16
            pm_x1 = badge_cx - pill_m_w // 2
            pm_y1 = badge_cy - badge_r + 14
            draw.rounded_rectangle([(pm_x1, pm_y1), (pm_x1 + pill_m_w, pm_y1 + pill_m_h)], radius=8, fill=(255, 69, 113, 255))
            try:
                font_mini = ImageFont.truetype(self.arial_black_font, 11)
            except Exception:
                font_mini = ImageFont.load_default()
            draw.text((badge_cx, pm_y1 + pill_m_h // 2), "MEME", font=font_mini, fill=(255, 255, 255, 255), anchor="mm")

            # Deal With It Sunglasses Graphic
            sg_y = badge_cy - 12
            draw.polygon([(badge_cx - 36, sg_y - 12), (badge_cx - 6, sg_y - 12), (badge_cx - 6, sg_y + 10), (badge_cx - 26, sg_y + 10), (badge_cx - 36, sg_y)], fill=(0, 240, 255, 255))
            draw.polygon([(badge_cx + 6, sg_y - 12), (badge_cx + 36, sg_y - 12), (badge_cx + 36, sg_y), (badge_cx + 26, sg_y + 10), (badge_cx + 6, sg_y + 10)], fill=(0, 240, 255, 255))
            draw.line([(badge_cx - 6, sg_y - 8), (badge_cx + 6, sg_y - 8)], fill=(255, 255, 255, 255), width=3)
            draw.line([(badge_cx - 30, sg_y - 8), (badge_cx - 22, sg_y - 8)], fill=(255, 255, 255, 255), width=2)
            draw.line([(badge_cx + 12, sg_y - 8), (badge_cx + 20, sg_y - 8)], fill=(255, 255, 255, 255), width=2)

            blines = textwrap.wrap(side_meme_text.upper(), width=10)
            by_start = badge_cy + 22
            for bi, bline in enumerate(blines):
                draw.text((badge_cx, by_start + (bi * 20)), bline, font=font_badge, fill=(255, 255, 255, 255), anchor="mm")

        # --- 3. LOWER NOTIFICATION SLIDER / LIVE CHAT TICKER (y=1390 to y=1455) ---
        ticker_msg = chat_reaction or subtitle or "LIVESTREAM HIGHLIGHT"
        clean_ticker = re.sub(r'[\U00010000-\U0010ffff]', '', ticker_msg).strip().upper()
        clean_ticker = re.sub(r'[^\w\s\?\!\:\-\'\"\.#]', '', clean_ticker)
        if clean_ticker:
            t_bbox = draw.textbbox((0, 0), clean_ticker, font=font_sub)
            tw = min(t_bbox[2] - t_bbox[0] + 180, 880)
            th = 52
            tx1 = 540 - tw // 2
            ty1 = 1395
            tx2 = 540 + tw // 2
            ty2 = ty1 + th

            # Glassmorphic purple bar with Neon Cyan border (#00F0FF)
            draw.rounded_rectangle([(tx1, ty1), (tx2, ty2)], radius=18, fill=(18, 5, 28, 235), outline=(0, 240, 255, 190), width=2)

            # Neon Cyan Corner Gem Badge
            gem_w = 110
            draw.rounded_rectangle([(tx1 + 6, ty1 + 6), (tx1 + gem_w, ty2 - 6)], radius=12, fill=(0, 240, 255, 255))
            draw.text((tx1 + 6 + gem_w // 2, ty1 + th // 2), "LIVE CHAT", font=font_gem, fill=(10, 15, 26, 255), anchor="mm")

            # Reaction text
            draw.text((tx1 + gem_w + 16, ty1 + th // 2), f'"{clean_ticker[:40]}"', font=font_sub, fill=(255, 255, 255, 240), anchor="lm")

        img.save(output_png)
        return output_png

    def create_hook_overlay_image(self, hook_text: str = "WAIT TILL THE END...", output_png: Optional[Path] = None) -> Path:
        """Renders an optional first 3-second attention-grabbing hook badge (y=585, just above gameplay)."""
        import re
        if not output_png:
            output_png = Path(tempfile.gettempdir()) / f"hook_badge_{abs(hash(hook_text)) % 100000}.png"

        img = Image.new("RGBA", (1080, 1920), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)

        try:
            font_hook = ImageFont.truetype(self.arial_black_font, 28)
        except Exception:
            font_hook = ImageFont.load_default()

        clean_hook = re.sub(r'[\U00010000-\U0010ffff]', '', hook_text).strip().upper()
        h_bbox = draw.textbbox((0, 0), clean_hook, font=font_hook)
        hw, hh = h_bbox[2] - h_bbox[0], h_bbox[3] - h_bbox[1]
        hook_box = [(540 - hw // 2 - 24, 585 - 10), (540 + hw // 2 + 24, 585 + hh + 10)]
        draw.rounded_rectangle(hook_box, radius=12, fill=(10, 15, 26, 230), outline=(255, 45, 85, 200), width=2)
        draw.text((540, 585 + hh // 2), clean_hook, font=font_hook, fill=(255, 255, 255, 255), anchor="mm")

        img.save(output_png)
        return output_png

    def create_smart_censor_image(
        self,
        censor_box: Tuple[int, int, int, int] = (390, 800, 690, 1120),
        censor_mode: str = "round_robin",
        brand_name: str = "OUTLAW CLIPS",
        output_png: Optional[Path] = None
    ) -> Tuple[Path, str]:
        """
        Renders a transparent PNG overlay implementing the 3-Way Censor Strategy:
        1. 'mosaic_8bit': Retro arcade pixelation
        2. 'meme_sticker': Sarcastic Gen-Z 'NO HORNY / DOWN BAD' sticker
        3. 'brand_logo': Outlaw Clips neon brand stamp watermark
        Dispatches via 'round_robin' or 'random'.
        Returns (output_png_path, chosen_mode_name).
        """
        if not output_png:
            output_png = Path(tempfile.gettempdir()) / f"censor_{abs(hash(str(censor_box) + str(self._censor_counter))) % 100000}.png"

        canvas = Image.new("RGBA", (1080, 1920), (0, 0, 0, 0))
        draw = ImageDraw.Draw(canvas)

        modes = ["mosaic_8bit", "meme_sticker", "brand_logo"]
        if censor_mode in modes:
            chosen = censor_mode
        elif censor_mode == "random":
            chosen = random.choice(modes)
        else: # round_robin
            chosen = modes[self._censor_counter % len(modes)]
            self._censor_counter += 1

        x1, y1, x2, y2 = censor_box
        bw, bh = x2 - x1, y2 - y1
        cx, cy = (x1 + x2) // 2, (y1 + y2) // 2

        try:
            font_arial = ImageFont.truetype(self.arial_black_font, 14)
            font_tag = ImageFont.truetype(self.arial_black_font, 13)
            font_impact = ImageFont.truetype(self.impact_font, 28)
            font_brand = ImageFont.truetype(self.impact_font, 32)
        except Exception:
            font_arial = font_tag = font_impact = font_brand = ImageFont.load_default()

        if chosen == "mosaic_8bit":
            step = 16
            for gx in range(x1, x2, step):
                for gy in range(y1, y2, step):
                    c_val = random.choice([
                        (24, 7, 36, 245),
                        (45, 12, 60, 245),
                        (255, 69, 113, 230),
                        (0, 240, 255, 220),
                        (15, 5, 22, 255)
                    ])
                    draw.rectangle([(gx, gy), (min(gx + step - 1, x2), min(gy + step - 1, y2))], fill=c_val)
            draw.rectangle([(x1, y1), (x2, y2)], outline=(0, 240, 255, 255), width=3)
            draw.rounded_rectangle([(x1, y1 - 28), (x1 + 130, y1)], radius=6, fill=(24, 7, 36, 255), outline=(0, 240, 255, 255), width=2)
            draw.text((x1 + 65, y1 - 14), "8-BIT MOSAIC", font=font_arial, fill=(0, 240, 255, 255), anchor="mm")

        elif chosen == "meme_sticker":
            draw.rounded_rectangle([(x1, y1), (x2, y2)], radius=20, fill=(20, 5, 28, 240), outline=(255, 69, 113, 255), width=3)
            for s in range(x1, x2 + bh, 24):
                draw.line([(s, y1), (s - bh, y2)], fill=(255, 69, 113, 40), width=8)

            badge_w, badge_h = min(bw + 60, 360), 120
            bx1, by1 = cx - badge_w // 2, cy - badge_h // 2
            draw.rounded_rectangle([(bx1, by1), (bx1 + badge_w, by1 + badge_h)], radius=18, fill=(18, 5, 26, 250), outline=(255, 69, 113, 255), width=3)

            draw.rounded_rectangle([(bx1 + 18, by1 + 12), (bx1 + 130, by1 + 36)], radius=8, fill=(255, 69, 113, 255))
            draw.text((bx1 + 74, by1 + 24), "NO HORNY", font=font_tag, fill=(255, 255, 255, 255), anchor="mm")
            draw.text((cx, cy + 18), "DOWN BAD DETECTED", font=font_impact, fill=(0, 240, 255, 255), anchor="mm")

        else: # brand_logo
            draw.rounded_rectangle([(x1, y1), (x2, y2)], radius=20, fill=(24, 7, 36, 240), outline=(0, 240, 255, 220), width=3)
            badge_w, badge_h = min(bw + 40, 340), 110
            bx1, by1 = cx - badge_w // 2, cy - badge_h // 2
            draw.rounded_rectangle([(bx1, by1), (bx1 + badge_w, by1 + badge_h)], radius=22, fill=(20, 6, 32, 250), outline=(255, 69, 113, 255), width=3)

            draw.rounded_rectangle([(bx1 + 12, by1 + 15), (bx1 + 75, by1 + 95)], radius=12, fill=(255, 69, 113, 255))
            ecx, ecy = bx1 + 43, by1 + 55
            draw.polygon([(ecx, ecy - 20), (ecx + 16, ecy), (ecx, ecy + 20), (ecx - 16, ecy)], fill=(24, 7, 36, 255))
            draw.polygon([(ecx, ecy - 12), (ecx + 9, ecy), (ecx, ecy + 12), (ecx - 9, ecy)], fill=(0, 240, 255, 255))

            draw.text((bx1 + 90, by1 + 42), brand_name.upper(), font=font_brand, fill=(255, 255, 255, 255), anchor="lm")
            draw.text((bx1 + 92, by1 + 75), "GTA VI MEDIA", font=font_tag, fill=(0, 240, 255, 240), anchor="lm")

        canvas.save(output_png)
        return output_png, chosen

    def create_outro_cta_image(self, brand_name: str = "OUTLAW CLIPS", output_png: Optional[Path] = None) -> Path:
        """Renders the final 2.5-second call-to-action subscribe card (y=1500)."""
        if not output_png:
            output_png = Path(tempfile.gettempdir()) / f"cta_badge_{abs(hash(brand_name)) % 100000}.png"

        img = Image.new("RGBA", (1080, 1920), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)

        try:
            font_cta = ImageFont.truetype(self.arial_black_font, 32)
        except Exception:
            font_cta = ImageFont.load_default()

        clean_brand = brand_name.replace(" ", "").upper()
        cta_text = f"FOLLOW @{clean_brand} FOR MORE GTA 6"
        c_bbox = draw.textbbox((0, 0), cta_text, font=font_cta)
        cw, ch = c_bbox[2] - c_bbox[0], c_bbox[3] - c_bbox[1]
        cta_box = [(540 - cw // 2 - 24, 1500 - 12), (540 + cw // 2 + 24, 1500 + ch + 12)]
        draw.rounded_rectangle(cta_box, radius=14, fill=(10, 15, 26, 230), outline=(0, 240, 255, 180), width=2)
        draw.text((540, 1500 + ch // 2), cta_text, font=font_cta, fill=(255, 255, 255, 255), anchor="mm")

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
        brand_name: str = "OUTLAW CLIPS",
        creator_credit: Optional[str] = None,
        chat_reaction: Optional[str] = None,
        hook_text: Optional[str] = None,
        side_meme_text: Optional[str] = None,
        censor_box: Optional[Tuple[int, int, int, int]] = None,
        censor_mode: Optional[str] = None
    ) -> bool:
        """
        Slices a video window and formats it into a 9:16 (1080x1920) vertical video.
        Composites:
        1. Darkened ambient blurred 9:16 background with 3px framed gameplay
        2. Channel Brand Stamp (OUTLAW CLIPS) + Creator Attribution
        3. Optional 3-way smart censor overlay (8-Bit Mosaic / Naughty Meme / Brand Stamp)
        4. First 3-second animated attention hook (between(t, 0, 3.0))
        5. Final 2.5-second call-to-action subscribe prompt (gte(t, duration - 2.5))
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
                creator_credit=creator_credit,
                chat_reaction=chat_reaction,
                side_meme_text=side_meme_text
            )

        censor_png = None
        if censor_box or censor_mode:
            box = censor_box or (390, 800, 690, 1120)
            mode = censor_mode or "round_robin"
            censor_png, _ = self.create_smart_censor_image(
                censor_box=box,
                censor_mode=mode,
                brand_name=brand_name
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
            if censor_png:
                inputs.extend(["-i", str(censor_png)])
                filter_chain.append(f"[{curr_stream}][{curr_idx}:v]overlay=0:0[stage{curr_idx}]")
                curr_stream = f"stage{curr_idx}"
                curr_idx += 1

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

import subprocess
import shutil
import tempfile
from pathlib import Path
from typing import Optional, Tuple, List
import random
import cv2
import numpy as np
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
        self.face_model = Path(__file__).parent.parent / "models" / "face_detection_yunet_2023mar.onnx"

    def detect_streamer_facecam_info(self, video_path: str) -> Tuple[Optional[str], Optional[str]]:
        """
        Detects if a streamer facecam is active in one of the 4 corners of a 16:9 stream.
        Calculates a dynamic face-centered crop box so the creator's face has natural
        headroom and is NEVER clipped or covered by the divider banner!
        Returns (corner_name, dynamic_ffmpeg_crop_filter).
        """
        if not self.face_model.exists():
            return None, None
        cap = cv2.VideoCapture(str(video_path))
        if not cap.isOpened():
            return None, None
        w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        if w < 1000 or h < 600:
            cap.release()
            return None, None

        try:
            detector = cv2.FaceDetectorYN.create(
                model=str(self.face_model),
                config="",
                input_size=(w, h),
                score_threshold=0.45,
                nms_threshold=0.3
            )
        except Exception:
            cap.release()
            return None, None

        corner_votes = {'top_right': [], 'top_left': [], 'bottom_right': [], 'bottom_left': []}
        for sec in [1.0, 2.5, 4.0]:
            cap.set(cv2.CAP_PROP_POS_MSEC, sec * 1000)
            ret, frame = cap.read()
            if not ret:
                continue
            detector.setInputSize((w, h))
            res = detector.detect(frame)
            if res[1] is not None:
                for face in res[1]:
                    fx, fy, fw, fh = int(face[0]), int(face[1]), int(face[2]), int(face[3])
                    if fx > 0.58 * w and fy < 0.52 * h:
                        corner_votes['top_right'].append((fx, fy, fw, fh))
                    elif fx < 0.42 * w and fy < 0.52 * h:
                        corner_votes['top_left'].append((fx, fy, fw, fh))
                    elif fx > 0.58 * w and fy > 0.48 * h:
                        corner_votes['bottom_right'].append((fx, fy, fw, fh))
                    elif fx < 0.42 * w and fy > 0.48 * h:
                        corner_votes['bottom_left'].append((fx, fy, fw, fh))
        cap.release()

        best_corner, faces = max(corner_votes.items(), key=lambda x: len(x[1]))
        if len(faces) < 2:
            return None, None

        # Calculate average face centroid
        avg_cx = int(sum(f[0] + f[2] // 2 for f in faces) / len(faces))
        avg_cy = int(sum(f[1] + f[3] // 2 for f in faces) / len(faces))

        # Dynamic face-centered crop box (640x420)
        # Position face in upper 35% of the frame so it has ample headroom and 250px+ margin below!
        crop_w = min(640, w)
        crop_h = min(420, h)

        # Center horizontally on face, clamped to video bounds
        crop_x = max(0, min(w - crop_w, avg_cx - crop_w // 2))
        if best_corner in ['top_right', 'bottom_right']:
            crop_x = max(w - crop_w, crop_x)
        elif best_corner in ['top_left', 'bottom_left']:
            crop_x = min(0, crop_x)

        # Vertical: face at 35% from top of crop
        crop_y = max(0, min(h - crop_h, avg_cy - int(0.35 * crop_h)))

        crop_filter = f"crop={crop_w}:{crop_h}:{crop_x}:{crop_y}"
        return best_corner, crop_filter

    def detect_streamer_facecam(self, video_path: str) -> Optional[str]:
        """Detects if a streamer facecam is active in one of the 4 corners of a 16:9 stream."""
        corner, _ = self.detect_streamer_facecam_info(video_path)
        return corner

    def apply_dynamic_motion_censor(
        self,
        video_path: str,
        censor_mode: str = "round_robin",
        brand_name: str = "OUTLAW CLIPS",
        has_facecam: bool = False
    ) -> bool:
        """
        Dynamic Motion-Tracking Censor Compositor:
        Tracks character motion inside the gameplay window frame-by-frame,
        smooths centroid via Exponential Moving Average (alpha=0.25),
        and stamps the moving censor overlay (8-Bit Mosaic / Naughty Meme / Brand Stamp).
        Losslessly remuxes audio back into the final video.
        """
        cap = cv2.VideoCapture(str(video_path))
        if not cap.isOpened():
            return False

        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

        temp_raw = Path(video_path).parent / f"temp_cv_{Path(video_path).name}"
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        out = cv2.VideoWriter(str(temp_raw), fourcc, fps, (width, height))

        font_arial = ImageFont.truetype(self.arial_black_font, 13)
        font_impact = ImageFont.truetype(self.impact_font, 26)

        # Active gameplay window boundary (excludes facecam on top if present)
        roi_top = 612 if has_facecam else 52
        roi_bottom = 1798

        curr_cx = width // 2
        curr_cy = (roi_top + roi_bottom) // 2
        box_w, box_h = 280, 240

        # Load Outlaw Clips brand logo for the moving blur patch
        brand_logo_p = Path(__file__).parent.parent / "downloads/brand_assets/badge_outlaw_with_logo.png"
        logo_img = None
        if brand_logo_p.exists():
            try:
                raw_logo = Image.open(brand_logo_p).convert("RGBA")
                logo_w, logo_h = 240, 66
                logo_img = raw_logo.resize((logo_w, logo_h), Image.Resampling.LANCZOS)
            except Exception:
                logo_img = None

        frame_idx = 0
        while True:
            ret, frame = cap.read()
            if not ret:
                break

            # Detect motion or skin contour within gameplay region
            gameplay = frame[roi_top:roi_bottom, :]
            ycrcb = cv2.cvtColor(gameplay, cv2.COLOR_BGR2YCrCb)
            lower_skin = np.array([0, 133, 77], dtype=np.uint8)
            upper_skin = np.array([255, 173, 127], dtype=np.uint8)
            mask = cv2.inRange(ycrcb, lower_skin, upper_skin)

            # Restrict horizontal mask to avoid side pillarbox artifacts
            mask[:, :200] = 0
            mask[:, 880:] = 0

            M = cv2.moments(mask)
            if M["m00"] > 4000:
                target_cx = int(M["m10"] / M["m00"])
                target_cy = int(M["m01"] / M["m00"]) + roi_top
                curr_cx = int(0.75 * curr_cx + 0.25 * target_cx)
                curr_cy = int(0.75 * curr_cy + 0.25 * target_cy)

            # Clamp coordinates to stay within gameplay bounds
            curr_cx = max(240, min(840, curr_cx))
            curr_cy = max(roi_top + 100, min(roi_bottom - 100, curr_cy))

            x1 = curr_cx - box_w // 2
            y1 = curr_cy - box_h // 2
            x2 = curr_cx + box_w // 2
            y2 = curr_cy + box_h // 2

            # 1. Apply heavy frosted Gaussian blur over the moving NSFW ROI
            roi = frame[y1:y2, x1:x2]
            if roi.shape[0] > 0 and roi.shape[1] > 0:
                blurred = cv2.GaussianBlur(roi, (51, 51), 0)
                frame[y1:y2, x1:x2] = blurred

            # 2. Alpha-composite Outlaw Clips logo directly centered on the blur patch
            if logo_img is not None:
                pil_frame = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)).convert("RGBA")
                lx = curr_cx - 120
                ly = curr_cy - 33
                pil_frame.alpha_composite(logo_img, (lx, ly))
                frame = cv2.cvtColor(np.array(pil_frame.convert("RGB")), cv2.COLOR_RGB2BGR)

            out.write(frame)
            frame_idx += 1

        cap.release()
        out.release()

        # Losslessly mux original audio back in
        final_temp = Path(video_path).parent / f"final_{Path(video_path).name}"
        cmd = [
            self.ffmpeg_bin, "-y",
            "-i", str(temp_raw),
            "-i", str(video_path),
            "-c:v", "libx264",
            "-preset", "veryfast",
            "-crf", "22",
            "-c:a", "copy",
            "-movflags", "+faststart",
            "-map", "0:v",
            "-map", "1:a?",
            "-shortest",
            str(final_temp)
        ]
        subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        temp_raw.unlink(missing_ok=True)
        if final_temp.exists() and final_temp.stat().st_size > 1000:
            final_temp.replace(video_path)
            return True
        return False

    def round_duration(self, raw_duration: float, step: int = 5, min_sec: int = 15, max_sec: int = 60) -> int:
        """Rounds a duration up to the nearest clean 5s window."""
        rounded = int(step * round(raw_duration / step))
        if rounded < raw_duration:
            rounded += step
        return max(min_sec, min(max_sec, rounded))

    def create_text_banner_image(
        self,
        title: Optional[str] = None,
        subtitle: Optional[str] = None,
        tag_text: str = "LIVE GTA 6",
        brand_name: str = "OUTLAW CLIPS",
        creator_credit: Optional[str] = None,
        chat_reaction: Optional[str] = None,
        side_meme_text: Optional[str] = None,
        has_facecam: bool = False,
        output_png: Optional[Path] = None
    ) -> Path:
        """
        Renders the Clean Outlaw Clips Branding Overlay:
        - Leaves the creator facecam on top [0..560] and gameplay below [560..1920] 100% CLEAN and UNOBSTRUCTED.
        - Zero floating audio text overlays.
        - Renders only the discrete 'Follow Outlaw Clips' glassmorphic pill in the bottom safe area (y=1790).
        """
        if not output_png:
            output_png = Path(tempfile.gettempdir()) / f"viral_banner_{abs(hash(str(title) + brand_name)) % 100000}.png"

        img = Image.new("RGBA", (1080, 1920), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)

        # --- BOTTOM AREA BRANDING ONLY: "Follow Outlaw Clips" ---
        bot_text = "Follow Outlaw Clips"
        try:
            bot_font = ImageFont.truetype(self.arial_black_font, 20)
        except Exception:
            bot_font = ImageFont.load_default()

        bot_bbox = draw.textbbox((0, 0), bot_text, font=bot_font)
        bot_tw = bot_bbox[2] - bot_bbox[0]
        bot_th = bot_bbox[3] - bot_bbox[1]

        # Pill geometry at y=1790 (safe bottom area above mobile UI controls)
        bp_w = bot_tw + 64
        bp_h = bot_th + 24
        bp_x1 = 540 - bp_w // 2
        bp_y1 = 1790 - bp_h // 2
        bp_x2 = 540 + bp_w // 2
        bp_y2 = bp_y1 + bp_h

        # Sleek dark glass card with Outlaw neon coral outline (#FF2A6D)
        draw.rounded_rectangle([(bp_x1, bp_y1), (bp_x2, bp_y2)], radius=14, fill=(14, 8, 22, 230), outline=(255, 42, 109, 255), width=2)
        # Coral dot + Text
        dot_r = 4
        dot_cx = bp_x1 + 22
        dot_cy = (bp_y1 + bp_y2) // 2
        draw.ellipse([(dot_cx - dot_r, dot_cy - dot_r), (dot_cx + dot_r, dot_cy + dot_r)], fill=(255, 42, 109, 255))
        draw.text((540 + 8, (bp_y1 + bp_y2) // 2), bot_text, font=bot_font, fill=(255, 255, 255, 255), anchor="mm")

        img.save(output_png)
        return output_png

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

        # --- BOTTOM AREA BRANDING: "Follow Outlaw Clips" ---
        bot_text = "Follow Outlaw Clips"
        try:
            bot_font = ImageFont.truetype(self.arial_black_font, 20)
        except Exception:
            bot_font = ImageFont.load_default()

        bot_bbox = draw.textbbox((0, 0), bot_text, font=bot_font)
        bot_tw = bot_bbox[2] - bot_bbox[0]
        bot_th = bot_bbox[3] - bot_bbox[1]

        # Pill geometry at y=1790 (safe bottom area above UI controls)
        bp_w = bot_tw + 64
        bp_h = bot_th + 24
        bp_x1 = 540 - bp_w // 2
        bp_y1 = 1790 - bp_h // 2
        bp_x2 = 540 + bp_w // 2
        bp_y2 = bp_y1 + bp_h

        # Sleek dark glass card with Outlaw neon coral outline (#FF2A6D)
        draw.rounded_rectangle([(bp_x1, bp_y1), (bp_x2, bp_y2)], radius=14, fill=(14, 8, 22, 230), outline=(255, 42, 109, 255), width=2)
        # Coral dot + Text
        dot_r = 4
        dot_cx = bp_x1 + 22
        dot_cy = (bp_y1 + bp_y2) // 2
        draw.ellipse([(dot_cx - dot_r, dot_cy - dot_r), (dot_cx + dot_r, dot_cy + dot_r)], fill=(255, 42, 109, 255))
        draw.text((540 + 8, (bp_y1 + bp_y2) // 2), bot_text, font=bot_font, fill=(255, 255, 255, 255), anchor="mm")

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

        # --- BOTTOM AREA BRANDING: "Follow Outlaw Clips" ---
        bot_text = "Follow Outlaw Clips"
        try:
            bot_font = ImageFont.truetype(self.arial_black_font, 20)
        except Exception:
            bot_font = ImageFont.load_default()

        bot_bbox = draw.textbbox((0, 0), bot_text, font=bot_font)
        bot_tw = bot_bbox[2] - bot_bbox[0]
        bot_th = bot_bbox[3] - bot_bbox[1]

        # Pill geometry at y=1790 (safe bottom area above UI controls)
        bp_w = bot_tw + 64
        bp_h = bot_th + 24
        bp_x1 = 540 - bp_w // 2
        bp_y1 = 1790 - bp_h // 2
        bp_x2 = 540 + bp_w // 2
        bp_y2 = bp_y1 + bp_h

        # Sleek dark glass card with Outlaw neon coral outline (#FF2A6D)
        draw.rounded_rectangle([(bp_x1, bp_y1), (bp_x2, bp_y2)], radius=14, fill=(14, 8, 22, 230), outline=(255, 42, 109, 255), width=2)
        # Coral dot + Text
        dot_r = 4
        dot_cx = bp_x1 + 22
        dot_cy = (bp_y1 + bp_y2) // 2
        draw.ellipse([(dot_cx - dot_r, dot_cy - dot_r), (dot_cx + dot_r, dot_cy + dot_r)], fill=(255, 42, 109, 255))
        draw.text((540 + 8, (bp_y1 + bp_y2) // 2), bot_text, font=bot_font, fill=(255, 255, 255, 255), anchor="mm")

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

        # --- BOTTOM AREA BRANDING: "Follow Outlaw Clips" ---
        bot_text = "Follow Outlaw Clips"
        try:
            bot_font = ImageFont.truetype(self.arial_black_font, 20)
        except Exception:
            bot_font = ImageFont.load_default()

        bot_bbox = draw.textbbox((0, 0), bot_text, font=bot_font)
        bot_tw = bot_bbox[2] - bot_bbox[0]
        bot_th = bot_bbox[3] - bot_bbox[1]

        # Pill geometry at y=1790 (safe bottom area above UI controls)
        bp_w = bot_tw + 64
        bp_h = bot_th + 24
        bp_x1 = 540 - bp_w // 2
        bp_y1 = 1790 - bp_h // 2
        bp_x2 = 540 + bp_w // 2
        bp_y2 = bp_y1 + bp_h

        # Sleek dark glass card with Outlaw neon coral outline (#FF2A6D)
        draw.rounded_rectangle([(bp_x1, bp_y1), (bp_x2, bp_y2)], radius=14, fill=(14, 8, 22, 230), outline=(255, 42, 109, 255), width=2)
        # Coral dot + Text
        dot_r = 4
        dot_cx = bp_x1 + 22
        dot_cy = (bp_y1 + bp_y2) // 2
        draw.ellipse([(dot_cx - dot_r, dot_cy - dot_r), (dot_cx + dot_r, dot_cy + dot_r)], fill=(255, 42, 109, 255))
        draw.text((540 + 8, (bp_y1 + bp_y2) // 2), bot_text, font=bot_font, fill=(255, 255, 255, 255), anchor="mm")

        img.save(output_png)
        return output_png

    def ensure_vice_city_dual_frame(self) -> Path:
        """Ensures the Vice City Sunset gradient dual-window container overlay asset exists."""
        assets_dir = Path(__file__).parent.parent / "data/brand_assets"
        assets_dir.mkdir(parents=True, exist_ok=True)
        dual_path = assets_dir / "vice_city_dual_frame.png"

        w, h = 1080, 1920
        top_rgb = np.array([18, 16, 45], dtype=float)
        mid_rgb = np.array([180, 40, 110], dtype=float)
        bot_rgb = np.array([255, 174, 115], dtype=float)

        grad = np.zeros((h, w, 3), dtype=np.uint8)
        mid_y = int(h * 0.52)
        for y in range(mid_y):
            t = y / mid_y
            grad[y, :] = (top_rgb * (1 - t) + mid_rgb * t).astype(np.uint8)
        for y in range(mid_y, h):
            t = (y - mid_y) / (h - mid_y)
            grad[y, :] = (mid_rgb * (1 - t) + bot_rgb * t).astype(np.uint8)

        bg_img = Image.fromarray(grad).convert("RGBA")

        # Palm Fronds
        palm_overlay = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        pdraw = ImageDraw.Draw(palm_overlay)
        palm_color = (24, 12, 38, 130)
        for angle in range(-30, 45, 8):
            rad = np.radians(angle)
            xe = int(w + 50 - 380 * np.cos(rad))
            ye = int(240 + 260 * np.sin(rad))
            pdraw.line([(w, 200), (xe, ye)], fill=palm_color, width=4)
        for angle in range(-25, 40, 8):
            rad = np.radians(angle)
            xe = int(-40 + 340 * np.cos(rad))
            ye = int(1400 + 240 * np.sin(rad))
            pdraw.line([(0, 1380), (xe, ye)], fill=palm_color, width=4)
        bg_img = Image.alpha_composite(bg_img, palm_overlay)

        font_gta = ImageFont.truetype(self.arial_black_font, 22)
        font_bot = ImageFont.truetype(self.arial_black_font, 18)

        dual_frame = bg_img.copy()
        mask = Image.new("L", (w, h), 255)
        mdraw = ImageDraw.Draw(mask)
        fc_box = [(42, 52), (1038, 574)]      # Facecam window (996x522)
        gp_box = [(42, 616), (1038, 1850)]     # Gameplay window (996x1234)
        mdraw.rounded_rectangle(fc_box, radius=18, fill=0)
        mdraw.rounded_rectangle(gp_box, radius=18, fill=0)
        dual_frame.putalpha(mask)

        fdraw = ImageDraw.Draw(dual_frame)
        # Top GTA 6 badge
        b_bb = fdraw.textbbox((0, 0), "GTA 6", font=font_gta)
        bw, bh = b_bb[2] - b_bb[0], b_bb[3] - b_bb[1]
        pw, ph = bw + 40, bh + 14
        px1, py1 = 540 - pw // 2, 26 - ph // 2
        px2, py2 = 540 + pw // 2, py1 + ph
        fdraw.rounded_rectangle([(px1, py1), (px2, py2)], radius=10, fill=(20, 8, 30, 240), outline=(255, 42, 109, 255), width=2)
        fdraw.rounded_rectangle([(px1 + 2, py1 + 2), (px2 - 2, py2 - 2)], radius=8, fill=None, outline=(0, 240, 255, 140), width=1)
        fdraw.text((540, 26), "GTA 6", font=font_gta, fill=(255, 255, 255, 255), anchor="mm")

        # Window borders
        fdraw.rounded_rectangle(fc_box, radius=18, fill=None, outline=(255, 42, 109, 255), width=3)
        fdraw.rounded_rectangle([(44, 54), (1036, 572)], radius=16, fill=None, outline=(0, 240, 255, 120), width=1)
        fdraw.rounded_rectangle(gp_box, radius=18, fill=None, outline=(255, 42, 109, 255), width=3)
        fdraw.rounded_rectangle([(44, 618), (1036, 1848)], radius=16, fill=None, outline=(0, 240, 255, 120), width=1)

        # Middle divider: Follow Outlaw Clips
        fdraw.line([(100, 595), (320, 595)], fill=(255, 42, 109, 140), width=2)
        fdraw.line([(760, 595), (980, 595)], fill=(255, 42, 109, 140), width=2)
        bot_text = "Follow Outlaw Clips"
        bb = fdraw.textbbox((0, 0), bot_text, font=font_bot)
        bw, bh = bb[2] - bb[0], bb[3] - bb[1]
        pw, ph = bw + 56, bh + 18
        px1, py1 = 540 - pw // 2, 595 - ph // 2
        px2, py2 = 540 + pw // 2, py1 + ph
        fdraw.rounded_rectangle([(px1, py1), (px2, py2)], radius=12, fill=(16, 8, 26, 245), outline=(255, 42, 109, 255), width=2)
        fdraw.ellipse([(px1 + 16, 595 - 4), (px1 + 24, 595 + 4)], fill=(255, 42, 109, 255))
        fdraw.text((546, 595), bot_text, font=font_bot, fill=(255, 255, 255, 255), anchor="mm")

        dual_frame.save(dual_path)
        return dual_path

    def ensure_vice_city_single_frame(self) -> Path:
        """Ensures the Vice City Sunset gradient single-window container overlay asset exists."""
        assets_dir = Path(__file__).parent.parent / "data/brand_assets"
        assets_dir.mkdir(parents=True, exist_ok=True)
        single_path = assets_dir / "vice_city_single_frame.png"

        w, h = 1080, 1920
        top_rgb = np.array([18, 16, 45], dtype=float)
        mid_rgb = np.array([180, 40, 110], dtype=float)
        bot_rgb = np.array([255, 174, 115], dtype=float)

        grad = np.zeros((h, w, 3), dtype=np.uint8)
        mid_y = int(h * 0.52)
        for y in range(mid_y):
            t = y / mid_y
            grad[y, :] = (top_rgb * (1 - t) + mid_rgb * t).astype(np.uint8)
        for y in range(mid_y, h):
            t = (y - mid_y) / (h - mid_y)
            grad[y, :] = (mid_rgb * (1 - t) + bot_rgb * t).astype(np.uint8)

        bg_img = Image.fromarray(grad).convert("RGBA")

        # Palm Fronds
        palm_overlay = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        pdraw = ImageDraw.Draw(palm_overlay)
        palm_color = (24, 12, 38, 130)
        for angle in range(-30, 45, 8):
            rad = np.radians(angle)
            xe = int(w + 50 - 380 * np.cos(rad))
            ye = int(240 + 260 * np.sin(rad))
            pdraw.line([(w, 200), (xe, ye)], fill=palm_color, width=4)
        for angle in range(-25, 40, 8):
            rad = np.radians(angle)
            xe = int(-40 + 340 * np.cos(rad))
            ye = int(1400 + 240 * np.sin(rad))
            pdraw.line([(0, 1380), (xe, ye)], fill=palm_color, width=4)
        bg_img = Image.alpha_composite(bg_img, palm_overlay)

        font_gta = ImageFont.truetype(self.arial_black_font, 22)
        font_bot = ImageFont.truetype(self.arial_black_font, 18)

        single_frame = bg_img.copy()
        smask = Image.new("L", (w, h), 255)
        smdraw = ImageDraw.Draw(smask)
        single_box = [(42, 52), (1038, 1720)]   # Gameplay window (996x1668)
        smdraw.rounded_rectangle(single_box, radius=18, fill=0)
        single_frame.putalpha(smask)

        sfdraw = ImageDraw.Draw(single_frame)
        # Top GTA 6 badge
        b_bb = sfdraw.textbbox((0, 0), "GTA 6", font=font_gta)
        bw, bh = b_bb[2] - b_bb[0], b_bb[3] - b_bb[1]
        pw, ph = bw + 40, bh + 14
        px1, py1 = 540 - pw // 2, 26 - ph // 2
        px2, py2 = 540 + pw // 2, py1 + ph
        sfdraw.rounded_rectangle([(px1, py1), (px2, py2)], radius=10, fill=(20, 8, 30, 240), outline=(255, 42, 109, 255), width=2)
        sfdraw.rounded_rectangle([(px1 + 2, py1 + 2), (px2 - 2, py2 - 2)], radius=8, fill=None, outline=(0, 240, 255, 140), width=1)
        sfdraw.text((540, 26), "GTA 6", font=font_gta, fill=(255, 255, 255, 255), anchor="mm")

        sfdraw.rounded_rectangle(single_box, radius=18, fill=None, outline=(255, 42, 109, 255), width=3)
        sfdraw.rounded_rectangle([(44, 54), (1036, 1718)], radius=16, fill=None, outline=(0, 240, 255, 120), width=1)

        # Bottom Follow Pill: at y=1770 (Safe visible bottom area, not very bottom!)
        bot_text = "Follow Outlaw Clips"
        bb = sfdraw.textbbox((0, 0), bot_text, font=font_bot)
        bw, bh = bb[2] - bb[0], bb[3] - bb[1]
        pw, ph = bw + 56, bh + 18
        px1, py1 = 540 - pw // 2, 1770 - ph // 2
        px2, py2 = 540 + pw // 2, py1 + ph
        sfdraw.rounded_rectangle([(px1, py1), (px2, py2)], radius=12, fill=(16, 8, 26, 245), outline=(255, 42, 109, 255), width=2)
        sfdraw.ellipse([(px1 + 16, 1770 - 4), (px1 + 24, 1770 + 4)], fill=(255, 42, 109, 255))
        sfdraw.text((546, 1770), bot_text, font=font_bot, fill=(255, 255, 255, 255), anchor="mm")

        single_frame.save(single_path)
        return single_path

    def slice_clip(
        self,
        input_path: str,
        start_sec: float,
        duration_sec: float,
        output_path: str,
        style: str = "split_screen",
        facecam_corner: Optional[str] = "auto",
        overlay_text: Optional[str] = None,
        overlay_subtitle: Optional[str] = None,
        tag_text: str = "🔥 GTA SHOWCASE",
        brand_name: str = "OUTLAW CLIPS",
        creator_credit: Optional[str] = None,
        chat_reaction: Optional[str] = None,
        hook_text: Optional[str] = None,
        side_meme_text: Optional[str] = None,
        censor_box: Optional[Tuple[int, int, int, int]] = None,
        censor_mode: Optional[str] = None,
        dynamic_censor: bool = True
    ) -> bool:
        """
        Slices a video window and formats it into a 9:16 (1080x1920) vertical video.
        Composites:
        1. Creator Facecam on Top (560px) + Full Gameplay taking the entire vertical space below (1360px)
           (If no facecam detected, gameplay cropped to fill entire 1080x1920 canvas)
        2. Channel Brand Stamp (OUTLAW CLIPS) + Creator Attribution
        3. Dynamic Motion-Tracking Censor (8-Bit Mosaic / Naughty Meme / Brand Stamp)
        4. First 3-second animated attention hook (between(t, 0, 3.0))
        5. Final 2.5-second call-to-action subscribe prompt (gte(t, duration - 2.5))
        """
        start_sec = max(0.0, start_sec)
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)

        corner = None
        dynamic_crop = None
        if style in ["split_screen", "vice_city_container"]:
            if facecam_corner == "auto":
                corner, dynamic_crop = self.detect_streamer_facecam_info(input_path)
            elif facecam_corner in ["top_left", "top_right", "bottom_left", "bottom_right"]:
                corner = facecam_corner

        censor_png = None
        if (censor_box or censor_mode) and not dynamic_censor:
            box = censor_box or (390, 800, 690, 1120)
            mode = censor_mode or "round_robin"
            censor_png, _ = self.create_smart_censor_image(
                censor_box=box,
                censor_mode=mode,
                brand_name=brand_name
            )

        inputs = ["-i", input_path]

        if style in ["split_screen", "vice_city_container"]:
            if corner:
                dual_frame = self.ensure_vice_city_dual_frame()
                inputs.extend(["-i", str(dual_frame)])
                frame_idx = (len(inputs) // 2) - 1
                fc_crop = dynamic_crop or "crop=640:420:1280:0"
                filter_chain = [
                    f"[0:v]{fc_crop},scale=996:522[fc]",
                    "[0:v]crop=ih*(996/1234):ih:(iw-ow)/2:0,scale=996:1234[gp]",
                    f"color=s=1080x1920:c=black:r=30:d={duration_sec}[base]",
                    "[base][fc]overlay=42:52[s1]",
                    "[s1][gp]overlay=42:616[s2]",
                    f"[s2][{frame_idx}:v]overlay=0:0[stage0]"
                ]
            else:
                single_frame = self.ensure_vice_city_single_frame()
                inputs.extend(["-i", str(single_frame)])
                frame_idx = (len(inputs) // 2) - 1
                filter_chain = [
                    "[0:v]crop=ih*(996/1668):ih:(iw-ow)/2:0,scale=996:1668[gp]",
                    f"color=s=1080x1920:c=black:r=30:d={duration_sec}[base]",
                    "[base][gp]overlay=42:52[s1]",
                    f"[s1][{frame_idx}:v]overlay=0:0[stage0]"
                ]
        elif style == "blur_bg":
            filter_chain = [
                "[0:v]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,boxblur=30:5,eq=brightness=-0.30:contrast=1.15[bg]",
                "[0:v]scale=1080:608,drawbox=x=0:y=0:w=1080:h=3:color=white@0.5:t=fill,drawbox=x=0:y=605:w=1080:h=3:color=white@0.5:t=fill[fg]",
                "[bg][fg]overlay=(W-w)/2:(H-h)/2[stage0]"
            ]
        else: # direct 9:16 crop
            filter_chain = [
                "[0:v]crop=ih*(9/16):ih:(iw-ow)/2:0,scale=1080:1920[stage0]"
            ]

        curr_stream = "stage0"
        curr_idx = len(inputs)
        if censor_png:
            inputs.extend(["-i", str(censor_png)])
            filter_chain.append(f"[{curr_stream}][{curr_idx}:v]overlay=0:0[stage{curr_idx}]")
            curr_stream = f"stage{curr_idx}"
            curr_idx += 1

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
            "-movflags", "+faststart",
            "-avoid_negative_ts", "make_zero",
            "-async", "1",
            output_path
        ]

        res = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        success = res.returncode == 0 and Path(output_path).exists()
        if success and censor_mode and dynamic_censor:
            self.apply_dynamic_motion_censor(
                video_path=output_path,
                censor_mode=censor_mode,
                brand_name=brand_name,
                has_facecam=bool(corner)
            )

        return success

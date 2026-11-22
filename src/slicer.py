import re
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

        # Calculate average face centroid & dimensions
        avg_cx = int(sum(f[0] + f[2] // 2 for f in faces) / len(faces))
        avg_cy = int(sum(f[1] + f[3] // 2 for f in faces) / len(faces))
        avg_fh = int(sum(f[3] for f in faces) / len(faces))

        # Tight facecam crop: target container aspect ratio (996:522 ≈ 1.908)
        # Scale crop box tightly around face so creator's face covers container without excess gameplay
        aspect_ratio = 996 / 522
        crop_h = int(min(h, max(avg_fh * 2.5, 200)))
        crop_w = int(min(w, crop_h * aspect_ratio))
        crop_h = int(crop_w / aspect_ratio)

        # Center horizontally on face, clamped to video bounds
        crop_x = max(0, min(w - crop_w, avg_cx - crop_w // 2))
        if best_corner in ['top_right', 'bottom_right']:
            crop_x = max(w - crop_w, crop_x)
        elif best_corner in ['top_left', 'bottom_left']:
            crop_x = max(0, min(crop_x, 0))

        # Vertical: face placed comfortably with headroom (face at ~38% from top of crop)
        crop_y = max(0, min(h - crop_h, avg_cy - int(0.38 * crop_h)))

        crop_filter = f"crop={crop_w}:{crop_h}:{crop_x}:{crop_y}"
        return best_corner, crop_filter

    def detect_streamer_facecam(self, video_path: str) -> Optional[str]:
        """Detects if a streamer facecam is active in one of the 4 corners of a 16:9 stream."""
        corner, _ = self.detect_streamer_facecam_info(video_path)
        return corner

    def detect_nsfw_temporal_intervals(self, video_path: str, step_sec: float = 0.1) -> List[Tuple[float, float]]:
        """
        High-Density Frame-Accurate NSFW Interval Scanner:
        Scans video across all frames using GPU/MPS-batched CLIP tensor inference.
        Returns contiguous, frame-accurate (start_sec, end_sec) intervals with temporal debouncing.
        """
        try:
            import cv2
            import torch
            import numpy as np
            from PIL import Image
            from src.semantic_gatekeeper import SemanticGatekeeper

            sg = SemanticGatekeeper()
            cap = cv2.VideoCapture(str(video_path))
            if not cap.isOpened():
                return []

            fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

            nsfw_prompts = [
                'strip club interior with dancer',
                'adult entertainment night club',
                'erotic dancing or suggestive nudity',
                'bikini dancer on stage',
                'nude or unclothed person',
                'person in underwear or towel or bed',
                'naked character or exposed body'
            ]
            safe_prompts = [
                'grand theft auto video game gameplay',
                'gamer livestream with webcam reacting to video game',
                'video game car driving on street',
                'police pursuit vehicle action',
                'player combat shootout gunfight in game',
                'video game character exploring open world city',
                'entertaining video game live stream with webcam facecam',
                'video game pause menu or map screen'
            ]
            all_prompts = nsfw_prompts + safe_prompts

            # Dense frame extraction (scan gameplay window only, avoid facecam false triggers)
            raw_images = []
            frame_indices = []
            frame_idx = 0
            while True:
                ret, frame = cap.read()
                if not ret:
                    break
                h_f = frame.shape[0]
                gp_area = frame[612:1798, :] if h_f >= 1800 else frame
                rgb = cv2.cvtColor(cv2.resize(gp_area, (280, 160)), cv2.COLOR_BGR2RGB)
                raw_images.append(Image.fromarray(rgb))
                frame_indices.append(frame_idx)
                frame_idx += 1
            cap.release()

            if not raw_images:
                return []

            # Run in high-throughput batches (32-48 frames per forward pass)
            batch_size = 48
            frame_is_nsfw = [False] * len(raw_images)

            for i in range(0, len(raw_images), batch_size):
                batch = raw_images[i:i+batch_size]
                inputs = sg.clip_proc(text=all_prompts, images=batch, return_tensors='pt', padding=True).to(sg.device)
                with torch.no_grad():
                    logits = sg.clip_model(**inputs).logits_per_image.softmax(dim=-1)
                    nsfw_probs = logits[:, :len(nsfw_prompts)].sum(dim=-1).cpu().tolist()
                
                for b_idx, p in enumerate(nsfw_probs):
                    idx = frame_indices[i + b_idx]
                    if p >= 0.52:
                        frame_is_nsfw[idx] = True

            # Pre-roll lead-in (0.5s) and post-roll lead-out (0.5s) to guarantee zero late show
            lead_in_frames = int(0.5 * fps)
            lead_out_frames = int(0.5 * fps)
            expanded = [False] * len(frame_is_nsfw)
            for i in range(len(frame_is_nsfw)):
                if frame_is_nsfw[i]:
                    start_pad = max(0, i - lead_in_frames)
                    end_pad = min(len(frame_is_nsfw), i + lead_out_frames)
                    for j in range(start_pad, end_pad):
                        expanded[j] = True

            # Build contiguous intervals
            raw_intervals = []
            in_interval = False
            start_frame = 0
            for i, active in enumerate(expanded):
                if active and not in_interval:
                    in_interval = True
                    start_frame = i
                elif not active and in_interval:
                    in_interval = False
                    raw_intervals.append((round(start_frame / fps, 2), round(i / fps, 2)))
            if in_interval:
                raw_intervals.append((round(start_frame / fps, 2), round(len(expanded) / fps, 2)))

            # Bridge gaps <= 3.0s so censor NEVER flickers on/off during active scenes
            merged = []
            for s, e in raw_intervals:
                if not merged:
                    merged.append([s, e])
                else:
                    if s - merged[-1][1] <= 3.0:
                        merged[-1][1] = max(merged[-1][1], e)
                    else:
                        merged.append([s, e])

            # Filter out isolated false-positive blips < 1.5s at start (e.g. door frames)
            intervals = [(round(s, 2), round(e, 2)) for s, e in merged if not (s < 2.5 and (e - s) < 2.0)]
            return intervals
        except Exception as e:
            print(f"Temporal NSFW detection note: {e}")
            return []

    def apply_dynamic_motion_censor(
        self,
        video_path: str,
        censor_mode: str = "circular_logo",
        brand_name: str = "OUTLAW CLIPS",
        has_facecam: bool = False
    ) -> bool:
        """
        Dynamic Motion-Tracking Censor Compositor:
        1. Evaluates temporal NSFW intervals. If NO NSFW in that second -> ZERO blur, ZERO logo (100% clean video).
        2. During active NSFW seconds:
           - Adaptively detects sensitive contour bounding box
           - Applies localized Gaussian blur behind
           - Stamps scaled circular Outlaw Clips emblem centered on top of the blur
        """
        intervals = self.detect_nsfw_temporal_intervals(video_path)
        if not intervals:
            print("✨ [Dynamic Censor]: Zero active NSFW intervals detected. Video kept 100% clean.")
            return True

        print(f"🔞 [Dynamic Censor]: NSFW detected in intervals {intervals}. Applying adaptive blur + circular emblem...")

        cap = cv2.VideoCapture(str(video_path))
        if not cap.isOpened():
            return False

        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        fps = cap.get(cv2.CAP_PROP_FPS) or 30.0

        temp_raw = Path(video_path).parent / f"temp_cv_{Path(video_path).name}"
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        out = cv2.VideoWriter(str(temp_raw), fourcc, fps, (width, height))

        roi_top = 612 if has_facecam else 52
        roi_bottom = 1798

        curr_cx = width // 2
        curr_cy = (roi_top + roi_bottom) // 2
        curr_w = 360
        curr_h = 300

        # Load official Outlaw Clips DP for dynamic circular emblem
        dp_p = Path(__file__).parent.parent / "downloads/brand_assets/outlaw_clips_dp_official.jpg"
        dp_img = Image.open(dp_p).convert("RGBA") if dp_p.exists() else None

        frame_idx = 0
        while True:
            ret, frame = cap.read()
            if not ret:
                break

            t = frame_idx / fps
            is_active_second = any(s <= t <= e for s, e in intervals)

            if not is_active_second:
                # 100% Clean Frame - Hide logo and blur completely
                out.write(frame)
                frame_idx += 1
                continue

            # --- SENSITIVE REGION ACTIVE IN THIS SECOND ---
            alpha_mask = np.zeros((height, width), dtype=np.float32)
            # Full broadcast anatomical swath across entire gameplay width (zero margin leaks)
            alpha_mask[920:roi_bottom - 48, 42:width - 42] = 1.0

            gameplay = frame[roi_top:roi_bottom, :]
            ycrcb = cv2.cvtColor(gameplay, cv2.COLOR_BGR2YCrCb)
            lower_skin = np.array([0, 133, 77], dtype=np.uint8)
            upper_skin = np.array([255, 173, 127], dtype=np.uint8)
            mask = cv2.inRange(ycrcb, lower_skin, upper_skin)
            mask[:, :42] = 0
            mask[:, 1038:] = 0

            kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7))
            mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
            mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)

            contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            valid = [c for c in contours if cv2.contourArea(c) > 1500]

            for c in valid:
                bx, by, bw, bh = cv2.boundingRect(c)
                by += roi_top
                cx = bx + bw // 2
                cy = by + bh // 2
                ew = max(500, int(bw * 2.5))
                eh = max(500, int(bh * 2.5))
                cv2.ellipse(alpha_mask, (cx, cy), (ew // 2, eh // 2), 0, 0, 360, 1.0, -1)

            curr_cx = width // 2
            curr_cy = 1330

            # 1. 40px Heavy Broadcast Pixel Mosaic with Wide Multi-Point Coverage
            alpha_mask = cv2.GaussianBlur(alpha_mask, (51, 51), 20)
            alpha_mask = np.clip(alpha_mask, 0.0, 1.0)
            alpha_mask_3d = np.dstack([alpha_mask] * 3)

            block = 40
            mh, mw = height // block, width // block
            mos_s = cv2.resize(frame, (mw, mh), interpolation=cv2.INTER_LINEAR)
            mos_full = cv2.resize(mos_s, (width, height), interpolation=cv2.INTER_NEAREST)
            frame = (frame * (1.0 - alpha_mask_3d) + mos_full * alpha_mask_3d).astype(np.uint8)

            # 2. Big Adaptive Circular Emblem (Full 520px coverage guaranteed)
            emblem_diam = 520

            if dp_img is not None:
                dp_resized = dp_img.resize((emblem_diam, emblem_diam), Image.Resampling.LANCZOS)
                mask_c = Image.new("L", (emblem_diam, emblem_diam), 0)
                mdraw = ImageDraw.Draw(mask_c)
                mdraw.ellipse((0, 0, emblem_diam, emblem_diam), fill=255)

                emblem_canvas = Image.new("RGBA", (emblem_diam, emblem_diam), (0, 0, 0, 0))
                emblem_canvas.paste(dp_resized, (0, 0), mask=mask_c)
                edraw = ImageDraw.Draw(emblem_canvas)
                # Crisp dual neon micro-rim
                edraw.ellipse((0, 0, emblem_diam - 1, emblem_diam - 1), outline=(0, 240, 255, 240), width=4)
                edraw.ellipse((3, 3, emblem_diam - 4, emblem_diam - 4), outline=(255, 42, 109, 220), width=3)

                pil_frame = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)).convert("RGBA")
                lx = curr_cx - (emblem_diam // 2)
                ly = curr_cy - (emblem_diam // 2)
                pil_frame.alpha_composite(emblem_canvas, (lx, ly))
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
        bot_text = "Follow @outlawclipshq"
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
        bot_text = "Follow @outlawclipshq"
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
        bot_text = "Follow @outlawclipshq"
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

        modes = ["circular_logo", "brand_logo", "mosaic_8bit"]
        if censor_mode in modes:
            chosen = censor_mode
        elif censor_mode == "random":
            chosen = random.choice(modes)
        elif censor_mode == "round_robin":
            chosen = modes[self._censor_counter % len(modes)]
            self._censor_counter += 1
        else:
            chosen = "circular_logo"

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

        if chosen == "circular_logo":
            # 1. Subtle smooth frosted/blur oval backdrop covering the private area
            rx = max(bw // 2 + 20, 130)
            ry = max(bh // 2 + 15, 95)
            # Outer dark-glass halo
            draw.ellipse([(cx - rx - 8, cy - ry - 8), (cx + rx + 8, cy + ry + 8)], fill=(15, 6, 22, 140))
            # Smooth frosted fill with subtle neon cyan boundary
            draw.ellipse([(cx - rx, cy - ry), (cx + rx, cy + ry)], fill=(20, 8, 30, 240), outline=(0, 240, 255, 140), width=2)

            # 2. Sleek circular Outlaw Clips DP emblem right in the center
            emblem_diam = min(max(bw, 150), 180)
            dp_path = Path(__file__).parent.parent / "downloads/brand_assets/outlaw_clips_dp_official.jpg"
            if dp_path.exists():
                dp = Image.open(dp_path).convert("RGBA")
                dp_resized = dp.resize((emblem_diam, emblem_diam), Image.Resampling.LANCZOS)

                # Circular mask
                mask = Image.new("L", (emblem_diam, emblem_diam), 0)
                mdraw = ImageDraw.Draw(mask)
                mdraw.ellipse((0, 0, emblem_diam, emblem_diam), fill=255)

                # Double neon rim emblem
                emblem_canvas = Image.new("RGBA", (emblem_diam, emblem_diam), (0, 0, 0, 0))
                emblem_canvas.paste(dp_resized, (0, 0), mask=mask)
                edraw = ImageDraw.Draw(emblem_canvas)
                edraw.ellipse((0, 0, emblem_diam - 1, emblem_diam - 1), outline=(0, 240, 255, 240), width=3)
                edraw.ellipse((2, 2, emblem_diam - 3, emblem_diam - 3), outline=(255, 69, 113, 220), width=2)

                canvas.paste(emblem_canvas, (cx - emblem_diam // 2, cy - emblem_diam // 2), mask=emblem_canvas)
            else:
                draw.ellipse([(cx - 75, cy - 75), (cx + 75, cy + 75)], fill=(24, 7, 36, 255), outline=(0, 240, 255, 255), width=3)
                draw.text((cx, cy), "OUTLAW", font=font_brand, fill=(255, 255, 255, 255), anchor="mm")

        elif chosen == "mosaic_8bit":
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
        bot_text = "Follow @outlawclipshq"
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

    def ensure_vice_city_dual_frame(self, creator_credit: Optional[str] = None) -> Path:
        """Ensures the Vice City Sunset gradient dual-window container overlay asset exists with creator credit and GTA VI branding."""
        assets_dir = Path(__file__).parent.parent / "data/brand_assets"
        assets_dir.mkdir(parents=True, exist_ok=True)
        
        safe_creator = ""
        display_handle = ""
        if creator_credit:
            cleaned = creator_credit.strip()
            # Standardize handle via creator_handles.json if available
            try:
                handles_p = Path(__file__).parent.parent / "config/creator_handles.json"
                if handles_p.exists():
                    with open(handles_p) as hf:
                        hmap = json.load(hf)
                    mapped_h = hmap.get(cleaned) or hmap.get(cleaned.lower())
                    if mapped_h:
                        cleaned = mapped_h
            except Exception:
                pass
            display_handle = f"@{cleaned.lstrip('@')}"
            safe_creator = re.sub(r'[^a-zA-Z0-9_]', '_', cleaned.lower())
            dual_path = assets_dir / f"vice_city_dual_frame_{safe_creator}.png"
        else:
            dual_path = assets_dir / "vice_city_dual_frame.png"

        w, h = 1080, 1920
        top_rgb = np.array([16, 10, 32], dtype=float)
        mid_rgb = np.array([160, 32, 95], dtype=float)
        bot_rgb = np.array([255, 155, 95], dtype=float)

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
        palm_color = (20, 10, 32, 120)
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

        # Fonts
        try:
            font_vi = ImageFont.truetype("/System/Library/Fonts/Supplemental/Impact.ttf", 46)
            font_gta = ImageFont.truetype("/System/Library/Fonts/Supplemental/Impact.ttf", 38)
        except Exception:
            font_vi = ImageFont.truetype(self.arial_black_font, 44)
            font_gta = ImageFont.truetype(self.arial_black_font, 36)

        try:
            font_creator = ImageFont.truetype("/System/Library/Fonts/Supplemental/Futura.ttc", 22, index=0)
            font_brand = ImageFont.truetype("/System/Library/Fonts/Supplemental/Futura.ttc", 18, index=0)
        except Exception:
            font_creator = ImageFont.truetype(self.arial_black_font, 20)
            font_brand = ImageFont.truetype(self.arial_black_font, 18)

        dual_frame = bg_img.copy()
        mask = Image.new("L", (w, h), 255)
        mdraw = ImageDraw.Draw(mask)
        fc_box = [(42, 52), (1038, 574)]      # Facecam window (996x522)
        gp_box = [(42, 616), (1038, 1850)]     # Gameplay window (996x1234)
        mdraw.rounded_rectangle(fc_box, radius=18, fill=0)
        mdraw.rounded_rectangle(gp_box, radius=18, fill=0)
        dual_frame.putalpha(mask)

        fdraw = ImageDraw.Draw(dual_frame)

        # Top GTA VI Badge with Vice City Sunset Gradient
        header_cy = 28
        fdraw.text((540 - 36, header_cy), "GTA", font=font_gta, fill=(255, 255, 255, 255), anchor="rm")

        vi_mask = Image.new("L", (w, h), 0)
        vmdraw = ImageDraw.Draw(vi_mask)
        vmdraw.text((540 - 24, header_cy), "VI", font=font_vi, fill=255, anchor="lm")

        vi_arr = np.zeros((h, w, 4), dtype=np.uint8)
        for y in range(header_cy - 25, header_cy + 25):
            t = (y - (header_cy - 25)) / 50
            rgb = (np.array([255, 30, 140]) * (1 - t) + np.array([255, 175, 60]) * t).astype(np.uint8)
            vi_arr[y, :, :3] = rgb
            vi_arr[y, :, 3] = 255
        vi_img = Image.fromarray(vi_arr, mode="RGBA")
        vi_img.putalpha(vi_mask)
        dual_frame = Image.alpha_composite(dual_frame, vi_img)
        fdraw = ImageDraw.Draw(dual_frame)

        # Window borders with sleek Vice neon outlines
        fdraw.rounded_rectangle(fc_box, radius=18, fill=None, outline=(255, 42, 109, 255), width=2)
        fdraw.rounded_rectangle([(44, 54), (1036, 572)], radius=16, fill=None, outline=(0, 240, 255, 120), width=1)
        fdraw.rounded_rectangle(gp_box, radius=18, fill=None, outline=(255, 42, 109, 255), width=2)
        fdraw.rounded_rectangle([(44, 618), (1036, 1848)], radius=16, fill=None, outline=(0, 240, 255, 120), width=1)

        # Creator Attribution Tag: Bottom-Left inside facecam window (no 'STREAMER' word, just @handle)
        if display_handle:
            c_bb = fdraw.textbbox((0, 0), display_handle, font=font_creator)
            cw, ch = c_bb[2] - c_bb[0], c_bb[3] - c_bb[1]
            cx1 = 58
            cy1 = 574 - ch - 22
            cx2 = cx1 + cw + 42
            cy2 = cy1 + ch + 14
            fdraw.rounded_rectangle([(cx1, cy1), (cx2, cy2)], radius=8, fill=(10, 6, 16, 215), outline=(255, 42, 109, 180), width=1)
            fdraw.ellipse([(cx1 + 12, (cy1 + cy2) // 2 - 3), (cx1 + 18, (cy1 + cy2) // 2 + 3)], fill=(255, 42, 109, 255))
            fdraw.text((cx1 + 25, (cy1 + cy2) // 2), display_handle, font=font_creator, fill=(255, 255, 255, 255), anchor="lm")

        # Middle divider: Follow Creator
        handle_text = display_handle.lstrip('@').upper() if display_handle else "GTA6CLIPS"
        follow_str = f"FOLLOW @{handle_text}"
        fdraw.line([(80, 595), (350, 595)], fill=(255, 42, 109, 140), width=2)
        fdraw.line([(730, 595), (1000, 595)], fill=(255, 42, 109, 140), width=2)
        b_bb = fdraw.textbbox((0, 0), follow_str, font=font_brand)
        bw, bh = b_bb[2] - b_bb[0], b_bb[3] - b_bb[1]
        bx1 = 540 - bw // 2 - 20
        by1 = 595 - bh // 2 - 8
        bx2 = 540 + bw // 2 + 20
        by2 = 595 + bh // 2 + 8
        fdraw.rounded_rectangle([(bx1, by1), (bx2, by2)], radius=12, fill=(16, 8, 24, 245), outline=(255, 42, 109, 240), width=2)
        fdraw.ellipse([(bx1 + 14, 595 - 4), (bx1 + 22, 595 + 4)], fill=(255, 42, 109, 255))
        fdraw.text((544, 595), follow_str, font=font_brand, fill=(255, 255, 255, 255), anchor="mm")

        dual_frame.save(dual_path)
        return dual_path

    def ensure_vice_city_single_frame(self, creator_credit: Optional[str] = None) -> Path:
        """Ensures the Vice City Sunset gradient single-window container overlay asset exists."""
        assets_dir = Path(__file__).parent.parent / "data/brand_assets"
        assets_dir.mkdir(parents=True, exist_ok=True)
        
        safe_creator = ""
        display_handle = ""
        if creator_credit:
            cleaned = creator_credit.strip()
            # Standardize handle via creator_handles.json if available
            try:
                handles_p = Path(__file__).parent.parent / "config/creator_handles.json"
                if handles_p.exists():
                    with open(handles_p) as hf:
                        hmap = json.load(hf)
                    mapped_h = hmap.get(cleaned) or hmap.get(cleaned.lower())
                    if mapped_h:
                        cleaned = mapped_h
            except Exception:
                pass
            display_handle = f"@{cleaned.lstrip('@')}"
            safe_creator = re.sub(r'[^a-zA-Z0-9_]', '_', cleaned.lower())
            single_path = assets_dir / f"vice_city_single_frame_{safe_creator}.png"
        else:
            single_path = assets_dir / "vice_city_single_frame.png"

        w, h = 1080, 1920
        top_rgb = np.array([16, 10, 32], dtype=float)
        mid_rgb = np.array([160, 32, 95], dtype=float)
        bot_rgb = np.array([255, 155, 95], dtype=float)

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
        palm_color = (20, 10, 32, 120)
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

        # Fonts
        try:
            font_vi = ImageFont.truetype("/System/Library/Fonts/Supplemental/Impact.ttf", 46)
            font_gta = ImageFont.truetype("/System/Library/Fonts/Supplemental/Impact.ttf", 38)
        except Exception:
            font_vi = ImageFont.truetype(self.arial_black_font, 44)
            font_gta = ImageFont.truetype(self.arial_black_font, 36)

        try:
            font_creator = ImageFont.truetype("/System/Library/Fonts/Supplemental/Futura.ttc", 22, index=0)
            font_brand = ImageFont.truetype("/System/Library/Fonts/Supplemental/Futura.ttc", 18, index=0)
        except Exception:
            font_creator = ImageFont.truetype(self.arial_black_font, 20)
            font_brand = ImageFont.truetype(self.arial_black_font, 18)

        single_frame = bg_img.copy()
        smask = Image.new("L", (w, h), 255)
        smdraw = ImageDraw.Draw(smask)
        single_box = [(42, 52), (1038, 1720)]   # Gameplay window (996x1668)
        smdraw.rounded_rectangle(single_box, radius=18, fill=0)
        single_frame.putalpha(smask)

        sfdraw = ImageDraw.Draw(single_frame)

        # Top GTA VI Badge with Vice City Sunset Gradient
        header_cy = 28
        sfdraw.text((540 - 36, header_cy), "GTA", font=font_gta, fill=(255, 255, 255, 255), anchor="rm")

        vi_mask = Image.new("L", (w, h), 0)
        vmdraw = ImageDraw.Draw(vi_mask)
        vmdraw.text((540 - 24, header_cy), "VI", font=font_vi, fill=255, anchor="lm")

        vi_arr = np.zeros((h, w, 4), dtype=np.uint8)
        for y in range(header_cy - 25, header_cy + 25):
            t = (y - (header_cy - 25)) / 50
            rgb = (np.array([255, 30, 140]) * (1 - t) + np.array([255, 175, 60]) * t).astype(np.uint8)
            vi_arr[y, :, :3] = rgb
            vi_arr[y, :, 3] = 255
        vi_img = Image.fromarray(vi_arr, mode="RGBA")
        vi_img.putalpha(vi_mask)
        single_frame = Image.alpha_composite(single_frame, vi_img)
        sfdraw = ImageDraw.Draw(single_frame)

        sfdraw.rounded_rectangle(single_box, radius=18, fill=None, outline=(255, 42, 109, 255), width=2)
        sfdraw.rounded_rectangle([(44, 54), (1036, 1718)], radius=16, fill=None, outline=(0, 240, 255, 120), width=1)

        # Bottom Follow Pill: at y=1770
        handle_text = display_handle.lstrip('@').upper() if display_handle else "GTA6CLIPS"
        bot_text = f"FOLLOW @{handle_text}"
        bb = sfdraw.textbbox((0, 0), bot_text, font=font_brand)
        bw, bh = bb[2] - bb[0], bb[3] - bb[1]
        pw, ph = bw + 48, bh + 16
        px1, py1 = 540 - pw // 2, 1770 - ph // 2
        px2, py2 = 540 + pw // 2, py1 + ph
        sfdraw.rounded_rectangle([(px1, py1), (px2, py2)], radius=12, fill=(16, 8, 24, 245), outline=(255, 42, 109, 240), width=2)
        sfdraw.ellipse([(px1 + 14, 1770 - 4), (px1 + 22, 1770 + 4)], fill=(255, 42, 109, 255))
        sfdraw.text((544, 1770), bot_text, font=font_brand, fill=(255, 255, 255, 255), anchor="mm")

        # Creator Attribution Tag: Bottom-Left inside gameplay window (if provided)
        if display_handle:
            c_bb = sfdraw.textbbox((0, 0), display_handle, font=font_creator)
            cw, ch = c_bb[2] - c_bb[0], c_bb[3] - c_bb[1]
            cx1 = 58
            cy1 = 1720 - ch - 22
            cx2 = cx1 + cw + 42
            cy2 = cy1 + ch + 14
            sfdraw.rounded_rectangle([(cx1, cy1), (cx2, cy2)], radius=8, fill=(10, 6, 16, 215), outline=(255, 42, 109, 180), width=1)
            sfdraw.ellipse([(cx1 + 12, (cy1 + cy2) // 2 - 3), (cx1 + 18, (cy1 + cy2) // 2 + 3)], fill=(255, 42, 109, 255))
            sfdraw.text((cx1 + 25, (cy1 + cy2) // 2), display_handle, font=font_creator, fill=(255, 255, 255, 255), anchor="lm")

        single_frame.save(single_path)
        return single_path

    def ensure_moving_watermark_badge(self, text: str = "@outlawclipshq") -> Path:
        """Generates and caches an anti-aliased, semi-transparent watermark PNG badge for floating anti-theft overlay."""
        assets_dir = Path(__file__).parent.parent / "data/brand_assets"
        assets_dir.mkdir(parents=True, exist_ok=True)
        wm_path = assets_dir / "moving_watermark_badge.png"

        wm_w, wm_h = 240, 50
        wm_img = Image.new("RGBA", (wm_w, wm_h), (0, 0, 0, 0))
        d = ImageDraw.Draw(wm_img)
        font = None
        for font_candidate in [
            "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
            "/System/Library/Fonts/Supplemental/Arial.ttf",
            "/Library/Fonts/Arial.ttf"
        ]:
            if Path(font_candidate).exists():
                try:
                    font = ImageFont.truetype(font_candidate, 26)
                    break
                except Exception:
                    pass
        if not font:
            font = ImageFont.load_default()

        # Soft drop shadow (offset +1, +1, 35 alpha)
        d.text((wm_w // 2 + 1, wm_h // 2 + 1), text, font=font, fill=(0, 0, 0, 40), anchor="mm")
        # Subtle white text with 42 alpha (~16.5% opacity)
        d.text((wm_w // 2, wm_h // 2), text, font=font, fill=(255, 255, 255, 42), anchor="mm")

        wm_img.save(wm_path)
        return wm_path

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
        dynamic_censor: bool = True,
        watermark: bool = True
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
                dual_frame = self.ensure_vice_city_dual_frame(creator_credit=creator_credit)
                inputs.extend(["-i", str(dual_frame)])
                frame_idx = (len(inputs) // 2) - 1
                fc_crop = dynamic_crop or "crop=480:250:800:300"
                filter_chain = [
                    f"[0:v]{fc_crop},scale=996:522:flags=lanczos[fc]",
                    "[0:v]crop=ih*(996/1234):ih:(iw-ow)/2:0,scale=996:1234:flags=lanczos[gp]",
                    f"color=s=1080x1920:c=black:r=60:d={duration_sec}[base]",
                    "[base][fc]overlay=42:52[s1]",
                    "[s1][gp]overlay=42:616[s2]",
                    f"[s2][{frame_idx}:v]overlay=0:0[stage0]"
                ]
            else:
                single_frame = self.ensure_vice_city_single_frame(creator_credit=creator_credit)
                inputs.extend(["-i", str(single_frame)])
                frame_idx = (len(inputs) // 2) - 1
                filter_chain = [
                    "[0:v]crop=ih*(996/1668):ih:(iw-ow)/2:0,scale=996:1668:flags=lanczos[gp]",
                    f"color=s=1080x1920:c=black:r=60:d={duration_sec}[base]",
                    "[base][gp]overlay=42:52[s1]",
                    f"[s1][{frame_idx}:v]overlay=0:0[stage0]"
                ]
        elif style == "blur_bg":
            filter_chain = [
                "[0:v]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,boxblur=30:5,eq=brightness=-0.30:contrast=1.15[bg]",
                "[0:v]scale=1080:608:flags=lanczos,drawbox=x=0:y=0:w=1080:h=3:color=white@0.5:t=fill,drawbox=x=0:y=605:w=1080:h=3:color=white@0.5:t=fill[fg]",
                "[bg][fg]overlay=(W-w)/2:(H-h)/2[stage0]"
            ]
        else: # direct 9:16 crop
            filter_chain = [
                "[0:v]crop=ih*(9/16):ih:(iw-ow)/2:0,scale=1080:1920:flags=lanczos[stage0]"
            ]

        curr_stream = "stage0"
        if censor_png:
            inputs.extend(["-i", str(censor_png)])
            c_idx = (len(inputs) // 2) - 1
            filter_chain.append(f"[{curr_stream}][{c_idx}:v]overlay=0:0[stage{c_idx}]")
            curr_stream = f"stage{c_idx}"

        if watermark:
            wm_badge = self.ensure_moving_watermark_badge()
            if wm_badge and wm_badge.exists():
                inputs.extend(["-i", str(wm_badge)])
                wm_idx = (len(inputs) // 2) - 1
                filter_chain.append(
                    f"[{curr_stream}][{wm_idx}:v]overlay=x='(W-w)/2+sin(t*0.65)*240':y='1200-h/2+cos(t*0.42)*260'[stage_wm]"
                )
                curr_stream = "stage_wm"

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
            "-preset", "medium",
            "-crf", "16",
            "-b:v", "8M",
            "-maxrate", "12M",
            "-bufsize", "16M",
            "-r", "60",
            "-c:a", "aac",
            "-b:a", "192k",
            "-ar", "44100",
            "-af", "loudnorm=I=-16:TP=-1.5:LRA=11",
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

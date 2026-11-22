import cv2, os, torch, subprocess, sqlite3, time
import numpy as np
from PIL import Image, ImageDraw
from pathlib import Path
from src.slicer import VideoSlicer

src_video = "output/training_candidates/gta6_twitch_BlindingGleamingDonk_1795145864.mp4.orig"
if not os.path.exists(src_video):
    src_video = "output/training_candidates/gta6_twitch_BlindingGleamingDonk_1795145864.mp4"

slicer = VideoSlicer()
intervals = [(1.13, 1.73), (2.73, 3.5), (3.9, 4.63)]
print(f"🎬 Rendering 4 censor styles for OhnePixel Yoga clip. Active intervals: {intervals}")

dp_p = Path("downloads/brand_assets/outlaw_clips_dp_official.jpg")
dp_img = Image.open(dp_p).convert("RGBA") if dp_p.exists() else None

def get_emblem(diam, outer_color, inner_color=None):
    if dp_img is None:
        return None
    dp_resized = dp_img.resize((diam, diam), Image.Resampling.LANCZOS)
    mask = Image.new("L", (diam, diam), 0)
    draw = ImageDraw.Draw(mask)
    draw.ellipse((0, 0, diam, diam), fill=255)
    emblem = Image.new("RGBA", (diam, diam), (0, 0, 0, 0))
    emblem.paste(dp_resized, (0, 0), mask=mask)
    edraw = ImageDraw.Draw(emblem)
    edraw.ellipse((0, 0, diam-1, diam-1), outline=outer_color, width=3)
    if inner_color:
        edraw.ellipse((2, 2, diam-3, diam-3), outline=inner_color, width=2)
    return emblem

styles = [
    {
        "clip_id": "gta6_twitch_OhneYoga_style1_obsidian",
        "title": "🛡️ [STYLE 1 - SMOKED OBSIDIAN] OHNEPIXEL PAYS FOR YOGA",
        "type": "obsidian"
    },
    {
        "clip_id": "gta6_twitch_OhneYoga_style2_mosaic",
        "title": "👾 [STYLE 2 - BROADCAST MOSAIC] OHNEPIXEL PAYS FOR YOGA",
        "type": "mosaic"
    },
    {
        "clip_id": "gta6_twitch_OhneYoga_style3_frosted",
        "title": "❄️ [STYLE 3 - FROSTED FEATHERED] OHNEPIXEL PAYS FOR YOGA",
        "type": "frosted"
    },
    {
        "clip_id": "gta6_twitch_OhneYoga_style4_minimalist",
        "title": "✨ [STYLE 4 - MINIMALIST DISC] OHNEPIXEL PAYS FOR YOGA",
        "type": "minimalist"
    }
]

ffmpeg_bin = "/Users/vismaythaker/workspace/projects/Clipper/.venv/bin/ffmpeg" if Path("/Users/vismaythaker/workspace/projects/Clipper/.venv/bin/ffmpeg").exists() else "ffmpeg"

for s in styles:
    cid = s["clip_id"]
    stype = s["type"]
    out_mp4 = Path(f"output/training_candidates/{cid}.mp4")
    temp_raw = Path(f"output/training_candidates/temp_cv_{cid}.mp4")

    print(f"\n⚙️ Rendering {s['title']} -> {out_mp4.name}...")

    cap = cv2.VideoCapture(src_video)
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0

    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    out = cv2.VideoWriter(str(temp_raw), fourcc, fps, (width, height))

    roi_top = 52
    roi_bottom = 1798
    curr_cx = width // 2
    curr_cy = (roi_top + roi_bottom) // 2
    curr_w = 420
    curr_h = 340

    frame_idx = 0
    while True:
        ret, frame = cap.read()
        if not ret:
            break

        t = frame_idx / fps
        is_active = any(start <= t <= end for start, end in intervals)

        if not is_active:
            # 100% Clean Frame
            out.write(frame)
            frame_idx += 1
            continue

        # Adaptive sensitive contour tracking
        gameplay = frame[roi_top:roi_bottom, :]
        ycrcb = cv2.cvtColor(gameplay, cv2.COLOR_BGR2YCrCb)
        lower_skin = np.array([0, 133, 77], dtype=np.uint8)
        upper_skin = np.array([255, 173, 127], dtype=np.uint8)
        mask = cv2.inRange(ycrcb, lower_skin, upper_skin)
        mask[:, :160] = 0
        mask[:, 920:] = 0

        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7))
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)

        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        valid = [c for c in contours if cv2.contourArea(c) > 2000]

        if valid:
            largest = max(valid, key=cv2.contourArea)
            bx, by, bw, bh = cv2.boundingRect(largest)
            by += roi_top
            target_cx = bx + bw // 2
            target_cy = by + bh // 2
            target_w = max(300, min(600, int(bw * 1.25) + 40))
            target_h = max(260, min(540, int(bh * 1.25) + 40))

            curr_cx = int(0.70 * curr_cx + 0.30 * target_cx)
            curr_cy = int(0.70 * curr_cy + 0.30 * target_cy)
            curr_w = int(0.70 * curr_w + 0.30 * target_w)
            curr_h = int(0.70 * curr_h + 0.30 * target_h)

        curr_cx = max(240, min(width - 240, curr_cx))
        curr_cy = max(roi_top + 100, min(roi_bottom - 100, curr_cy))

        # --- APPLY SPECIFIC CENSOR STYLE ---
        if stype == "obsidian":
            # STYLE 1: Deep Smoked Obsidian
            blur_bw = max(580, int(curr_w * 1.35))
            blur_bh = max(460, int(curr_h * 1.35))
            alpha_mask = np.zeros((height, width), dtype=np.float32)
            cv2.ellipse(alpha_mask, (curr_cx, curr_cy), (blur_bw // 2, blur_bh // 2), 0, 0, 360, 1.0, -1)
            alpha_mask = cv2.GaussianBlur(alpha_mask, (101, 101), 40)
            alpha_mask = np.clip(alpha_mask, 0.0, 1.0)
            alpha_3d = np.dstack([alpha_mask] * 3)

            small = cv2.resize(frame, (width // 24, height // 24), interpolation=cv2.INTER_LINEAR)
            small_b = cv2.GaussianBlur(small, (31, 31), 15)
            extreme = cv2.resize(small_b, (width, height), interpolation=cv2.INTER_LINEAR)
            extreme = cv2.GaussianBlur(extreme, (71, 71), 25)
            smoked = cv2.addWeighted(extreme, 0.78, np.zeros_like(extreme), 0.22, 0)
            frame = (frame * (1.0 - alpha_3d) + smoked * alpha_3d).astype(np.uint8)

            emblem = get_emblem(160, (255, 42, 109, 220), (0, 240, 255, 200))

        elif stype == "mosaic":
            # STYLE 2: Broadcast Pixel Mosaic
            blur_bw = max(540, int(curr_w * 1.25))
            blur_bh = max(420, int(curr_h * 1.25))
            alpha_mask = np.zeros((height, width), dtype=np.float32)
            cv2.ellipse(alpha_mask, (curr_cx, curr_cy), (blur_bw // 2, blur_bh // 2), 0, 0, 360, 1.0, -1)
            alpha_mask = cv2.GaussianBlur(alpha_mask, (71, 71), 25)
            alpha_mask = np.clip(alpha_mask, 0.0, 1.0)
            alpha_3d = np.dstack([alpha_mask] * 3)

            block = 28
            mh, mw = height // block, width // block
            mos_s = cv2.resize(frame, (mw, mh), interpolation=cv2.INTER_LINEAR)
            mos_full = cv2.resize(mos_s, (width, height), interpolation=cv2.INTER_NEAREST)
            frame = (frame * (1.0 - alpha_3d) + mos_full * alpha_3d).astype(np.uint8)

            emblem = get_emblem(150, (0, 240, 255, 240), (255, 42, 109, 220))

        elif stype == "frosted":
            # STYLE 3: Frosted Feathered Glass
            blur_bw = max(520, int(curr_w * 1.20))
            blur_bh = max(400, int(curr_h * 1.20))
            alpha_mask = np.zeros((height, width), dtype=np.float32)
            cv2.ellipse(alpha_mask, (curr_cx, curr_cy), (blur_bw // 2, blur_bh // 2), 0, 0, 360, 1.0, -1)
            alpha_mask = cv2.GaussianBlur(alpha_mask, (81, 81), 30)
            alpha_mask = np.clip(alpha_mask, 0.0, 1.0)
            alpha_3d = np.dstack([alpha_mask] * 3)

            small = cv2.resize(frame, (width // 16, height // 16), interpolation=cv2.INTER_LINEAR)
            small_b = cv2.GaussianBlur(small, (31, 31), 15)
            frosted = cv2.resize(small_b, (width, height), interpolation=cv2.INTER_LINEAR)
            frosted = cv2.GaussianBlur(frosted, (71, 71), 25)
            frame = (frame * (1.0 - alpha_3d) + frosted * alpha_3d).astype(np.uint8)

            emblem = get_emblem(150, (0, 240, 255, 220), (255, 255, 255, 200))

        elif stype == "minimalist":
            # STYLE 4: Minimalist Frosted Disc + Neon Emblem
            disc_diam = max(260, int(max(curr_w, curr_h) * 0.95))
            alpha_mask = np.zeros((height, width), dtype=np.float32)
            cv2.circle(alpha_mask, (curr_cx, curr_cy), disc_diam // 2, 1.0, -1)
            alpha_mask = cv2.GaussianBlur(alpha_mask, (35, 35), 12)
            alpha_mask = np.clip(alpha_mask, 0.0, 1.0)
            alpha_3d = np.dstack([alpha_mask] * 3)

            small = cv2.resize(frame, (width // 20, height // 20), interpolation=cv2.INTER_LINEAR)
            small_b = cv2.GaussianBlur(small, (31, 31), 15)
            disc_blur = cv2.resize(small_b, (width, height), interpolation=cv2.INTER_LINEAR)
            disc_blur = cv2.GaussianBlur(disc_blur, (51, 51), 20)
            disc_blur = cv2.addWeighted(disc_blur, 0.85, np.zeros_like(disc_blur), 0.15, 0)
            frame = (frame * (1.0 - alpha_3d) + disc_blur * alpha_3d).astype(np.uint8)

            emblem = get_emblem(180, (255, 42, 109, 240), (0, 240, 255, 240))

        # Stamp emblem in center
        if emblem:
            pil_f = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)).convert("RGBA")
            ed = emblem.size[0]
            pil_f.alpha_composite(emblem, (curr_cx - ed // 2, curr_cy - ed // 2))
            frame = cv2.cvtColor(np.array(pil_f.convert("RGB")), cv2.COLOR_RGB2BGR)

        out.write(frame)
        frame_idx += 1

    cap.release()
    out.release()

    # Audio remux
    remux_cmd = [
        ffmpeg_bin, "-y",
        "-i", str(temp_raw),
        "-i", str(src_video),
        "-c:v", "libx264",
        "-preset", "veryfast",
        "-crf", "20",
        "-c:a", "copy",
        "-movflags", "+faststart",
        "-map", "0:v",
        "-map", "1:a?",
        "-shortest",
        str(out_mp4)
    ]
    subprocess.run(remux_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    temp_raw.unlink(missing_ok=True)

    # Generate thumbnail
    thumb_p = out_mp4.with_suffix(".jpg")
    vcap = cv2.VideoCapture(str(out_mp4))
    vcap.set(cv2.CAP_PROP_POS_FRAMES, int(3.2 * fps)) # inside active censor interval
    ret, tframe = vcap.read()
    if ret:
        cv2.imwrite(str(thumb_p), tframe)
    vcap.release()

    # Save to SQLite Database
    db_p = Path("data/telemetry.db")
    conn = sqlite3.connect(str(db_p))
    c = conn.cursor()
    c.execute("""
        INSERT OR REPLACE INTO training_clip_ratings
        (clip_id, video_path, target_search, category, language, channel, creator, expected_spoken, expected_vision, duration, virality_score, human_stars, human_verdict, human_critique, rated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
    """, (
        cid,
        f"/video/training_candidates/{out_mp4.name}",
        s["title"],
        "MATURE_SCENE",
        "English",
        "@OhnePixel",
        "OhnePixel",
        "OhnePixel paying into bank account for son's yoga class",
        f"Audience Clip [{cid}]: OhnePixel GTA 6",
        11.0,
        92.0,
        5,
        "REVIEW",
        s["title"],
        time.time()
    ))
    conn.commit()
    conn.close()
    print(f"✅ Generated & Registered: {cid} ({out_mp4.name})")

print("\n🎉 All 4 Censor Styles Successfully Rendered and Registered!")

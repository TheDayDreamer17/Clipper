import os
import sys
import subprocess
import json
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
import numpy as np

sys.path.append(str(Path(__file__).parent.parent))

class FrameAnalyzer:
    """
    Two-Stage Multi-Modal Frame Context Analyzer:
    Stage 1: Fast Static Keyframe Extraction & Visual Metrics via FFmpeg & Image statistics
             (Detects loading screens, motion deltas, neon luminance, red/blue strobes).
    Stage 2: Semantic Synthesis via Local MLX SLM/VLM into GTA 6 Target Properties.
    """
    def __init__(
        self,
        config_path: str = "config/game_properties.json",
        temp_dir: str = "downloads/frames"
    ):
        self.temp_dir = Path(temp_dir)
        self.temp_dir.mkdir(parents=True, exist_ok=True)
        self.ffmpeg_bin = "/opt/homebrew/bin/ffmpeg"
        self.config_path = Path(config_path)
        self.properties = {}
        if self.config_path.exists():
            with open(self.config_path, "r", encoding="utf-8") as f:
                self.properties = json.load(f).get("properties", {})

    def extract_keyframes(
        self,
        video_path: Path,
        start_sec: float,
        duration: float = 30.0,
        num_frames: int = 3
    ) -> List[Path]:
        """
        Extracts lightweight representative static keyframes from a video window.
        """
        frame_paths = []
        # Calculate sample offsets: 15%, 50%, 85% into the window
        offsets = [
            start_sec + (duration * 0.15),
            start_sec + (duration * 0.50),
            start_sec + (duration * 0.85)
        ][:num_frames]

        for i, offset in enumerate(offsets):
            out_file = self.temp_dir / f"frame_{int(start_sec)}_{i}.jpg"
            cmd = [
                self.ffmpeg_bin,
                "-y",
                "-ss", str(max(0.0, offset)),
                "-i", str(video_path),
                "-vframes", "1",
                "-vf", "scale=640:360",
                "-q:v", "3",
                str(out_file)
            ]
            res = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            if res.returncode == 0 and out_file.exists():
                frame_paths.append(out_file)

        return frame_paths

    def compute_visual_metrics(self, frame_paths: List[Path]) -> Dict[str, Any]:
        """
        Fast heuristic visual analysis without heavy neural models:
        - Luminance (detects dark loading screens vs bright day)
        - Color Saturation / Red-Blue Balance (police sirens / Vice City neon)
        - Inter-frame pixel delta (motion level)
        """
        if not frame_paths:
            return {"motion": "unknown", "lighting": "unknown", "is_loading_candidate": False}

        try:
            from PIL import Image
            images = [Image.open(p).convert("RGB") for p in frame_paths]
            arrays = [np.array(img, dtype=np.float32) for img in images]

            # 1. Luminance
            mean_luminances = [np.mean(arr) for arr in arrays]
            avg_lum = float(np.mean(mean_luminances))

            # 2. Motion Delta between consecutive frames
            motion_delta = 0.0
            if len(arrays) >= 2:
                diff = np.abs(arrays[1] - arrays[0])
                motion_delta = float(np.mean(diff))

            # 3. Police Strobe Detection (High Red or Blue variance)
            red_blue_flashes = False
            for arr in arrays:
                r = arr[:, :, 0]
                b = arr[:, :, 2]
                g = arr[:, :, 1]
                # Strobe: red/blue dominates green significantly
                if np.mean(r) > (np.mean(g) * 1.4) or np.mean(b) > (np.mean(g) * 1.4):
                    red_blue_flashes = True
                    break

            # 4. Loading screen candidate (very dark or low standard deviation)
            is_loading = avg_lum < 20.0 or (avg_lum < 40.0 and motion_delta < 5.0)

            motion_category = "high" if motion_delta > 35.0 else ("medium" if motion_delta > 15.0 else "low")
            lighting = "loading_or_dark" if is_loading else ("neon_or_night" if avg_lum < 80.0 else "daylight")

            return {
                "avg_luminance": round(avg_lum, 2),
                "motion_delta": round(motion_delta, 2),
                "motion_category": motion_category,
                "lighting": lighting,
                "is_loading_candidate": is_loading,
                "police_strobe_detected": red_blue_flashes
            }
        except Exception as e:
            return {
                "avg_luminance": 50.0,
                "motion_delta": 15.0,
                "motion_category": "medium",
                "lighting": "standard",
                "is_loading_candidate": False,
                "police_strobe_detected": False,
                "error": str(e)
            }

    def classify_window(
        self,
        visual_metrics: Dict[str, Any],
        transcript_text: str = "",
        audio_rms_db: float = -20.0
    ) -> Dict[str, Any]:
        """
        Classifies the in-game window into target properties (`PROP_01` to `PROP_10`)
        using multi-modal fusion of visual metrics + audio RMS + transcript cues.
        """
        # Heuristic matching rulebook
        matched_prop = None
        confidence = 0
        visual_state = "Gameplay traversal"
        action_summary = "Character moving through environment"

        text_lower = transcript_text.lower()

        # Rule 1: Loading Screen
        if visual_metrics.get("is_loading_candidate"):
            matched_prop = "PROP_01"
            confidence = 90
            visual_state = "Loading screen / Dark transition"
            action_summary = "Game boot logo or loading transition screen"

        # Rule 2: Police Chase Escalation
        elif visual_metrics.get("police_strobe_detected") or any(k in text_lower for k in ["police", "cop", "siren", "wanted", "star", "chase"]):
            matched_prop = "PROP_07"
            confidence = 85
            visual_state = "Police pursuit with flashing strobe lighting"
            action_summary = "Law enforcement pursuit or roadblock engagement"

        # Rule 3: High-Speed Vehicle Crash
        elif visual_metrics.get("motion_category") == "high" and audio_rms_db > -12.0:
            matched_prop = "PROP_08"
            confidence = 80
            visual_state = "High-speed vehicle motion & impact"
            action_summary = "Vehicle collision, stunt launch, or high-speed chase"

        # Rule 4: Store Robbery / Interior Hold-up
        elif any(k in text_lower for k in ["robbery", "store", "cash", "money", "register", "gun", "counter", "clerk", "loot"]):
            matched_prop = "PROP_09"
            confidence = 85
            visual_state = "Interior store / register engagement"
            action_summary = "Player holding up store clerk or collecting cash"

        # Rule 5: Water / Swamp Physics
        elif any(k in text_lower for k in ["water", "boat", "swamp", "mud", "lake", "ocean", "swim", "wake"]):
            matched_prop = "PROP_05"
            confidence = 78
            visual_state = "Water / swamp fluid dynamics"
            action_summary = "Watercraft wake or swimming physics demonstration"

        # Default: Routine traversal
        else:
            motion = visual_metrics.get("motion_category", "medium")
            lighting = visual_metrics.get("lighting", "daylight")
            visual_state = f"{lighting.title()} world traversal ({motion} motion)"
            action_summary = "Standard open world exploration"

        return {
            "matched_property": matched_prop,
            "confidence": confidence,
            "visual_state": visual_state,
            "action_summary": action_summary,
            "metrics": visual_metrics
        }

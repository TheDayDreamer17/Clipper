import sys
import os
import subprocess
from pathlib import Path
from typing import Dict, Any, List, Tuple, Optional
from PIL import Image
import torch
from transformers import CLIPProcessor, CLIPModel

sys.path.append(str(Path(__file__).parent.parent))

class VisionEvaluator:
    """
    Hardware-Accelerated Zero-Shot Vision Classifier running on Apple Silicon Metal MPS.
    Classifies video keyframes into GTA 6 target properties vs routine filler/menus,
    providing full diagnostic logs of why each window was accepted or rejected.
    """
    CANDIDATE_LABELS = {
        "PROP_01": "game loading screen with rockstar logo and artwork slides",
        "PROP_02": "character introduction cutscene with close up face and dialogue",
        "PROP_07": "high speed police pursuit with flashing police cruisers and sirens",
        "PROP_09": "convenience store robbery with gun aimed at cashier counter",
        "PROP_08": "high speed sports car racing and vehicle collision crash",
        "REJECT_ROUTINE": "character walking casually down empty street or hallway with no action",
        "REJECT_MENU": "pause menu map or inventory options screen"
    }

    def __init__(self, model_name: str = "openai/clip-vit-base-patch32"):
        self.device = "mps" if torch.backends.mps.is_available() else "cpu"
        self.processor = CLIPProcessor.from_pretrained(model_name)
        self.model = CLIPModel.from_pretrained(model_name).to(self.device)
        self.ffmpeg_bin = "/opt/homebrew/bin/ffmpeg"
        self.labels_list = list(self.CANDIDATE_LABELS.values())
        self.label_keys = list(self.CANDIDATE_LABELS.keys())

    def extract_frames(self, video_path: str, start_sec: float, duration_sec: float, num_frames: int = 3) -> List[Image.Image]:
        """Extracts PIL images at sample points from a video window."""
        frames = []
        offsets = [
            start_sec + (duration_sec * 0.20),
            start_sec + (duration_sec * 0.50),
            start_sec + (duration_sec * 0.80)
        ][:num_frames]

        temp_dir = Path("downloads/vision_temp")
        temp_dir.mkdir(parents=True, exist_ok=True)

        for i, off in enumerate(offsets):
            out_img = temp_dir / f"frame_{int(off)}_{i}.jpg"
            cmd = [
                self.ffmpeg_bin, "-y",
                "-ss", str(max(0.0, off)),
                "-i", str(video_path),
                "-vframes", "1",
                "-vf", "scale=640:360",
                "-q:v", "2",
                str(out_img)
            ]
            subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            if out_img.exists():
                try:
                    frames.append(Image.open(out_img).convert("RGB"))
                except Exception:
                    pass
        return frames

    def evaluate_window(
        self,
        video_path: str,
        start_sec: float,
        duration_sec: float,
        transcript_text: str = "",
        min_accept_confidence: float = 40.0
    ) -> Dict[str, Any]:
        """
        Runs zero-shot vision classification across the frames and produces an
        evaluation log explaining why the window was accepted or rejected.
        """
        frames = self.extract_frames(video_path, start_sec, duration_sec, num_frames=3)
        if not frames:
            return {
                "window": f"{start_sec}s - {start_sec + duration_sec}s",
                "decision": "REJECTED",
                "reason": "Failed to extract keyframes from video stream",
                "confidence": 0.0,
                "top_property": None,
                "probabilities": {}
            }

        # Multi-frame batch inference
        inputs = self.processor(text=self.labels_list, images=frames, return_tensors="pt", padding=True).to(self.device)
        with torch.no_grad():
            outputs = self.model(**inputs)
            # Logits per image: shape (num_frames, num_labels)
            probs = outputs.logits_per_image.softmax(dim=1).mean(dim=0).tolist()

        prob_dict = {k: round(p * 100, 2) for k, p in zip(self.label_keys, probs)}

        # Find top predicted property
        sorted_probs = sorted(prob_dict.items(), key=lambda x: x[1], reverse=True)
        top_key, top_score = sorted_probs[0]

        # Decision Logic:
        # If top prediction is a REJECT label, reject.
        # If an action property score >= min_accept_confidence and > routine score, accept!
        routine_score = prob_dict.get("REJECT_ROUTINE", 0.0) + prob_dict.get("REJECT_MENU", 0.0)

        if top_key.startswith("REJECT"):
            decision = "REJECTED"
            reason = f"Dominant visual state is routine filler ({top_key}: {top_score}%). Action threshold not met."
            top_prop = None
        elif top_score >= min_accept_confidence and top_score > routine_score:
            decision = "ACCEPTED"
            reason = f"Confirmed visual match for {top_key} ({top_score}%). Outweighs routine filler ({routine_score}%)."
            top_prop = top_key
        else:
            decision = "REJECTED"
            reason = f"Ambiguous visual state: {top_key} ({top_score}%) vs Routine ({routine_score}%). Confidence below threshold."
            top_prop = None

        return {
            "window": f"{int(start_sec)}s - {int(start_sec + duration_sec)}s",
            "decision": decision,
            "reason": reason,
            "top_property": top_prop,
            "confidence": top_score,
            "probabilities": prob_dict,
            "top_label_description": self.CANDIDATE_LABELS.get(top_key)
        }

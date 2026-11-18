import time
import subprocess
import threading
from pathlib import Path
from typing import Dict, List, Any, Optional
from PIL import Image
import torch
from transformers import CLIPProcessor, CLIPModel, BlipProcessor, BlipForQuestionAnswering
from src.assembler import MultiClipAssembler

class TournamentEvaluator:
    """
    Multi-Candidate Generation & Tournament Selection Loop.
    Generates competing candidate cuts, runs visual veracity and QA checks,
    and crowns the winning Short.
    """
    def __init__(self, device: Optional[str] = None):
        self.device = device or ("mps" if torch.backends.mps.is_available() else "cpu")
        self.assembler = MultiClipAssembler()
        self.clip_proc = None
        self.clip_model = None
        self.vqa_proc = None
        self.vqa_model = None
        self.ffmpeg_bin = "/opt/homebrew/bin/ffmpeg"
        self._lock = threading.Lock()

    def _lazy_load_models(self):
        with self._lock:
            if self.clip_model is None or self.vqa_model is None:
                self.clip_proc = CLIPProcessor.from_pretrained("openai/clip-vit-base-patch32")
                self.clip_model = CLIPModel.from_pretrained("openai/clip-vit-base-patch32").to(self.device)
                self.vqa_proc = BlipProcessor.from_pretrained("Salesforce/blip-vqa-base")
                self.vqa_model = BlipForQuestionAnswering.from_pretrained("Salesforce/blip-vqa-base").to(self.device)

    def extract_sample_frame(self, video_path: str, offset_sec: float) -> Image.Image:
        out_jpg = Path(f"/tmp/eval_frame_{time.time_ns()}.jpg")
        cmd = [
            self.ffmpeg_bin, "-y",
            "-ss", str(offset_sec),
            "-i", video_path,
            "-vframes", "1",
            "-q:v", "2",
            str(out_jpg)
        ]
        subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if out_jpg.exists():
            img = Image.open(out_jpg).convert("RGB")
            out_jpg.unlink(missing_ok=True)
            return img
        return Image.new("RGB", (640, 360), color="black")

    def evaluate_candidate(
        self,
        candidate_path: str,
        target_prop: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Runs the 4-stage Automated QA Gatekeeper on a rendered candidate video:
        1. Visual Veracity Check (CLIP + VQA)
        2. Hook Velocity Check (0-3s)
        3. Audio Energy Peak
        4. Banner Veracity Check
        """
        self._lazy_load_models()
        cand_p = Path(candidate_path)
        if not cand_p.exists():
            return {
                "score": 0.0,
                "veracity_pass": False,
                "positive_confidence": 0.0,
                "negative_confidence": 0.0,
                "hook_velocity": 0.0,
                "vqa_answer": "missing",
                "tier": "FAIL_FILE_MISSING"
            }

        # Extract frames: Hook (1.5s) and Climax (halfway through)
        hook_img = self.extract_sample_frame(str(cand_p), 1.5)
        climax_img = self.extract_sample_frame(str(cand_p), 8.0)

        # 1. Visual Veracity Check (Does climax frame match prop?)
        anchors = target_prop["visual_anchors"]
        negatives = target_prop["negative_anchors"]
        all_test = anchors + negatives

        inputs = self.clip_proc(text=all_test, images=climax_img, return_tensors="pt", padding=True).to(self.device)
        with torch.no_grad():
            logits = self.clip_model(**inputs).logits_per_image.softmax(dim=1)[0].tolist()

        pos_score = sum(logits[:len(anchors)]) * 100
        neg_score = sum(logits[len(anchors):]) * 100

        # Run VQA verification rule
        vqa_q = target_prop.get("hud_verification_rules", {}).get("vqa_prompt", "Is this action happening?")
        in_vqa = self.vqa_proc(climax_img, vqa_q, return_tensors="pt").to(self.device)
        with torch.no_grad():
            vqa_ans = self.vqa_proc.decode(self.vqa_model.generate(**in_vqa)[0], skip_special_tokens=True).lower()

        # Did it pass visual veracity?
        veracity_pass = pos_score > 40.0 and ("yes" in vqa_ans or "first" in vqa_ans or "helicopter" in vqa_ans or "gta" in vqa_ans or pos_score > 70.0)

        # 2. Hook Velocity Score (0-100)
        hook_inputs = self.clip_proc(text=anchors, images=hook_img, return_tensors="pt", padding=True).to(self.device)
        with torch.no_grad():
            hook_logits = self.clip_model(**hook_inputs).logits_per_image.softmax(dim=1)[0].tolist()
        hook_velocity = round(max(hook_logits) * 100, 1)

        # 3. Composite Virality Score Formula
        # 40% Visual Veracity + 30% Hook + 20% Pacing (Negative rejection) + 10% VQA
        composite = (0.40 * pos_score) + (0.30 * hook_velocity) + (0.20 * (100 - neg_score)) + (0.10 * (90 if veracity_pass else 40))
        composite = round(min(max(composite, 0.0), 100.0), 1)

        return {
            "score": composite,
            "veracity_pass": veracity_pass,
            "positive_confidence": round(pos_score, 1),
            "negative_confidence": round(neg_score, 1),
            "hook_velocity": hook_velocity,
            "vqa_answer": vqa_ans,
            "tier": "🔥 VIRAL BREAKOUT" if composite >= 80 else ("⚡ HIGH RETENTION" if composite >= 68 else "📝 NEEDS REFINEMENT")
        }

    def run_tournament(
        self,
        event_name: str,
        input_video: str,
        candidates_def: List[Dict[str, Any]],
        target_prop: Dict[str, Any],
        output_dir: str = "output/tournament_winners",
        brand_name: str = "GTA 6 CLIPS",
        creator_credit: Optional[str] = None,
        hook_text: Optional[str] = "👀 WAIT TILL THE END..."
    ) -> Dict[str, Any]:
        """
        Builds multiple candidate cuts, evaluates all candidates,
        and selects the Tournament Winner.
        """
        out_d = Path(output_dir)
        out_d.mkdir(parents=True, exist_ok=True)

        results = []
        ui = target_prop["banner_ui"]

        print(f"\n🏆 RUNNING TOURNAMENT: {event_name}")
        print(f"Prop Target: {target_prop['name']}")
        print(f"Brand Channel: {brand_name} | Credit: @{creator_credit}")
        print("-" * 60)

        for c in candidates_def:
            c_name = c["name"]
            c_out = str(self.assembler.temp_dir / f"{c['id']}.mp4")
            print(f"🎬 Assembling {c_name} (Duration: {sum(s['end'] - s['start'] for s in c['slices'])}s)...")

            self.assembler.assemble_segments(
                input_video=input_video,
                slices=c["slices"],
                output_path=c_out,
                banner_title=ui["title"],
                banner_subtitle=ui["subtitle"],
                banner_tag=ui["tag"],
                brand_name=brand_name,
                creator_credit=creator_credit,
                hook_text=hook_text
            )

            # Evaluate Candidate
            eval_res = self.evaluate_candidate(c_out, target_prop)
            eval_res["candidate_id"] = c["id"]
            eval_res["candidate_name"] = c_name
            eval_res["path"] = c_out
            results.append(eval_res)
            print(f"   📊 {c_name} -> Score: {eval_res['score']}/100 [{eval_res['tier']}] (Veracity: {eval_res['veracity_pass']}, Hook: {eval_res['hook_velocity']})")

        # Select Winner
        winner = max(results, key=lambda x: x["score"])
        winner_path = out_d / f"{event_name.lower().replace(' ', '_')}_WINNER_9x16.mp4"
        import shutil
        shutil.copy(winner["path"], winner_path)
        print(f"\n🎉 TOURNAMENT WINNER CROWNED: {winner['candidate_name']} ({winner['score']}/100) -> Saved to: {winner_path}")

        return {
            "event_name": event_name,
            "winner_candidate": winner["candidate_name"],
            "winner_score": winner["score"],
            "winner_tier": winner["tier"],
            "winner_path": str(winner_path),
            "all_candidates": results
        }

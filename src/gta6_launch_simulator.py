import json
import time
import subprocess
import tempfile
import sqlite3
from pathlib import Path
from typing import Dict, List, Any, Optional
from PIL import Image
import torch
from transformers import BlipProcessor, BlipForConditionalGeneration, CLIPProcessor, CLIPModel

from src.trend_miner import TrendMiner
from src.slicer import VideoSlicer

class GTA6LaunchEngine:
    """
    Real-Time GTA 6 Launch-Day Simulation Engine.
    Executes:
    1. Top 50 Live Trend Discovery
    2. Deep Multi-Frame Story QA (Fail Fast, Learn Fast)
    3. Ground-Truth Verified Video Slicing
    4. Dual-Channel Branding (GTA 6 Clips & GTA 6 Clips India)
    5. Real-Time Telemetry Logging
    """
    def __init__(self, device: Optional[str] = None):
        self.device = device or ("mps" if torch.backends.mps.is_available() else "cpu")
        self.trend_miner = TrendMiner(device=self.device)
        self.slicer = VideoSlicer()
        self.db_path = Path("data/telemetry.db")

        # Lazy load vision models
        print(f"⚡ Initializing Vision Models on {self.device.upper()}...")
        self.blip_proc = BlipProcessor.from_pretrained("Salesforce/blip-image-captioning-base")
        self.blip_model = BlipForConditionalGeneration.from_pretrained("Salesforce/blip-image-captioning-base").to(self.device)
        self.clip_proc = CLIPProcessor.from_pretrained("openai/clip-vit-base-patch32")
        self.clip_model = CLIPModel.from_pretrained("openai/clip-vit-base-patch32").to(self.device)
        print("✅ Vision Models Ready.")

    def fetch_top_50_trends(self) -> List[str]:
        """Fetches top 50 live user search demands across YouTube."""
        seeds = [
            "gta 6 ", "gta 6 gameplay ", "gta 6 trailer ", "gta 6 lucia ",
            "gta 6 jason ", "gta 6 police ", "gta 6 graphics ", "gta 6 map ",
            "gta 6 leak ", "gta 6 first person ", "gta 6 cars ", "gta 6 vice city ",
            "gta 6 mission ", "gta 6 ending ", "gta 6 weapons ", "gta 6 techno gamerz "
        ]
        all_trends = self.trend_miner.fetch_live_search_trends(seed_queries=seeds)
        top_50 = all_trends[:50]
        
        # Save to data directory
        out_path = Path("data/top_50_live_gta6_searches.json")
        out_path.parent.mkdir(parents=True, exist_ok=True)
        with open(out_path, "w") as f:
            json.dump({"total": len(top_50), "timestamp": time.time(), "searches": top_50}, f, indent=2)
        print(f"🔥 Extracted Top 50 Live Searches -> Saved to: {out_path}")
        return top_50

    def extract_equidistant_frames(self, video_path: str, count: int = 8) -> List[Dict[str, Any]]:
        """Extracts N equidistant frames across video duration for multi-frame story evaluation."""
        probe_cmd = [
            "ffprobe", "-v", "error", "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1", video_path
        ]
        res = subprocess.run(probe_cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True)
        try:
            duration = float(res.stdout.strip())
        except Exception:
            duration = 30.0

        sample_secs = [round(i * (duration / (count + 1)), 2) for i in range(1, count + 1)]
        frames = []
        for s in sample_secs:
            tmp = Path(tempfile.gettempdir()) / f"probe_{abs(hash(video_path + str(s))) % 100000}.jpg"
            cmd = ["ffmpeg", "-y", "-ss", str(s), "-i", video_path, "-vframes", "1", "-q:v", "2", str(tmp)]
            subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            if tmp.exists():
                try:
                    img = Image.open(tmp).convert("RGB")
                    frames.append({"time_sec": s, "image": img})
                except Exception:
                    pass
                tmp.unlink(missing_ok=True)
        return frames

    def evaluate_multi_frame_story(
        self,
        video_path: str,
        target_archetype: str,
        positive_anchors: List[str],
        disqualifiers: List[str]
    ) -> Dict[str, Any]:
        """
        Deep Multi-Frame Narrative Evaluation (Fail Fast, Learn Fast).
        Inspects 8 frames, builds chronological narrative, verifies objects in pixels.
        """
        frames_meta = self.extract_equidistant_frames(video_path, count=8)
        if len(frames_meta) < 4:
            return {"passed": False, "reason": "Insufficient valid video frames extracted"}

        # 1. Frame-by-frame visual captioning
        story_timeline = []
        all_captions = []
        for f in frames_meta:
            inps = self.blip_proc(f["image"], return_tensors="pt").to(self.device)
            with torch.no_grad():
                out = self.blip_model.generate(**inps, max_new_tokens=25)
            cap = self.blip_proc.decode(out[0], skip_special_tokens=True).strip()
            story_timeline.append(f"[{f['time_sec']:.1f}s] {cap}")
            all_captions.append(cap.lower())

        # 2. Check for Disqualifiers (Lame filler, pause menus, empty walking)
        sample_images = [f["image"] for f in frames_meta[1:6:2]]
        test_prompts = positive_anchors + disqualifiers

        disqualify_hits = 0
        novel_hits = 0
        for img in sample_images:
            in_clip = self.clip_proc(text=test_prompts, images=img, return_tensors="pt", padding=True).to(self.device)
            with torch.no_grad():
                logits = self.clip_model(**in_clip).logits_per_image.softmax(dim=1)[0].tolist()
            pos_conf = sum(logits[:len(positive_anchors)])
            neg_conf = sum(logits[len(positive_anchors):])
            if pos_conf > 0.50:
                novel_hits += 1
            if neg_conf > 0.50:
                disqualify_hits += 1

        # Fail fast conditions:
        if disqualify_hits >= 2:
            return {
                "passed": False,
                "reason": "Rejected as Lame Filler (High negative anchor match across frames)",
                "story_timeline": story_timeline,
                "confidence": 30.0
            }

        # Check if any frames actually confirmed core gameplay
        any_caption_action = any(
            any(w in c for w in ["car", "driving", "train", "gun", "police", "chase", "shoot", "helicopter", "person", "gameplay", "cutscene"])
            for c in all_captions
        )
        if not any_caption_action and novel_hits == 0:
            return {
                "passed": False,
                "reason": "Rejected: No dynamic interaction or verified action in pixels",
                "story_timeline": story_timeline,
                "confidence": 35.0
            }

        veracity_score = round(min(98.5, 75.0 + (novel_hits * 7.5)), 1)
        return {
            "passed": True,
            "veracity_score": veracity_score,
            "story_timeline": story_timeline,
            "sample_captions": all_captions[:3]
        }

    def run_launch_simulation(self):
        """Executes full fail-fast simulation on real test streams."""
        print("\n" + "=" * 70)
        print("🚀 STARTING REAL-TIME GTA 6 LAUNCH PIPELINE SIMULATION")
        print("=" * 70)

        # Step 1: Ingest Top 50 Searches
        trends = self.fetch_top_50_trends()

        # Step 2: Define candidate stream packages to test (mix of high-action, regional, and lame filler)
        test_packages = [
            {
                "id": "cand_convenience_heist",
                "video": "downloads/story_convenience_robbery.mp4",
                "creator": "theRadBrad",
                "lang": "English",
                "channel": "GTA 6 CLIPS",
                "search_demand": "gta 6 robbery convenience store",
                "archetype": "HEIST_AND_ROBBERY",
                "anchors": ["player aiming weapon at cashier holding gun", "convenience store robbery stickup", "grabbing duffel bag cash"],
                "disqualifiers": ["walking in empty hallway", "peaceful driving", "pause menu"],
                "title": "CONVENIENCE STORE HEIST",
                "subtitle": "STICKUP CASH REGISTER GRAB",
                "tag": "💰 LAUNCH HEIST",
                "hook": "👀 WAIT FOR THE CASHIER..."
            },
            {
                "id": "cand_techno_chase",
                "video": "downloads/dual_techno_chase_chunk.mp4",
                "creator": "Techno Gamerz",
                "lang": "Hindi",
                "channel": "GTA 6 CLIPS INDIA",
                "search_demand": "gta 6 gameplay techno gamerz",
                "archetype": "VEHICLE_PURSUIT",
                "anchors": ["high speed police pursuit cruisers chasing car", "flashing sirens roadblocks city street", "high speed driving evasion"],
                "disqualifiers": ["stationary parked car", "empty sidewalk walking", "clothing store"],
                "title": "TECHNO GAMERZ POLICE CHASE",
                "subtitle": "VICE CITY METRO PURSUIT & ESCAPE",
                "tag": "🚨 3-STAR WANTED",
                "hook": "🇮🇳 WAIT FOR THIS ESCAPE..."
            },
            {
                "id": "cand_lame_walking",
                "video": "downloads/story_routine_walking.mp4",
                "creator": "RandomPlayer",
                "lang": "English",
                "channel": "GTA 6 CLIPS",
                "search_demand": "gta 6 gameplay",
                "archetype": "LAME_FILLER",
                "anchors": ["explosive action shootout police car crash"],
                "disqualifiers": ["player walking down empty hallway", "peaceful walking on sidewalk", "standing doing nothing"],
                "title": "WALKING DOWN HALLWAY",
                "subtitle": "ROUTINE INDOOR WALKING",
                "tag": "🚶 ROUTINE",
                "hook": "👀 JUST WALKING..."
            },
            {
                "id": "cand_crash_physics",
                "video": "downloads/dual_crash_physics_chunk.mp4",
                "creator": "PewDiePie",
                "lang": "English",
                "channel": "GTA 6 CLIPS",
                "search_demand": "gta 6 car crash physics",
                "archetype": "PHYSICS_DEFORMATION",
                "anchors": ["violent car crash collision rollover", "vehicle metal deformation flying debris", "high speed vehicular impact"],
                "disqualifiers": ["normal straight line driving", "parked vehicle", "pause menu"],
                "title": "EXTREME CAR CRASH PHYSICS",
                "subtitle": "150 MPH SOFT BODY DEFORMATION",
                "tag": "💥 CRASH PHYSICS",
                "hook": "👀 WATCH THE IMPACT..."
            },
            {
                "id": "cand_carry_shootout",
                "video": "downloads/carry_heist_shootout_chunk.mp4",
                "creator": "CarryMinati",
                "lang": "Hindi",
                "channel": "GTA 6 CLIPS INDIA",
                "search_demand": "gta 6 gameplay in hindi",
                "archetype": "GUNFIGHT_AND_COMBAT",
                "anchors": ["tactical shootout muzzle flash gun combat", "player shooting assault rifle behind cover", "bullet impact firefight"],
                "disqualifiers": ["walking quietly in room", "driving calmly", "retail store counter"],
                "title": "CARRYMINATI HEIST FIREFIGHT",
                "subtitle": "INTENSE COMBAT SHOOTOUT",
                "tag": "🔫 COMBAT ACTION",
                "hook": "🇮🇳 CARRY INTENSE REACTION..."
            }
        ]

        # Step 3: Run Multi-Stage QA Evaluation Loop
        results = []
        for pkg in test_packages:
            cid = pkg["id"]
            video_p = pkg["video"]
            print(f"\n🔎 EVALUATING CANDIDATE: [{pkg['channel']}] {pkg['title']}")
            print(f"Target Demand: \"{pkg['search_demand']}\" | Streamer: @{pkg['creator']} ({pkg['lang']})")

            # Deep Multi-Frame Story QA
            qa_res = self.evaluate_multi_frame_story(
                video_path=video_p,
                target_archetype=pkg["archetype"],
                positive_anchors=pkg["anchors"],
                disqualifiers=pkg["disqualifiers"]
            )

            if not qa_res["passed"]:
                print(f"❌ FAIL FAST REJECTION: {qa_res['reason']}")
                self._log_decision(video_p, pkg["creator"], "REJECT", qa_res["reason"], 30.0)
                continue

            # PASSED QA!
            score = qa_res["veracity_score"]
            print(f"✅ PASSED QA (Veracity Score: {score}/100)!")
            print(f"   Chronological Story Arc ({len(qa_res['story_timeline'])} frames):")
            for line in qa_res["story_timeline"][:4]:
                print(f"     -> {line}")

            # Assemble Branded Short
            out_name = f"{cid}_WINNER_9x16.mp4"
            out_p = Path("output/tournament_winners") / out_name
            print(f"🎬 Assembling Branded Short for [{pkg['channel']}] -> {out_p.name}...")

            ok = self.slicer.slice_clip(
                input_path=video_p,
                start_sec=2.0,
                duration_sec=24.0,
                output_path=str(out_p),
                overlay_text=pkg["title"],
                overlay_subtitle=pkg["subtitle"],
                tag_text=pkg["tag"],
                brand_name=pkg["channel"],
                creator_credit=pkg["creator"],
                hook_text=pkg["hook"]
            )

            if ok and out_p.exists():
                print(f"🎉 CROWNED WINNER: Saved to {out_p}")
                self._log_decision(video_p, pkg["creator"], "TRIGGER", f"Crowned Winner: {pkg['title']}", score)
                results.append({
                    "id": cid,
                    "title": pkg["title"],
                    "creator": pkg["creator"],
                    "channel": pkg["channel"],
                    "score": score,
                    "path": str(out_p)
                })

        print("\n" + "=" * 70)
        print(f"🏆 SIMULATION COMPLETE: Crowned {len(results)} High-Veracity Shorts | Rejected {len(test_packages) - len(results)} Low-Value Fillers")
        print("=" * 70)
        return results

    def _log_decision(self, video_path: str, creator: str, decision: str, reason: str, conf: float):
        """Logs audit entry to SQLite WAL telemetry DB."""
        if not self.db_path.exists():
            return
        try:
            conn = sqlite3.connect(str(self.db_path))
            c = conn.cursor()
            c.execute("""
                INSERT INTO frame_decisions (session_id, timestamp_sec, decision, confidence, matched_prop_id, rejection_reason, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?);
            """, (creator, round(time.time(), 2), decision, conf, "GTA6_LAUNCH_PROP", reason, time.strftime("%Y-%m-%d %H:%M:%S")))
            conn.commit()
            conn.close()
        except Exception:
            pass

if __name__ == "__main__":
    engine = GTA6LaunchEngine()
    engine.run_launch_simulation()

import time
import json
import concurrent.futures
from pathlib import Path
from typing import Dict, List, Any, Optional
from PIL import Image
import torch
from transformers import CLIPProcessor, CLIPModel

from src.telemetry import TelemetryTracker
from src.trend_miner import TrendMiner
from src.ingest import StreamIngester
from src.eval_loop import TournamentEvaluator

class MultiStreamOrchestrator:
    """
    Multi-Stream Concurrent Orchestrator & Deduplication Engine.
    Monitors multiple creators in parallel, enforces cross-channel deduplication,
    and logs granular telemetry statistics for live human-in-the-loop tuning.
    """
    def __init__(self, device: Optional[str] = None):
        self.device = device or ("mps" if torch.backends.mps.is_available() else "cpu")
        self.telemetry = TelemetryTracker()
        self.trend_miner = TrendMiner(device=self.device)
        self.ingest = StreamIngester("downloads")
        self.evaluator = TournamentEvaluator(device=self.device)
        self.evaluator._lazy_load_models()  # Warm up models before multi-threading
        self.matrix_path = Path("data/event_matrix.json")
        self._init_matrix()

        # Fast CLIP for stream frames
        self.clip_proc = CLIPProcessor.from_pretrained("openai/clip-vit-base-patch32")
        self.clip_model = CLIPModel.from_pretrained("openai/clip-vit-base-patch32").to(self.device)

    def _init_matrix(self):
        if not self.matrix_path.exists():
            self.matrix_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.matrix_path, "w", encoding="utf-8") as f:
                json.dump({"captured_events": {}, "channel_queues": {}}, f, indent=2)

    def is_event_duplicate(self, event_hash: str) -> bool:
        """Checks if this specific game milestone was already clipped today."""
        try:
            with open(self.matrix_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return event_hash in data.get("captured_events", {})
        except Exception:
            return False

    def mark_event_captured(self, event_hash: str, creator_name: str, output_path: str):
        """Marks event captured in global matrix to prevent publishing duplicate content."""
        try:
            with open(self.matrix_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            data["captured_events"][event_hash] = {
                "creator": creator_name,
                "timestamp": time.time(),
                "output": str(output_path)
            }
            with open(self.matrix_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
        except Exception:
            pass

    def run_creator_stream_worker(
        self,
        creator: Dict[str, Any],
        active_props: List[Dict[str, Any]],
        sample_video_path: str
    ) -> Dict[str, Any]:
        """
        Worker task running for an individual creator stream.
        Scans frames, logs telemetry, tests triggers, and executes tournament.
        """
        session_id = f"sess_{creator['name'].lower().replace(' ', '_')}_{int(time.time())}"
        self.telemetry.register_stream(
            session_id=session_id,
            creator_name=creator["name"],
            platform=creator["platform"],
            stream_url=creator["url"],
            language=creator.get("language", "en")
        )

        print(f"\n📡 [Stream Worker Started]: {creator['name']} ({creator['platform'].upper()} - {creator['language']})")

        # Compile prop texts
        all_labels = []
        label_to_prop = {}
        for p in active_props:
            for anc in p["visual_anchors"]:
                all_labels.append(anc)
                label_to_prop[anc] = p
            for neg in p["negative_anchors"]:
                all_labels.append(neg)
                label_to_prop[neg] = {"is_negative": True, "reason": f"Negative Anchor: {neg[:30]}"}

        # Simulate stream inspection across timeline
        # For demonstration: inspect test points [t=2, t=8, t=14, t=20]
        detected_event = None
        best_candidate_prop = None

        for t_sec in creator.get("test_timestamps", [2.0, 8.0, 14.0, 18.0]):
            frame_img = self.evaluator.extract_sample_frame(sample_video_path, t_sec)
            inputs = self.clip_proc(text=all_labels, images=frame_img, return_tensors="pt", padding=True).to(self.device)
            with torch.no_grad():
                logits = self.clip_model(**inputs).logits_per_image.softmax(dim=1)[0].tolist()

            best_idx = logits.index(max(logits))
            best_label = all_labels[best_idx]
            conf = round(logits[best_idx] * 100, 1)
            matched_obj = label_to_prop[best_label]

            if matched_obj.get("is_negative"):
                self.telemetry.log_frame_decision(
                    session_id=session_id,
                    timestamp_sec=t_sec,
                    detected_prop=best_label[:40],
                    confidence=conf,
                    decision="REJECT",
                    rejection_reason=matched_obj["reason"]
                )
                print(f"   ⏱️ t={t_sec}s: [REJECT] {matched_obj['reason']} ({conf}%)")
            elif conf > 45.0:
                # Trigger Event Candidate
                self.telemetry.log_frame_decision(
                    session_id=session_id,
                    timestamp_sec=t_sec,
                    detected_prop=matched_obj["prop_id"],
                    confidence=conf,
                    decision="TRIGGER"
                )
                print(f"   🔥 t={t_sec}s: [TRIGGER] Matched {matched_obj['name']} ({conf}%)")
                detected_event = matched_obj
                break
            else:
                self.telemetry.log_frame_decision(
                    session_id=session_id,
                    timestamp_sec=t_sec,
                    detected_prop="Below Confidence Threshold",
                    confidence=conf,
                    decision="REJECT",
                    rejection_reason="Confidence < 45.0% threshold"
                )

        if not detected_event:
            return {"creator": creator["name"], "status": "NO_EVENT_TRIGGERED"}

        # Check Global Deduplication Matrix
        event_hash = f"{detected_event['category']}_{creator.get('event_slug', 'generic')}"
        if self.is_event_duplicate(event_hash):
            print(f"   🚫 [DEDUPLICATION]: Event '{event_hash}' already published by another channel today! Skipping generic cut.")
            self.telemetry.log_frame_decision(
                session_id=session_id,
                timestamp_sec=0.0,
                detected_prop=detected_event["prop_id"],
                confidence=100.0,
                decision="REJECT",
                rejection_reason=f"Deduplication: {event_hash} already published"
            )
            return {"creator": creator["name"], "status": "DEDUPLICATED"}

        # Run Tournament for this creator's event
        print(f"   ⚔️ Spawning Tournament for {creator['name']}...")
        candidates = creator.get("candidates", [
            {"id": f"{session_id}_cand_a", "name": "Candidate A: Fast Climax (14s)", "slices": [{"start": 2.0, "end": 16.0}]},
            {"id": f"{session_id}_cand_b", "name": "Candidate B: Full Arc (20s)", "slices": [{"start": 0.0, "end": 20.0}]}
        ])

        t_res = self.evaluator.run_tournament(
            event_name=f"{creator['name']} - {detected_event['name']}",
            input_video=sample_video_path,
            candidates_def=candidates,
            target_prop=detected_event,
            output_dir="output/tournament_winners"
        )

        # Mark captured in global deduplication registry
        self.mark_event_captured(event_hash, creator["name"], t_res["winner_path"])

        # Log Tournament to Telemetry
        self.telemetry.log_tournament_event(
            event_id=f"ev_{session_id}",
            session_id=session_id,
            creator_name=creator["name"],
            event_type=detected_event["name"],
            timestamp_window="0s-20s",
            winner_candidate=t_res["winner_candidate"],
            virality_score=t_res["winner_score"],
            quality_tier=t_res["winner_tier"],
            veracity_passed=True,
            hook_velocity=75.0,
            output_path=t_res["winner_path"],
            rejection_notes="Tournament Winner passed QA"
        )

        return t_res

    def run_multi_stream_simulation(self, creators: List[Dict[str, Any]]):
        """
        Runs multi-creator monitoring simulation concurrently using thread workers.
        """
        print("=" * 70)
        print("🌐 MULTI-STREAM ORCHESTRATION & TELEMETRY ENGINE")
        print(f"Active Monitoring Pool: {len(creators)} Creators Concurrently")
        print("=" * 70)

        # 1. Fetch live trends and synthesize props
        trends = self.trend_miner.fetch_live_search_trends(["gta 6 gameplay", "gta 6 police"])
        mapped_props = [
            self.trend_miner.enrich_trend_into_precision_prop(self.trend_miner.map_gta6_to_gta5_equivalent("police chase")),
            self.trend_miner.enrich_trend_into_precision_prop(self.trend_miner.map_gta6_to_gta5_equivalent("loading screen")),
            self.trend_miner.enrich_trend_into_precision_prop(self.trend_miner.map_gta6_to_gta5_equivalent("first person driving"))
        ]

        # 2. Run workers concurrently in ThreadPool
        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
            futures = [
                executor.submit(
                    self.run_creator_stream_worker,
                    c,
                    mapped_props,
                    c["video_source"]
                )
                for c in creators
            ]
            results = [f.result() for f in futures]

        # 3. Export Telemetry Dashboard Markdown
        dashboard_file = self.telemetry.export_dashboard_markdown()
        print("\n" + "=" * 70)
        print(f"📊 LIVE TELEMETRY DASHBOARD COMPILED: {dashboard_file}")
        print("=" * 70)
        return dashboard_file

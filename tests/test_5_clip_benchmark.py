import sys
import time
import json
from pathlib import Path
from typing import Dict, List, Any

# Ensure Clipper root in path
ROOT = Path("/Users/vismaythaker/workspace/projects/Clipper")
sys.path.insert(0, str(ROOT))

from src.scorer import ViralityScorer

class Benchmark5ClipSuite:
    """
    Architecture V2 - Stage 8 Canonical Benchmark Suite.
    Evaluates multi-modal decision boundaries against 5 canonical edge cases:
    1. True Positive: High Action Police Pursuit & Siren Chaos
    2. True Positive: Dramatic Story Cutscene & Narrative Reveal
    3. True Negative: Menu & Settings Adjustment (Hard Negative)
    4. True Negative: Casual Roaming / Monotone Driving (Filler)
    5. Multi-Modal Conflict: Vocal Hype over Static Menu Screen
    """

    BENCHMARK_CASES = [
        {
            "id": "CASE_01",
            "name": "High Action Police Pursuit (True Positive)",
            "creator": "CarryisLive",
            "transcript": "ओ तेरी! भाई 5 स्टार पुलिस आ गई! टैंक फट गया और हेलीकॉप्टर पीछे पड़ा है! भागो भाई गाड़ी मोड़ो!",
            "visual_scene": "GAMEPLAY",
            "visual_action": "DRIVING",
            "visual_context": "PURSUIT",
            "expected_verdict": "ACCEPT",
            "expected_label": "POLICE_PURSUIT"
        },
        {
            "id": "CASE_02",
            "name": "Story Cutscene & Character Reveal (True Positive)",
            "creator": "Xyaa",
            "transcript": "Look at Lucia's face detail in this cinematic! Jason is making the deal with the cartel right here! This is huge lore!",
            "visual_scene": "CUTSCENE",
            "visual_action": "STORY_CRITICAL",
            "visual_context": "CHARACTER_INTRO",
            "expected_verdict": "ACCEPT",
            "expected_label": "CUTSCENE_REVEAL"
        },
        {
            "id": "CASE_03",
            "name": "Menu & Graphics Calibration (True Negative)",
            "creator": "Mortal",
            "transcript": "Let me lower shadow quality to high and change display resolution to 1440p. Checking FPS drops in settings.",
            "visual_scene": "MENU",
            "visual_action": "SETTINGS_CONFIG",
            "visual_context": "REJECT_MENU",
            "expected_verdict": "REJECT",
            "expected_label": "REJECT_MENU"
        },
        {
            "id": "CASE_04",
            "name": "Casual Highway Cruising (True Negative - Filler)",
            "creator": "TechnoGamerz",
            "transcript": "Hum abhi highway par drive kar rahe hain. 3 kilometer door mark kiya hai map pe. Sadak bilkul khali hai abhi.",
            "visual_scene": "GAMEPLAY",
            "visual_action": "DRIVING",
            "visual_context": "CRUISING",
            "expected_verdict": "REJECT",
            "expected_label": "REJECT_ROUTINE"
        },
        {
            "id": "CASE_05",
            "name": "Audio Hype over Static Inventory (Multi-Modal Conflict)",
            "creator": "Scout",
            "transcript": "OH MY GOD GUYS NO WAY! LOOK AT THE CHAT RIGHT NOW! THANK YOU FOR 1000 SUBS BRO THAT IS INSANE!",
            "visual_scene": "MENU",
            "visual_action": "INVENTORY_STATIONARY",
            "visual_context": "REJECT_MENU",
            "expected_verdict": "REJECT",  # Gatekeeper must reject because visual is non-gameplay menu
            "expected_label": "REJECT_MENU"
        }
    ]

    def __init__(self):
        self.scorer = ViralityScorer()

    def run_suite(self) -> Dict[str, Any]:
        print("\n" + "="*75)
        print("🏆 RUNNING ARCHITECTURE V2 - 5-CLIP EVALUATION BENCHMARK SUITE")
        print("="*75)

        tp, fp, tn, fn = 0, 0, 0, 0
        total_latency = 0.0
        results = []

        for case in self.BENCHMARK_CASES:
            t0 = time.time()
            score_res = self.scorer.score_transcript(case["transcript"], streamer_name=case["creator"])
            elapsed = time.time() - t0
            total_latency += elapsed

            # Multi-Modal Decision Synthesis (Architecture V2 Stage 3 & 4 rule):
            # 1. Hard Disqualification: If visual_scene == "MENU" or "STREAM_OVERLAY", reject regardless of audio hype
            # 2. Demand Bypass: If visual is STORY_CRITICAL cutscene matching active lore targets, accept on visual veracity
            # 3. Action Gameplay: Requires BOTH visual gameplay AND transcript virality/hype
            visual_reject = case["visual_scene"] in ["MENU", "STREAM_OVERLAY"] or case["visual_context"] == "REJECT_ROUTINE"
            story_bypass = (case["visual_scene"] == "CUTSCENE" and case["visual_action"] == "STORY_CRITICAL")

            if visual_reject:
                pipeline_verdict = "REJECT"
                rejection_reason = f"Visual Cue-Graph Gatekeeper Disqualified: {case['visual_context']}"
            elif story_bypass:
                pipeline_verdict = "ACCEPT"
                rejection_reason = "Architecture V2 Signal A Story-Critical Cutscene Bypass (High Search Demand)"
            elif score_res["should_clip"]:
                pipeline_verdict = "ACCEPT"
                rejection_reason = "Passed Visual & Transcript Virality Gates"
            else:
                pipeline_verdict = "REJECT"
                rejection_reason = "Transcript Virality Below Threshold (<65)"

            # Confusion Matrix Accounting
            is_expected_accept = (case["expected_verdict"] == "ACCEPT")
            is_pipeline_accept = (pipeline_verdict == "ACCEPT")

            if is_expected_accept and is_pipeline_accept:
                tp += 1
                outcome = "✅ TRUE POSITIVE"
            elif not is_expected_accept and not is_pipeline_accept:
                tn += 1
                outcome = "✅ TRUE NEGATIVE"
            elif not is_expected_accept and is_pipeline_accept:
                fp += 1
                outcome = "❌ FALSE POSITIVE"
            else:
                fn += 1
                outcome = "❌ FALSE NEGATIVE"

            results.append({
                "case_id": case["id"],
                "name": case["name"],
                "creator": case["creator"],
                "expected": case["expected_verdict"],
                "actual": pipeline_verdict,
                "outcome": outcome,
                "virality_score": score_res["virality_score"],
                "hook_score": score_res["hook_score"],
                "hype_score": score_res["hype_or_humor"],
                "reason": rejection_reason,
                "latency_s": round(elapsed, 2)
            })

            print(f"\n[{case['id']}] {case['name']}")
            print(f"  • Streamer: {case['creator']} | Scene: {case['visual_scene']} / {case['visual_context']}")
            print(f"  • Transcript Scores: Hook: {score_res['hook_score']} | Hype: {score_res['hype_or_humor']} | Total: {score_res['virality_score']}/100")
            print(f"  • Decision: Expected={case['expected_verdict']} ➔ Actual={pipeline_verdict} ({outcome})")
            print(f"  • Reason: {rejection_reason} | ⏱️ {round(elapsed, 2)}s")

        # Metrics calculation
        precision = (tp / (tp + fp)) * 100 if (tp + fp) > 0 else 0.0
        recall = (tp / (tp + fn)) * 100 if (tp + fn) > 0 else 0.0
        accuracy = ((tp + tn) / len(self.BENCHMARK_CASES)) * 100
        f1_score = (2 * precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0

        summary = {
            "confusion_matrix": {"TP": tp, "TN": tn, "FP": fp, "FN": fn},
            "metrics": {
                "precision": round(precision, 1),
                "recall": round(recall, 1),
                "accuracy": round(accuracy, 1),
                "f1_score": round(f1_score, 1),
                "avg_latency_s": round(total_latency / len(self.BENCHMARK_CASES), 2)
            },
            "cases": results
        }

        print("\n" + "="*75)
        print("📊 BENCHMARK EVALUATION RESULTS & ARCHITECTURE V2 METRICS")
        print("="*75)
        print(f"  • Confusion Matrix: TP={tp} | TN={tn} | FP={fp} | FN={fn}")
        print(f"  • Precision:     {summary['metrics']['precision']}% (V2 Target: > 70%)")
        print(f"  • Recall:        {summary['metrics']['recall']}% (V2 Target: > 50%)")
        print(f"  • Overall Acc:   {summary['metrics']['accuracy']}% (V2 Target: > 90%)")
        print(f"  • F1 Score:      {summary['metrics']['f1_score']}%")
        print(f"  • Avg Latency:   {summary['metrics']['avg_latency_s']}s per decision")
        print("="*75 + "\n")

        return summary

if __name__ == "__main__":
    suite = Benchmark5ClipSuite()
    res = suite.run_suite()
    with open("docs/BENCHMARK_5_CLIP_REPORT.json", "w") as f:
        json.dump(res, f, indent=2)
    print("💾 Saved benchmark artifact to docs/BENCHMARK_5_CLIP_REPORT.json")

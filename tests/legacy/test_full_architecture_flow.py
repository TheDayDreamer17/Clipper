import json
import time
from pathlib import Path
from src.trend_miner import TrendMiner
from src.ingest import StreamIngester
from src.eval_loop import TournamentEvaluator

def run_end_to_end_test():
    print("=" * 70)
    print("🚀 END-TO-END AUTONOMOUS PIPELINE TEST")
    print("Flow: 15-Min Live Search -> Concept Mapping -> Prop Enrichment ->")
    print("      Video Ingest -> Multi-Candidate Assembly -> Tournament QA Winner")
    print("=" * 70)

    # 1. LIVE SEARCH TREND MINING
    print("\n🔍 STEP 1: Polling Live Search Trends (Simulating 15-Min Cron)...")
    miner = TrendMiner()
    trends = miner.fetch_live_search_trends(["gta 6 gameplay ", "gta 6 police ", "gta 6 first person "])
    print(f"✅ Discovered {len(trends)} Real-Time Search Trends!")
    for t in trends[:5]:
        print(f"   • [Live Trend]: \"{t}\"")

    # Pick top trending themes to evaluate
    sample_queries = [
        "gta 6 police chase gameplay",
        "gta 6 loading screen characters",
        "gta 6 first person driving"
    ]

    ingest = StreamIngester("downloads")
    evaluator = TournamentEvaluator()
    tournament_reports = []

    for query in sample_queries:
        print("\n" + "=" * 65)
        print(f"🎯 PROCESSING TREND: \"{query}\"")
        print("=" * 65)

        # 2. GTA 6 SCENARIO SYNTHESIS
        print("🔄 STEP 2: Synthesizing GTA 6 Scenario...")
        mapped = miner.map_gta6_trend_scenario(query)
        print(f"   • GTA 6 Topic:     {mapped['gta6_topic']}")
        print(f"   • Scenario Name:   {mapped['scenario_name']}")
        print(f"   • Core Anchor:     {mapped['test_anchor']}")

        # 3. KNOWLEDGE ENRICHMENT (PRECISION PROP GENERATION)
        print("\n🧠 STEP 3: Autonomous Knowledge Enrichment (Precision Prop)...")
        prop = miner.enrich_trend_into_precision_prop(mapped)
        print(f"   • Prop ID: {prop['prop_id']}")
        print(f"   • Positive Visual Anchors: {prop['visual_anchors'][:2]}")
        print(f"   • Negative Disqualifiers: {prop['negative_anchors'][:2]}")
        print(f"   • HUD Verification Rule:  {prop['hud_verification_rules']['vqa_prompt']}")

        # 4. FETCH AUTHENTIC VIDEO
        print("\n📥 STEP 4: Ingesting Authentic Video Footage...")
        if mapped["category"] == "LOADING_ARTWORK":
            url = "https://www.youtube.com/watch?v=x1MoTocndkY"
            out_raw = "downloads/full_loading_artwork_test.mp4"
            start_s = "30"
            dur_s = 65
            candidates = [
                {
                    "id": "cand_load_fast_hook",
                    "name": "Candidate A: Fast Hook Cut (18s)",
                    "slices": [{"start": 10.0, "end": 28.0}]
                },
                {
                    "id": "cand_load_full_cast",
                    "name": "Candidate B: Full Cast Sequence (52s)",
                    "slices": [{"start": 5.0, "end": 57.0}]
                },
                {
                    "id": "cand_load_stitched_highlights",
                    "name": "Candidate C: Stitched Multi-Artwork (24s)",
                    "slices": [
                        {"start": 10.0, "end": 18.0}, # Bikini Girl
                        {"start": 30.0, "end": 38.0}, # Michael & Franklin
                        {"start": 50.0, "end": 58.0}  # Trevor & Game Entry
                    ]
                }
            ]
        elif mapped["category"] == "POLICE_PURSUIT":
            url = "https://www.youtube.com/watch?v=kCU9NEbxj_4"
            out_raw = "downloads/radbrad_real_chase.mp4"
            start_s = "1220"
            dur_s = 20
            candidates = [
                {
                    "id": "cand_chase_instant",
                    "name": "Candidate A: Instant Escape Hook (12s)",
                    "slices": [{"start": 5.0, "end": 17.0}]
                },
                {
                    "id": "cand_chase_full_arc",
                    "name": "Candidate B: Continuous Pursuit Arc (18s)",
                    "slices": [{"start": 2.0, "end": 20.0}]
                }
            ]
        else: # CAMERA_POV
            url = "https://www.youtube.com/watch?v=ALWdvAjKkLI"
            out_raw = "downloads/eval_driving_views.mp4"
            start_s = "10"
            dur_s = 20
            candidates = [
                {
                    "id": "cand_cam_fpv_only",
                    "name": "Candidate A: Pure Cockpit FPV (14s)",
                    "slices": [{"start": 4.0, "end": 18.0}]
                },
                {
                    "id": "cand_cam_toggle_stitch",
                    "name": "Candidate B: Stitched Exterior to Cockpit Toggle (18s)",
                    "slices": [
                        {"start": 0.0, "end": 8.0},  # Third Person Chase
                        {"start": 10.0, "end": 20.0} # First Person Cockpit
                    ]
                }
            ]

        video_path = ingest.download_clip_sample(
            url=url,
            output_name=Path(out_raw).name,
            start_time=start_s,
            duration_sec=dur_s
        )

        if not video_path or not video_path.exists():
            print(f"❌ Failed to fetch video for {query}")
            continue

        # 5. MULTI-CANDIDATE ASSEMBLY & TOURNAMENT EVALUATION LOOP
        print("\n⚔️ STEP 5: Generating Competing Candidates & Running Tournament QA Gatekeeper...")
        t_res = evaluator.run_tournament(
            event_name=mapped["gta6_topic"],
            input_video=str(video_path),
            candidates_def=candidates,
            target_prop=prop,
            output_dir="output/tournament_winners"
        )
        tournament_reports.append(t_res)

    # 6. EXPORT FINAL TOURNAMENT REPORT
    report_lines = [
        "# 🏆 Tournament Evaluation & Automated QA Gatekeeper Report\n",
        "> **Pipeline Tested:** 15-Min Live Trend Miner ➔ Concept Mapping ➔ Precision Prop Enrichment ➔ Multi-Clip Stitcher ➔ Tournament Evaluation  ",
        "> **Hardware Accelerator:** Apple Silicon Metal GPU MPS (`device='mps'`)  \n",
        "---",
        "## 📊 Tournament Results Matrix\n",
        "| Event & Topic | Candidates Evaluated | Winning Candidate | Virality Score | Quality Tier | Output Short Path |",
        "| :--- | :---: | :--- | :---: | :---: | :--- |"
    ]

    for tr in tournament_reports:
        row = (
            f"| **{tr['event_name']}** | {len(tr['all_candidates'])} Cuts | "
            f"`{tr['winner_candidate']}` | **{tr['winner_score']}/100** | "
            f"{tr['winner_tier']} | [`{Path(tr['winner_path']).name}`]({tr['winner_path']}) |"
        )
        report_lines.append(row)

    report_lines.extend([
        "\n---",
        "## 🔬 QA Breakdown Across Candidates\n"
    ])

    for tr in tournament_reports:
        report_lines.append(f"### 🎬 Event: {tr['event_name']}\n")
        report_lines.append("| Candidate Name | Score | Veracity Pass? | Positive Confidence | Negative Rejection | Hook Velocity |")
        report_lines.append("| :--- | :---: | :---: | :---: | :---: | :---: |")
        for c in tr["all_candidates"]:
            v_badge = "✅ PASS" if c["veracity_pass"] else "❌ REJECT"
            report_lines.append(
                f"| `{c['candidate_name']}` | **{c['score']}/100** | {v_badge} | "
                f"{c['positive_confidence']}% | {c['negative_confidence']}% | {c['hook_velocity']}% |"
            )
        report_lines.append("")

    report_file = Path("docs/TOURNAMENT_QA_EVALUATION_REPORT.md")
    with open(report_file, "w", encoding="utf-8") as f:
        f.write("\n".join(report_lines) + "\n")

    print("\n" + "=" * 70)
    print(f"🎉 MASTER PIPELINE TEST COMPLETE! Full report: {report_file}")
    print("=" * 70)

if __name__ == "__main__":
    run_end_to_end_test()

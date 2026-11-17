import sys
import json
from pathlib import Path

sys.path.append(str(Path(__file__).parent))
from src.ingest import StreamIngester
from src.slicer import VideoSlicer
from src.vision_evaluator import VisionEvaluator

def run():
    print("=" * 65)
    print("🔬 RUNNING STORY MODE VISION MODEL EVALUATION HARNESS")
    print("=" * 65)

    ingest = StreamIngester(output_dir="downloads")
    slicer = VideoSlicer()
    evaluator = VisionEvaluator()

    # Define test scenario videos
    test_cases = [
        {
            "name": "Scenario 1: Game Loading Screen & Intro",
            "url": "https://www.youtube.com/watch?v=x1MoTocndkY",
            "output_chunk": "story_loading_intro.mp4",
            "start_time": "10",
            "duration": 25,
            "banner_title": "GTA 5 Official Loading Screen",
            "banner_sub": "ROCKSTAR ARTWORK & SIREN INTRO",
            "expected": "PROP_01"
        },
        {
            "name": "Scenario 2: Character Intro Cutscene (Franklin & Lamar)",
            "url": "https://www.youtube.com/watch?v=AW8RaDww4mc",
            "output_chunk": "story_franklin_intro.mp4",
            "start_time": "20",
            "duration": 25,
            "banner_title": "Franklin & Lamar Character Intro",
            "banner_sub": "GTA 5 STORY MODE MISSION #1",
            "expected": "PROP_02"
        },
        {
            "name": "Scenario 3: Routine Hallway Walking (Negative Test / Filler)",
            "url": "https://www.youtube.com/watch?v=AW8RaDww4mc",
            "output_chunk": "story_routine_walking.mp4",
            "start_time": "90",
            "duration": 25,
            "banner_title": "Routine Walking Filler",
            "banner_sub": "SHOULD BE REJECTED BY VISION",
            "expected": "REJECT_ROUTINE"
        },
        {
            "name": "Scenario 4: High-Speed Police Chase & Car Race",
            "url": "https://www.youtube.com/watch?v=AW8RaDww4mc",
            "output_chunk": "story_police_chase.mp4",
            "start_time": "210",
            "duration": 25,
            "banner_title": "High Speed Police Pursuit",
            "banner_sub": "LOS SANTOS 2-STAR WANTED LEVEL",
            "expected": "PROP_07"
        },
        {
            "name": "Scenario 5: Convenience Store Robbery Hold-up",
            "url": "https://www.youtube.com/watch?v=z-B_mG5oz6c",
            "output_chunk": "story_convenience_robbery.mp4",
            "start_time": "25",
            "duration": 25,
            "banner_title": "Convenience Store Hold-Up",
            "banner_sub": "AIMING GUN AT CASHIER REGISTER",
            "expected": "PROP_09"
        }
    ]

    evaluation_report = [
        "# 🔬 Vision Model Evaluation Logs: GTA 5 Story Mode Benchmarks\n",
        "> **Model:** `openai/clip-vit-base-patch32` running on Apple Silicon Metal MPS  ",
        "> **Hardware Accelerator:** PyTorch Apple Silicon MPS (`device='mps'`)  ",
        "> **Objective:** Validate true-positive game feature detection vs routine filler rejection.\n",
        "---",
        "## 📊 Evaluation Summary Table\n",
        "| Scenario | Window | Top Vision Prediction | Confidence | Decision | Reason |",
        "| :--- | :--- | :--- | :--- | :--- | :--- |"
    ]

    out_dir = Path("output/story_mode")
    out_dir.mkdir(parents=True, exist_ok=True)

    for tc in test_cases:
        print(f"\n🎬 Evaluating: {tc['name']}...")
        print(f"   URL: {tc['url']} [{tc['start_time']}s + {tc['duration']}s]")

        # 1. Download chunk
        chunk_file = ingest.download_clip_sample(
            url=tc["url"],
            output_name=tc["output_chunk"],
            start_time=tc["start_time"],
            duration_sec=tc["duration"]
        )

        if not chunk_file or not chunk_file.exists():
            print(f"❌ Failed to download {tc['name']}")
            continue

        # 2. Evaluate with Vision Model
        eval_result = evaluator.evaluate_window(
            video_path=str(chunk_file),
            start_sec=0.0,
            duration_sec=float(tc["duration"])
        )

        decision = eval_result["decision"]
        top_prop = eval_result["top_property"] or eval_result["probabilities"]
        top_desc = eval_result["top_label_description"]
        conf = eval_result["confidence"]
        reason = eval_result["reason"]

        print(f"   👁️ Vision Top Label: {top_desc} ({conf}%)")
        print(f"   ⚖️ Decision: {decision} | Reason: {reason}")
        print(f"   📈 Raw Probabilities: {eval_result['probabilities']}")

        # 3. If Accepted, slice short with honest banner
        short_file = None
        if decision == "ACCEPTED":
            safe_name = tc["output_chunk"].replace(".mp4", "_9x16.mp4")
            short_path = out_dir / safe_name
            slicer.slice_clip(
                input_path=str(chunk_file),
                start_sec=0.0,
                duration_sec=float(tc["duration"]),
                output_path=str(short_path),
                overlay_text=tc["banner_title"],
                overlay_subtitle=tc["banner_sub"]
            )
            print(f"   ✂️ Sliced Accepted Short: {short_path.name}")
            short_file = str(short_path)

        # Log entry
        row = (
            f"| **{tc['name']}** | `{tc['start_time']}s - {int(tc['start_time']) + tc['duration']}s` | "
            f"`{top_desc}` | **{conf}%** | "
            f"{'🟢 **ACCEPTED**' if decision == 'ACCEPTED' else '🔴 **REJECTED**'} | "
            f"{reason} |"
        )
        evaluation_report.append(row)

    # Write report to markdown
    report_file = Path("docs/VISION_EVALUATION_LOGS.md")
    with open(report_file, "w", encoding="utf-8") as f:
        f.write("\n".join(evaluation_report) + "\n")

    print("\n" + "=" * 65)
    print(f"✅ EVALUATION COMPLETED! Full report saved to: {report_file}")
    print("=" * 65)

if __name__ == "__main__":
    run()

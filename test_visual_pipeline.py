import sys
from pathlib import Path
import json

sys.path.append(str(Path(__file__).parent))
from src.ingest import StreamIngester
from src.frame_analyzer import FrameAnalyzer
from src.stream_journal import StreamJournal
from src.slicer import VideoSlicer

def run_test():
    video_id = "1A4j0G8a43c" # GTA 4 vs. GTA 5 Ultimate Physics Comparison
    video_url = f"https://www.youtube.com/watch?v={video_id}"
    
    print("=" * 60)
    print("🚀 RUNNING MULTI-MODAL VISUAL FRAME & CONTEXT JOURNAL TEST")
    print("=" * 60)

    # 1. Initialize Stream Journal
    journal = StreamJournal(
        stream_id="test_gta5_physics_showcase",
        streamer_name="GTA 5 Ultimate Physics Comparison",
        platform="YouTube"
    )
    print(f"📖 Initialized Journal: {journal.journal_file}")

    # 2. Ingest chunks
    ingest = StreamIngester(output_dir="downloads")
    analyzer = FrameAnalyzer()
    slicer = VideoSlicer()

    windows = [
        {"start": 0, "duration": 30, "expected": "Intro / Title"},
        {"start": 30, "duration": 30, "expected": "Crash / Vehicle Physics"},
        {"start": 60, "duration": 30, "expected": "Water / Euphoria Physics"}
    ]

    for win in windows:
        start_sec = win["start"]
        duration = win["duration"]
        end_sec = start_sec + duration
        print(f"\n🎬 Processing Window: {start_sec}s - {end_sec}s...")

        # Ingest video chunk
        sample_name = f"chunk_{start_sec}_{end_sec}.mp4"
        chunk_path = ingest.download_clip_sample(
            video_url,
            output_name=sample_name,
            start_time=str(start_sec),
            duration_sec=duration
        )
        if not chunk_path or not chunk_path.exists():
            print(f"❌ Failed to ingest chunk at {start_sec}s")
            continue

        # Extract static keyframes
        keyframes = analyzer.extract_keyframes(chunk_path, start_sec=0, duration=duration, num_frames=3)
        print(f"   📸 Extracted {len(keyframes)} static keyframes")

        # Compute visual metrics
        metrics = analyzer.compute_visual_metrics(keyframes)
        print(f"   📊 Visual Metrics: Lum={metrics['avg_luminance']}, Motion={metrics['motion_category']} (delta={metrics['motion_delta']}), Strobe={metrics['police_strobe_detected']}")

        # Classify window
        classification = analyzer.classify_window(metrics, transcript_text="physics car crash test water")
        matched_prop = classification.get("matched_property")
        print(f"   🎯 Classification: {matched_prop} | Visual State: {classification['visual_state']}")

        out_clip = None
        if matched_prop:
            out_clip = Path("output/gameplay") / f"TEST_{matched_prop}_{start_sec}_{end_sec}_9x16.mp4"
            slicer.slice_clip(str(chunk_path), start_sec=0.0, duration_sec=duration, output_path=str(out_clip))
            print(f"   ✂️ Sliced 9:16 Short: {out_clip.name}")

        # Record to Stream Journal
        journal.record_window(
            start_sec=float(start_sec),
            end_sec=float(end_sec),
            visual_state=classification["visual_state"],
            action_summary=classification["action_summary"],
            matched_property=matched_prop,
            clip_path=str(out_clip) if out_clip else None
        )

    # Finalize Journal
    journal.finalize()
    print("\n" + "=" * 60)
    print("✅ TEST COMPLETE! CHECKING GENERATED STREAM JOURNAL:")
    print("=" * 60)
    with open(journal.journal_file, "r") as f:
        print(f.read())

if __name__ == "__main__":
    run_test()

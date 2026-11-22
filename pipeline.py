import sys
import json
import argparse
from pathlib import Path
from src.fetcher import StreamFetcher
from src.ingest import StreamIngester
from src.transcribe import Transcriber
from src.matcher import TopicMatcher
from src.slicer import VideoSlicer

def run_pipeline(url: str = None, query: str = "GTA 6 Hindi", output_dir: str = "output"):
    out_path = Path(output_dir)
    out_path.mkdir(parents=True, exist_ok=True)

    print("=" * 60)
    print("🎬 Project Clipper: Live Stream Topic Matcher & Slicer")
    print("=" * 60)

    # 1. Fetch Stream if not provided
    if not url:
        print(f"\n[1/5] Fetching best performing stream for query: '{query}'...")
        fetcher = StreamFetcher()
        best_stream = fetcher.get_best_stream(platform="youtube", query=query)
        if not best_stream:
            print("❌ No streams found.")
            return
        url = best_stream["url"]
        print(f"🎯 Selected Stream: \"{best_stream['title']}\"")
        print(f"🔗 URL: {url}")
    else:
        print(f"\n[1/5] Using provided Target URL: {url}")

    # 2. Ingestion
    print("\n[2/5] Ingesting test segment (90s window)...")
    ingester = StreamIngester(output_dir="downloads")
    sample_file = ingester.download_clip_sample(
        url=url,
        output_name="gta_test_sample.mp4",
        start_time="00:03:00",
        duration_sec=90
    )

    if not sample_file or not sample_file.exists():
        print("❌ Failed to download sample segment.")
        return

    print(f"✅ Ingested: {sample_file} ({sample_file.stat().st_size / (1024*1024):.2f} MB)")

    # 3. Transcription
    print("\n[3/5] Running MLX-Whisper on Metal GPU...")
    transcriber = Transcriber(model_name="mlx-community/whisper-large-v3-turbo")
    segments = transcriber.transcribe(str(sample_file))
    print(f"✅ Transcribed {len(segments)} spoken segments.")

    # 4. Topic Matching
    print("\n[4/5] Scanning transcripts for Hot Search Topics...")
    matcher = TopicMatcher()
    candidate_moments = []

    for seg in segments:
        matches = matcher.scan_segment(seg["text"])
        if matches:
            candidate_moments.append({
                "start": seg["start"],
                "end": seg["end"],
                "text": seg["text"],
                "matches": matches
            })
            print(f"  🎯 [{seg['start']:.1f}s - {seg['end']:.1f}s]: \"{seg['text']}\"")
            for m in matches:
                print(f"     -> Category: {m['category']} (Triggers: {m['matched_keywords']})")

    # 5. Slicing & Vertical Formatting
    print("\n[5/5] Generating 9:16 Vertical Short...")
    slicer = VideoSlicer()

    if candidate_moments:
        best_moment = candidate_moments[0]
        clip_start = max(0.0, best_moment["start"] - 5.0)
        clip_duration = min(40.0, (best_moment["end"] - clip_start) + 15.0)
        clip_duration = max(20.0, clip_duration)
        clip_title = best_moment["matches"][0]["topic_id"]
    else:
        print("ℹ️ No specific topic trigger found in this 90s sample. Using highlight window [15s-45s].")
        clip_start = 15.0
        clip_duration = 30.0
        clip_title = "gta_highlight"

    output_clip = out_path / f"{clip_title}_short_9x16.mp4"
    print(f"Rendering vertical clip from {clip_start:.1f}s for {clip_duration:.1f}s -> {output_clip}")
    
    success = slicer.slice_clip(
        input_path=str(sample_file),
        start_sec=clip_start,
        duration_sec=clip_duration,
        output_path=str(output_clip),
        style="blur_bg"
    )

    if success and output_clip.exists():
        print(f"\n🎉 SUCCESS! Generated Short:")
        print(f"File: {output_clip}")
        print(f"Size: {output_clip.stat().st_size / (1024*1024):.2f} MB")
    else:
        print("❌ Slicing failed.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run the end-to-end Clipper pipeline.")
    parser.add_argument("--url", help="Direct stream/video URL to process.")
    parser.add_argument("--query", default="GTA 6 Hindi", help="Search query to auto-fetch the best stream.")
    parser.add_argument("--output_dir", default="output", help="Directory for rendered clips.")
    args = parser.parse_args()

    run_pipeline(url=args.url, query=args.query, output_dir=args.output_dir)

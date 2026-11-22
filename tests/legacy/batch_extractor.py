import json
import subprocess
from pathlib import Path
from typing import List, Dict, Any

from src.transcribe import Transcriber
from src.matcher import TopicMatcher
from src.scorer import ViralityScorer
from src.slicer import VideoSlicer

def extract_top_bucket_clips(
    video_url: str,
    audio_path: str,
    streamer_name: str = "CarryMinati",
    target_count: int = 5,
    output_dir: str = "output"
):
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    temp_dir = Path("downloads")
    ytdlp_bin = "/Users/vismaythaker/workspace/projects/Clipper/.venv/bin/yt-dlp"

    print("=" * 65)
    print(f"🎯 Intelligent 30s Window Virality Extractor: {streamer_name}")
    print(f"Video: {video_url}")
    print("=" * 65)

    # 1. Transcribe full audio
    print("\n[1/4] Transcribing audio with MLX Whisper on Metal GPU...")
    transcriber = Transcriber(model_name="mlx-community/whisper-large-v3-turbo")
    segments = transcriber.transcribe(audio_path)
    print(f"✅ Extracted {len(segments)} micro-segments.")

    # 2. Build 30-second conversational windows
    print("\n[2/4] Constructing 30-second rolling narrative windows...")
    windows = []
    max_time = int(segments[-1]["end"]) if segments else 0
    matcher = TopicMatcher()

    for start_t in range(0, max_time, 25):
        end_t = start_t + 30
        chunk_texts = [s["text"].strip() for s in segments if start_t <= s["start"] < end_t]
        if not chunk_texts:
            continue
        combined_text = " ".join(chunk_texts)
        words = combined_text.split()
        
        # Filter out silent or repetitive static loops
        if len(words) < 8 or len(set(words)) < 5:
            continue

        topic_matches = matcher.scan_segment(combined_text)
        windows.append({
            "start": start_t,
            "end": end_t,
            "text": combined_text,
            "matches": topic_matches
        })

    print(f"✅ Created {len(windows)} valid 30-second conversational windows.")

    # 3. Score windows with Local SLM (Qwen2.5-1.5B)
    print("\n[3/4] Evaluating windows with Local SLM Virality Scorer...")
    scorer = ViralityScorer()
    scored_candidates = []

    for w in windows:
        score_res = scorer.score_transcript(w["text"], streamer_name=streamer_name)
        v_score = score_res.get("virality_score", 0)
        
        # Categorize: use top matched bucket or default to streamer reaction
        if w["matches"]:
            bucket_id = w["matches"][0]["topic_id"]
            category = w["matches"][0]["category"]
        else:
            bucket_id = "T3_13_streamer_reaction"
            category = "Streamer Reaction & Hype"

        print(f"  Window [{w['start']}s - {w['end']}s]: Score {v_score}/100 (Hook: {score_res.get('hook_score')} | Hype: {score_res.get('hype_or_humor')})")
        print(f"    Title: \"{score_res.get('viral_title')}\"")

        if score_res.get("should_clip") and v_score >= 70:
            scored_candidates.append({
                "start": w["start"],
                "end": w["end"],
                "text": w["text"],
                "topic_id": bucket_id,
                "category": category,
                "score": v_score,
                "title": score_res.get("viral_title"),
                "reason": score_res.get("why_viral")
            })

    # Pick top distinct buckets
    seen_buckets = set()
    selected_clips = []
    
    # Sort by virality score descending
    scored_candidates = sorted(scored_candidates, key=lambda x: x["score"], reverse=True)
    for c in scored_candidates:
        if c["topic_id"] not in seen_buckets:
            seen_buckets.add(c["topic_id"])
            selected_clips.append(c)
        if len(selected_clips) >= target_count:
            break

    # If we need more to reach target_count, fill with remaining high-scoring candidates
    if len(selected_clips) < target_count:
        for c in scored_candidates:
            if c not in selected_clips:
                selected_clips.append(c)
            if len(selected_clips) >= target_count:
                break

    print(f"\n🏆 Selected Top {len(selected_clips)} Viral Clips:")
    for i, c in enumerate(selected_clips, 1):
        print(f"  {i}. [{c['topic_id']}] @ {c['start']}s: \"{c['title']}\" (Score: {c['score']}/100)")

    # 4. Pull video slices & render 9:16 vertical shorts
    print(f"\n[4/4] Slicing & Rendering {len(selected_clips)} Vertical 9:16 Shorts...")
    slicer = VideoSlicer()
    rendered_files = []

    for i, clip in enumerate(selected_clips, 1):
        start_sec = max(0, clip["start"])
        end_sec = min(start_sec + 30, max_time)
        duration = end_sec - start_sec

        topic_id = clip["topic_id"]
        temp_video = temp_dir / f"raw_win_{topic_id}_{start_sec}.mp4"
        clean_title = "".join(c for c in clip["title"] if c.isalnum() or c in (" ", "_", "-")).strip().replace(" ", "_")[:30]
        out_short = out_dir / f"{streamer_name}_{topic_id}_{clean_title}_9x16.mp4"

        print(f"\n[{i}/{len(selected_clips)}] Pulling video slice [{start_sec}s - {end_sec}s] -> {out_short.name}...")
        cmd = [
            ytdlp_bin,
            "--ffmpeg-location", "/opt/homebrew/bin/ffmpeg",
            "--download-sections", f"*{start_sec}-{end_sec}",
            "-f", "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",
            "--force-overwrites",
            "--no-warnings",
            "-o", str(temp_video),
            video_url
        ]
        subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        if temp_video.exists():
            print(f"🎨 Rendering 9:16 layout (blur background + synced audio)...")
            slicer.slice_clip(
                input_path=str(temp_video),
                start_sec=0.0,
                duration_sec=float(duration),
                output_path=str(out_short),
                style="blur_bg"
            )
            temp_video.unlink(missing_ok=True)
            if out_short.exists():
                print(f"🎉 Generated: {out_short.name} ({out_short.stat().st_size / (1024*1024):.2f} MB)")
                rendered_files.append(out_short)

    print("\n" + "=" * 65)
    print(f"🚀 FINISHED! Successfully created {len(rendered_files)} Shorts in {output_dir}/")
    print("=" * 65)
    return rendered_files

if __name__ == "__main__":
    extract_top_bucket_clips(
        video_url="https://www.youtube.com/watch?v=mJVVZbPGDdw",
        audio_path="downloads/carry_heist_full_audio.m4a",
        streamer_name="CarryMinati",
        target_count=5
    )

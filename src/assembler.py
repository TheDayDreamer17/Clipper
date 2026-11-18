import subprocess
import shutil
from pathlib import Path
from typing import List, Dict, Any, Optional
from src.slicer import VideoSlicer

class MultiClipAssembler:
    """
    Assembles multiple time-sliced segments, trims dead-air/filler,
    and stitches them into a unified vertical 9:16 short with glassmorphic UI.
    """
    def __init__(self, temp_dir: Optional[str] = None):
        self.temp_dir = Path(temp_dir or "downloads/assembly_temp")
        self.temp_dir.mkdir(parents=True, exist_ok=True)
        self.slicer = VideoSlicer()
        self.ffmpeg_bin = "/opt/homebrew/bin/ffmpeg"

    def assemble_segments(
        self,
        input_video: str,
        slices: List[Dict[str, float]],
        output_path: str,
        banner_title: str,
        banner_subtitle: str,
        banner_tag: str = "🔥 HIGHLIGHT"
    ) -> Path:
        """
        Takes slices: [{'start': 12.0, 'end': 19.5}, {'start': 32.0, 'end': 44.0}],
        removes dead air between them, and stitches them into a single high-action Short.
        """
        out_p = Path(output_path)
        out_p.parent.mkdir(parents=True, exist_ok=True)

        if not slices:
            raise ValueError("No time slices provided for assembly!")

        # 1. Extract each sub-segment into intermediate MP4
        temp_clips = []
        for idx, sl in enumerate(slices):
            s_start = sl["start"]
            s_dur = sl["end"] - sl["start"]
            seg_out = self.temp_dir / f"seg_{idx}_{int(s_start)}_{int(s_dur)}.mp4"

            cmd = [
                self.ffmpeg_bin, "-y",
                "-ss", str(s_start),
                "-t", str(s_dur),
                "-i", input_video,
                "-c:v", "libx264", "-preset", "veryfast", "-crf", "18",
                "-c:a", "aac", "-b:a", "192k", "-ar", "44100",
                str(seg_out)
            ]
            subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            if seg_out.exists():
                temp_clips.append(seg_out)

        if not temp_clips:
            raise RuntimeError("Failed to extract any sub-segments!")

        # 2. If single segment, format directly to vertical 9:16
        if len(temp_clips) == 1:
            stitched_raw = temp_clips[0]
        else:
            # Concat multiple segments using FFmpeg concat filter
            stitched_raw = self.temp_dir / "stitched_raw.mp4"
            inputs = []
            filter_parts = []
            for i, c in enumerate(temp_clips):
                inputs.extend(["-i", str(c)])
                filter_parts.append(f"[{i}:v:0][{i}:a:0]")

            filter_complex = f"{''.join(filter_parts)}concat=n={len(temp_clips)}:v=1:a=1[outv][outa]"
            cmd_concat = [
                self.ffmpeg_bin, "-y",
                *inputs,
                "-filter_complex", filter_complex,
                "-map", "[outv]",
                "-map", "[outa]",
                "-c:v", "libx264", "-preset", "veryfast", "-crf", "18",
                "-c:a", "aac", "-b:a", "192k",
                str(stitched_raw)
            ]
            subprocess.run(cmd_concat, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        # 3. Apply 9:16 mobile canvas + glassmorphic banner UI
        total_dur = sum(sl["end"] - sl["start"] for sl in slices)
        self.slicer.slice_clip(
            input_path=str(stitched_raw),
            start_sec=0.0,
            duration_sec=total_dur,
            output_path=str(out_p),
            overlay_text=banner_title,
            overlay_subtitle=banner_subtitle,
            tag_text=banner_tag
        )

        return out_p

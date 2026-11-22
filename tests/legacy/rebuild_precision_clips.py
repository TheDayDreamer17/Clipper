import sys
import subprocess
from pathlib import Path

sys.path.append(str(Path(__file__).parent))
from src.slicer import VideoSlicer
from src.ingest import StreamIngester

def run():
    print("=" * 60)
    print("🎯 RE-SLICING WITH PRECISION CLIMAX BOUNDARY ANCHORING")
    print("=" * 60)

    slicer = VideoSlicer()
    ingest = StreamIngester(output_dir="downloads")

    # -----------------------------------------------------------------
    # 1. CHARACTER SWITCHING: Cut from 17.5s to 38.5s (21s Duration)
    #    Starts right when wheel opens -> satellite orbit -> lands on Franklin!
    # -----------------------------------------------------------------
    print("\n[1/3] Slicing Character Switch with Zero-Filler Climax...")
    char_src = "downloads/character_switch_full.mp4.webm"
    char_out = "output/english/gta6_character_switching_satellite_orbit_9x16.mp4"
    slicer.slice_clip(
        input_path=char_src,
        start_sec=17.5,
        duration_sec=21.0,
        output_path=char_out,
        overlay_text="GTA 6 Seamless Character Switch",
        overlay_subtitle="SATELLITE ZOOM & ORBIT TRANSITION"
    )
    print(f"✅ Generated: {char_out}")

    # -----------------------------------------------------------------
    # 2. CARMEN TWITCH CLIP: Cut from 25.0s to 45.0s (20s Duration)
    #    Cuts out the 24s filler -> 100% screaming climax & payoff!
    # -----------------------------------------------------------------
    print("\n[2/3] Slicing Carmen Clip with Pure Climax Payoff (25s - 45s)...")
    carmen_src = "downloads/twitch_carmen_raw.mp4"
    carmen_out = "output/twitch_auto/twitch_carmen_killer_reveal_reaction_9x16.mp4"
    slicer.slice_clip(
        input_path=carmen_src,
        start_sec=25.0,
        duration_sec=20.0,
        output_path=carmen_out,
        overlay_text="CARMELLA DISCOVERS THE KILLER!",
        overlay_subtitle="NOPIXEL RP LIVE TWITCH REACTION"
    )
    print(f"✅ Generated: {carmen_out}")

    # -----------------------------------------------------------------
    # 3. CARRYMINATI INTENSE FIREFIGHT: Download 195s to 225s of mJVVZbPGDdw
    #    Real helicopter shootout & RPG attack from the heist!
    # -----------------------------------------------------------------
    print("\n[3/3] Ingesting CarryMinati Helicopter RPG Shootout (195s - 225s)...")
    carry_url = "https://www.youtube.com/watch?v=mJVVZbPGDdw"
    carry_chunk = ingest.download_clip_sample(
        url=carry_url,
        output_name="carry_heist_shootout_chunk.mp4",
        start_time="195",
        duration_sec=30
    )
    carry_out = "output/hindi/carryminati_helicopter_shootout_climax_9x16.mp4"
    slicer.slice_clip(
        input_path=str(carry_chunk),
        start_sec=0.0,
        duration_sec=28.0,
        output_path=carry_out,
        overlay_text="CARRYMINATI UNDER RPG ATTACK!",
        overlay_subtitle="GTA 6 HELICOPTER FIREFIGHT (4-STAR WANTED)"
    )
    print(f"✅ Generated: {carry_out}")

    print("\n" + "=" * 60)
    print("🎉 PRECISION-ANCHORED CLIPS REBUILT SUCCESSFULLY!")
    print("=" * 60)

if __name__ == "__main__":
    run()

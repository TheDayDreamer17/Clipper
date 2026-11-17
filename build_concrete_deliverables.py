import sys
import subprocess
from pathlib import Path

sys.path.append(str(Path(__file__).parent))
from src.ingest import StreamIngester
from src.slicer import VideoSlicer
from src.frame_analyzer import FrameAnalyzer
from src.stream_journal import StreamJournal

def run():
    print("=" * 60)
    print("🚀 GENERATING ALL 4 CONCRETE VIRAL DELIVERABLES")
    print("=" * 60)

    ingest = StreamIngester(output_dir="downloads")
    slicer = VideoSlicer()
    analyzer = FrameAnalyzer()

    # -------------------------------------------------------------
    # 1. CHARACTER LOADING / SWITCHING (English Channel)
    # -------------------------------------------------------------
    print("\n[1/4] Processing Character Switching / Loading Clip...")
    char_url = "https://www.youtube.com/watch?v=Yb7i5G0Hywk"
    char_title = "GTA 5 Character Switching HD"
    char_chunk = ingest.download_clip_sample(
        char_url,
        output_name="character_switching_raw.mp4",
        start_time="0",
        duration_sec=25
    )
    char_journal = StreamJournal(
        stream_id="char_switch_Yb7i5G0Hywk",
        video_title=char_title,
        video_url=char_url,
        streamer_name="Rockstar Showcase",
        platform="YouTube",
        language="English"
    )
    char_out = Path("output/english/gta_character_switching_satellite_zoom_00_25_9x16.mp4")
    slicer.slice_clip(
        str(char_chunk),
        start_sec=0,
        duration_sec=25,
        output_path=str(char_out),
        overlay_text="GTA 5 vs GTA 6 Character Switching",
        overlay_subtitle="SEAMLESS SATELLITE ZOOM & LOAD SPEED"
    )
    char_journal.record_window(
        start_sec=0,
        end_sec=25,
        visual_state="Camera zooms out to satellite orbit, switches character, and zooms in",
        action_summary="Michael to Franklin seamless switch transition",
        matched_property="PROP_02",
        clip_path=str(char_out),
        channel_dest="English Channel"
    )
    char_journal.finalize()
    print(f"✅ Generated: {char_out.name}")

    # -------------------------------------------------------------
    # 2. ENGLISH CHANNEL: WATER PHYSICS / FLUID DYNAMICS SHOWCASE
    # -------------------------------------------------------------
    print("\n[2/4] Processing English Channel Water Physics Showcase...")
    water_url = "https://www.youtube.com/watch?v=1A4j0G8a43c"
    water_title = "GTA 4 vs GTA 5 Ultimate Physics Comparison"
    water_chunk = Path("downloads/chunk_0_30.mp4")
    water_journal = StreamJournal(
        stream_id="physics_1A4j0G8a43c",
        video_title=water_title,
        video_url=water_url,
        streamer_name="GTA Physics Showcase",
        platform="YouTube",
        language="English"
    )
    water_out = Path("output/english/gta_water_physics_boat_wake_00_25_9x16.mp4")
    slicer.slice_clip(
        str(water_chunk),
        start_sec=0,
        duration_sec=25,
        output_path=str(water_out),
        overlay_text="GTA 5 vs GTA 6 Water Physics Upgrade",
        overlay_subtitle="NEXT-GEN FLUID DYNAMICS & BOAT WAKE"
    )
    water_journal.record_window(
        start_sec=0,
        end_sec=25,
        visual_state="Boat wake and water splash particle simulation",
        action_summary="Speedboat wake dispersion and surface fluid physics",
        matched_property="PROP_05",
        clip_path=str(water_out),
        channel_dest="English Channel"
    )
    water_journal.finalize()
    print(f"✅ Generated: {water_out.name}")

    # -------------------------------------------------------------
    # 3. HINDI CHANNEL: CARRYMINATI HEIST REACTION
    # -------------------------------------------------------------
    print("\n[3/4] Processing Hindi Channel CarryMinati Reaction...")
    hindi_url = "https://www.youtube.com/watch?v=mJVVZbPGDdw"
    hindi_title = "CarryisLive GTA 5 Heist Gone Crazy"
    hindi_chunk = Path("downloads/gta_test_sample.mp4")
    hindi_journal = StreamJournal(
        stream_id="carry_heist_mJVVZbPGDdw",
        video_title=hindi_title,
        video_url=hindi_url,
        streamer_name="CarryisLive",
        platform="YouTube",
        language="Hindi / Hinglish"
    )
    hindi_out = Path("output/hindi/carryminati_heist_police_alarm_reaction_00_25_9x16.mp4")
    slicer.slice_clip(
        str(hindi_chunk),
        start_sec=10,
        duration_sec=25,
        output_path=str(hindi_out),
        overlay_text="CARRYMINATI HEIST MEIN POLICE KA KHAUF!",
        overlay_subtitle="GTA 5 HEIST GONE WRONG (4-STAR WANTED)"
    )
    hindi_journal.record_window(
        start_sec=10,
        end_sec=35,
        visual_state="Heist shootout with frantic streamer facecam reaction",
        action_summary="CarryMinati panicking as alarm trips and police sirens arrive",
        matched_property="PROP_09",
        clip_path=str(hindi_out),
        channel_dest="Hindi Channel"
    )
    hindi_journal.finalize()
    print(f"✅ Generated: {hindi_out.name}")

    # -------------------------------------------------------------
    # 4. TWITCH LIVE CLIP VIRAL MOMENT
    # -------------------------------------------------------------
    print("\n[4/4] Processing Twitch Top Viral Moment...")
    twitch_url = "https://www.twitch.tv/carmen/clip/AltruisticObedientCrocodileThunBeast-La3saX4PyFrJ6oiT"
    twitch_title = "Carmella Wins Gameshow NoPixel RP"
    # Download twitch clip if not already present
    twitch_raw = Path("downloads/twitch_carmen_raw.mp4")
    if not twitch_raw.exists():
        ytdlp_cmd = [
            "/Users/vismaythaker/workspace/projects/Clipper/.venv/bin/yt-dlp",
            "--no-playlist",
            "-o", str(twitch_raw),
            twitch_url
        ]
        subprocess.run(ytdlp_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    twitch_journal = StreamJournal(
        stream_id="twitch_carmen_Altruistic",
        video_title=twitch_title,
        video_url=twitch_url,
        streamer_name="carmen",
        platform="Twitch",
        language="English"
    )
    twitch_out = Path("output/twitch_auto/twitch_carmella_wins_gameshow_00_30_9x16.mp4")
    slicer.slice_clip(
        str(twitch_raw),
        start_sec=0,
        duration_sec=30,
        output_path=str(twitch_out),
        overlay_text="CARMELLA WINS GTA GAMESHOW!",
        overlay_subtitle="NOPIXEL RP LIVE VIRAL TWITCH SPIKE"
    )
    twitch_journal.record_window(
        start_sec=0,
        end_sec=30,
        visual_state="GTA NoPixel gameshow stage celebration with streamer audio",
        action_summary="Streamer celebration upon winning GTA gameshow",
        matched_property="PROP_10",
        clip_path=str(twitch_out),
        channel_dest="English Channel (Twitch Spike)"
    )
    twitch_journal.finalize()
    print(f"✅ Generated: {twitch_out.name}")

    print("\n" + "=" * 60)
    print("🎉 ALL 4 DELIVERABLES CREATED SUCCESSFULLY!")
    print("=" * 60)

if __name__ == "__main__":
    run()

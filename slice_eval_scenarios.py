from pathlib import Path
from src.slicer import VideoSlicer

def slice_all():
    slicer = VideoSlicer()
    out_dir = Path("output/eval_scenarios")
    out_dir.mkdir(parents=True, exist_ok=True)

    items = [
        {
            "in": "downloads/eval_loading_art.mp4",
            "out": "output/eval_scenarios/01_loading_character_artwork_9x16.mp4",
            "start": 0.0,
            "dur": 15.0,
            "tag": "🔥 GTA ARTWORK",
            "title": "OFFICIAL CHARACTER ARTWORK",
            "sub": "ROTATING LOADING SCREEN SLIDES"
        },
        {
            "in": "downloads/eval_police_chase.mp4",
            "out": "output/eval_scenarios/02_police_chase_3stars_9x16.mp4",
            "start": 0.0,
            "dur": 15.0,
            "tag": "🚨 3-STAR WANTED",
            "title": "HIGH SPEED POLICE CHASE",
            "sub": "LOS SANTOS CRUISER PURSUIT"
        },
        {
            "in": "downloads/eval_weapon_shootout.mp4",
            "out": "output/eval_scenarios/03_weapon_wheel_gunfight_9x16.mp4",
            "start": 0.0,
            "dur": 15.0,
            "tag": "🎯 WEAPON WHEEL",
            "title": "GUNFIGHT COMBAT SHOOTOUT",
            "sub": "RADIAL SELECTION & COVER FIRE"
        },
        {
            "in": "downloads/eval_heli_sunset.mp4",
            "out": "output/eval_scenarios/04_heli_flight_sunset_9x16.mp4",
            "start": 0.0,
            "dur": 15.0,
            "tag": "🚁 AERIAL VIEW",
            "title": "HELICOPTER SUNSET FLIGHT",
            "sub": "LOS SANTOS HORIZON SKYLINE"
        },
        {
            "in": "downloads/eval_rain_night.mp4",
            "out": "output/eval_scenarios/05_rainy_night_driving_9x16.mp4",
            "start": 0.0,
            "dur": 15.0,
            "tag": "🌧️ WET ASPHALT",
            "title": "RAINY NIGHT CITY DRIVING",
            "sub": "DYNAMIC WEATHER & REFLECTIONS"
        },
        {
            "in": "downloads/eval_driving_views.mp4",
            "out": "output/eval_scenarios/06_fpv_cockpit_driving_9x16.mp4",
            "start": 5.0,
            "dur": 15.0,
            "tag": "🚗 FIRST PERSON",
            "title": "IN-CAR COCKPIT DRIVING",
            "sub": "STEERING WHEEL & DASHBOARD POV"
        }
    ]

    for item in items:
        in_p = Path(item["in"])
        if not in_p.exists():
            print(f"Skipping {item['out']} (input not found: {in_p})")
            continue
        print(f"🎬 Slicing {item['out']}...")
        slicer.slice_clip(
            input_path=str(in_p),
            start_sec=item["start"],
            duration_sec=item["dur"],
            output_path=item["out"],
            overlay_text=item["title"],
            overlay_subtitle=item["sub"],
            tag_text=item["tag"]
        )
    print("🎉 All 6 scenario clips sliced successfully!")

if __name__ == "__main__":
    slice_all()

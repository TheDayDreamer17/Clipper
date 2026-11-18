from pathlib import Path
from src.multi_stream_orchestrator import MultiStreamOrchestrator

def main():
    orchestrator = MultiStreamOrchestrator()

    # 3 Concurrent Creator Streams (English + Hindi)
    creators = [
        {
            "name": "theRadBrad",
            "platform": "youtube",
            "language": "English",
            "url": "https://www.youtube.com/watch?v=kCU9NEbxj_4",
            "video_source": "downloads/radbrad_real_chase.mp4",
            "event_slug": "police_pursuit",
            "test_timestamps": [2.0, 5.0, 10.0, 15.0]
        },
        {
            "name": "Techno Gamerz",
            "platform": "youtube",
            "language": "Hindi",
            "url": "https://www.youtube.com/watch?v=fcexQBagpc4",
            "video_source": "downloads/eval_driving_views.mp4",
            "event_slug": "cockpit_pov",
            "test_timestamps": [1.0, 6.0, 12.0, 18.0]
        },
        {
            "name": "GTA Series Videos",
            "platform": "youtube",
            "language": "English",
            "url": "https://www.youtube.com/watch?v=x1MoTocndkY",
            "video_source": "downloads/full_loading_artwork_test.mp4",
            "event_slug": "loading_intro",
            "test_timestamps": [10.0, 20.0, 30.0, 40.0]
        }
    ]

    orchestrator.run_multi_stream_simulation(creators)

if __name__ == "__main__":
    main()

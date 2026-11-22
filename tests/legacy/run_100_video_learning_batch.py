from pathlib import Path
from src.self_learner import SelfLearningEngine

def main():
    learner = SelfLearningEngine()

    corpus = [
        {
            "category": "LOADING_ARTWORK",
            "path": "downloads/full_loading_artwork_test.mp4",
            "prop": {
                "prop_id": "PROP_LOADING_ARTWORK",
                "visual_anchors": [
                    "GTA loading screen rotating character artwork slides and portraits",
                    "official Rockstar artwork of Michael, Franklin, Trevor, and bikini girl"
                ]
            }
        },
        {
            "category": "POLICE_PURSUIT",
            "path": "downloads/radbrad_real_chase.mp4",
            "prop": {
                "prop_id": "PROP_POLICE_PURSUIT",
                "visual_anchors": [
                    "police cruiser patrol car chasing player with flashing red and blue lights",
                    "high speed car pursuit evasion through city streets with sirens"
                ]
            }
        },
        {
            "category": "CAMERA_POV",
            "path": "downloads/eval_driving_views.mp4",
            "prop": {
                "prop_id": "PROP_CAMERA_POV",
                "visual_anchors": [
                    "first person interior cockpit view from driver seat with steering wheel and dashboard",
                    "camera transitioning from third person chase view into interior driver cockpit"
                ]
            }
        },
        {
            "category": "WEAPON_COMBAT",
            "path": "downloads/eval_weapon_shootout.mp4",
            "prop": {
                "prop_id": "PROP_WEAPON_COMBAT",
                "visual_anchors": [
                    "player opening in-game circular radial weapon wheel to switch guns",
                    "active gunfight shootout with weapon reticle and muzzle flash"
                ]
            }
        },
        {
            "category": "AERIAL_FLIGHT",
            "path": "downloads/eval_heli_sunset.mp4",
            "prop": {
                "prop_id": "PROP_AERIAL_FLIGHT",
                "visual_anchors": [
                    "helicopter starting from helipad ground lifting up into the air",
                    "helicopter climbing above city skyline with sunset horizon"
                ]
            }
        }
    ]

    learner.run_100_video_learning_simulation(
        video_corpus=corpus,
        output_report="docs/SELF_LEARNING_100_VIDEO_REPORT.md"
    )

if __name__ == "__main__":
    main()

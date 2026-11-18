import json
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Dict, List, Any, Optional
import torch
from transformers import CLIPProcessor, CLIPModel

class TrendMiner:
    """
    Autonomous 15-Minute Dynamic Trend Miner & Game Knowledge Enrichment Engine.
    Queries live search auto-complete demand and synthesizes high-precision Target Props.
    """
    def __init__(self, device: Optional[str] = None):
        self.device = device or ("mps" if torch.backends.mps.is_available() else "cpu")
        self.clip_proc = None
        self.clip_model = None

    def _lazy_load_clip(self):
        if self.clip_model is None:
            self.clip_proc = CLIPProcessor.from_pretrained("openai/clip-vit-base-patch32")
            self.clip_model = CLIPModel.from_pretrained("openai/clip-vit-base-patch32").to(self.device)

    def fetch_live_search_trends(self, seed_queries: Optional[List[str]] = None) -> List[str]:
        """
        Polls real-time YouTube search demand for high-velocity user queries.
        Returns clean, unique trending query strings.
        """
        seeds = seed_queries or [
            "gta 6 ", "gta 6 gameplay ", "gta 6 police ", "gta 6 cars ",
            "gta 6 graphics ", "gta 6 first person "
        ]
        results = set()
        for seed in seeds:
            try:
                url = f"https://suggestqueries.google.com/complete/search?client=firefox&ds=yt&q={urllib.parse.quote(seed)}"
                req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
                with urllib.request.urlopen(req, timeout=5) as resp:
                    data = json.loads(resp.read().decode("utf-8"))
                    for q in data[1]:
                        results.add(q.strip().lower())
            except Exception as e:
                pass
        return sorted(list(results))

    def map_gta6_to_gta5_equivalent(self, query: str) -> Dict[str, Any]:
        """
        Maps a trending GTA 6 query to its corresponding GTA 5 benchmark scenario
        for pre-release testing and validation.
        """
        q = query.lower()
        if any(w in q for w in ["police", "chase", "cop", "wanted", "pursuit", "stars"]):
            return {
                "category": "POLICE_PURSUIT",
                "gta6_topic": "Vice City Metro Police 3-Star Cruiser Ambush",
                "gta5_equivalent": "Los Santos High-Speed 3-Star Police Pursuit with Cruisers & Sirens",
                "test_anchor": "police cruisers pursuing player with sirens, roadblocks and wanted stars"
            }
        elif any(w in q for w in ["first person", "fpv", "cockpit", "interior", "pov", "camera"]):
            return {
                "category": "CAMERA_POV",
                "gta6_topic": "Vehicle Interior Cockpit FPV with Functional Mirrors",
                "gta5_equivalent": "In-Car Cockpit Driving with Steering Wheel & Dashboard Toggle",
                "test_anchor": "first person driver cockpit view inside vehicle showing steering wheel"
            }
        elif any(w in q for w in ["helicopter", "plane", "flying", "heli", "aerial", "sky"]):
            return {
                "category": "AERIAL_FLIGHT",
                "gta6_topic": "Maverick Helicopter Flight Over Vice Beach Sunset",
                "gta5_equivalent": "Helicopter Helipad Ground Takeoff to Los Santos Skyline",
                "test_anchor": "helicopter takeoff from ground climbing up over city skyline at sunset"
            }
        elif any(w in q for w in ["loading", "intro", "boot", "artwork", "characters"]):
            return {
                "category": "LOADING_ARTWORK",
                "gta6_topic": "Official Lucia & Jason Launch Loading Artwork Slides",
                "gta5_equivalent": "Complete Character Artwork Rotation (Michael, Franklin, Trevor, Bikini Girl)",
                "test_anchor": "GTA loading screen rotating character artwork portraits and title logo"
            }
        elif any(w in q for w in ["weapon", "gun", "inventory", "shoot", "combat", "wheel"]):
            return {
                "category": "WEAPON_COMBAT",
                "gta6_topic": "Physical Weapon Sling & Tactical Firefight",
                "gta5_equivalent": "In-Game Radial Weapon Wheel Selection & Combat Shootout",
                "test_anchor": "player aiming gun with weapon wheel circular selector menu open in combat"
            }
        else:
            return {
                "category": "DYNAMIC_DRIVING",
                "gta6_topic": "Next-Gen Vehicle Physics & Wet Road SSR",
                "gta5_equivalent": "Rainy Night Wet Road Driving with Neon Reflections",
                "test_anchor": "car driving on wet city street at night with rain reflections"
            }

    def enrich_trend_into_precision_prop(self, mapped_concept: Dict[str, Any]) -> Dict[str, Any]:
        """
        Enriches a raw trend into an exhaustive, high-precision detection Prop
        with positive anchors, negative disqualifiers, and HUD triggers.
        """
        cat = mapped_concept["category"]

        if cat == "POLICE_PURSUIT":
            return {
                "prop_id": "PROP_POLICE_PURSUIT_ENRICHED",
                "category": cat,
                "name": mapped_concept["gta5_equivalent"],
                "visual_anchors": [
                    "police cruiser patrol car chasing player with flashing red and blue lights",
                    "high speed car pursuit evasion through city streets with sirens",
                    "cop cars attempting pit maneuver or roadblock"
                ],
                "negative_anchors": [
                    "calm street driving with no police cars",
                    "walking on sidewalk",
                    "retail store interior",
                    "loading screen"
                ],
                "hud_verification_rules": {
                    "must_have": ["wanted stars or flashing red/blue minimap radar"],
                    "vqa_prompt": "Are there police cars chasing or flashing wanted stars on screen?"
                },
                "banner_ui": {
                    "tag": "🚨 3-STAR WANTED",
                    "title": "HIGH SPEED POLICE CHASE",
                    "subtitle": "LOS SANTOS CRUISER PURSUIT & ESCAPE"
                }
            }

        elif cat == "CAMERA_POV":
            return {
                "prop_id": "PROP_CAMERA_POV_ENRICHED",
                "category": cat,
                "name": mapped_concept["gta5_equivalent"],
                "visual_anchors": [
                    "first person interior cockpit view from driver seat with steering wheel and dashboard",
                    "camera transitioning from third person chase view into interior driver cockpit",
                    "hands holding steering wheel driving car from first person perspective"
                ],
                "negative_anchors": [
                    "third person camera hovering behind the bumper",
                    "cinematic cutscene",
                    "walking on foot"
                ],
                "hud_verification_rules": {
                    "must_have": ["visible dashboard gauges or steering wheel"],
                    "vqa_prompt": "Is this a first person camera view from inside the car cockpit?"
                },
                "banner_ui": {
                    "tag": "🚗 FIRST PERSON",
                    "title": "IN-CAR COCKPIT POV",
                    "subtitle": "STEERING WHEEL & DASHBOARD CAMERA TOGGLE"
                }
            }

        elif cat == "AERIAL_FLIGHT":
            return {
                "prop_id": "PROP_AERIAL_FLIGHT_ENRICHED",
                "category": cat,
                "name": mapped_concept["gta5_equivalent"],
                "visual_anchors": [
                    "helicopter starting from helipad ground lifting up into the air",
                    "helicopter climbing above city skyline with sunset horizon",
                    "aerial panoramic view from aircraft over skyscrapers"
                ],
                "negative_anchors": [
                    "car driving on asphalt road",
                    "subway tunnel",
                    "indoor gunfight"
                ],
                "hud_verification_rules": {
                    "must_have": ["helicopter blades or cockpit altimeter"],
                    "vqa_prompt": "Is a helicopter lifting off or flying over the city?"
                },
                "banner_ui": {
                    "tag": "🚁 AERIAL VIEW",
                    "title": "HELICOPTER GROUND TAKEOFF",
                    "subtitle": "ROTOR SPOOL-UP TO SKYLINE SUNSET"
                }
            }

        elif cat == "LOADING_ARTWORK":
            return {
                "prop_id": "PROP_LOADING_ARTWORK_ENRICHED",
                "category": cat,
                "name": mapped_concept["gta5_equivalent"],
                "visual_anchors": [
                    "GTA loading screen rotating character artwork slides and portraits",
                    "official Rockstar artwork of Michael, Franklin, Trevor, and bikini girl",
                    "loading screen transition with background artwork into game world"
                ],
                "negative_anchors": [
                    "active 3D in-game camera driving or walking",
                    "dark black screen with no artwork",
                    "pause settings menu"
                ],
                "hud_verification_rules": {
                    "must_have": ["loading icon or artwork character illustrations"],
                    "vqa_prompt": "Is this a loading screen displaying 2D character artwork?"
                },
                "banner_ui": {
                    "tag": "🔥 GTA ARTWORK",
                    "title": "FULL CHARACTER ARTWORK",
                    "subtitle": "COMPLETE LOADING SCREEN ROTATION"
                }
            }

        else: # WEAPON_COMBAT
            return {
                "prop_id": "PROP_WEAPON_COMBAT_ENRICHED",
                "category": cat,
                "name": mapped_concept["gta5_equivalent"],
                "visual_anchors": [
                    "player opening in-game circular radial weapon wheel to switch guns",
                    "active gunfight shootout with weapon reticle and muzzle flash",
                    "aiming shotgun or rifle in combat cover"
                ],
                "negative_anchors": [
                    "browsing retail gun shop shelves or Ammu-Nation counter",
                    "driving vehicle with no weapons",
                    "loading screen"
                ],
                "hud_verification_rules": {
                    "must_have": ["radial weapon selector or crosshair reticle"],
                    "vqa_prompt": "Is the in-game radial weapon wheel or a gunfight visible?"
                },
                "banner_ui": {
                    "tag": "🎯 WEAPON WHEEL",
                    "title": "COMBAT WEAPON SELECTION",
                    "subtitle": "RADIAL WHEEL SLOW-MO & SHOOTOUT"
                }
            }

    def compile_prop_vector_embeddings(self, props: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Compiles all precision visual anchors into an in-memory 512-dim matrix
        on Metal MPS for sub-15ms real-time stream matching.
        """
        self._lazy_load_clip()
        text_prompts = []
        prop_mapping = []
        for p in props:
            for anchor in p["visual_anchors"]:
                text_prompts.append(anchor)
                prop_mapping.append(p["prop_id"])

        inputs = self.clip_proc(text=text_prompts, return_tensors="pt", padding=True).to(self.device)
        with torch.no_grad():
            text_features = self.clip_model.get_text_features(**inputs)
            text_features = text_features / text_features.norm(dim=-1, keepdim=True)

        return {
            "text_prompts": text_prompts,
            "prop_mapping": prop_mapping,
            "text_features": text_features, # Shape: [N_anchors, 512]
            "device": self.device
        }

"""
Game Pretext Engine: Domain grounding module for Vision Models & Search Retrieval.
Fetches, caches, and provides structured game ontology (characters, mechanics, world locations,
combat systems, and emergent physics) so vision models and search engines understand the exact
game context being viewed.
"""

import json
import re
from pathlib import Path
from typing import Dict, Any, List, Optional

PRETEXT_DIR = Path("data")

class GamePretextEngine:
    def __init__(self, game_code: str = "gta6"):
        self.game_code = game_code.lower()
        self.pretext_file = PRETEXT_DIR / f"game_pretext_{self.game_code}.json"
        self.data = self._load_or_default()

    def _load_or_default(self) -> Dict[str, Any]:
        """Loads cached game pretext from disk or returns default GTA 6 specification."""
        if self.pretext_file.exists():
            try:
                with open(self.pretext_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                print(f"Error loading {self.pretext_file}: {e}")

        # Default fallback specification
        return {
            "game_title": "Grand Theft Auto VI",
            "short_code": "GTA6",
            "setting": {
                "region": "State of Leonida",
                "cities": ["Vice City", "Port Gellhorn", "Ambrosia", "Grassrivers", "Vice Keys"],
                "environmental_traits": ["tropical palm avenues", "neon beachfront hotels", "swamps", "ocean canals", "bridges"]
            },
            "protagonists": {
                "leads": ["Lucia Caminos", "Jason Duval"],
                "coop_mechanics": ["character swapping", "companion callouts", "passenger seat shooting", "partner driving"]
            },
            "core_gameplay_systems": {
                "stealth_and_infiltration": {
                    "description": "Tactical covert movement, sneaking past guards, crawling prone, silenced weapons, and security evasion.",
                    "visual_indicators": ["crouched posture", "prone crawling", "silenced pistol", "unseen movement", "radar detection evasion"],
                    "typical_scenarios": ["prison corridor escape", "compound night infiltration", "covert sneaking"]
                },
                "crime_and_heists": {
                    "description": "Store hold-ups, register looting, bank vault drilling, and clerk confrontations.",
                    "visual_indicators": ["pointing gun at cashier", "bagging cash", "clerk drawing shotgun", "vault blast"],
                    "typical_scenarios": ["supermarket register robbery", "armored car vault blast", "jewelry store heist"]
                },
                "law_enforcement_and_heat": {
                    "description": "Dynamic police responses, 1-5 wanted stars, and the evidentiary Heat tracking system.",
                    "visual_indicators": ["cruiser sirens", "roadblock squad cars", "spike strips", "police helicopter searchlight", "wanted stars"],
                    "typical_scenarios": ["alleyway roadblock drift", "helicopter spotlight tracking", "PIT maneuver collisions"]
                },
                "aviation_and_vehicle_physics": {
                    "description": "Extreme vehicle handling, high-speed collisions, bridge fly-unders, and ragdoll physics.",
                    "visual_indicators": ["airplane wing clipping", "cockpit dive", "vehicle rollover", "ragdoll ejection", "WASTED screen"],
                    "typical_scenarios": ["bridge fly-under disaster", "tree-line plane dive", "highway T-bone crash"]
                },
                "open_world_and_npc_emergence": {
                    "description": "Dynamic Florida wildlife (alligators), comedic NPC anomalies, and street encounters.",
                    "visual_indicators": ["alligators in urban areas", "bizarre NPC fistfights", "gang street ambushes", "social media reels"],
                    "typical_scenarios": ["aura walk-in street regret", "swamp wildlife encounters", "bizarre pedestrian reactions"]
                }
            }
        }

    def get_vision_caption_prefix(self) -> str:
        """Returns the domain conditioning prefix for BLIP/VQA captioning."""
        title = self.data.get("game_title", "GTA 6")
        region = self.data.get("setting", {}).get("region", "Leonida")
        return f"A video game screenshot of {title} in {region} showing"

    def get_vision_archetype_prompts(self) -> List[str]:
        """Generates rich CLIP archetype prompts directly from the game's core systems."""
        prompts = []
        systems = self.data.get("core_gameplay_systems", {})
        for sys_key, info in systems.items():
            desc = info.get("description", "")
            indicators = ", ".join(info.get("visual_indicators", [])[:3])
            scenarios = ", ".join(info.get("typical_scenarios", [])[:2])
            prompts.append(f"{self.data.get('game_title')} gameplay: {desc} showing {indicators} during {scenarios}")
        return prompts

    def contextualize_user_query(self, query: str) -> Dict[str, Any]:
        """
        Enriches a raw user query with the game's comprehensive pretext.
        Matches user query words against game systems, visual indicators, and typical scenarios.
        """
        q = query.lower()
        matched_systems = []
        semantic_tokens = set(re.findall(r"\w+", q))

        systems = self.data.get("core_gameplay_systems", {})
        for sys_key, info in systems.items():
            text_corpus = f"{sys_key} {info.get('description', '')} {' '.join(info.get('visual_indicators', []))} {' '.join(info.get('typical_scenarios', []))}".lower()
            
            # Check if any token from user query matches this system
            overlap = [t for t in semantic_tokens if t in text_corpus and len(t) > 2]
            if overlap:
                matched_systems.append({
                    "system_key": sys_key,
                    "description": info.get("description"),
                    "overlap_terms": overlap,
                    "visual_clues": info.get("visual_indicators", []),
                    "scenarios": info.get("typical_scenarios", [])
                })
                semantic_tokens.update(info.get("visual_indicators", []))
                semantic_tokens.update(info.get("typical_scenarios", []))

        # Flatten semantic tokens into simple words
        clean_tokens = set()
        for s in semantic_tokens:
            clean_tokens.update(re.findall(r"\w+", s.lower()))

        pretext_summary = f"{self.data.get('game_title')} Context: {' + '.join(s['system_key'].replace('_', ' ').title() for s in matched_systems) if matched_systems else 'General Leonida Gameplay'}"
        return {
            "raw_query": query,
            "game_title": self.data.get("game_title"),
            "matched_systems": matched_systems,
            "pretext_summary": pretext_summary,
            "expanded_tokens": list(clean_tokens)
        }

_ENGINE_INSTANCE: Optional[GamePretextEngine] = None

def get_game_pretext(game_code: str = "gta6") -> GamePretextEngine:
    global _ENGINE_INSTANCE
    if _ENGINE_INSTANCE is None or _ENGINE_INSTANCE.game_code != game_code.lower():
        _ENGINE_INSTANCE = GamePretextEngine(game_code)
    return _ENGINE_INSTANCE

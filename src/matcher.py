import json
import re
from pathlib import Path
from typing import List, Dict, Any, Optional

class TopicMatcher:
    def __init__(self, config_path: Optional[str] = None):
        if not config_path:
            config_path = str(Path(__file__).parent.parent / "config" / "topics.json")
        with open(config_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        self.topics = data.get("topics", [])

    def scan_segment(self, text: str) -> List[Dict[str, Any]]:
        """
        Scans a text segment (Devanagari, Romanized Hindi, or English)
        against all pre-defined topic dictionaries.
        Returns a list of matched topics with match score and triggers.
        """
        lower_text = text.lower()
        matches = []

        for topic in self.topics:
            hits = []
            
            # Check English keywords
            for kw in topic.get("keywords_en", []):
                if re.search(r"\b" + re.escape(kw.lower()) + r"\b", lower_text):
                    hits.append(kw)
            
            # Check Hindi Devanagari keywords
            for kw in topic.get("keywords_hi", []):
                if kw in text:
                    hits.append(kw)
            
            # Check Romanized Hindi slang
            for kw in topic.get("keywords_roman", []):
                if re.search(r"\b" + re.escape(kw.lower()) + r"\b", lower_text):
                    hits.append(kw)

            if hits:
                matches.append({
                    "topic_id": topic["id"],
                    "category": topic["category"],
                    "matched_keywords": list(set(hits)),
                    "hit_count": len(hits)
                })

        return sorted(matches, key=lambda x: x["hit_count"], reverse=True)

#!/usr/bin/env python3
"""
Auto-SEO Viral Tag Engine for Outlaw Clips (YouTube Shorts & Instagram Reels)
- Fetches real-time YouTube Autocomplete search demand queries (no API key required)
- Generates 20-30 viral, high-ranking YouTube tags under 500 characters
- Uses Qwen-2.5 SLM to generate high-CTR click-worthy titles, descriptions, and hashtags
- Natively enforces YouTube Category ID 20 (Gaming)
"""
import re
import json
import urllib.parse
import urllib.request
from pathlib import Path
from typing import List, Dict, Any, Optional

class ViralSEOEngine:
    @staticmethod
    def censor_sensitive_words(text: str) -> str:
        """
        Masks sensitive or edgy words with asterisks (e.g. 'ass' -> 'a**', 'bitch' -> 'b*tch')
        so human viewers immediately understand the viral punchline while bypassing strict
        Meta and YouTube AI safety filters.
        """
        if not text:
            return text

        replacements = [
            (r"\bass\b", "booty"),
            (r"\bbitch(?:es)?\b", "bro"),
            (r"\bfuck(?:ing|er|ed)?\b", "freaking"),
            (r"\bshit(?:ting|ty)?\b", "crazy"),
            (r"\bdicks?\b", "guy"),
            (r"\bporn\b", "mature"),
            (r"\bsex\b", "wild"),
            (r"\bnudes?\b", "unhinged"),
            (r"\bnaked\b", "wild")
        ]
        censored = text
        for pattern, repl in replacements:
            censored = re.sub(pattern, repl, censored, flags=re.IGNORECASE)
        return censored

    def slm_sanitize_and_censor(self, text: str) -> str:
        """
        Uses local Qwen-2.5 SLM (running on Apple Silicon Metal) to evaluate
        text with full internet-wide slang and context awareness.
        Intelligently rewrites or auto-masks edgy terms (ass -> a**, etc.)
        while preserving viral punchlines and humor.
        Falls back to deterministic regex if SLM is not loaded.
        """
        if not text:
            return text

        try:
            from mlx_lm import load, generate
            if not hasattr(self, "_slm_model") or self._slm_model is None:
                self._slm_model, self._slm_tok = load("mlx-community/Qwen2.5-1.5B-Instruct-4bit")
            
            prompt = (
                f"<|im_start|>system\n"
                f"You are a viral social media compliance editor for YouTube Shorts and Instagram Reels.\n"
                f"Your task: Check the given text for any profanity, sexual/anatomical innuendos, or policy violations.\n"
                f"Rule 1: Do NOT make it boring or corporate. Keep the viral humor and slang.\n"
                f"Rule 2: Mask sensitive words with asterisks (e.g. 'ass' -> 'a**', 'booty' -> 'b**ty', 'bitch' -> 'b*tch', 'fuck' -> 'f*ck', 'shit' -> 'sh*t', 'dick' -> 'd*ck', 'porn' -> 'p*rn').\n"
                f"Rule 3: Return ONLY the final sanitized text string. No quotes, no intro, no commentary.<|im_end|>\n"
                f"<|im_start|>user\n"
                f"Sanitize this text: {text}<|im_end|>\n"
                f"<|im_start|>assistant\n"
            )
            out = generate(self._slm_model, self._slm_tok, prompt=prompt, max_tokens=100)
            res = out.strip().strip('"').strip("'")
            if res and len(res) > 3:
                return self.censor_sensitive_words(res)
        except Exception:
            pass

        return self.censor_sensitive_words(text)

    def __init__(self):
        self.default_base_tags = [
            "GTA 6", "GTA VI", "Grand Theft Auto VI", "GTA 6 Clips",
            "Outlaw Clips", "Gaming", "Gaming Shorts", "Twitch Clips",
            "GTA 6 Gameplay", "Shorts"
        ]
        self.affiliate_config_path = Path(__file__).parent.parent / "config/affiliate_links.json"

    def get_affiliate_links(self) -> Dict[str, str]:
        if self.affiliate_config_path.exists():
            try:
                with open(self.affiliate_config_path, "r") as f:
                    return json.load(f)
            except Exception:
                pass
        return {
            "linktree_url": "https://linktr.ee/outlawclips",
            "vpn_affiliate": "https://nordvpn.com/outlawclips",
            "gear_affiliate": "https://amzn.to/outlawclips-gear"
        }

    def fetch_live_youtube_tags(self, topic: str, streamer_name: Optional[str] = None) -> List[str]:
        """
        Queries YouTube's live search autocomplete endpoint in real-time.
        Returns actual search queries typed by millions of users right now.
        """
        clean_topic = topic.lower().replace("gta vi", "gta 6")
        seeds = [
            clean_topic,
            f"gta 6 {clean_topic}",
            f"{clean_topic} shorts",
            f"gta 6 viral"
        ]
        if streamer_name:
            seeds.append(f"{streamer_name} gta 6")
            seeds.append(f"{streamer_name} clips")

        discovered = set()
        for seed in seeds:
            try:
                url = f"https://suggestqueries.google.com/complete/search?client=firefox&ds=yt&q={urllib.parse.quote(seed)}"
                req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"})
                with urllib.request.urlopen(req, timeout=4) as resp:
                    data = json.loads(resp.read().decode("utf-8"))
                    if len(data) > 1 and isinstance(data[1], list):
                        for query in data[1]:
                            cleaned = query.strip()
                            if len(cleaned) > 2 and len(cleaned) < 40:
                                discovered.add(cleaned)
            except Exception:
                pass

        # Combine base tags with real-time trending queries
        final_tags = list(self.default_base_tags)
        if streamer_name:
            final_tags.extend([streamer_name, f"{streamer_name} Clips", f"{streamer_name} GTA 6"])

        for q in discovered:
            if q not in final_tags:
                final_tags.append(q)

        # Enforce YouTube 500-character total tag limit
        yt_tags = []
        total_len = 0
        for tag in final_tags:
            if total_len + len(tag) + 1 <= 480: # Safe margin below 500
                yt_tags.append(tag)
                total_len += len(tag) + 1
            else:
                break

        return yt_tags

    def generate_seo_package(
        self,
        action_headline: str,
        transcript: str,
        streamer_name: str,
        channel_type: str = "us",
        slm_metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Creates full viral SEO payload:
        1. High-CTR Title derived dynamically from situational action & creator
        2. Description with creator credit & monetization call-to-action
        3. Real-time YouTube Tags list (Gaming Category 20)
        4. Editorial Instagram Caption + Hashtags tailored to the moment
        """
        # 1. Fetch live YouTube autocomplete tags
        tags = self.fetch_live_youtube_tags(action_headline, streamer_name)

        # 2. Build High-CTR Shorts Title with Auto-Masking of Sensitive Words (SLM + Regex)
        slm = slm_metadata or {}
        raw_headline = slm.get("viral_title") or action_headline.strip()
        clean_headline = self.slm_sanitize_and_censor(raw_headline)
        clean_headline = re.sub(r'(#Shorts\s*)+', '', clean_headline, flags=re.IGNORECASE).strip()
        clean_headline = re.sub(r'[*]+', '', clean_headline).strip()
        if streamer_name and streamer_name.lower() not in clean_headline.lower():
            title = f"{clean_headline} ft. @{streamer_name} #Shorts"
        else:
            title = f"{clean_headline} #Shorts"

        if len(title) > 95:
            title = title[:90] + "... #Shorts"

        title = self.censor_sensitive_words(title)

        # 3. Build Engaging Description with Attribution & Monetization Link
        channel_brand = "Outlaw Clips Global" if channel_type == "us" else "Outlaw Clips Hindi"
        handle = "@outlawclipsglobal" if channel_type == "us" else "@outlawclipshq"
        aff = self.get_affiliate_links()
        aff_enabled = aff.get("enabled", True) and bool(aff.get("linktree_url"))
        linktree = aff.get("linktree_url", "")
        vpn_link = aff.get("vpn_affiliate", "")

        # Situational narrative from SLM or spoken transcript
        witty_desc = slm.get("witty_description") or ""
        if not witty_desc and transcript:
            clean_tx = transcript.strip()[:180]
            context_line = f"Streamer moment: \"{self.slm_sanitize_and_censor(clean_tx)}\""
        elif witty_desc:
            context_line = self.slm_sanitize_and_censor(witty_desc)
        else:
            context_line = f"Live high stakes sequence with @{streamer_name} in GTA 6."

        # Monetization section (only included when affiliate is enabled)
        monetization_yt = f"🛒 Best Gaming Setup: {linktree}\n🛡️ 70% Off Gaming VPN: {vpn_link}\n\n" if aff_enabled else ""

        description = (
            f"⚡ {clean_headline}\n\n"
            f"👤 Creator: @{streamer_name}\n"
            f"🎮 Game: Grand Theft Auto VI\n"
            f"📝 {context_line}\n\n"
            f"🔥 Subscribe to {channel_brand} ({handle}) for the wildest GTA 6 live stream moments!\n\n"
            f"{monetization_yt}"
            f"#{streamer_name.replace(' ', '')} #GTA6 #Shorts #Gaming #GTA6Clips #GrandTheftAutoVI"
        )

        # 4. Instagram Caption & Hashtags
        ig_hashtags = [
            "#GTA6", "#GTAVI", "#Gaming", "#GrandTheftAuto6", "#OutlawClips",
            "#TwitchClips", "#GamingReels", "#Gamer", "#ViralReels", "#ExplorePage"
        ]
        if streamer_name:
            ig_hashtags.append(f"#{streamer_name.replace(' ', '')}")

        ig_caption = (
            f"{context_line}\n\n"
            f"⚡ {clean_headline}\n"
            f"👤 Streamer: @{streamer_name}\n\n"
            f"Follow @outlawclipshq for daily unhinged GTA 6 moments!\n.\n.\n"
            + " ".join(ig_hashtags)
        )
        ig_caption = self.slm_sanitize_and_censor(ig_caption)

        pinned_comment = aff.get(
            "pinned_comment_template",
            "🔥 Subscribe for daily viral GTA 6 stream moments & gameplay!"
        )

        return {
            "title": title,
            "description": description,
            "youtube_tags": tags,
            "category_id": "20", # YouTube Gaming Category ID
            "instagram_caption": ig_caption,
            "pinned_comment": pinned_comment,
            "tag_count": len(tags)
        }

if __name__ == "__main__":
    engine = ViralSEOEngine()
    test_pkg = engine.generate_seo_package(
        action_headline="PULLS OFF CRAZY 5 STAR ESCAPE",
        transcript="Oh my god the cops are everywhere I am flying off the bridge",
        streamer_name="caseoh_",
        channel_type="us"
    )
    print("=== Viral SEO Package Test ===")
    print(f"Title: {test_pkg['title']}")
    print(f"Category: {test_pkg['category_id']} (Gaming)")
    print(f"Tags Count: {test_pkg['tag_count']}")
    print(f"Tags Sample: {test_pkg['youtube_tags'][:8]}")
    print(f"\nDescription:\n{test_pkg['description']}")

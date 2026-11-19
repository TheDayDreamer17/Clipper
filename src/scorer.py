import json
import re
from typing import Dict, Any, Optional
from mlx_lm import load, generate

class ViralityScorer:
    """
    Local SLM Virality & Hook Evaluator powered by Apple Silicon Metal GPU.
    Runs Qwen2.5-1.5B-Instruct (4-bit quantized, ~1.2 GB RAM, 0 cloud tokens).
    """
    DEFAULT_MODEL = "mlx-community/Qwen2.5-1.5B-Instruct-4bit"

    def __init__(self, model_name: str = DEFAULT_MODEL):
        self.model_name = model_name
        self._model = None
        self._tokenizer = None

    def _ensure_loaded(self):
        if self._model is None:
            print(f"🧠 Loading Local SLM Virality Evaluator ({self.model_name})...")
            self._model, self._tokenizer = load(self.model_name)

    def score_transcript(
        self,
        transcript_text: str,
        streamer_name: str = "Streamer",
        chat_context: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Evaluates a transcript snippet (English, Hindi, or Hinglish) and optional audience
        live chat context (±15s window) for short-form virality, hook strength, and entertainment value.
        Uses Few-Shot In-Context Learning (ICL) and Chain-of-Thought (CoT)
        to prevent score compression and hallucinated ratings.
        """
        self._ensure_loaded()
        
        system_prompt = (
            "You are a strict, skeptical YouTube Shorts and TikTok viral gaming editor. "
            "Your job is to REJECT mundane, low-energy, or routine commentary, and only approve genuine viral moments.\n\n"
            "Evaluation Rules:\n"
            "1. hook_critique: Analyze the first 3 seconds. Is there immediate shock, high stakes, or curiosity gap?\n"
            "2. energy_critique: Assess vocal volume, scream, laughter, or panic. Low vocal energy = LOW SCORE.\n"
            "3. payoff_critique: Did an unexpected fail, hilarious punchline, or chaotic climax occur?\n"
            "4. Score ranges:\n"
            "   - 0 to 35: Mundane chatter, navigation, checking settings/store, quiet exploration.\n"
            "   - 36 to 65: Moderately interesting gameplay talk, casual humor, mild action.\n"
            "   - 66 to 100: Extreme screaming, catastrophic fails, peak viral chaos, iconic punchlines.\n"
            "5. Chat Reaction Context: When audience live chat comments are provided in the ±15s window, analyze the crowd reaction to identify inside jokes, memes, creator roasts, or punchlines (e.g. chat spamming a meme, comparing someone to Johnny Sins, laughing at awkward situations). Weave that audience context directly into why_viral, top_hook, and viral_title!\n"
            f"6. Action-Driven Copywriting: ALWAYS describe specifically WHAT HAPPENED using the creator's actual name '{streamer_name.upper()}' or 'THIS GUY'. "
            f"NEVER use the generic word 'STREAMER' (e.g. write '{streamer_name.upper()} CRASHED HIS BOAT' or 'THIS GUY MISCLICKED AND BOUGHT A VIP DANCE', NEVER 'STREAMER CRASHED...'). "
            "Write what_happened and top_hook as a punchy, witty 4-8 word capitalized action headline without emojis describing what they did.\n\n"
            "You MUST respond ONLY with valid JSON following this exact schema:\n"
            "{\n"
            '  "what_happened": "<5-8 words in ALL CAPS describing specifically what literal physical incident, mistake, or stunt happened in the gameplay>",\n'
            '  "hook_critique": "<step-by-step reasoning on first 3 seconds>",\n'
            '  "energy_critique": "<critique of vocal adrenaline and streamer emotion>",\n'
            '  "payoff_critique": "<critique of comedic or action climax>",\n'
            '  "hook_score": <int 0-100>,\n'
            '  "hype_or_humor": <int 0-100>,\n'
            '  "payoff": <int 0-100>,\n'
            '  "why_viral": "<1 concise summary sentence>",\n'
            '  "top_hook": "<4-8 words in ALL CAPS stating what the streamer did>",\n'
            '  "viral_title": "<situational title describing the incident>",\n'
            '  "witty_description": "<1-2 sarcastic sentences for Instagram Reels/Shorts caption + 4 hashtags>"\n'
            "}"
        )

        messages = [
            {"role": "system", "content": system_prompt},
            # Few-shot Exemplar 1 (Negative - Low Virality Mundane Chatter)
            {
                "role": "user",
                "content": 'Streamer: CarryMinati\nTranscript:\n"Let\'s open the map. Where do we have to go now? Okay, 2 kilometers straight. Let me check the car engine sound."'
            },
            {
                "role": "assistant",
                "content": json.dumps({
                    "hook_critique": "Streamer starts with boring navigational check; no curiosity gap or urgency in opening seconds.",
                    "energy_critique": "Monotone, relaxed low vocal energy, routine driving setup.",
                    "payoff_critique": "No twist, crash, or funny incident occurs.",
                    "hook_score": 18,
                    "hype_or_humor": 15,
                    "payoff": 20,
                    "why_viral": "Mundane navigation and routine driving with zero comedic or action hook.",
                    "viral_title": "Carry Checks The Map"
                })
            },
            # Few-shot Exemplar 2 (Positive - High Virality Hindi Screaming/Fail)
            {
                "role": "user",
                "content": 'Streamer: CarryisLive\nTranscript:\n"ओ तेरी! भाई ये क्या हो गया?! टैंक हवा में उड़ गया और सीधा मेरे सिर पे गिरा! अरे भागो 5 स्टार पुलिस आ गई भाई!"'
            },
            {
                "role": "assistant",
                "content": json.dumps({
                    "hook_critique": "Immediate shock opening in first 2 words ('ओ तेरी!') with maximum vocal urgency.",
                    "energy_critique": "Peak screaming adrenaline, hysterical laughter, intense emotional panic.",
                    "payoff_critique": "Absurd physics fail followed by escalating threat level (5-star police arrive).",
                    "hook_score": 94,
                    "hype_or_humor": 96,
                    "payoff": 90,
                    "why_viral": "Explosive vocal hook with tank explosion fail and 5-star police panic.",
                    "viral_title": "TANK CRUSHED MY HEAD?! 5 Star Police Escape 😱💥"
                })
            },
            # Few-shot Exemplar 3 (Negative - Ambiguous/Mild Exploration)
            {
                "role": "user",
                "content": 'Streamer: Xyaa\nTranscript:\n"What is behind the store now? Let\'s see. Okay one minute let me check this corner. Is there anything here? No nothing."'
            },
            {
                "role": "assistant",
                "content": json.dumps({
                    "hook_critique": "Mild rhetorical question with no immediate tension or visual consequence.",
                    "energy_critique": "Slow conversational pace, pauses with 'one minute', zero adrenaline.",
                    "payoff_critique": "Anti-climactic ending ('No nothing') with no punchline.",
                    "hook_score": 32,
                    "hype_or_humor": 25,
                    "payoff": 20,
                    "why_viral": "Slow exploration with anti-climactic resolution and no viral tension.",
                    "viral_title": "Exploring Behind The Store"
                })
            },
            # Few-shot Exemplar 4 (Positive - Chat Meme & Inside Joke Payoff)
            {
                "role": "user",
                "content": (
                    'Streamer: KaiCenat\n'
                    'Transcript:\n"Yo look at this NPC in the barbershop! Why does he have that exact haircut?!"\n\n'
                    'Audience Live Chat (±15s window):\n'
                    '- BRO GOT THE EDGAR CUT LMAOO\n'
                    '- CUH DETECTED 💀💀\n'
                    '- NAHHH NOT THE EDGAR CUT IN GTA 6\n'
                    '- Chat is dying rn'
                )
            },
            {
                "role": "assistant",
                "content": json.dumps({
                    "hook_critique": "High vocal urgency and visual focus on ridiculous NPC appearance.",
                    "energy_critique": "Excited laughter and rapid cadence.",
                    "payoff_critique": "Chat amplifies the joke exponentially with the viral 'Edgar Cut' meme.",
                    "hook_score": 82,
                    "hype_or_humor": 89,
                    "payoff": 85,
                    "why_viral": "Streamer spots hilarious NPC and chat explodes with the viral Edgar cut meme.",
                    "viral_title": "HE FOUND AN EDGAR CUT NPC IN GTA 6?! 💀💈"
                })
            },
            # Actual Input
            {
                "role": "user",
                "content": (
                    f'Streamer: {streamer_name}\nTranscript:\n"{transcript_text}"'
                    + (
                        f'\n\nAudience Live Chat (±15s window):\n' + "\n".join(f"- {c}" for c in chat_context[:15])
                        + "\n(Incorporate prominent audience memes, inside jokes, or creator roasts into why_viral and viral_title!)"
                        if chat_context else ""
                    )
                )
            }
        ]

        prompt = self._tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
        response_text = generate(
            self._model,
            self._tokenizer,
            prompt=prompt,
            max_tokens=350,
            verbose=False
        )
        # Debug print
        # print("DEBUG SLM RESPONSE:", response_text)

        # Parse JSON from response
        parsed = {}
        try:
            match = re.search(r"\{.*\}", response_text, re.DOTALL)
            if match:
                parsed = json.loads(match.group(0))
        except Exception:
            pass

        hook = parsed.get("hook_score", 30)
        hype = parsed.get("hype_or_humor", 30)
        payoff = parsed.get("payoff", 30)

        # Strict Mathematical Virality Formula
        composite_score = int(0.4 * hook + 0.4 * hype + 0.2 * payoff)
        is_viral = (hook >= 60 and hype >= 65 and composite_score >= 65)

        # 100% Dynamic Inference: Extract situational action headline from the SLM
        action_headline = parsed.get("what_happened") or parsed.get("top_hook") or parsed.get("viral_title")
        
        # If parsing was empty, run a focused zero-shot SLM generation on the transcript circumstances
        if not action_headline or len(str(action_headline).strip()) < 3:
            direct_messages = [
                {"role": "system", "content": "You are an AI video editor. In 4 to 8 words in ALL CAPS, describe specifically what physical incident, mistake, or stunt happened in this transcript. Respond ONLY with the headline, nothing else."},
                {"role": "user", "content": f"Streamer: {streamer_name}\nTranscript: \"{transcript_text[:300]}\""}
            ]
            direct_prompt = self._tokenizer.apply_chat_template(direct_messages, tokenize=False, add_generation_prompt=True)
            action_headline = generate(self._model, self._tokenizer, prompt=direct_prompt, max_tokens=25, verbose=False).strip()

        # Clean formatting and TrueType font safety
        clean_headline = re.sub(r'[\U00010000-\U0010ffff]', '', str(action_headline)).split('\n')[0].replace('"', '').strip().upper()
        # Ensure generic word STREAMER is replaced with actual creator name or THIS GUY
        creator_name = streamer_name.lstrip('@').strip().upper()
        if "STREAMER" in clean_headline:
            clean_headline = clean_headline.replace("STREAMER'S", f"{creator_name}'S").replace("STREAMER", creator_name)

        # Collapse duplicate/repeated entity phrases (e.g. PAPAPLATTE'S PAPAPLATTE'S...)
        if creator_name:
            clean_headline = re.sub(rf'\b({re.escape(creator_name)}(\'S)?\b)(\s+\1)+', r'\1', clean_headline)
            clean_headline = re.sub(rf'\b{re.escape(creator_name)}\b(?:\s+.*?\s+BY\s+)\b{re.escape(creator_name)}\b', f'{creator_name} GETS HIT IN GAMEPLAY', clean_headline)

        # Enforce concise headline constraint (max 8-10 words, punchy 1-2 lines)
        words = clean_headline.split()
        if len(words) > 10:
            clean_headline = " ".join(words[:10])

        return {
            "hook_score": hook,
            "hype_or_humor": hype,
            "payoff": payoff,
            "virality_score": composite_score,
            "should_clip": is_viral,
            "what_happened": clean_headline,
            "hook_critique": parsed.get("hook_critique", "Evaluated dynamically by SLM"),
            "energy_critique": parsed.get("energy_critique", "Evaluated dynamically by SLM"),
            "payoff_critique": parsed.get("payoff_critique", "Evaluated dynamically by SLM"),
            "why_viral": parsed.get("why_viral", f"Situational moment dynamically analyzed from @{streamer_name}"),
            "top_hook": clean_headline,
            "viral_title": parsed.get("viral_title", clean_headline),
            "witty_description": parsed.get("witty_description", f"Watch @{streamer_name} in GTA 6. #GTA6 #Gaming #Reels #OutlawClips")
        }

if __name__ == "__main__":
    scorer = ViralityScorer()
    
    # Test sample 1: Mundane chatter
    sample_mundane = "My pencil makes a big. I need to check settings. Let me drive to the next checkpoint."
    res1 = scorer.score_transcript(sample_mundane, "CarryMinati")
    print("\n--- Test 1 (Mundane Chatter) ---")
    print(json.dumps(res1, indent=2, ensure_ascii=False))
    print(f"Passed Filter: {res1['should_clip']}")

    # Test sample 2: High energy Hindi scream/fail
    sample_viral = "ओ तेरी! ये यहाँ पर क्या हुआ? हेलीकॉप्टर को उड़ा दिया और टैंक फट गया! भाई भागो 5 स्टार पुलिस आ गई!"
    res2 = scorer.score_transcript(sample_viral, "TechnoGamerz")
    print("\n--- Test 2 (High Energy Hype) ---")
    print(json.dumps(res2, indent=2, ensure_ascii=False))
    print(f"Passed Filter: {res2['should_clip']}")

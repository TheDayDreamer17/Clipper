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

    def score_transcript(self, transcript_text: str, streamer_name: str = "Streamer") -> Dict[str, Any]:
        """
        Evaluates a transcript snippet (English, Hindi, or Hinglish)
        for short-form virality, hook strength, and entertainment value.
        """
        self._ensure_loaded()
        
        system_prompt = (
            "You are a strict viral YouTube Shorts and TikTok editor. "
            "Evaluate speech from a gaming stream (English, Hindi, or Hinglish). "
            "Score from 0 to 100 on:\n"
            "1. hook_score: Curiosity gap, shock, loud opening in the first sentence.\n"
            "2. hype_or_humor: Intense screaming, laughing, unexpected fail, or extreme chaos.\n"
            "3. payoff: Funny punchline or situation resolution.\n"
            "Strict Rule: Give low scores (<40) to mundane chatter (driving around, pencil talk, checking inventory, low energy).\n"
            "Respond ONLY with a valid JSON object matching this schema:\n"
            "{\n"
            '  "hook_score": <int 0-100>,\n'
            '  "hype_or_humor": <int 0-100>,\n'
            '  "payoff": <int 0-100>,\n'
            '  "why_viral": "<1 sentence explanation>",\n'
            '  "viral_title": "<catchy title with emoji>"\n'
            "}"
        )

        user_content = f"Streamer: {streamer_name}\nTranscript:\n\"{transcript_text}\""

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content}
        ]

        prompt = self._tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
        response_text = generate(
            self._model,
            self._tokenizer,
            prompt=prompt,
            max_tokens=220,
            verbose=False
        )

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
        # Must have BOTH strong hook AND high hype/humor to pass
        composite_score = int(0.4 * hook + 0.4 * hype + 0.2 * payoff)
        is_viral = (hook >= 60 and hype >= 65 and composite_score >= 65)

        return {
            "hook_score": hook,
            "hype_or_humor": hype,
            "payoff": payoff,
            "virality_score": composite_score,
            "should_clip": is_viral,
            "why_viral": parsed.get("why_viral", "Evaluated by SLM"),
            "viral_title": parsed.get("viral_title", f"{streamer_name} Highlight")
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

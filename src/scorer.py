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
            "You are a viral YouTube Shorts and TikTok editor specializing in gaming highlights (GTA, streams). "
            "Analyze the speech from a gaming stream (can be English, Hindi, or Hinglish). "
            "Evaluate if this segment has high entertainment value, shock, humor, or a viral hook. "
            "Ignore mundane gameplay talk (e.g. driving quietly, checking settings, meaningless chatter). "
            "Respond ONLY with a valid JSON object matching this schema:\n"
            "{\n"
            '  "hook_score": <int 0-100>,\n'
            '  "hype_or_humor": <int 0-100>,\n'
            '  "payoff": <int 0-100>,\n'
            '  "virality_score": <int 0-100>,\n'
            '  "should_clip": <bool>,\n'
            '  "why_viral": "<1 sentence explanation>",\n'
            '  "viral_title": "<punchy title with emoji>"\n'
            "}"
        )

        user_content = f"Streamer: {streamer_name}\nTranscript Segment:\n\"{transcript_text}\""

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content}
        ]

        prompt = self._tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
        response_text = generate(
            self._model,
            self._tokenizer,
            prompt=prompt,
            max_tokens=250,
            verbose=False
        )

        # Parse JSON from response
        try:
            # Extract json block if enclosed in markdown backticks
            match = re.search(r"\{.*\}", response_text, re.DOTALL)
            if match:
                return json.loads(match.group(0))
        except Exception:
            pass

        # Fallback if generation wasn't strict JSON
        return {
            "hook_score": 50,
            "hype_or_humor": 50,
            "payoff": 50,
            "virality_score": 50,
            "should_clip": False,
            "why_viral": "Could not parse JSON score",
            "viral_title": f"{streamer_name} GTA Moment"
        }

if __name__ == "__main__":
    scorer = ViralityScorer()
    
    # Test sample 1: Mundane chatter (should be rejected)
    sample_mundane = "My pencil makes a big. I need to check settings. Let me drive to the next checkpoint."
    res1 = scorer.score_transcript(sample_mundane, "CarryMinati")
    print("\n--- Test 1 (Mundane Chatter) ---")
    print(json.dumps(res1, indent=2, ensure_ascii=False))

    # Test sample 2: High energy Hindi scream/fail (should be clipped)
    sample_viral = "ओ तेरी! ये यहाँ पर क्या हुआ? हेलीकॉप्टर को उड़ा दिया और टैंक फट गया! भाई भागो 5 स्टार पुलिस आ गई!"
    res2 = scorer.score_transcript(sample_viral, "TechnoGamerz")
    print("\n--- Test 2 (High Energy Hype) ---")
    print(json.dumps(res2, indent=2, ensure_ascii=False))

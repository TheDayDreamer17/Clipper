from pathlib import Path
from typing import List, Dict, Any, Optional
import mlx_whisper

class Transcriber:
    def __init__(self, model_name: str = "mlx-community/whisper-large-v3-turbo"):
        self.model_name = model_name
        self._translator_model = None
        self._translator_tok = None

    def _translate_to_english(self, text: str, source_lang: str) -> str:
        """Translates foreign speech to fluent English using local Qwen-2.5 SLM."""
        if not text or not text.strip():
            return text
        try:
            from mlx_lm import load, generate
            if self._translator_model is None:
                self._translator_model, self._translator_tok = load("mlx-community/Qwen2.5-1.5B-Instruct-4bit")
            prompt = (
                f"<|im_start|>system\nYou are a professional multilingual translator. "
                f"Translate foreign gaming commentary directly into natural, fluent English without meta-commentary or quotation marks.<|im_end|>\n"
                f"<|im_start|>user\nTranslate this {source_lang} transcript to English:\n\"{text}\"<|im_end|>\n"
                f"<|im_start|>assistant\n"
            )
            out = generate(self._translator_model, self._translator_tok, prompt=prompt, max_tokens=160, verbose=False)
            clean = out.strip().strip('"').strip("'").strip()
            return clean if clean else text
        except Exception:
            return text

    def transcribe(
        self,
        audio_or_video_path: str,
        language: Optional[str] = None,
        auto_translate: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Runs MLX Whisper with Metal GPU acceleration.
        If auto_translate is True:
        Automatically translates any foreign speech (German, Spanish, Russian, Hindi, etc.)
        directly into fluent English via local Qwen-2.5 SLM so you understand what happened!
        Returns list of segments: [{'start': 12.5, 'end': 16.2, 'text': '...', 'language': 'de'}]
        """
        kwargs = {
            "path_or_hf_repo": self.model_name,
            "word_timestamps": False
        }
        if language:
            kwargs["language"] = language

        # Whisper task='translate' or transcribe
        if auto_translate:
            kwargs["task"] = "translate"
        else:
            kwargs["task"] = "transcribe"

        result = mlx_whisper.transcribe(str(audio_or_video_path), **kwargs)
        detected_lang = result.get("language", "en")
        segments = []
        for seg in result.get("segments", []):
            segments.append({
                "start": seg["start"],
                "end": seg["end"],
                "text": seg["text"].strip(),
                "detected_language": detected_lang
            })

        # Ensure non-English speech is translated to fluent English via local SLM
        if auto_translate and detected_lang.lower() not in ["en", "english"] and segments:
            full_foreign = " ".join(s["text"] for s in segments if s["text"]).strip()
            if full_foreign:
                translated_eng = self._translate_to_english(full_foreign, detected_lang)
                if translated_eng and translated_eng != full_foreign:
                    for s in segments:
                        s["original_text"] = s["text"]
                    segments[0]["text"] = translated_eng
                    for s in segments[1:]:
                        s["text"] = ""

        return segments

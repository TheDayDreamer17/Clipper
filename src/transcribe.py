from pathlib import Path
from typing import List, Dict, Any, Optional
import mlx_whisper

class Transcriber:
    def __init__(self, model_name: str = "mlx-community/whisper-large-v3-turbo"):
        self.model_name = model_name

    def transcribe(self, audio_or_video_path: str, language: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Runs MLX Whisper with Metal GPU acceleration.
        Returns list of segments: [{'start': 12.5, 'end': 16.2, 'text': '...'}]
        """
        kwargs = {
            "path_or_hf_repo": self.model_name,
            "word_timestamps": False
        }
        if language:
            kwargs["language"] = language

        result = mlx_whisper.transcribe(str(audio_or_video_path), **kwargs)
        segments = []
        for seg in result.get("segments", []):
            segments.append({
                "start": seg["start"],
                "end": seg["end"],
                "text": seg["text"].strip()
            })
        return segments

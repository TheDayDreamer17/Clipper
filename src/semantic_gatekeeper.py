import time
from pathlib import Path
from typing import Dict, List, Any, Optional
from PIL import Image
import torch
from transformers import BlipProcessor, BlipForConditionalGeneration, CLIPProcessor, CLIPModel

class SemanticGatekeeper:
    """
    Multi-Frame Semantic Interaction Arbiter.
    Uses multi-frame visual context to distinguish genuine novel game interactions
    (first character looks, robberies, physics feats, combat) from lame filler.
    Auto-synthesizes YouTube Shorts & Instagram Reels metadata.
    """
    def __init__(self, device: Optional[str] = None):
        self.device = device or ("mps" if torch.backends.mps.is_available() else "cpu")
        self.blip_proc = BlipProcessor.from_pretrained("Salesforce/blip-image-captioning-base")
        self.blip_model = BlipForConditionalGeneration.from_pretrained("Salesforce/blip-image-captioning-base").to(self.device)
        self.clip_proc = CLIPProcessor.from_pretrained("openai/clip-vit-base-patch32")
        self.clip_model = CLIPModel.from_pretrained("openai/clip-vit-base-patch32").to(self.device)

        # High-Value Interaction Archetypes
        self.novel_archetypes = [
            "first character reveal cinematic cutscene with close up face",
            "high-speed police pursuit with cruisers and flashing emergency sirens",
            "player in active gunfight shootout or radial weapon wheel selection",
            "helicopter or plane taking off from ground into city skyline",
            "spectacular high velocity car crash with soft body deformation",
            "first person vehicle cockpit driving looking at steering wheel",
            "robbing a store or holding up a cashier at gunpoint",
            "unusual wildlife animal interaction like an alligator or pet",
            "official game loading screen rotating character artwork slides"
        ]

        # Trivial / Lame Disqualifiers
        self.lame_disqualifiers = [
            "player walking down an empty hallway or sidewalk with no action",
            "browsing retail gun shop shelves or clothing store racks",
            "stationary car parked on street with no active pursuit",
            "adjusting settings in pause menu or options screen",
            "driving calmly in a straight line with no traffic or police"
        ]

    def evaluate_multi_frame_context(
        self,
        frames: List[Image.Image],
        streamer_name: str = "Streamer",
        game_title: str = "GTA"
    ) -> Dict[str, Any]:
        """
        Analyzes a sequence of frames, determines if it's a genuine novel interaction,
        and generates rich social metadata if accepted.
        """
        if not frames:
            return {"is_worth_clipping": False, "reason": "No frames provided"}

        # 1. Generate descriptive captions across frames
        frame_captions = []
        for idx, img in enumerate(frames):
            prefix = "A video game screenshot of Grand Theft Auto showing"
            inps = self.blip_proc(img, text=prefix, return_tensors="pt").to(self.device)
            with torch.no_grad():
                out = self.blip_model.generate(**inps, max_new_tokens=25)
            cap = self.blip_proc.decode(out[0], skip_special_tokens=True).replace(prefix, "").strip()
            frame_captions.append(cap)

        # 2. Evaluate Semantic Interaction Score (CLIP contrast against archetypes vs lame)
        mid_frame = frames[len(frames) // 2]
        all_prompts = self.novel_archetypes + self.lame_disqualifiers
        in_clip = self.clip_proc(text=all_prompts, images=mid_frame, return_tensors="pt", padding=True).to(self.device)
        with torch.no_grad():
            logits = self.clip_model(**in_clip).logits_per_image.softmax(dim=1)[0].tolist()

        novel_scores = logits[:len(self.novel_archetypes)]
        lame_scores = logits[len(self.novel_archetypes):]

        best_novel_idx = novel_scores.index(max(novel_scores))
        best_novel_prompt = self.novel_archetypes[best_novel_idx]
        best_novel_score = round(max(novel_scores) * 100, 1)

        best_lame_idx = lame_scores.index(max(lame_scores))
        best_lame_prompt = self.lame_disqualifiers[best_lame_idx]
        best_lame_score = round(max(lame_scores) * 100, 1)

        # 3. Decision Gate: Is it a genuine interaction or lame filler?
        is_worth = (best_novel_score > 35.0) and (best_novel_score > best_lame_score)
        reason = f"Novel Interaction: {best_novel_prompt[:40]}..." if is_worth else f"Rejected as Lame Filler: {best_lame_prompt[:40]}..."

        # 4. Synthesize Social Metadata (Title, Description, Tags)
        if is_worth:
            metadata = self._synthesize_social_metadata(best_novel_prompt, frame_captions, streamer_name, game_title)
        else:
            metadata = None

        return {
            "is_worth_clipping": is_worth,
            "decision_reason": reason,
            "confidence": best_novel_score,
            "novel_archetype": best_novel_prompt,
            "lame_contrast": f"{best_lame_prompt[:35]}... ({best_lame_score}%)",
            "frame_captions": frame_captions,
            "metadata": metadata
        }

    def _synthesize_social_metadata(
        self,
        archetype: str,
        captions: List[str],
        streamer_name: str,
        game_title: str
    ) -> Dict[str, Any]:
        """Auto-generates ready-to-upload YouTube Shorts & Instagram Reels metadata."""
        arch = archetype.lower()
        detail = captions[-1] if captions else "epic moment"

        if "police" in arch:
            title = f"🚨 3-STAR POLICE ESCAPE! ({streamer_name} Gameplay) #Shorts"
            caption_text = f"Watch {streamer_name} pull off an insane police cruiser escape in {game_title}! Did you see that near-miss?\n\nFollow for daily GTA gameplay!"
            tag_list = ["gta", "gta6", "policechase", "gtagameplay", "shorts", "gaming", "rockstargames"]
        elif "character" in arch or "loading" in arch:
            title = f"🔥 OFFICIAL CHARACTER ARTWORK REVEAL! ({game_title}) #Shorts"
            caption_text = f"First look at the iconic rotating character artwork slides for {game_title}! Which character are you playing first?\n\nDrop a comment below!"
            tag_list = ["gta6", "gtav", "rockstargames", "gtaartwork", "gaming", "shorts", "reels"]
        elif "cockpit" in arch or "first person" in arch:
            title = f"🚗 INSANE FIRST-PERSON COCKPIT DRIVING! #Shorts"
            caption_text = f"The interior cockpit driving physics in {game_title} look absolutely unreal! Check out the functional dashboard and mirrors.\n\nLike & Subscribe!"
            tag_list = ["gta6", "cockpitview", "firstperson", "gtacars", "shorts", "gaming"]
        elif "helicopter" in arch:
            title = f"🚁 HELICOPTER SUNSET TAKEOFF! Los Santos Skyline #Shorts"
            caption_text = f"Ascending over the city skyline during golden hour! The draw distance and lighting engine look incredible.\n\nShare with a friend!"
            tag_list = ["gta6", "helicopter", "gaming", "skyline", "shorts", "reels"]
        else:
            title = f"💥 UNREAL {game_title.upper()} MOMENT! ({streamer_name}) #Shorts"
            caption_text = f"Can you believe this happened in {streamer_name}'s stream? The physics engine is crazy!\n\nFollow for more clips!"
            tag_list = ["gta", "gta6", "gamingclips", "streamerhighlights", "shorts", "reels"]

        hashtags_yt = " ".join([f"#{t}" for t in tag_list])
        hashtags_ig = " ".join([f"#{t}" for t in tag_list + ["viral", "explorepage", "gamer"]])

        return {
            "youtube_title": title,
            "youtube_description": f"{caption_text}\n\n{hashtags_yt}",
            "youtube_tags": ", ".join(tag_list),
            "instagram_caption": f"{caption_text}\n.\n.\n{hashtags_ig}",
            "hashtags": tag_list
        }

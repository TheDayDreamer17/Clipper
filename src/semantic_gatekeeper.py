import time
from pathlib import Path
from typing import Dict, List, Any, Optional
from PIL import Image
import torch
from transformers import BlipProcessor, BlipForConditionalGeneration, CLIPProcessor, CLIPModel
from src.game_pretext_engine import get_game_pretext

class SemanticGatekeeper:
    """
    Multi-Frame Semantic Interaction Arbiter.
    Uses multi-frame visual context to distinguish genuine novel game interactions
    (first character looks, robberies, physics feats, combat) from lame filler.
    Auto-synthesizes YouTube Shorts & Instagram Reels metadata.
    """
    def __init__(self, device: Optional[str] = None):
        self.device = device or ("mps" if torch.backends.mps.is_available() else "cpu")
        self.pretext_engine = get_game_pretext("gta6")
        try:
            self.blip_proc = BlipProcessor.from_pretrained("Salesforce/blip-image-captioning-base", local_files_only=True)
            self.blip_model = BlipForConditionalGeneration.from_pretrained("Salesforce/blip-image-captioning-base", local_files_only=True).to(self.device)
        except Exception:
            self.blip_proc = None
            self.blip_model = None

        self.clip_proc = CLIPProcessor.from_pretrained("openai/clip-vit-base-patch32", local_files_only=True)
        self.clip_model = CLIPModel.from_pretrained("openai/clip-vit-base-patch32", local_files_only=True).to(self.device)

        # High-Value Emergent Gameplay Archetypes (GTA 6 Domain Pretext Grounding)
        self.novel_archetypes = [
            "tactical stealth infiltration crouching behind cover with silenced weapon and stealth radar HUD",
            "low-altitude aviation disaster plane fly-under bridge collision or tree-line crash into WASTED screen",
            "armed store hold-up robbery with cashier pulling sawed-off shotgun in combat shootout",
            "high-speed police pursuit with squad cruisers, roadblock spike strips, and chopper searchlight",
            "spectacular high velocity car crash with ragdoll physics and vehicle rollover",
            "intense player gunfight shootout with weapon crosshair and combat HUD",
            "aura walk-in street encounter turning into instant gang ambush and firefight",
            "chaotic traffic collision with airborne stunt jump and near-miss escape",
            "first person vehicle cockpit driving weaving through dense highway traffic",
            "robbing a store or holding up a cashier at gunpoint with active player controls",
            "hilarious streamer death or mission failed screen after accidental chaos",
            "high-speed sports car drifting around tight city corners with tire smoke"
        ]

        # Trivial / Lame Disqualifiers (Cinematic Cutscenes, Menus, Boring Cruising)
        self.lame_disqualifiers = [
            "cinematic story dialogue cutscene with no gameplay controls or HUD",
            "official game loading screen rotating character artwork slides",
            "player walking down an empty hallway or sidewalk with no action",
            "browsing retail gun shop shelves or clothing store racks",
            "stationary car parked on street with no active pursuit",
            "adjusting settings in pause menu or map options screen",
            "driving calmly in a straight line with no traffic or police",
            "talking head cutscene with two characters speaking in a room"
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

        # 1. Generate descriptive captions across frames grounded in Game Pretext
        frame_captions = []
        prefix = self.pretext_engine.get_vision_caption_prefix()
        for idx, img in enumerate(frames):
            inps = self.blip_proc(img, text=prefix, return_tensors="pt").to(self.device)
            with torch.no_grad():
                out = self.blip_model.generate(**inps, max_new_tokens=25)
            cap = self.blip_proc.decode(out[0], skip_special_tokens=True).replace(prefix, "").strip()
            frame_captions.append(cap)

        # 2. Evaluate Semantic Interaction Score (CLIP contrast against game systems vs lame)
        mid_frame = frames[len(frames) // 2]
        system_prompts = self.novel_archetypes + self.pretext_engine.get_vision_archetype_prompts()
        all_prompts = system_prompts + self.lame_disqualifiers
        in_clip = self.clip_proc(text=all_prompts, images=mid_frame, return_tensors="pt", padding=True).to(self.device)
        with torch.no_grad():
            logits = self.clip_model(**in_clip).logits_per_image.softmax(dim=1)[0].tolist()

        novel_scores = logits[:len(system_prompts)]
        lame_scores = logits[len(system_prompts):]

        best_novel_idx = novel_scores.index(max(novel_scores))
        best_novel_prompt = system_prompts[best_novel_idx]
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

        if "police" in arch or "pursuit" in arch:
            title = f"🚨 3-STAR POLICE ESCAPE! ({streamer_name} Gameplay) #Shorts"
            caption_text = f"Watch {streamer_name} pull off an insane police cruiser escape in {game_title}! Did you see that near-miss?\n\nFollow for daily GTA gameplay!"
            tag_list = ["gta", "gta6", "policechase", "gtagameplay", "shorts", "gaming", "rockstargames"]
        elif "crash" in arch or "collision" in arch:
            title = f"💥 150 MPH CATASTROPHIC CRASH! ({streamer_name} Gameplay) #Shorts"
            caption_text = f"The soft-body vehicle deformation physics in {game_title} are unreal! Watch {streamer_name}'s car get totaled.\n\nLike & Subscribe!"
            tag_list = ["gta6", "gtacrash", "physicsfail", "gamingclips", "shorts", "reels"]
        elif "shootout" in arch or "gunfight" in arch or "combat" in arch:
            title = f"🔫 INTENSE HEIST SHOOTOUT! ({streamer_name} Gameplay) #Shorts"
            caption_text = f"{streamer_name} pinned down under heavy crossfire in {game_title}! High-stakes tactical gunfight.\n\nFollow for more clips!"
            tag_list = ["gta6", "gtashootout", "heist", "gaming", "shorts", "viral"]
        elif "stunt" in arch or "jump" in arch:
            title = f"🚀 INSANE AIRBORNE STUNT JUMP! ({streamer_name} Gameplay) #Shorts"
            caption_text = f"Airborne stunt physics launch in {game_title}! Did he stick the landing?\n\nDrop a comment below!"
            tag_list = ["gta6", "gtastunt", "airborne", "gamingclips", "shorts", "reels"]
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

    def check_video_visual_nsfw(self, video_path: str, threshold: float = 0.55) -> Dict[str, Any]:
        """
        Runs zero-shot visual CLIP verification across sampled frames.
        Detects strip club interiors, adult clubs, and suggestive scenes with balanced prior calibration.
        """
        import cv2
        vpath = Path(video_path)
        if not vpath.exists():
            return {"is_nsfw": False, "confidence": 0.0, "reason": "file_not_found"}

        cap = cv2.VideoCapture(str(vpath))
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
        if total_frames <= 0:
            cap.release()
            return {"is_nsfw": False, "confidence": 0.0, "reason": "empty_video"}

        nsfw_prompts = [
            "strip club interior with dancer",
            "adult entertainment night club",
            "erotic dancing or suggestive nudity",
            "bikini dancer on stage"
        ]
        safe_prompts = [
            "grand theft auto video game gameplay",
            "gamer livestream with webcam reacting to video game",
            "video game car driving on street",
            "police pursuit vehicle action",
            "player combat shootout gunfight in game",
            "video game character exploring open world city",
            "entertaining video game live stream with webcam facecam",
            "video game pause menu or map screen"
        ]
        all_prompts = nsfw_prompts + safe_prompts

        sample_fractions = [0.15, 0.40, 0.65, 0.85]
        max_nsfw_prob = 0.0
        detected_category = None
        top_match_is_nsfw = False

        try:
            for frac in sample_fractions:
                target_frame = int(total_frames * frac)
                cap.set(cv2.CAP_PROP_POS_FRAMES, target_frame)
                ret, frame = cap.read()
                if not ret:
                    continue

                pil_img = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
                inputs = self.clip_proc(text=all_prompts, images=pil_img, return_tensors="pt", padding=True).to(self.device)
                with torch.no_grad():
                    logits = self.clip_model(**inputs).logits_per_image.softmax(dim=1)[0].tolist()

                nsfw_prob = sum(logits[:len(nsfw_prompts)])
                top_idx = logits.index(max(logits))
                
                if nsfw_prob > max_nsfw_prob:
                    max_nsfw_prob = nsfw_prob
                    best_nsfw_idx = logits[:len(nsfw_prompts)].index(max(logits[:len(nsfw_prompts)]))
                    detected_category = nsfw_prompts[best_nsfw_idx]
                    top_match_is_nsfw = (top_idx < len(nsfw_prompts))

                if max_nsfw_prob >= threshold and top_match_is_nsfw:
                    break
        finally:
            cap.release()

        # Requires substantial NSFW mass AND top prediction being an adult prompt, OR overwhelming mass (>0.70)
        is_mature = (max_nsfw_prob >= threshold and top_match_is_nsfw) or (max_nsfw_prob >= 0.70)
        return {
            "is_nsfw": is_mature,
            "confidence": round(max_nsfw_prob, 3),
            "detected_category": detected_category if is_mature else "safe_gameplay"
        }

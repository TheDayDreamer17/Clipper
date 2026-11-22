import os
import json
import time
from pathlib import Path
from typing import Dict, Any, Optional, List

class VideoPublisher:
    """
    Automated Multi-Platform Video Publisher for:
    1. Instagram Reels (via Direct Mobile Session or Graph API)
    2. YouTube Shorts (Unlisted Verification Uploads)
    """
    def __init__(self, config_dir: str = "config"):
        self.config_dir = Path(config_dir)
        self.config_dir.mkdir(parents=True, exist_ok=True)
        self.ig_creds_path = self.config_dir / "instagram_credentials.json"
        self.ig_session_path = self.config_dir / "ig_session.json"
        self.yt_creds_path = self.config_dir / "youtube_credentials.json"
        self.yt_token_path = self.config_dir / "token_india.json"
        self.yt_creds_us_path = self.config_dir / "youtube_credentials_us.json"
        self.yt_token_us_path = self.config_dir / "token_us.json"

    # --- INSTAGRAM REELS DISPATCHER ---
    def upload_instagram_reel(
        self,
        video_path: str,
        caption: str,
        thumbnail_path: Optional[str] = None,
        streamer_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Uploads an MP4 vertical video directly to Instagram Reels using instagrapi.
        Uses cached session if available to avoid repeated login challenges.
        """
        if not self.ig_creds_path.exists():
            return {
                "status": "error",
                "message": f"Instagram credentials not found at {self.ig_creds_path}. Please add your username and password."
            }

        with open(self.ig_creds_path, "r") as f:
            creds = json.load(f)

        session_id = creds.get("session_id", "").strip()
        username = creds.get("username", "").strip()
        password = creds.get("password", "").strip()

        if not session_id and (not username or not password or "YOUR_INSTAGRAM_PASSWORD" in password):
            return {
                "status": "error",
                "message": "Please set a valid session_id or username and password in config/instagram_credentials.json"
            }

        vpath = Path(video_path)
        if not vpath.exists():
            return {"status": "error", "message": f"Video file not found at {video_path}"}

        # --- PRE-FLIGHT COMPLIANCE GUARDRAIL ---
        try:
            from src.instagram_guardrail import InstagramPreflightValidator
            validator = InstagramPreflightValidator()
            preflight = validator.validate_preflight(
                clip_id=vpath.stem,
                video_path=str(vpath),
                headline="",
                caption=caption
            )
            if not preflight["passed"]:
                violations_msg = " | ".join(preflight["violations"])
                print(f"🛑 [Instagram Pre-Flight Rejected]: {violations_msg}")
                return {
                    "status": "error",
                    "platform": "instagram",
                    "message": f"Pre-flight Guardrail Rejected: {violations_msg}",
                    "preflight": preflight
                }
            caption = preflight.get("sanitized_caption", caption)
        except Exception as ve:
            print(f"⚠️ [Pre-Flight Warning]: Could not run validator ({ve}), proceeding with caution...")

        try:
            from instagrapi import Client
            cl = Client()
            cl.delay_range = [2, 5]

            # 1. Primary: Authenticate using active session_id cookie (bypasses ClientNeedsUpgradeError)
            session_loaded = False
            if session_id:
                try:
                    cl.login_by_sessionid(session_id)
                    session_loaded = True
                    cl.dump_settings(self.ig_session_path)
                    print(f"Logged into Instagram using session_id. Settings dumped to {self.ig_session_path}.")
                except Exception as e:
                    print(f"Session ID login notice ({e}), trying saved settings...")

            # 2. Secondary: Try loading saved session settings
            if not session_loaded and self.ig_session_path.exists():
                try:
                    cl.load_settings(self.ig_session_path)
                    if username and password:
                        cl.login(username, password)
                    session_loaded = True
                    print(f"Logged into Instagram using saved session settings.")
                except Exception as se:
                    print(f"Session load warning ({se}), falling back to direct login...")

            # 3. Fallback: Direct login
            if not session_loaded:
                cl.login(username, password)
                cl.dump_settings(self.ig_session_path)
                print(f"Logged into Instagram as @{username}. Session saved to {self.ig_session_path}.")

            # Auto-generate video thumbnail if none provided (required by Instagram Reels API)
            thumb_path = thumbnail_path
            if not thumb_path or not Path(thumb_path).exists():
                gen_thumb = vpath.with_suffix(".thumb.jpg")
                if not gen_thumb.exists():
                    import subprocess
                    subprocess.run([
                        "ffmpeg", "-y", "-ss", "00:00:01", "-i", str(vpath),
                        "-vframes", "1", "-q:v", "2", str(gen_thumb)
                    ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                if gen_thumb.exists():
                    thumb_path = str(gen_thumb)

            # Tag creator as official collaborator/author to satisfy Meta's Originality & Attribution guidelines
            usertags = []
            extra_upload_data = {}
            if streamer_name:
                try:
                    handles_path = self.config_dir / "creator_handles.json"
                    if handles_path.exists():
                        with open(handles_path) as hf:
                            hmap = json.load(hf)
                        target_handle = hmap.get(streamer_name) or hmap.get(streamer_name.lower())
                        if target_handle:
                            from instagrapi.types import Usertag, UserShort
                            c_user = cl.user_info_by_username(target_handle)
                            if c_user and c_user.pk:
                                u_short = UserShort(pk=str(c_user.pk), username=c_user.username)
                                usertags.append(Usertag(user=u_short, x=0.5, y=0.85))
                                # Co-Author / Collaborator invite parameters for Meta originality compliance
                                extra_upload_data["coauthor_producer_ids"] = [str(c_user.pk)]
                                extra_upload_data["invite_coauthor_user_ids"] = [str(c_user.pk)]
                                extra_upload_data["coauthor_producers"] = [str(c_user.pk)]
                                print(f"🏷️ [Collab Tag]: Attributed Reel to creator @{target_handle} (ID: {c_user.pk}) as coauthor collaborator.")
                except Exception as te:
                    print(f"⚠️ [Collab Tag Notice]: Could not tag creator ({te}), proceeding with upload...")

            print(f"Uploading Reel to Instagram: {vpath.name} ({vpath.stat().st_size} bytes)...")
            media = cl.clip_upload(
                path=vpath,
                caption=caption,
                thumbnail=Path(thumb_path) if thumb_path else None,
                usertags=usertags,
                extra_data=extra_upload_data
            )

            media_pk = media.pk
            media_code = media.code
            reel_url = f"https://www.instagram.com/reel/{media_code}/"

            return {
                "status": "ok",
                "platform": "instagram",
                "media_id": media_pk,
                "media_code": media_code,
                "url": reel_url,
                "caption": caption
            }
        except Exception as e:
            return {
                "status": "error",
                "platform": "instagram",
                "message": f"Instagram upload failed: {str(e)}"
            }

    # --- YOUTUBE SHORTS DISPATCHER ---
    def upload_youtube_unlisted(
        self,
        video_path: str,
        title: str,
        description: str,
        tags: Optional[List[str]] = None,
        target_channel: str = "us",
        privacy_status: str = "public"
    ) -> Dict[str, Any]:
        """
        Uploads a video to YouTube Data API v3 as a Public Short.
        Supports target_channel='us' or 'india'.
        """
        creds_file = self.yt_creds_us_path if target_channel.lower() == "us" else self.yt_creds_path
        token_file = self.yt_token_us_path if target_channel.lower() == "us" else self.yt_token_path

        if not creds_file.exists():
            return {
                "status": "error",
                "message": f"YouTube credentials not found at {creds_file} for channel '{target_channel}'."
            }

        vpath = Path(video_path)
        if not vpath.exists():
            return {"status": "error", "message": f"Video file not found at {video_path}"}

        try:
            from google.oauth2.credentials import Credentials
            from google_auth_oauthlib.flow import InstalledAppFlow
            from google.auth.transport.requests import Request
            from googleapiclient.discovery import build
            from googleapiclient.http import MediaFileUpload

            SCOPES = [
                "https://www.googleapis.com/auth/youtube.upload",
                "https://www.googleapis.com/auth/youtube.readonly"
            ]
            creds = None

            if token_file.exists():
                creds = Credentials.from_authorized_user_file(str(token_file), SCOPES)

            if not creds or not creds.valid:
                if creds and creds.expired and creds.refresh_token:
                    creds.refresh(Request())
                else:
                    flow = InstalledAppFlow.from_client_secrets_file(str(creds_file), SCOPES)
                    creds = flow.run_local_server(port=0)

                with open(token_file, "w") as tf:
                    tf.write(creds.to_json())

            youtube = build("youtube", "v3", credentials=creds)

            clean_title = (title if "#Shorts" in title else f"{title} #Shorts")[:100]
            # Auto-SEO Tag Generation if none provided
            if not tags:
                try:
                    from src.seo_engine import ViralSEOEngine
                    seo = ViralSEOEngine()
                    tags = seo.fetch_live_youtube_tags(clean_title)
                except Exception:
                    tags = ["GTA 6", "Gaming", "OutlawClips", "Shorts", "GTA 6 Clips"]

            # YouTube Strict Tag Sanitization (prevent invalidTags / 500-char quote expansion error)
            import re
            clean_tags = []
            total_chars = 0
            for t in (tags or []):
                clean_t = re.sub(r'^[#@]+', '', str(t)).strip()
                clean_t = re.sub(r'[<>,.\'\"!?:;\r\n\t]', '', clean_t).strip()
                if not clean_t or len(clean_t) < 2 or len(clean_t) > 60:
                    continue
                tag_len = len(clean_t) + (2 if ' ' in clean_t else 0) + 1
                if total_chars + tag_len <= 350 and len(clean_tags) < 15:
                    if clean_t.lower() not in [ct.lower() for ct in clean_tags]:
                        clean_tags.append(clean_t)
                        total_chars += tag_len

            body = {
                "snippet": {
                    "title": clean_title,
                    "description": description,
                    "tags": clean_tags,
                    "categoryId": "20" # YouTube Official Gaming Category
                },
                "status": {
                    "privacyStatus": privacy_status, # Public Shorts dispatch!
                    "selfDeclaredMadeForKids": False
                }
            }

            media = MediaFileUpload(str(vpath), chunksize=-1, resumable=True, mimetype="video/mp4")
            req = youtube.videos().insert(part="snippet,status", body=body, media_body=media)

            print(f"Uploading Public Short to YouTube: {vpath.name}...")
            response = None
            while response is None:
                status, response = req.next_chunk()
                if status:
                    print(f"Uploaded {int(status.progress() * 100)}%")

            video_id = response.get("id")
            yt_url = f"https://youtu.be/{video_id}"

            return {
                "status": "ok",
                "platform": "youtube",
                "video_id": video_id,
                "url": yt_url,
                "privacy": privacy_status,
                "title": clean_title
            }
        except Exception as e:
            return {
                "status": "error",
                "platform": "youtube",
                "message": f"YouTube upload failed: {str(e)}"
            }

if __name__ == "__main__":
    pub = VideoPublisher()
    print("VideoPublisher ready.")
    print("Instagram Config:", pub.ig_creds_path.exists())
    print("YouTube Config:", pub.yt_creds_path.exists())

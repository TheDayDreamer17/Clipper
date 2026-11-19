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
        thumbnail_path: Optional[str] = None
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

        username = creds.get("username", "").strip()
        password = creds.get("password", "").strip()

        if not username or not password or "YOUR_INSTAGRAM_PASSWORD" in password:
            return {
                "status": "error",
                "message": "Please set a valid username and password in config/instagram_credentials.json"
            }

        vpath = Path(video_path)
        if not vpath.exists():
            return {"status": "error", "message": f"Video file not found at {video_path}"}

        try:
            from instagrapi import Client
            cl = Client()
            cl.delay_range = [2, 5]

            # Try loading saved session
            session_loaded = False
            if self.ig_session_path.exists():
                try:
                    cl.load_settings(self.ig_session_path)
                    cl.login(username, password)
                    session_loaded = True
                    print(f"Logged into Instagram as @{username} using saved session.")
                except Exception as se:
                    print(f"Session load warning ({se}), logging in fresh...")

            if not session_loaded:
                cl.login(username, password)
                cl.dump_settings(self.ig_session_path)
                print(f"Logged into Instagram as @{username}. Session saved to {self.ig_session_path}.")

            print(f"Uploading Reel to Instagram: {vpath.name} ({vpath.stat().st_size} bytes)...")
            media = cl.clip_upload(
                path=vpath,
                caption=caption,
                thumbnail=Path(thumbnail_path) if thumbnail_path else None
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

    # --- YOUTUBE SHORTS UNLISTED DISPATCHER ---
    def upload_youtube_unlisted(
        self,
        video_path: str,
        title: str,
        description: str,
        tags: Optional[List[str]] = None,
        target_channel: str = "us"
    ) -> Dict[str, Any]:
        """
        Uploads a video to YouTube Data API v3 with status 'unlisted' for private verification.
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

            body = {
                "snippet": {
                    "title": clean_title,
                    "description": description,
                    "tags": tags,
                    "categoryId": "20" # YouTube Official Gaming Category
                },
                "status": {
                    "privacyStatus": "unlisted", # Unlisted verification mode!
                    "selfDeclaredMadeForKids": False
                }
            }

            media = MediaFileUpload(str(vpath), chunksize=-1, resumable=True, mimetype="video/mp4")
            req = youtube.videos().insert(part="snippet,status", body=body, media_body=media)

            print(f"Uploading Unlisted Short to YouTube: {vpath.name}...")
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
                "privacy": "unlisted",
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

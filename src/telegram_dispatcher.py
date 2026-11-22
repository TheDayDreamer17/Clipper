import json
import time
import os
import urllib.request
import urllib.parse
from pathlib import Path
from typing import Optional, Dict, Any, List

class TelegramDispatcher:
    def __init__(self, config_path: str = "config/telegram.json"):
        self.config_path = Path(config_path)
        self.config = self._load_config()
        self.token = self.config.get("bot_token", "").strip()
        self.chat_id = self.config.get("chat_id")
        self.api_base = f"https://api.telegram.org/bot{self.token}"

    def _load_config(self) -> Dict[str, Any]:
        if self.config_path.exists():
            try:
                with open(self.config_path, "r") as f:
                    return json.load(f)
            except Exception:
                pass
        return {}

    def _save_config(self):
        try:
            with open(self.config_path, "w") as f:
                json.dump(self.config, f, indent=2)
        except Exception as e:
            print(f"Error saving telegram config: {e}")

    def resolve_chat_id(self) -> Optional[int]:
        """
        Polls getUpdates to detect user who clicked /start or sent a message to the bot.
        """
        if self.chat_id:
            return self.chat_id

        try:
            url = f"{self.api_base}/getUpdates"
            req = urllib.request.Request(url, headers={"User-Agent": "ClipperTelegramBot/1.0"})
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read().decode("utf-8"))

            if data.get("ok") and data.get("result"):
                for update in reversed(data["result"]):
                    msg = update.get("message") or update.get("channel_post") or update.get("my_chat_member")
                    if msg:
                        chat = msg.get("chat")
                        if chat and "id" in chat:
                            cid = chat["id"]
                            self.chat_id = cid
                            self.config["chat_id"] = cid
                            self._save_config()
                            username = chat.get("username", chat.get("first_name", "User"))
                            print(f"✅ Found and registered Telegram Chat ID: {cid} (@{username})")
                            return cid
        except Exception as e:
            print(f"Error resolving chat_id: {e}")

        return None

    def ensure_telegram_size(self, file_path: Path, max_mb: float = 49.0) -> Path:
        """
        Ensures video is under Telegram's 50MB bot upload limit.
        If larger, transcodes to high-efficiency CRF under 49MB.
        """
        size_mb = file_path.stat().st_size / (1024 * 1024)
        if size_mb <= max_mb:
            return file_path

        out_path = file_path.with_name(f"{file_path.stem}_tg{file_path.suffix}")
        print(f"Video {file_path.name} is {size_mb:.1f}MB (>50MB). Optimizing to under 50MB for Telegram...")
        
        # Calculate target video bitrate in kbps based on duration
        import subprocess
        probe_cmd = ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", str(file_path)]
        duration_sec = 60.0
        try:
            res = subprocess.run(probe_cmd, capture_output=True, text=True, check=True)
            duration_sec = max(float(res.stdout.strip()), 10.0)
        except Exception:
            pass

        target_total_bits = (max_mb - 2.0) * 8 * 1024 * 1024
        target_bitrate_kbps = int((target_total_bits / duration_sec) / 1000)
        video_bitrate_kbps = max(target_bitrate_kbps - 128, 400)

        compress_cmd = [
            "ffmpeg", "-y", "-i", str(file_path),
            "-c:v", "libx264", "-preset", "veryfast",
            "-b:v", f"{video_bitrate_kbps}k", "-maxrate", f"{int(video_bitrate_kbps * 1.3)}k", "-bufsize", f"{video_bitrate_kbps * 2}k",
            "-c:a", "aac", "-b:a", "128k",
            str(out_path)
        ]
        subprocess.run(compress_cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return out_path

    def send_video(self, video_path: str, caption: str = "") -> Dict[str, Any]:
        """
        Sends video to registered chat_id using multipart/form-data.
        """
        cid = self.resolve_chat_id()
        if not cid:
            return {
                "status": "error",
                "message": "Chat ID not registered. The user must open @RavoGamerBot on Telegram and tap 'Start'."
            }

        vpath = Path(video_path)
        if not vpath.exists():
            return {"status": "error", "message": f"File not found: {video_path}"}

        upload_path = self.ensure_telegram_size(vpath)

        import requests
        url = f"{self.api_base}/sendVideo"
        try:
            with open(upload_path, "rb") as vf:
                files = {"video": (upload_path.name, vf, "video/mp4")}
                data = {
                    "chat_id": cid,
                    "caption": caption[:1024],
                    "supports_streaming": True
                }
                print(f"Uploading {upload_path.name} to Telegram chat {cid}...")
                resp = requests.post(url, data=data, files=files, timeout=120)
                res_data = resp.json()

            # Clean up temporary compressed file if one was generated
            if upload_path != vpath:
                upload_path.unlink(missing_ok=True)

            if res_data.get("ok"):
                msg_id = res_data["result"]["message_id"]
                print(f"🎉 Sent to Telegram successfully! Message ID: {msg_id}")
                return {"status": "ok", "message_id": msg_id}
            else:
                return {"status": "error", "message": res_data.get("description", "Unknown Telegram error")}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def dispatch_all_vault_clips(self) -> List[Dict[str, Any]]:
        """
        Iterates over all clips in ravi/, dispatches them to Telegram, and removes local files on success.
        """
        vault_root = Path("ravi")
        if not vault_root.exists():
            return []

        results = []
        video_files = list(vault_root.glob("**/*.mp4"))
        if not video_files:
            print("No video clips found in ravi/")
            return results

        cid = self.resolve_chat_id()
        if not cid:
            print("⚠️ Cannot dispatch: Telegram Chat ID not established. Please send /start to @RavoGamerBot.")
            return [{"status": "error", "message": "Chat ID not registered. Send /start to @RavoGamerBot first."}]

        for vf in video_files:
            category = vf.parent.name.upper()
            caption = f"🎬 Ravo OP Clip [{category}]\n⚡ File: {vf.name}\n🎮 Game: GTA 6 Gameplay\n✨ Clean 1080p60 Raw Clip"
            
            res = self.send_video(str(vf), caption=caption)
            results.append({"file": vf.name, "result": res})

            if res.get("status") == "ok":
                # User requirement: "then remove from ravi folder"
                vf.unlink(missing_ok=True)
                print(f"🧹 Removed {vf.name} from {vf.parent} after successful Telegram dispatch.")

        return results

if __name__ == "__main__":
    dispatcher = TelegramDispatcher()
    print("Bot info:", dispatcher.config.get("bot_username"))
    cid = dispatcher.resolve_chat_id()
    if cid:
        print("Ready with Chat ID:", cid)
    else:
        print("Waiting for user to tap Start on Telegram @RavoGamerBot...")

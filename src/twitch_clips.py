import sys
import subprocess
from pathlib import Path
from typing import List, Dict, Any, Optional
import requests

sys.path.append(str(Path(__file__).parent.parent))
from src.slicer import VideoSlicer

class TwitchClipEngine:
    """
    Automated Twitch Clip pipeline:
    Fetches human-curated viral clips from Twitch, downloads them,
    and formats them into 9:16 vertical shorts.
    """
    TWITCH_GQL_URL = "https://gql.twitch.tv/gql"
    TWITCH_PUBLIC_CLIENT_ID = "kimne78kx3ncx6brgo4mv6wki5h1ko"

    def __init__(
        self,
        client_id: Optional[str] = None,
        client_secret: Optional[str] = None,
        output_dir: str = "output",
        temp_dir: str = "downloads"
    ):
        self.client_id = client_id
        self.client_secret = client_secret
        self.output_dir = Path(output_dir)
        self.temp_dir = Path(temp_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.temp_dir.mkdir(parents=True, exist_ok=True)
        self.slicer = VideoSlicer()
        self.ytdlp_bin = "/Users/vismaythaker/workspace/projects/Clipper/.venv/bin/yt-dlp"

    def fetch_top_clips(
        self,
        game_name: str = "Grand Theft Auto V",
        limit: int = 5,
        period: str = "LAST_DAY"
    ) -> List[Dict[str, Any]]:
        """
        Fetches top human-clipped moments for a game sorted by view velocity.
        """
        headers = {"Client-ID": self.TWITCH_PUBLIC_CLIENT_ID}
        query = f"""
        query {{
          game(name: "{game_name}") {{
            id
            name
            clips(first: {limit}, criteria: {{ filter: {period} }}) {{
              edges {{
                node {{
                  id
                  slug
                  title
                  viewCount
                  durationSeconds
                  url
                  broadcaster {{
                    displayName
                    login
                  }}
                }}
              }}
            }}
          }}
        }}
        """
        try:
            r = requests.post(self.TWITCH_GQL_URL, headers=headers, json={"query": query}, timeout=8)
            if r.status_code != 200:
                return []

            data = r.json()
            edges = data.get("data", {}).get("game", {}).get("clips", {}).get("edges", [])
            clips = []

            for edge in edges:
                node = edge.get("node", {})
                broadcaster = node.get("broadcaster", {})
                clips.append({
                    "id": node.get("id"),
                    "slug": node.get("slug"),
                    "title": node.get("title"),
                    "view_count": node.get("viewCount", 0),
                    "duration": node.get("durationSeconds", 0),
                    "url": node.get("url"),
                    "channel": broadcaster.get("displayName") or broadcaster.get("login")
                })

            return sorted(clips, key=lambda x: x["view_count"], reverse=True)
        except Exception as e:
            print(f"Twitch clips fetch error: {e}")
            return []

    def process_clip_to_short(self, clip: Dict[str, Any]) -> Optional[Path]:
        """
        Downloads a Twitch clip and formats it into a 9:16 vertical short.
        """
        slug = clip["slug"]
        clean_channel = "".join(c for c in clip["channel"] if c.isalnum())
        raw_clip = self.temp_dir / f"twitch_{clean_channel}_{slug}.mp4"
        out_short = self.output_dir / f"twitch_{clean_channel}_{slug}_9x16.mp4"

        print(f"\n📥 Downloading Twitch Clip: \"{clip['title']}\" ({clip['view_count']:,} views)...")
        cmd = [
            self.ytdlp_bin,
            "--ffmpeg-location", "/opt/homebrew/bin/ffmpeg",
            "-f", "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",
            "--force-overwrites",
            "--no-warnings",
            "-o", str(raw_clip),
            clip["url"]
        ]
        res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        if not raw_clip.exists():
            print(f"❌ Failed to download clip: {res.stderr.decode()[:200]}")
            return None

        print(f"🎨 Rendering 9:16 Vertical Short -> {out_short.name}...")
        self.slicer.slice_clip(
            input_path=str(raw_clip),
            start_sec=0.0,
            duration_sec=float(clip["duration"]),
            output_path=str(out_short),
            style="blur_bg"
        )

        # Cleanup raw clip
        raw_clip.unlink(missing_ok=True)

        if out_short.exists():
            print(f"🎉 Generated Short: {out_short.name} ({out_short.stat().st_size / (1024*1024):.2f} MB)")
            return out_short
        return None

if __name__ == "__main__":
    engine = TwitchClipEngine()
    print("=" * 60)
    print("🔥 Twitch Clip Virality Engine (Human-Verified Clips)")
    print("=" * 60)

    clips = engine.fetch_top_clips(game_name="Grand Theft Auto V", limit=3)
    for i, c in enumerate(clips, 1):
        print(f"\n[{i}] {c['channel']} - \"{c['title']}\" ({c['view_count']:,} views | {c['duration']}s)")
        print(f"    URL: {c['url']}")

    if clips:
        print("\nConverting top clip into vertical 9:16 Short...")
        engine.process_clip_to_short(clips[0])

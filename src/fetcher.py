import json
import subprocess
from typing import List, Dict, Any, Optional
import requests

class StreamFetcher:
    """
    Unified multi-platform stream fetcher for YouTube and Twitch.
    Requires no paid API keys.
    """
    TWITCH_GQL_URL = "https://gql.twitch.tv/gql"
    TWITCH_PUBLIC_CLIENT_ID = "kimne78kx3ncx6brgo4mv6wki5h1ko"

    def __init__(self, ytdlp_path: str = "/Users/vismaythaker/workspace/projects/Clipper/.venv/bin/yt-dlp"):
        self.ytdlp_path = ytdlp_path

    # ==========================================
    # 🔴 YOUTUBE STREAM FETCHER
    # ==========================================
    def fetch_youtube_streams(
        self,
        query: str = "GTA 6 Live",
        limit: int = 5,
        live_only: bool = False
    ) -> List[Dict[str, Any]]:
        """
        Searches YouTube for top performing GTA streams/VODs using yt-dlp.
        Zero API quota consumption.
        """
        search_query = f"ytsearch{limit * 2}:{query}"
        cmd = [
            self.ytdlp_path,
            search_query,
            "--dump-json",
            "--flat-playlist",
            "--no-warnings"
        ]

        res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        results = []

        for line in res.stdout.strip().split("\n"):
            if not line:
                continue
            try:
                item = json.loads(line)
                is_live = item.get("is_live") or item.get("live_status") == "is_live"
                was_live = item.get("was_live") or item.get("live_status") == "was_live"

                if live_only and not is_live:
                    continue

                results.append({
                    "platform": "youtube",
                    "id": item.get("id"),
                    "title": item.get("title"),
                    "url": item.get("url") or f"https://www.youtube.com/watch?v={item.get('id')}",
                    "duration": item.get("duration"),
                    "duration_string": item.get("duration_string"),
                    "is_live": is_live,
                    "was_live": was_live,
                    "thumbnail": item.get("thumbnails", [{}])[0].get("url") if item.get("thumbnails") else None
                })
                if len(results) >= limit:
                    break
            except Exception:
                continue

        return results

    # ==========================================
    # 🟣 TWITCH STREAM FETCHER
    # ==========================================
    def fetch_twitch_streams(
        self,
        game_name: str = "Grand Theft Auto VI",
        limit: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Queries Twitch public GraphQL API for top live streams by viewer count.
        """
        headers = {"Client-ID": self.TWITCH_PUBLIC_CLIENT_ID}
        query = f"""
        query {{
          game(name: "{game_name}") {{
            id
            name
            streams(first: {limit}) {{
              edges {{
                node {{
                  id
                  title
                  viewersCount
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
            edges = data.get("data", {}).get("game", {}).get("streams", {}).get("edges", [])
            results = []

            for edge in edges:
                node = edge.get("node", {})
                broadcaster = node.get("broadcaster", {})
                login = broadcaster.get("login")
                results.append({
                    "platform": "twitch",
                    "id": node.get("id"),
                    "title": node.get("title"),
                    "channel": broadcaster.get("displayName"),
                    "viewers": node.get("viewersCount", 0),
                    "url": f"https://www.twitch.tv/{login}",
                    "is_live": True
                })

            return sorted(results, key=lambda x: x["viewers"], reverse=True)
        except Exception as e:
            print(f"Twitch fetch note: {e}")
            return []

    # ==========================================
    # 🏆 BEST STREAM SELECTOR
    # ==========================================
    def get_best_stream(
        self,
        platform: str = "all",
        query: str = "GTA 6 Live",
        game_name: str = "Grand Theft Auto VI"
    ) -> Optional[Dict[str, Any]]:
        """
        Returns the single best performing GTA 6 stream across YouTube/Twitch.
        """
        candidates = []

        if platform in ["all", "youtube"]:
            yt_streams = self.fetch_youtube_streams(query=query, limit=5, live_only=True)
            if not yt_streams:
                # Fallback to general recent GTA 6 streams
                yt_streams = self.fetch_youtube_streams(query=query, limit=5, live_only=False)
            candidates.extend(yt_streams)

        if platform in ["all", "twitch"]:
            twitch_streams = self.fetch_twitch_streams(game_name=game_name, limit=3)
            candidates.extend(twitch_streams)

        if not candidates:
            return None

        # Return top candidate (Live streams first)
        return candidates[0]

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Fetch top performing GTA 6 streams.")
    parser.add_argument("--platform", choices=["youtube", "twitch", "all"], default="all")
    parser.add_argument("--query", default="GTA 6 Live")
    parser.add_argument("--limit", type=int, default=3)
    args = parser.parse_args()

    fetcher = StreamFetcher()
    print("=" * 60)
    print(f"🔍 Searching Top Streams [{args.platform.upper()}] - Query: '{args.query}'")
    print("=" * 60)

    if args.platform in ["all", "twitch"]:
        print("\n🟣 TOP TWITCH STREAMS (Sorted by Real-Time Viewers):")
        twitch_results = fetcher.fetch_twitch_streams(limit=args.limit)
        for s in twitch_results:
            print(f"  • [{s['viewers']:,} viewers] {s['channel']}: \"{s['title']}\"")
            print(f"    URL: {s['url']}")

    if args.platform in ["all", "youtube"]:
        print(f"\n🔴 TOP YOUTUBE STREAMS / VODS:")
        yt_results = fetcher.fetch_youtube_streams(query=args.query, limit=args.limit)
        for s in yt_results:
            status = "LIVE NOW" if s["is_live"] else ("WAS LIVE" if s["was_live"] else "VIDEO")
            print(f"  • [{status} | {s['duration_string']}] \"{s['title']}\"")
            print(f"    URL: {s['url']}")

#!/usr/bin/env python3
"""
Competitor Analysis Script: YouTube Shorts & Instagram AI Profile
"""
import os
import sys
import json
import time
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).parent.parent))

def analyze_youtube():
    print("=" * 60)
    print("ANALYZING YOUTUBE SHORTS")
    print("=" * 60)
    import subprocess
    yt_dlp = str(Path(__file__).parent.parent / ".venv" / "bin" / "yt-dlp")
    
    videos = [
        ("Fzi_fCzcz98", "https://youtube.com/shorts/Fzi_fCzcz98"),
        ("DiBCe9lqLtE", "https://youtube.com/shorts/DiBCe9lqLtE")
    ]
    
    channels_to_inspect = set()
    
    for vid, url in videos:
        print(f"\n--- Checking {vid} ({url}) ---")
        cmd = [yt_dlp, "--dump-json", "--no-warnings", url]
        res = subprocess.run(cmd, capture_output=True, text=True)
        if res.returncode == 0:
            try:
                info = json.loads(res.stdout)
                print(f"Title: {info.get('title')}")
                print(f"Channel: {info.get('uploader')} ({info.get('uploader_url') or info.get('channel_url')})")
                print(f"Subscribers: {info.get('channel_follower_count')}")
                print(f"Views: {info.get('view_count'):,} | Likes: {info.get('like_count')} | Comments: {info.get('comment_count')}")
                print(f"Duration: {info.get('duration')}s")
                print(f"Upload Date: {info.get('upload_date')}")
                print(f"Tags: {info.get('tags')[:8] if info.get('tags') else []}")
                print(f"Description:\n{info.get('description', '')[:400]}")
                if info.get('channel_url'):
                    channels_to_inspect.add(info.get('channel_url'))
            except Exception as e:
                print(f"JSON parse error: {e}")
        else:
            print(f"Error: {res.stderr[:300]}")
            
    for channel_url in channels_to_inspect:
        shorts_url = f"{channel_url.rstrip('/')}/shorts"
        print(f"\n--- Top Shorts for {shorts_url} ---")
        cmd = [
            yt_dlp,
            "--flat-playlist",
            "--dump-json",
            "--playlist-end", "10",
            shorts_url
        ]
        res = subprocess.run(cmd, capture_output=True, text=True)
        if res.returncode == 0:
            for line in res.stdout.strip().split("\n"):
                if not line:
                    continue
                try:
                    item = json.loads(line)
                    print(f"  * {item.get('title')} | Views: {item.get('view_count')} | ID: {item.get('id')}")
                except Exception:
                    pass
        else:
            print(f"Error fetching channel shorts: {res.stderr[:200]}")

def analyze_instagram():
    print("\n" + "=" * 60)
    print("ANALYZING INSTAGRAM REEL & PROFILE VIA AGENT BROWSER")
    print("=" * 60)
    from playwright.sync_api import sync_playwright
    
    profile_dir = Path.home() / ".clipper_browser_profile"
    brave_bin = "/Applications/Brave Browser.app/Contents/MacOS/Brave Browser"
    
    if not profile_dir.exists():
        print(f"Profile dir {profile_dir} does not exist!")
        return

    reel_url = "https://www.instagram.com/reel/Df4m1IDPjXa/?knvt=MWd0MWF1ZWQ0cmJ2cw=="
    
    with sync_playwright() as p:
        context = p.chromium.launch_persistent_context(
            user_data_dir=str(profile_dir),
            executable_path=brave_bin,
            headless=True,
            viewport={"width": 1280, "height": 900},
            args=["--disable-blink-features=AutomationControlled"]
        )
        page = context.new_page()
        
        print(f"Navigating to {reel_url}...")
        try:
            page.goto(reel_url, wait_until="domcontentloaded", timeout=30000)
            page.wait_for_timeout(4000)
            
            # Dismiss any cookie or login modals if present
            for text in ["Allow all cookies", "Only allow essential", "Not Now", "Not now"]:
                btn = page.locator(f'button:has-text("{text}")').first
                if btn.is_visible():
                    try:
                        btn.click()
                        page.wait_for_timeout(1000)
                    except Exception:
                        pass
            
            # Extract reel details
            current_url = page.url
            print(f"Loaded URL: {current_url}")
            page_title = page.title()
            print(f"Page Title: {page_title}")
            
            # Extract author/username from page
            author = page.evaluate('''() => {
                // Find author link
                const links = Array.from(document.querySelectorAll('a[role="link"]'));
                for (const a of links) {
                    const href = a.getAttribute('href');
                    if (href && href.startsWith('/') && !href.includes('/p/') && !href.includes('/reel/') && !href.includes('/explore/') && !href.includes('/direct/')) {
                        const text = a.innerText.trim();
                        if (text && !text.includes(' ') && text.length > 2) {
                            return { username: text, href: href };
                        }
                    }
                }
                return null;
            }''')
            print(f"Author found: {author}")
            
            # Get reel caption / text
            caption = page.evaluate('''() => {
                const article = document.querySelector('article');
                if (article) {
                    const spans = article.querySelectorAll('h1, span');
                    for (const s of spans) {
                        if (s.innerText && s.innerText.length > 20) return s.innerText;
                    }
                }
                const meta = document.querySelector('meta[property="og:title"]');
                return meta ? meta.getAttribute('content') : document.body.innerText.slice(0, 500);
            }''')
            print(f"Caption preview: {caption[:300] if caption else 'None'}")
            
            # Find username to navigate to profile
            username = None
            if author and author.get('username'):
                username = author['username']
            else:
                # Look at title (often "User on Instagram: ...")
                if "on Instagram" in page_title:
                    username = page_title.split("on Instagram")[0].strip()
            
            print(f"Target Username: {username}")
            
            if username:
                profile_url = f"https://www.instagram.com/{username.strip('@')}/"
                print(f"\nNavigating to profile: {profile_url}")
                page.goto(profile_url, wait_until="domcontentloaded", timeout=30000)
                page.wait_for_timeout(4000)
                
                # Extract profile header info
                profile_info = page.evaluate('''() => {
                    const header = document.querySelector('header');
                    const text = header ? header.innerText : '';
                    return {
                        headerText: text,
                        title: document.title
                    };
                }''')
                print(f"Profile Header Summary:\n{profile_info.get('headerText')}")
                
                # Scroll down to load videos/reels
                print("\nFetching last 30 posts/reels...")
                reels_tab = page.locator('a[href*="/reels/"]').first
                if reels_tab.is_visible():
                    print("Clicking Reels tab...")
                    reels_tab.click()
                    page.wait_for_timeout(3000)
                
                videos_data = []
                for scroll_step in range(6):
                    items = page.evaluate('''() => {
                        const cards = document.querySelectorAll('a[href*="/reel/"], a[href*="/p/"]');
                        const results = [];
                        for (const c of cards) {
                            const href = c.getAttribute('href');
                            const img = c.querySelector('img');
                            const alt = img ? img.getAttribute('alt') : '';
                            // Find view count or play count if visible
                            const text = c.innerText.trim();
                            results.append ? results.push({ href, alt, text }) : results.push({ href, alt, text });
                        }
                        return results;
                    }''')
                    for item in items:
                        if not any(v['href'] == item['href'] for v in videos_data):
                            videos_data.append(item)
                    page.evaluate('window.scrollBy(0, 1000)')
                    page.wait_for_timeout(1500)
                    if len(videos_data) >= 35:
                        break
                
                print(f"Total video/reel cards found: {len(videos_data)}")
                for i, v in enumerate(videos_data[:30]):
                    print(f"[{i+1}] Link: {v['href']} | Views/Text: {v['text']} | Alt: {v['alt'][:100]}")
                    
                # Take screenshot of profile for visual audit
                screenshot_path = Path(__file__).parent.parent / "data" / "competitor_profile_audit.png"
                page.screenshot(path=str(screenshot_path))
                print(f"Saved profile screenshot to {screenshot_path}")

        except Exception as e:
            print(f"Playwright error: {e}")
        finally:
            context.close()

if __name__ == "__main__":
    analyze_youtube()
    analyze_instagram()

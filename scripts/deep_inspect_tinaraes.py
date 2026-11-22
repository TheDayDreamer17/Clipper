#!/usr/bin/env python3
import time
import json
from pathlib import Path
from playwright.sync_api import sync_playwright

profile_dir = Path.home() / ".clipper_browser_profile"
brave_bin = "/Applications/Brave Browser.app/Contents/MacOS/Brave Browser"

with sync_playwright() as p:
    context = p.chromium.launch_persistent_context(
        user_data_dir=str(profile_dir),
        executable_path=brave_bin,
        headless=True,
        viewport={"width": 1280, "height": 900},
        args=["--disable-blink-features=AutomationControlled"]
    )
    page = context.new_page()
    
    # 1. Inspect the specific Reel Df4m1IDPjXa
    reel_url = "https://www.instagram.com/reel/Df4m1IDPjXa/"
    print(f"Loading {reel_url}...")
    page.goto(reel_url, wait_until="networkidle", timeout=30000)
    page.wait_for_timeout(3000)
    
    # Get all text, caption, audio, video src
    details = page.evaluate('''() => {
        const text = document.body.innerText;
        const video = document.querySelector('video');
        const videoSrc = video ? video.src : '';
        const audios = Array.from(document.querySelectorAll('a[href*="/audio/"]')).map(a => a.innerText);
        const spans = Array.from(document.querySelectorAll('article span, div[role="main"] span')).map(s => s.innerText);
        return {
            videoSrc: videoSrc ? videoSrc.slice(0, 100) : 'none',
            audios: audios,
            keyText: text.slice(0, 1000)
        };
    }''')
    print("Reel details:", json.dumps(details, indent=2))
    
    # 2. Inspect Tina Perez profile reels tab and scroll to get up to 30 reels
    print("\nLoading https://www.instagram.com/tinaraes/reels/...")
    page.goto("https://www.instagram.com/tinaraes/reels/", wait_until="networkidle", timeout=30000)
    page.wait_for_timeout(3000)
    
    reels_info = []
    for scroll in range(8):
        new_items = page.evaluate('''() => {
            const anchors = Array.from(document.querySelectorAll('a[href*="/reel/"]'));
            return anchors.map(a => {
                const img = a.querySelector('img');
                return {
                    href: a.getAttribute('href'),
                    views: a.innerText.trim(),
                    alt: img ? img.getAttribute('alt') : ''
                };
            });
        }''')
        for item in new_items:
            if not any(r['href'] == item['href'] for r in reels_info):
                reels_info.append(item)
        page.evaluate('window.scrollBy(0, 1200)')
        page.wait_for_timeout(2000)
        if len(reels_info) >= 30:
            break
            
    print(f"\nFound {len(reels_info)} reels on profile:")
    for i, r in enumerate(reels_info[:30]):
        print(f"[{i+1}] {r['href']} | Views: {r['views']} | Alt: {r['alt'][:90]}")

    # 3. Sample 3 recent reels to get their exact captions and audio
    print("\nSampling 3 recent reels for exact copy & audio style...")
    for r in reels_info[:3]:
        url = f"https://www.instagram.com{r['href']}"
        page.goto(url, wait_until="domcontentloaded", timeout=20000)
        page.wait_for_timeout(2500)
        cap = page.evaluate('''() => {
            const article = document.querySelector('article') || document.querySelector('div[role="main"]');
            return article ? article.innerText.slice(0, 600) : '';
        }''')
        print(f"\n--- {r['href']} ---")
        print(cap[:400])

    context.close()

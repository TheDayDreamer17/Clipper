#!/usr/bin/env python3
"""
Persistent Agent Browser - 1-Time Setup Window
==============================================
Launches Brave with a dedicated persistent profile directory at:
~/.clipper_browser_profile/

Purpose:
Allows the user to log in to YouTube Studio and Instagram ONCE.
All authentication cookies, 2FA states, and tokens persist on the local SSD.
Survives Mac restarts, shutdowns, and sleep.
"""

import sys
import os
import time
from pathlib import Path
from playwright.sync_api import sync_playwright

PROFILE_DIR = Path.home() / ".clipper_browser_profile"
BRAVE_BIN = "/Applications/Brave Browser.app/Contents/MacOS/Brave Browser"

def run_setup():
    PROFILE_DIR.mkdir(parents=True, exist_ok=True)
    print("=" * 70)
    print("🚀 LAUNCHING DEDICATED PERSISTENT AGENT BROWSER")
    print(f"📁 Persistent Profile Path: {PROFILE_DIR}")
    print(f"🌐 Target Binary: {BRAVE_BIN}")
    print("=" * 70)
    print("👉 INSTRUCTIONS:")
    print("1. Log in to your YouTube Studio (Google Account) in Tab 1.")
    print("2. Log in to Instagram (@outlawclipshq) in Tab 2.")
    print("3. Once logged in, simply CLOSE the browser window.")
    print("✨ All session tokens and cookies will remain permanently saved on disk!")
    print("=" * 70)

    with sync_playwright() as p:
        context = p.chromium.launch_persistent_context(
            user_data_dir=str(PROFILE_DIR),
            executable_path=BRAVE_BIN,
            headless=False,
            viewport={"width": 1280, "height": 800},
            args=[
                "--no-first-run",
                "--no-default-browser-check",
                "--disable-blink-features=AutomationControlled"
            ]
        )

        page1 = context.pages[0] if context.pages else context.new_page()
        page1.goto("https://studio.youtube.com/")

        page2 = context.new_page()
        page2.goto("https://www.instagram.com/")

        print("\n⏳ Browser is open. Log in to both platforms, then close the browser when done...")

        # Keep alive until user closes all browser pages
        try:
            while len(context.pages) > 0:
                time.sleep(1)
        except Exception:
            pass

        print("\n✅ Setup session completed! Your agent credentials are saved permanently on your SSD.")

if __name__ == "__main__":
    run_setup()

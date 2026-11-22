#!/usr/bin/env python3
import time
from pathlib import Path
from playwright.sync_api import sync_playwright

PROFILE_DIR = Path.home() / ".clipper_browser_profile"
BRAVE_BIN = "/Applications/Brave Browser.app/Contents/MacOS/Brave Browser"

TARGET_URL = "https://www.instagram.com/reel/Df_-OHUMv0Y/"

with sync_playwright() as p:
    context = p.chromium.launch_persistent_context(
        user_data_dir=str(PROFILE_DIR),
        executable_path=BRAVE_BIN,
        headless=True,
        args=["--disable-blink-features=AutomationControlled"]
    )
    page = context.new_page()
    page.goto(TARGET_URL, wait_until="networkidle", timeout=30000)
    page.wait_for_timeout(3000)
    page.screenshot(path="data/new_reel_uploaded_verified.png")
    print("New Reel URL:", page.url)
    print("New Reel Title:", page.title())
    
    # Check profile
    page.goto("https://www.instagram.com/outlawclipshq/", wait_until="networkidle", timeout=30000)
    page.wait_for_timeout(2000)
    page.screenshot(path="data/profile_grid_after_cycle.png")
    print("Profile URL:", page.url)
    print("Profile Title:", page.title())
    
    context.close()

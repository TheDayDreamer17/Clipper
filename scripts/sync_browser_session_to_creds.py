#!/usr/bin/env python3
import json
from pathlib import Path
from playwright.sync_api import sync_playwright

PROFILE_DIR = Path.home() / ".clipper_browser_profile"
BRAVE_BIN = "/Applications/Brave Browser.app/Contents/MacOS/Brave Browser"

with sync_playwright() as p:
    context = p.chromium.launch_persistent_context(
        user_data_dir=str(PROFILE_DIR),
        executable_path=BRAVE_BIN,
        headless=True,
        args=["--disable-blink-features=AutomationControlled"]
    )
    
    cookies = context.cookies("https://www.instagram.com")
    session_id = None
    for c in cookies:
        if c['name'] == 'sessionid':
            session_id = c['value']
            break
            
    print("Found active session_id in Brave profile:", bool(session_id))
    if session_id:
        print("Session ID prefix:", session_id[:25], "...")
        creds_path = Path("config/instagram_credentials.json")
        with open(creds_path, "r") as f:
            creds = json.load(f)
            
        creds["session_id"] = session_id
        with open(creds_path, "w") as f:
            json.dump(creds, f, indent=2)
            
        print("Successfully updated config/instagram_credentials.json with the live session_id!")
    else:
        print("sessionid cookie was not found in browser context.")
        
    context.close()

#!/usr/bin/env python3
"""
CDP Instagram Caption Fixer
===========================
Connects directly to your live running Brave Browser via Chrome DevTools Protocol (CDP).
1. Uses your active, already-authenticated Instagram session.
2. Updates all 16 live Reels from '@outlawclips' -> '@outlawclipshq'.
3. Syncs fresh session cookies to config/instagram_credentials.json.
4. Zero logins, zero session IDs required.
"""

import re
import sys
import json
import time
from pathlib import Path
from playwright.sync_api import sync_playwright

REELS_TO_FIX = [
    "DgAC1BisDAF",
    "Df_JCbWMG4X",
    "Df-Z27Vsjr2",
    "Df-WNh-swKU",
    "Df-VeYZMp9C",
    "Df-TJO5MVhY",
    "Df-TFGCsf_q",
    "Df-RlKsMN7k",
    "Df-Q-mJsBOZ",
    "Df9JKtpMn-_",
    "Df87Q10MJHY",
    "Df8tX8YsK_8",
    "Df8dGPEMP1R",
    "Df8ZzPvsS95",
    "Df8ZqiYM5ig",
    "Df8ZjqusGCc",
    "Df8ZOGaMpXk"
]

def run_cdp_fix():
    print("Connecting to live Brave browser on http://127.0.0.1:9222...")
    with sync_playwright() as p:
        try:
            browser = p.chromium.connect_over_cdp("http://127.0.0.1:9222")
        except Exception as e:
            print("❌ Could not connect to Brave on port 9222.")
            print("Please restart Brave with CDP enabled by running:")
            print("   ./scripts/launch_brave_cdp.sh")
            return

        context = browser.contexts[0]
        
        # 1. Sync live cookies to config
        cookies = context.cookies("https://www.instagram.com")
        session_id = None
        for c in cookies:
            if c["name"] == "sessionid":
                session_id = c["value"]
                break
        
        if session_id:
            creds_path = Path("config/instagram_credentials.json")
            if creds_path.exists():
                with open(creds_path, "r") as f:
                    creds = json.load(f)
                creds["session_id"] = session_id
                creds["username"] = "outlawclipshq"
                with open(creds_path, "w") as f:
                    json.dump(creds, f, indent=2)
                print("✅ Synced fresh session_id cookie from your live Brave tab to config!")

        # 2. Open new tab to edit captions
        page = context.new_page()
        updated_count = 0

        for code in REELS_TO_FIX:
            url = f"https://www.instagram.com/p/{code}/"
            print(f"\nNavigating to {url}...")
            try:
                page.goto(url, wait_until="networkidle", timeout=30000)
                page.wait_for_timeout(2000)

                # Click More Options (...)
                opts_btn = page.locator("svg[aria-label='More Options'], svg[aria-label='More options'], svg[aria-label='Options']").first
                if not opts_btn.is_visible():
                    print(f"⚠️ More options button not visible on {code}")
                    continue

                opts_btn.evaluate("el => el.closest('div[role=\"button\"]').click()")
                page.wait_for_timeout(1200)

                # Click Edit in menu
                edit_item = page.locator("button:has-text('Edit'), div[role='button']:has-text('Edit')").first
                if not edit_item.is_visible():
                    print(f"⚠️ Edit option not available on {code} (not your post or already edited)")
                    # Dismiss modal by clicking cancel
                    cancel_btn = page.locator("button:has-text('Cancel')").first
                    if cancel_btn.is_visible():
                        cancel_btn.click()
                    continue

                edit_item.click()
                page.wait_for_timeout(1500)

                # Locate caption textarea
                textarea = page.locator("div[aria-label='Write a caption...'], textarea[aria-label='Write a caption...']").first
                if not textarea.is_visible():
                    textarea = page.locator("div[role='textbox']").first

                if textarea.is_visible():
                    current_text = textarea.inner_text()
                    new_text = re.sub(r'@outlawclips(?!hq\b)', '@outlawclipshq', current_text)
                    if "for daily unhinged GTA" in new_text and "moments" not in new_text:
                        new_text = new_text.replace("for daily unhinged GTA", "for daily unhinged GTA 6 moments!")

                    if new_text != current_text:
                        textarea.click()
                        page.keyboard.press("Meta+A")
                        page.keyboard.press("Backspace")
                        textarea.fill(new_text)
                        page.wait_for_timeout(500)

                        # Click Done
                        done_btn = page.locator("button:has-text('Done'), div[role='button']:has-text('Done')").first
                        if done_btn.is_visible():
                            done_btn.click()
                            page.wait_for_timeout(2500)
                            print(f"✅ Successfully updated caption on {code}!")
                            updated_count += 1
                        else:
                            print(f"⚠️ Could not find Done button on {code}")
                    else:
                        print(f"✓ Caption on {code} already has @outlawclipshq")
                        cancel_edit = page.locator("button:has-text('Cancel')").first
                        if cancel_edit.is_visible():
                            cancel_edit.click()
                else:
                    print(f"⚠️ Could not locate caption textarea on {code}")

            except Exception as e:
                print(f"❌ Error updating {code}: {e}")

        page.close()
        print(f"\n🎉 Finished! Total Reels updated via CDP: {updated_count}")

if __name__ == "__main__":
    run_cdp_fix()

#!/usr/bin/env python3
import time
from pathlib import Path
from playwright.sync_api import sync_playwright

PROFILE_DIR = Path.home() / ".clipper_browser_profile"
BRAVE_BIN = "/Applications/Brave Browser.app/Contents/MacOS/Brave Browser"

TARGET_URL = "https://www.instagram.com/p/Df_W18CM6sY/"

print(f"Deleting reel: {TARGET_URL}")

with sync_playwright() as p:
    context = p.chromium.launch_persistent_context(
        user_data_dir=str(PROFILE_DIR),
        executable_path=BRAVE_BIN,
        headless=True,
        args=["--disable-blink-features=AutomationControlled"]
    )
    page = context.new_page()
    page.goto(TARGET_URL, wait_until="networkidle", timeout=30000)
    page.wait_for_timeout(2000)
    
    # Click More Options (...)
    more_opts = page.locator('svg[aria-label="More Options"], svg[aria-label="More options"]').first
    if more_opts.is_visible():
        more_opts.evaluate("el => el.closest('div[role=\"button\"]').click()")
        page.wait_for_timeout(1500)
        
        # Click Delete item (div, span, button with text 'Delete')
        del_item = page.locator('div[role="button"]:has-text("Delete"), button:has-text("Delete"), span:has-text("Delete")').first
        print("Clicking Delete menu item...")
        del_item.click()
        page.wait_for_timeout(2000)
        page.screenshot(path="data/delete_confirmation_prompt.png")
        
        # In confirmation modal, click "Delete" again
        confirm_btn = page.locator('div[role="dialog"] button:has-text("Delete"), div[role="dialog"] div[role="button"]:has-text("Delete")').first
        if confirm_btn.is_visible():
            print("Confirming Delete in modal...")
            confirm_btn.click()
            page.wait_for_timeout(5000)
            page.screenshot(path="data/final_after_deleted.png")
            print("DELETED SUCCESSFULLY!")
        else:
            print("Confirm button not visible in modal.")
    else:
        print("More Options button not found.")
        
    context.close()

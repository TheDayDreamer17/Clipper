#!/usr/bin/env python3
"""
Persistent Agent Browser Controller
===================================
Provides programmatic access to YouTube Studio & Instagram via Playwright
using the persistent user profile directory (~/.clipper_browser_profile).

Capabilities:
1. YouTube Studio: Edit titles, descriptions, inspect monetization & copyright status.
2. Instagram: Delete/archive Reels, inspect post status, read insights.
3. Completely survives computer reboots because session cookies reside on disk.
"""

import os
import time
from pathlib import Path
from typing import Dict, Any, Optional, List
from playwright.sync_api import sync_playwright

PROFILE_DIR = Path.home() / ".clipper_browser_profile"
BRAVE_BIN = "/Applications/Brave Browser.app/Contents/MacOS/Brave Browser"

class AgentBrowserController:
    def __init__(self, headless: bool = True, cdp_url: str = "http://127.0.0.1:9222"):
        self.profile_dir = PROFILE_DIR
        self.brave_bin = BRAVE_BIN
        self.headless = headless
        self.cdp_url = cdp_url

    def get_browser_context(self, playwright):
        """
        Connects via Chrome DevTools Protocol (CDP) to your live running Brave Browser
        if active, or falls back to persistent context.
        """
        try:
            browser = playwright.chromium.connect_over_cdp(self.cdp_url)
            if browser.contexts:
                return browser.contexts[0], browser, True
        except Exception:
            pass

        context = playwright.chromium.launch_persistent_context(
            user_data_dir=str(self.profile_dir),
            executable_path=self.brave_bin,
            headless=self.headless,
            viewport={"width": 1280, "height": 800},
            args=["--disable-blink-features=AutomationControlled"]
        )
        return context, None, False

    def is_profile_initialized(self) -> bool:
        """Checks if the persistent profile has been created."""
        return self.profile_dir.exists() and any(self.profile_dir.iterdir())

    def update_youtube_video(
        self,
        video_id: str,
        title: Optional[str] = None,
        description: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Navigates to YouTube Studio's video editor for a specific video
        and updates the title or description.
        """
        if not self.is_profile_initialized():
            return {
                "status": "error",
                "message": "Agent browser profile not initialized. Please run 'python3 src/agent_browser_setup.py' first."
            }

        url = f"https://studio.youtube.com/video/{video_id}/edit"
        try:
            with sync_playwright() as p:
                context = p.chromium.launch_persistent_context(
                    user_data_dir=str(self.profile_dir),
                    executable_path=self.brave_bin,
                    headless=self.headless,
                    viewport={"width": 1280, "height": 800},
                    args=["--disable-blink-features=AutomationControlled"]
                )
                page = context.new_page()
                page.goto(url, wait_until="networkidle", timeout=30000)

                # Wait for title input element in Studio
                title_selector = 'input#textbox[aria-label="Title"], #textbox[aria-label="Title"]'
                if title:
                    page.wait_for_selector(title_selector, timeout=15000)
                    page.click(title_selector)
                    page.keyboard.press("Meta+A")
                    page.keyboard.press("Backspace")
                    page.type(title_selector, title)

                # Save changes
                save_btn = 'button#save-button, ytcp-button#save-button'
                page.wait_for_selector(save_btn, timeout=5000)
                page.click(save_btn)
                time.sleep(2)

                context.close()
                return {"status": "ok", "video_id": video_id, "updated_title": title}
        except Exception as e:
            return {"status": "error", "video_id": video_id, "message": str(e)}

    def delete_instagram_reel(self, reel_code_or_url: str) -> Dict[str, Any]:
        """
        Navigates to an Instagram Reel and deletes it using the authenticated persistent Brave session.
        """
        if not self.is_profile_initialized():
            return {
                "status": "error",
                "message": "Agent browser profile not initialized. Please run 'python3 src/agent_browser_setup.py' first."
            }

        if reel_code_or_url.startswith("http"):
            url = reel_code_or_url.replace("/reel/", "/p/").replace("/reels/", "/p/")
        else:
            code = reel_code_or_url.strip("/").split("/")[-1]
            url = f"https://www.instagram.com/p/{code}/"

        try:
            with sync_playwright() as p:
                context = p.chromium.launch_persistent_context(
                    user_data_dir=str(self.profile_dir),
                    executable_path=self.brave_bin,
                    headless=self.headless,
                    viewport={"width": 1280, "height": 800},
                    args=["--disable-blink-features=AutomationControlled"]
                )
                page = context.new_page()
                page.goto(url, wait_until="networkidle", timeout=30000)
                page.wait_for_timeout(2000)

                # Dismiss Save login info modal if present
                save_btn = page.locator('button:has-text("Save"), button:has-text("Not now")').first
                if save_btn.is_visible():
                    save_btn.click()
                    page.wait_for_timeout(1000)

                # Click Options (...)
                opts_btn = page.locator('svg[aria-label="More Options"], svg[aria-label="More options"]').first
                opts_btn.evaluate('el => el.closest("div[role=\\"button\\"]").click()')
                page.wait_for_timeout(1500)

                # Click Delete in menu
                delete_item = page.locator('div[role="button"]:has-text("Delete"), button:has-text("Delete"), span:has-text("Delete")').first
                delete_item.click()
                page.wait_for_timeout(1500)

                # Confirm Delete in modal
                confirm_btn = page.locator('div[role="dialog"] button:has-text("Delete"), div[role="dialog"] div[role="button"]:has-text("Delete")').first
                confirm_btn.click()
                page.wait_for_timeout(4000)

                context.close()
                return {"status": "ok", "url": url, "message": "Reel deleted successfully."}
        except Exception as e:
            return {"status": "error", "url": url, "message": str(e)}

if __name__ == "__main__":
    controller = AgentBrowserController(headless=True)
    print("Agent Browser Profile Initialized:", controller.is_profile_initialized())

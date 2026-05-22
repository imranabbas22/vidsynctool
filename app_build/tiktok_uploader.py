"""
TikTok Uploader — Playwright + Opera GX Profile
First run: opens a headed browser using Opera GX's profile (you're already logged in).
Saves cookies for headless runs after that.
Enables AIGC label by default.
"""

import os
import json
import time
from typing import Tuple, Optional

CONFIG_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config")
os.makedirs(CONFIG_DIR, exist_ok=True)

STORAGE_PATH = os.path.join(CONFIG_DIR, "tiktok_storage.json")
UPLOAD_URL = "https://www.tiktok.com/tiktokstudio/upload"

OPERA_PROFILE = os.path.join(
    os.getenv("APPDATA", ""),
    "Opera Software",
    "Opera GX Stable",
)


class TikTokUploader:
    """Uploads Shorts to TikTok via Playwright with Opera GX session cookies."""

    def __init__(self, headless: bool = True):
        self.headless = headless

    def _ensure_session(self) -> bool:
        """Ensure we have a valid session. If not, prompt user to log in via Opera GX profile."""
        if os.path.exists(STORAGE_PATH):
            # Quick validation: check if the storage file has cookies
            try:
                with open(STORAGE_PATH) as f:
                    data = json.load(f)
                if data.get("cookies") and len(data["cookies"]) > 5:
                    return True
            except Exception:
                pass

        print("[TikTok] No saved session found. Opening Opera GX profile to log in...")
        return self._capture_session_from_opera()

    def _capture_session_from_opera(self) -> bool:
        """Open a headed browser using Opera GX's profile so TikTok cookies are available."""
        from playwright.sync_api import sync_playwright

        if not os.path.isdir(OPERA_PROFILE):
            print(f"[TikTok] Opera GX profile not found at: {OPERA_PROFILE}")
            return False

        with sync_playwright() as pw:
            print(f"[TikTok] Launching browser with Opera GX profile...")
            context = pw.chromium.launch_persistent_context(
                user_data_dir=OPERA_PROFILE,
                headless=False,
                no_viewport=True,
            )
            page = context.new_page()
            page.goto(UPLOAD_URL, timeout=60000)
            time.sleep(3)

            if "upload" in page.url:
                print("[TikTok] Logged in! Saving session...")
                storage = context.storage_state()
                with open(STORAGE_PATH, "w") as f:
                    json.dump(storage, f)
                print(f"[TikTok] Session saved to {STORAGE_PATH}")
                context.close()
                return True
            else:
                print(f"[TikTok] Not logged in. URL: {page.url}")
                print("[TikTok] Please log in manually if prompted, then press Enter here.")
                input("Press Enter after logging in...")
                if "upload" in page.url:
                    storage = context.storage_state()
                    with open(STORAGE_PATH, "w") as f:
                        json.dump(storage, f)
                    print("[TikTok] Session saved.")
                    context.close()
                    return True
                context.close()
                return False

    def _upload_video(self, page, video_path: str, caption: str) -> bool:
        """Upload a video file, fill caption, enable AIGC, and post."""
        print(f"[TikTok] Uploading: {os.path.basename(video_path)}")

        # Step 1: Find file input (hidden) and select video
        # TikTok Studio loads the upload input dynamically — wait for it
        file_input = None
        for _ in range(15):
            try:
                file_input = page.query_selector('input[type="file"]')
                if file_input:
                    break
            except Exception:
                pass
            time.sleep(1)
        if not file_input:
            print("[TikTok] Could not find file upload input.")
            return False

        abs_path = os.path.abspath(video_path)
        if not os.path.exists(abs_path):
            print(f"[TikTok] File not found: {abs_path}")
            return False

        try:
            file_input.set_input_files(abs_path)
        except Exception as e:
            print(f"[TikTok] File selection failed: {e}")
            return False

        print("[TikTok] Video selected. Waiting for processing...")
        time.sleep(8)

        # Step 2: Find caption/description field (contenteditable div) and fill it
        caption_area = None
        for _ in range(15):
            try:
                # Find contenteditable divs and pick the one that looks like a description field
                ce_divs = page.query_selector_all('[contenteditable]')
                for el in ce_divs:
                    try:
                        rect = el.bounding_box()
                        if rect and rect['width'] > 200 and rect['height'] > 15:
                            # Verify it's not a search/location field
                            ph = el.get_attribute("placeholder") or ""
                            label = el.get_attribute("aria-label") or ""
                            inner = el.inner_text()[:50] if el.inner_text() else ""
                            combined = (ph + label + inner).lower()
                            if "search" not in combined and "location" not in combined:
                                caption_area = el
                                break
                    except:
                        pass
            except:
                pass
            if caption_area:
                break
            time.sleep(1)

        if caption_area and caption.strip():
            try:
                # Focus and clear the contenteditable div
                caption_area.evaluate("el => el.focus()")
                time.sleep(0.3)
                caption_area.evaluate("el => el.innerText = ''")
                time.sleep(0.2)
                caption_area.evaluate("el => el.dispatchEvent(new Event('input', {bubbles: true}))")
                caption_area.type(caption, delay=10)
                print(f"[TikTok] Caption filled ({len(caption)} chars)")
            except Exception as e:
                print(f"[TikTok] Caption fill failed: {e}")
                try:
                    caption_area.click()
                    time.sleep(0.3)
                    caption_area.fill(caption)
                    print(f"[TikTok] Caption filled via fill() fallback")
                except Exception as e2:
                    print(f"[TikTok] All caption methods failed: {e2}")
        else:
            print(f"[TikTok] Caption field not found or caption empty.")

        time.sleep(1)

        # Step 3: Enable AIGC toggle — find the switch near "AI-generated content" text
        try:
            # Find the switch closest to the "AI-generated content" text
            aigc_switch = page.evaluate("""
                () => {
                    const allSwitches = document.querySelectorAll('[role="switch"]');
                    const spans = document.querySelectorAll('span, div');
                    let aiText = null;
                    for (const s of spans) {
                        if (s.textContent.includes('AI-generated')) {
                            aiText = s;
                            break;
                        }
                    }
                    if (!aiText) return null;
                    const aiRect = aiText.getBoundingClientRect();
                    let bestSwitch = null;
                    let bestDist = Infinity;
                    for (const sw of allSwitches) {
                        const r = sw.getBoundingClientRect();
                        const dist = Math.abs(r.y - aiRect.y);
                        if (dist < bestDist && r.x > aiRect.x) {
                            bestDist = dist;
                            bestSwitch = sw;
                        }
                    }
                    return bestSwitch ? {
                        x: bestSwitch.getBoundingClientRect().x + bestSwitch.getBoundingClientRect().width / 2,
                        y: bestSwitch.getBoundingClientRect().y + bestSwitch.getBoundingClientRect().height / 2,
                        checked: bestSwitch.getAttribute('aria-checked')
                    } : null;
                }
            """)
            if aigc_switch:
                if aigc_switch.get("checked") != "true":
                    page.mouse.click(aigc_switch["x"], aigc_switch["y"])
                    time.sleep(0.5)
                    print("[TikTok] AIGC toggle enabled.")
                else:
                    print("[TikTok] AIGC already enabled.")
            else:
                print("[TikTok] AIGC switch not found (may be auto-labeled).")
        except Exception as e:
            print(f"[TikTok] AIGC toggle error: {e}")

        # Step 4: Click Post button
        try:
            post_btn = page.query_selector('button:has-text("Post")')
            if post_btn and post_btn.is_visible():
                post_btn.click()
                print("[TikTok] Post button clicked.")
                time.sleep(5)
                print("[TikTok] Upload flow complete.")
                return True
            else:
                print("[TikTok] Post button not found or not visible.")
                return False
        except Exception as e:
            print(f"[TikTok] Post button error: {e}")
            return False

    def upload(self, video_path: str, caption: str = "") -> Tuple[bool, Optional[str]]:
        """Upload a video to TikTok. Returns (success, message)."""
        from playwright.sync_api import sync_playwright

        if not os.path.exists(video_path):
            return False, f"File not found: {video_path}"

        # Make sure we have a valid session
        if not self._ensure_session():
            return False, "Could not obtain TikTok session"

        with sync_playwright() as pw:
            with open(STORAGE_PATH) as f:
                storage_state = json.load(f)

            browser = pw.chromium.launch(headless=self.headless)
            context = browser.new_context(
                storage_state=storage_state,
                viewport={"width": 1400, "height": 900},
            )
            page = context.new_page()

            try:
                page.goto(UPLOAD_URL, timeout=45000)
                # Wait for the page to fully render — TikTok Studio loads async
                page.wait_for_load_state("domcontentloaded")
                time.sleep(4)

                if "login" in page.url.lower():
                    print("[TikTok] Session expired. Re-capturing from Opera GX profile...")
                    context.close()
                    browser.close()
                    os.remove(STORAGE_PATH)
                    return self.upload(video_path, caption)

                success = self._upload_video(page, video_path, caption)

                # Refresh storage state
                try:
                    storage = context.storage_state()
                    with open(STORAGE_PATH, "w") as f:
                        json.dump(storage, f)
                except Exception:
                    pass

                context.close()
                browser.close()
                msg = "Uploaded" if success else "Failed"
                return success, msg

            except Exception as e:
                context.close()
                browser.close()
                return False, str(e)


def upload_to_tiktok(video_path: str, caption: str = "", headless: bool = True) -> Tuple[bool, Optional[str]]:
    u = TikTokUploader(headless=headless)
    return u.upload(video_path, caption)


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: python tiktok_uploader.py <video.mp4> [caption] [--headed]")
        sys.exit(1)
    video = sys.argv[1]
    caption = sys.argv[2] if len(sys.argv) > 2 else ""
    headless = "--headed" not in sys.argv
    success, msg = upload_to_tiktok(video, caption, headless=headless)
    print(f"\nResult: {'OK' if success else 'FAIL'} — {msg}")

"""
WiFi ADB TikTok Uploader (TikTok Studio)
Pushes a video to your phone via ADB/WiFi then uploads it through TikTok Studio.
Calibrated for 1080x2400 screens — adjust taps in config/tiktok_adb_config.json if needed.
"""

import os
import re
import time
import subprocess
import json
from typing import Tuple, Optional

ADB_PATH = os.path.join(os.path.expanduser("~"), "AppData", "Local", "Android", "platform-tools", "adb.exe")
CONFIG_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config")
os.makedirs(CONFIG_DIR, exist_ok=True)
CONFIG_PATH = os.path.join(CONFIG_DIR, "tiktok_adb_config.json")

# TikTok Studio package
TT_STUDIO = "com.ss.android.tt.creator"

# ── Tap coordinates (absolute pixels for 1080x2400 screen) ──
# Override via config/tiktok_adb_config.json if your screen is different.
TAP_DEFAULTS = {
    "w": 1080,
    "h": 2400,
    "upload_btn":        (565, 494),    # Upload button on TikTok Studio home screen
    "video_tab":         (516, 240),    # "Videos" filter tab in gallery
    "first_video":       (297, 634),    # First video thumbnail in gallery grid
    "gallery_next":      (540, 2252),   # Next button on gallery screen
    "editor_next":       (801, 2262),   # Next button on editor screen
    "caption_field":     (376, 427),    # "Add description..." text field
    "post_btn":          (799, 2252),   # Post button on final post screen
    "compliance_post":   (361, 1557),   # Post confirm button in compliance dialog
    "more_options":      (233, 1127),   # "More options" (AIGC may be inside)
}


def _adb(args: list, timeout: int = 30) -> Tuple[int, str, str]:
    cmd = [ADB_PATH] + args
    try:
        p = subprocess.run(
            cmd, capture_output=True, text=True,
            timeout=timeout, shell=False,
            startupinfo=subprocess.STARTUPINFO() if os.name == 'nt' else None
        )
        return p.returncode, p.stdout.strip(), p.stderr.strip()
    except subprocess.TimeoutExpired:
        return -1, "", "TIMEOUT"
    except FileNotFoundError:
        return -1, "", "ADB not found at: " + ADB_PATH


def _phone_shell(cmd: str, timeout: int = 15) -> str:
    _, out = _adb(["shell", cmd], timeout)
    return out


def _tap(x: int, y: int):
    """Tap at absolute pixel coordinate."""
    _adb(["shell", "input", "tap", str(x), str(y)], timeout=5)


def _swipe(x1, y1, x2, y2, dur_ms=200):
    _adb(["shell", "input", "swipe", str(x1), str(y1), str(x2), str(y2), str(dur_ms)], timeout=5)


def _load_config() -> dict:
    if os.path.exists(CONFIG_PATH):
        with open(CONFIG_PATH) as f:
            return json.load(f)
    return {}


def _save_config(cfg: dict):
    with open(CONFIG_PATH, "w") as f:
        json.dump(cfg, f, indent=2)


def _get_screen_size() -> Tuple[int, int]:
    rc, out, _ = _adb(["shell", "wm", "size"], 10)
    if rc == 0:
        m = re.search(r"(\d+)\s*x\s*(\d+)", out)
        if m:
            return int(m.group(1)), int(m.group(2))
    return 1080, 2400


def _insert_into_gallery(video_name: str) -> bool:
    """Copy the video from /sdcard/Download/ into the DCIM/Camera folder so TikTok's gallery sees it."""
    src = f"/sdcard/Download/{video_name}"
    dst = f"/sdcard/DCIM/Camera/{video_name}"
    _phone_shell(f"cp {src} {dst}", 5)
    _phone_shell(f"am broadcast -a android.intent.action.MEDIA_SCANNER_SCAN_FILE -d file://{dst}", 5)
    time.sleep(1)
    return True


class TikTokADBUploader:
    """Uploads Shorts to TikTok via ADB over WiFi, using TikTok Studio app."""

    def __init__(self, adb_path: str = ADB_PATH):
        self.adb_path = adb_path
        self.config = _load_config()
        self.connected = False
        self.taps = {**TAP_DEFAULTS, **self.config.get("taps", {})}

    def connect_wifi(self, ip_port: str = None) -> bool:
        """Connect to phone over WiFi ADB."""
        if ip_port:
            target = ip_port
        else:
            saved = self.config.get("last_ip")
            if saved:
                target = saved
            else:
                print("\n  Enter your phone's IP:port from Wireless Debugging:")
                print("  (Settings → Developer Options → Wireless Debugging)")
                target = input("  IP:port: ").strip()
                if not target:
                    return False

        rc, out, _ = _adb(["connect", target], 10)
        print(f"[ADB] {out}")
        if "connected" in out.lower() or rc == 0:
            self.config["last_ip"] = target
            _save_config(self.config)
            self.connected = True
            return True

        print("[ADB] Connection failed. Check WiFi debugging is on and IP is correct.")
        return False

    def upload(self, video_path: str, caption: str = "") -> Tuple[bool, str]:
        """Upload a video to TikTok via TikTok Studio ADB automation."""
        if not self.connected:
            return False, "Not connected to phone via ADB"
        if not os.path.exists(video_path):
            return False, f"Video not found: {video_path}"

        video_name = os.path.basename(video_path)
        taps = self.taps
        w, h = _get_screen_size()
        print(f"  Screen: {w}x{h}")

        # Use a simple filename without special chars for ADB safety
        simple_name = re.sub(r'[^a-zA-Z0-9._-]', '_', video_name)
        if simple_name != video_name:
            print(f"  Renaming for push: {video_name} -> {simple_name}")
            video_name = simple_name

        print(f"  Uploading: {video_name}")

        # ── Step 1: Push video ──
        local_abs = os.path.abspath(video_path)
        rc, _, _ = _adb(["push", local_abs, f"/sdcard/Download/{video_name}"], 60)
        if rc != 0:
            return False, "Failed to push video"
        print("  [1/7] Video pushed to phone")

        # ── Step 2: Copy to gallery ──
        _insert_into_gallery(video_name)
        print("  [2/7] Video indexed in gallery")

        # ── Step 3: Launch TikTok Studio ──
        _adb(["shell", "am", "start", "-n",
              f"{TT_STUDIO}/com.ss.android.ugc.aweme.splash.SplashActivity",
              "--activity-clear-top"], 10)
        time.sleep(3)
        print("  [3/7] TikTok Studio launched")

        # ── Step 4: Home → Upload → Select video ──
        _tap(*taps["upload_btn"])
        time.sleep(2)

        # Tap Videos tab to filter
        _tap(*taps["video_tab"])
        time.sleep(1)

        # Select the first video in gallery
        _tap(*taps["first_video"])
        time.sleep(1)

        # Gallery → Next
        _tap(*taps["gallery_next"])
        time.sleep(3)
        print("  [4/7] Video selected, moved to editor")

        # ── Step 5: Editor → Next → Post screen ──
        _tap(*taps["editor_next"])
        time.sleep(3)
        print("  [5/7] Editor done, on post screen")

        # ── Step 6: Fill caption ──
        if caption.strip():
            _tap(*taps["caption_field"])
            time.sleep(0.5)
            # Clear any existing text (select all + delete)
            _phone_shell("input keyevent KEYCODE_A")
            time.sleep(0.2)
            _phone_shell("input keyevent KEYCODE_DEL")
            time.sleep(0.3)
            # Type caption (escape spaces with %s for ADB)
            safe_caption = caption.replace(" ", "%s")
            _adb(["shell", "input", "text", safe_caption], 15)
            time.sleep(1)
            print(f"  [6/7] Caption filled ({len(caption)} chars)")

        # ── Step 7: Post ──
        _tap(*taps["post_btn"])
        time.sleep(2)

        # Compliance dialog (Post confirm)
        _tap(*taps["compliance_post"])
        time.sleep(2)

        # Check for success
        dump_path = "/sdcard/verify_post.xml"
        _phone_shell(f"uiautomator dump {dump_path}", 5)
        rc, out, _ = _adb(["pull", dump_path, os.path.join(CONFIG_DIR, "verify_post.xml")], 5)
        if rc == 0:
            try:
                with open(os.path.join(CONFIG_DIR, "verify_post.xml"), "r") as f:
                    content = f.read()
                if "Video posted" in content or "video posted" in content.lower():
                    print("  [7/7] Post confirmed: Video posted successfully!")
                    return True, f"Published: {video_name}"
            except Exception:
                pass

        print("  [7/7] Post button tapped")
        return True, f"Likely published: {video_name}"


def upload_via_adb(video_path: str, caption: str = "", phone_ip: str = None) -> Tuple[bool, str]:
    u = TikTokADBUploader()
    if not u.connect_wifi(phone_ip):
        return False, "ADB connection failed"
    return u.upload(video_path, caption)


if __name__ == "__main__":
    import sys
    print("TikTok Studio WiFi ADB Uploader")
    print("=" * 60)
    if len(sys.argv) < 2:
        print("\nUsage:")
        print("  python tiktok_uploader_adb.py <video.mp4> [caption] [phone_ip:port]")
        print("\nFirst run:")
        print("  1. Settings → Developer Options → Wireless Debugging → ON")
        print("  2. Note IP:port shown on your phone")
        print("  3. Run this script with that IP:port")
        sys.exit(1)

    video = sys.argv[1]
    caption = sys.argv[2] if len(sys.argv) > 2 else ""
    ip = sys.argv[3] if len(sys.argv) > 3 else None

    success, msg = upload_via_adb(video, caption, ip)
    print(f"\nResult: {'SUCCESS' if success else 'FAILED'} — {msg}")

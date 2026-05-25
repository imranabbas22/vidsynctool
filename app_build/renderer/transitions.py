"""
transitions.py — Transition effects and overlay utilities.

Standalone functions extracted from video_engine.py.
Provides burn transitions, glitch/VHS transitions, progress bars,
scanline overlays, file stamps, noise generators, and burn masks.
"""

from __future__ import annotations

import math
import random
from typing import Any, Optional

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

try:
    from moviepy.editor import VideoClip, VideoFileClip
except ImportError:
    from moviepy import VideoClip, VideoFileClip


# ── Math / Noise utilities ─────────────────────────────────────────────


def value_noise_2d(x: float, y: float, seed: int = 0) -> float:
    """Simple hash-based value noise returning [0, 1]."""
    n = int(x * 157) ^ int(y * 311) ^ seed
    n = (n << 13) ^ n
    return ((n * (n * n * 60493 + 19990303) + 1376312589) & 0x7FFFFFFF) / 0x7FFFFFFF


def generate_burn_mask(w: int, h: int, progress: float, seed: int = 0) -> np.ndarray:
    """
    Returns a 2D float32 numpy array of shape (h, w) in range [0, 1].

    0 = fully burnt (transparent), 1 = intact.
    Progress 0.0 = no burn, 1.0 = fully burnt.
    """
    xx, yy = np.meshgrid(
        np.arange(w, dtype=np.float32), np.arange(h, dtype=np.float32)
    )
    x_scaled = (xx * 0.02 * 157).astype(np.int32)
    y_scaled = (yy * 0.02 * 311).astype(np.int32)

    n = x_scaled ^ y_scaled ^ seed
    n = (n << 13) ^ n
    term = n * (n * n * 60493 + 19990303) + 1376312589
    noise_val = (term & 0x7FFFFFFF).astype(np.float32) / 0x7FFFFFFF

    nx = xx / w
    displaced = nx + (noise_val - 0.5) * 0.3
    burn_edge = 1.0 - pow(progress, 0.7)

    mask = np.clip((displaced - burn_edge) * 5.0, 0.0, 1.0)
    return mask


# ── Background frame processing ────────────────────────────────────────


def _process_bg_frame(
    bg_arr: np.ndarray,
    target_w: int = 1080,
    target_h: int = 1920,
    blur_radius: float = 6.0,
    darken_factor: float = 0.45,
) -> np.ndarray:
    """
    Resizes, center-crops, blurs, and darkens a background video frame.
    Returns a (target_h, target_w, 3) uint8 numpy array.
    """
    h, w, c = bg_arr.shape
    target_aspect = target_w / target_h
    current_aspect = w / h

    if current_aspect > target_aspect:
        # Too wide, crop sides
        new_w = int(h * target_aspect)
        left = (w - new_w) // 2
        bg_arr_cropped = bg_arr[:, left : left + new_w]
    else:
        # Too tall, crop top/bottom
        new_h = int(w / target_aspect)
        top = (h - new_h) // 2
        bg_arr_cropped = bg_arr[top : top + new_h, :]

    img_pil = Image.fromarray(bg_arr_cropped)
    if img_pil.size != (target_w, target_h):
        img_pil = img_pil.resize((target_w, target_h), Image.Resampling.BILINEAR)

    if blur_radius > 0.1:
        img_pil = img_pil.filter(ImageFilter.GaussianBlur(radius=blur_radius))

    if darken_factor > 0.0:
        dark_overlay = Image.new("RGB", (target_w, target_h), (10, 15, 30))
        img_pil = Image.blend(img_pil, dark_overlay, darken_factor)

    return np.array(img_pil)


# ── Scanline overlay ────────────────────────────────────────────────────


def create_scanline_overlay(width: int, height: int, opacity: float) -> np.ndarray:
    """Generates a static horizontal CRT scanline mesh overlay matrix.

    Returns a float32 array of shape (height, width, 3) with 1-pixel dark
    lines every 4 pixels.
    """
    overlay = np.zeros((height, width, 3), dtype=np.float32)
    for y in range(0, height, 4):
        overlay[y, :, :] = opacity
    return overlay


# ── Progress bar overlay ───────────────────────────────────────────────


def add_global_progress_bar(clip: VideoClip, style_dict: dict, height: int = 6) -> VideoClip:
    """Overlays a horizontal fill-bar at the bottom of every frame.

    The bar grows from left-to-right over the clip duration. Colour is taken
    from ``style_dict`` keys ``timer_bar_color`` or ``highlight_bg`` (default
    cyan ``(0, 242, 254)``).
    """
    duration = clip.duration
    color = style_dict.get(
        "timer_bar_color",
        style_dict.get("highlight_bg", (0, 242, 254)),
    )

    def filter_frame(gf, t):
        frame = gf(t)
        try:
            frame[0, 0] = frame[0, 0]
            writeable_frame = frame
        except ValueError:
            writeable_frame = frame.copy()

        h, w, c = writeable_frame.shape
        progress = min(1.0, t / duration)
        fill_width = int(w * progress)
        if fill_width > 0:
            writeable_frame[h - height : h, 0:fill_width, :] = color
        return writeable_frame

    return clip.fl(filter_frame)


# ── File stamp renderer ────────────────────────────────────────────────


def render_stamp(
    stamp_text: str,
    scene_idx: int,
    t: float,
    delay_offset: float,
    font_path: str = "",
) -> Optional[Image.Image]:
    """Render a 'File Stamp' overlay.

    Returns an RGBA PIL Image or ``None`` if outside the stamp window
    (0--0.6 seconds after ``delay_offset``, and only for ``scene_idx >= 2``).

    Colours:
    - Red (DEBUNKED / MYTH)
    - Green (VERIFIED / FACT)
    - Yellow (anything else)
    """
    if scene_idx < 2 or not stamp_text:
        return None
    stamp_t = t - delay_offset
    if stamp_t < 0 or stamp_t > 0.6:
        return None

    canvas = Image.new("RGBA", (500, 160), (0, 0, 0, 0))
    draw = ImageDraw.Draw(canvas)
    upper = stamp_text.upper()
    if "DEBUNKED" in upper or "MYTH" in upper:
        stamp_color = (220, 30, 30)
    elif "VERIFIED" in upper or "FACT" in upper:
        stamp_color = (30, 180, 60)
    else:
        stamp_color = (220, 180, 20)

    # Slam-bounce scale animation (first 0.15 s)
    slam_progress = min(1.0, stamp_t / 0.15)
    if slam_progress < 1.0:
        scale = 1.0 + 2.0 * (1.0 - slam_progress) * math.cos(
            slam_progress * math.pi * 2
        )
        scale = max(0.8, scale)
    else:
        scale = 1.0

    cw, ch = 500, 160
    scaled_w = int(cw * scale)
    scaled_h = int(ch * scale)
    sx = (cw - scaled_w) // 2
    sy = (ch - scaled_h) // 2

    stamp_frame = Image.new("RGBA", (scaled_w, scaled_h), (0, 0, 0, 0))
    sd = ImageDraw.Draw(stamp_frame)
    sd.rounded_rectangle(
        [4, 4, scaled_w - 4, scaled_h - 4],
        radius=16,
        fill=stamp_color + (220,),
        outline=(255, 255, 255, 200),
        width=4,
    )
    sd.rounded_rectangle(
        [10, 10, scaled_w - 10, scaled_h - 10],
        radius=12,
        fill=None,
        outline=(255, 255, 255, 80),
        width=1,
    )
    try:
        stamp_font = ImageFont.truetype(
            font_path, int(min(scaled_w, scaled_h) * 0.22)
        )
    except Exception:
        stamp_font = ImageFont.load_default()
    tw = sd.textlength(stamp_text, font=stamp_font)
    tx = (scaled_w - int(tw)) // 2
    ty = (scaled_h - int(min(scaled_w, scaled_h) * 0.25)) // 2
    sd.text((tx, ty), stamp_text, fill=(255, 255, 255, 240), font=stamp_font)
    canvas.paste(stamp_frame, (sx, sy), stamp_frame)
    return canvas


# ── Burn transition clip ───────────────────────────────────────────────


def create_burn_transition_clip(
    bg_source: Any,
    duration: float = 0.8,
    flash_image: Optional[Image.Image] = None,
) -> VideoClip:
    """Returns a VideoClip that applies a procedural burning-paper transition
    effect.

    Parameters
    ----------
    bg_source : str or np.ndarray or VideoClip
        Background source.  Can be a file path (image or video), a numpy
        array ``(H, W, 3)``, or a moviepy ``VideoClip``.
    duration : float
        Length of the transition in seconds (default 0.8).
    flash_image : PIL.Image or None
        Optional previous scene card to flash (desaturated, 40% opacity)
        during the first 0.1 s (Transition Memory Flash).
    """
    bg_video = None
    raw_img_pil = None
    base_arr = None

    if isinstance(bg_source, str):
        if bg_source.lower().endswith((".mp4", ".avi", ".mov", ".mkv")):
            bg_video = VideoFileClip(bg_source)
        else:
            raw_img_pil = (
                Image.open(bg_source)
                .convert("RGB")
                .resize((1080, 1920), Image.Resampling.LANCZOS)
            )
    elif hasattr(bg_source, "get_frame"):
        bg_video = bg_source
    else:
        base_arr = bg_source

    scanline_overlay = create_scanline_overlay(1080, 1920, opacity=0.15)

    # Pre-compute ember positions (seeded)
    ember_count = 30
    embers = []
    rng_embers = random.Random(42)
    for _ in range(ember_count):
        ex = rng_embers.uniform(0.0, 1.0)
        ey = rng_embers.uniform(0.0, 1.0)
        espeed = rng_embers.uniform(0.3, 0.8)
        esize = rng_embers.uniform(1.0, 3.0)
        embers.append((ex, ey, espeed, esize))

    def make_frame(t):
        progress = min(1.0, t / duration)
        seed = int(t * 1000) % 10000

        # ---- Get base bg frame ----
        if bg_video is not None:
            bg_dur = bg_video.duration
            raw_frame = bg_video.get_frame(t % bg_dur)
            bg_arr = _process_bg_frame(raw_frame, blur_radius=15.0, darken_factor=0.45)
        elif raw_img_pil is not None:
            glow = raw_img_pil.filter(ImageFilter.GaussianBlur(radius=15))
            dark = Image.new("RGB", (1080, 1920), (10, 15, 30))
            glow = Image.blend(glow, dark, 0.45)
            bg_arr = np.array(glow)
        else:
            bg_arr = base_arr.copy()

        # ---- Generate burn mask and flame glow ----
        burn_mask = generate_burn_mask(1080, 1920, progress, seed)
        bg_arr_float = bg_arr.astype(np.float32)

        xx, yy = np.meshgrid(
            np.arange(1080, dtype=np.float32), np.arange(1920, dtype=np.float32)
        )
        x_scaled = (xx * 0.02 * 157).astype(np.int32)
        y_scaled = (yy * 0.02 * 311).astype(np.int32)

        n = x_scaled ^ y_scaled ^ seed
        n = (n << 13) ^ n
        term = n * (n * n * 60493 + 19990303) + 1376312589
        noise_v = (term & 0x7FFFFFFF).astype(np.float32) / 0x7FFFFFFF

        nx = xx / 1080
        displaced = nx + (noise_v - 0.5) * 0.3
        edge_pos = 1.0 - pow(progress, 0.7)
        dist = displaced - edge_pos

        flame_mask = (dist >= 0.0) & (dist < 0.08)
        intensity = np.zeros_like(dist)
        intensity[flame_mask] = 1.0 - dist[flame_mask] / 0.08

        flame = np.zeros((1920, 1080, 3), dtype=np.float32)
        flame[:, :, 0] = 255 * intensity
        flame[:, :, 1] = 200 * intensity * np.clip(1.0 - dist * 3.0, 0.0, 1.0)
        flame[:, :, 2] = 50 * intensity * np.clip(1.0 - dist * 6.0, 0.0, 1.0)

        # ---- Composite flame over burnt areas ----
        mask_3ch = np.stack([burn_mask] * 3, axis=-1)
        result = bg_arr_float * mask_3ch + flame * (1.0 - mask_3ch)

        # ---- Ember particles ----
        for ex, ey_base, espeed, esize in embers:
            ey = ey_base - progress * espeed * 0.5
            if 0 <= ey <= 1 and progress > 0.1 and progress < 0.95:
                ex_px = int(ex * 1080)
                ey_px = int(ey * 1920)
                brightness = max(0, 1.0 - abs(progress - 0.5) * 2)
                if 0 <= ex_px < 1080 and 0 <= ey_px < 1920:
                    color = (255, int(200 * brightness), int(50 * brightness))
                    r = int(esize)
                    for dy in range(-r, r + 1):
                        for dx in range(-r, r + 1):
                            if dx * dx + dy * dy <= r * r:
                                px, py = ex_px + dx, ey_px + dy
                                if 0 <= px < 1080 and 0 <= py < 1920:
                                    result[py, px] = np.clip(
                                        result[py, px] * 0.6
                                        + np.array(color, dtype=np.float32) * 0.4,
                                        0,
                                        255,
                                    )

        result = np.clip(result, 0, 255).astype(np.uint8)

        # ---- Scanlines ----
        drift = int(t * 240) % 4
        scanlines = np.roll(scanline_overlay, drift, axis=0)
        result = (result * (1 - scanlines)).astype(np.uint8)

        # ---- Sprint 6: Transition Memory Flash ----
        if flash_image is not None and t < 0.1:
            flash_card = flash_image.copy()
            flash_arr = np.array(flash_card.convert("RGBA"), dtype=np.float32)
            gray = flash_arr[:, :, :3].mean(axis=2, keepdims=True)
            flash_arr[:, :, :3] = gray * 0.5 + flash_arr[:, :, :3] * 0.5
            flash_arr[:, :, 3] = flash_arr[:, :, 3] * 0.4
            fx = 540 - 840 // 2
            fy = 900 - 890 // 2
            flash_pil = Image.fromarray(flash_arr.astype(np.uint8))
            fused_pil = Image.fromarray(result).convert("RGBA")
            fused_pil.paste(flash_pil, (fx, fy), flash_pil)
            result = np.array(fused_pil.convert("RGB"))

        return result

    clip = VideoClip(make_frame, duration=duration)
    # Clean up bg_video when clip is closed
    if (
        isinstance(bg_source, str)
        and bg_source.lower().endswith((".mp4", ".avi", ".mov", ".mkv"))
        and bg_video is not None
    ):
        original_close = clip.close

        def custom_close():
            original_close()
            try:
                bg_video.close()
            except Exception:
                pass

        clip.close = custom_close
    return clip


# ── Glitch / VHS transition clip ──────────────────────────────────────


def create_transition_clip(
    bg_source: Any,
    duration: float = 0.5,
    flash_image: Optional[Image.Image] = None,
) -> VideoClip:
    """Returns a VideoClip that applies a glitchy VHS-style transition effect.

    Parameters
    ----------
    bg_source : str or np.ndarray or VideoClip
        Background source.  Can be a file path (image or video), a numpy
        array ``(H, W, 3)``, or a moviepy ``VideoClip``.
    duration : float
        Length of the transition in seconds (default 0.5).
    flash_image : PIL.Image or None
        Optional previous scene card to flash (desaturated, 40% opacity)
        during the first 0.1 s (Transition Memory Flash).
    """
    bg_video = None
    raw_img_pil = None
    base_arr = None

    if isinstance(bg_source, str):
        if bg_source.lower().endswith((".mp4", ".avi", ".mov", ".mkv")):
            bg_video = VideoFileClip(bg_source)
        else:
            raw_img_pil = (
                Image.open(bg_source)
                .convert("RGB")
                .resize((1080, 1920), Image.Resampling.LANCZOS)
            )
    elif hasattr(bg_source, "get_frame"):
        bg_video = bg_source
    else:
        base_arr = bg_source

    scanline_overlay = create_scanline_overlay(1080, 1920, opacity=0.15)

    def make_frame(t):
        # ---- Get base bg frame ----
        if bg_video is not None:
            bg_dur = bg_video.duration
            raw_frame = bg_video.get_frame(t % bg_dur)
            base_frame_arr = _process_bg_frame(
                raw_frame, blur_radius=15.0, darken_factor=0.45
            )
        elif raw_img_pil is not None:
            glow_base = raw_img_pil.filter(ImageFilter.GaussianBlur(radius=15))
            dark_overlay = Image.new("RGB", (1080, 1920), (10, 15, 30))
            glow_base = Image.blend(glow_base, dark_overlay, 0.45)
            base_frame_arr = np.array(glow_base)
        else:
            base_frame_arr = base_arr.copy()

        fused_arr = base_frame_arr.copy()

        # ---- Horizontal strip glitch ----
        num_strips = random.randint(6, 12)
        for _ in range(num_strips):
            y_start = random.randint(0, 1919)
            y_end = min(1920, y_start + random.randint(20, 120))
            shift = random.randint(-80, 80)
            fused_arr[y_start:y_end, :, :] = np.roll(
                fused_arr[y_start:y_end, :, :], shift, axis=1
            )

        # ---- Chromatic aberration (R / B channel shift) ----
        shift_r = random.randint(-20, 20)
        shift_b = random.randint(-20, 20)
        if shift_r != 0:
            fused_arr[:, :, 0] = np.roll(fused_arr[:, :, 0], shift_r, axis=1)
        if shift_b != 0:
            fused_arr[:, :, 2] = np.roll(fused_arr[:, :, 2], shift_b, axis=1)

        # ---- Flicker ----
        flicker_factor = random.uniform(0.6, 1.4)
        fused_arr = (
            np.clip(fused_arr.astype(np.float32) * flicker_factor, 0, 255)
            .astype(np.uint8)
        )

        # ---- Jitter (full-frame roll) ----
        dx = random.randint(-25, 25)
        dy = random.randint(-25, 25)
        fused_arr = np.roll(fused_arr, dx, axis=1)
        fused_arr = np.roll(fused_arr, dy, axis=0)

        # ---- Scanlines ----
        drift = int(t * 240) % 4
        scanlines = np.roll(scanline_overlay, drift, axis=0)
        fused_arr = (fused_arr * (1 - scanlines)).astype(np.uint8)

        # ---- Sprint 6: Transition Memory Flash ----
        if flash_image is not None and t < 0.1:
            flash_card = flash_image.copy()
            flash_arr = np.array(flash_card.convert("RGBA"), dtype=np.float32)
            gray = flash_arr[:, :, :3].mean(axis=2, keepdims=True)
            flash_arr[:, :, :3] = gray * 0.5 + flash_arr[:, :, :3] * 0.5
            flash_arr[:, :, 3] = flash_arr[:, :, 3] * 0.4
            fx = 540 - 840 // 2
            fy = 900 - 890 // 2
            flash_pil = Image.fromarray(flash_arr.astype(np.uint8))
            fused_pil = Image.fromarray(fused_arr).convert("RGBA")
            fused_pil.paste(flash_pil, (fx, fy), flash_pil)
            fused_arr = np.array(fused_pil.convert("RGB"))

        return fused_arr

    clip = VideoClip(make_frame, duration=duration)
    # Clean up bg_video when clip is closed
    if (
        isinstance(bg_source, str)
        and bg_source.lower().endswith((".mp4", ".avi", ".mov", ".mkv"))
        and bg_video is not None
    ):
        original_close = clip.close

        def custom_close():
            original_close()
            try:
                bg_video.close()
            except Exception:
                pass

        clip.close = custom_close

    return clip

# =============================================================================
# Card Generation & Mascot Renderer
# Standalone card generation, thumbnail creation, and Static mascot rendering.
# =============================================================================
import os
import math
import random
import hashlib
from typing import List, Optional, Dict, Any

import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageChops


# =============================================================================
# STYLE PRESETS (mirrored from video_engine.STYLE_PRESETS)
# =============================================================================
STYLE_PRESETS: Dict[str, Dict[str, Any]] = {
    "blueprint": {
        "bg_prompt_suffix": "Style of a declassified government document, dark blue and white blueprint, highly detailed.",
        "card_bg": (20, 25, 45),
        "card_myth_outline": (255, 75, 75),
        "card_truth_outline": (255, 255, 255),
        "card_myth_header_bg": (255, 75, 75),
        "card_truth_header_bg": (255, 242, 0),
        "card_myth_header_text": (255, 255, 255),
        "card_truth_header_text": (10, 15, 30),
        "myth_label": "EXHIBIT A: DECLASSIFIED MYTH",
        "truth_label": "EXHIBIT B: FORENSIC EVIDENCE",
        "anomaly_label": "EXHIBIT C: DECLASSIFIED ANOMALY",
        "subtitle_color": (255, 255, 255),
        "highlight_bg": (255, 242, 0),
        "highlight_text": (10, 15, 30),
        "grid_color": (0, 242, 254, 25),
        "watermark_color": (255, 60, 60),
        "timer_bar_color": (0, 242, 254),
    },
    "chalkboard": {
        "bg_prompt_suffix": "Style of a chalkboard lecture diagram, white chalk marks on dark green board, academic, highly detailed.",
        "card_bg": (25, 35, 25),
        "card_myth_outline": (255, 180, 60),
        "card_truth_outline": (220, 220, 220),
        "card_myth_header_bg": (255, 180, 60),
        "card_truth_header_bg": (200, 255, 200),
        "card_myth_header_text": (15, 30, 15),
        "card_truth_header_text": (15, 30, 15),
        "myth_label": "FALSE PREMISE: CHALKBOARD ANALYSIS",
        "truth_label": "CORRECTED: LECTURE PROOF",
        "anomaly_label": "UNSOLVED: CHALKBOARD ANOMALY",
        "subtitle_color": (220, 220, 220),
        "highlight_bg": (255, 255, 100),
        "highlight_text": (15, 30, 15),
        "grid_color": (180, 200, 180, 25),
        "watermark_color": (255, 180, 60),
        "timer_bar_color": (200, 255, 200),
    },
    "classified": {
        "bg_prompt_suffix": "Style of a declassified manila folder, redacted document, red stamps, typewriter aesthetic, highly detailed.",
        "card_bg": (45, 38, 25),
        "card_myth_outline": (255, 60, 60),
        "card_truth_outline": (255, 60, 60),
        "card_myth_header_bg": (255, 60, 60),
        "card_truth_header_bg": (255, 60, 60),
        "card_myth_header_text": (255, 255, 255),
        "card_truth_header_text": (255, 255, 255),
        "myth_label": "EXHIBIT A: REDACTED CLAIM",
        "truth_label": "EXHIBIT B: DECLASSIFIED TRUTH",
        "anomaly_label": "EXHIBIT C: ANOMALOUS FILE",
        "subtitle_color": (240, 230, 210),
        "highlight_bg": (255, 60, 60),
        "highlight_text": (255, 255, 255),
        "grid_color": (200, 160, 120, 25),
        "watermark_color": (255, 60, 60),
        "timer_bar_color": (255, 60, 60),
    },
    "cyberpunk": {
        "bg_prompt_suffix": "Style of a futuristic cyberpunk interface, high contrast neon pink and cyan telemetry details, glowing wireframe mesh, highly detailed.",
        "card_bg": (15, 10, 25),
        "card_myth_outline": (255, 0, 128),
        "card_truth_outline": (0, 242, 254),
        "card_myth_header_bg": (255, 0, 128),
        "card_truth_header_bg": (0, 242, 254),
        "card_myth_header_text": (255, 255, 255),
        "card_truth_header_text": (10, 15, 30),
        "myth_label": "THREAT DETECTED: SYSTEM CORRUPTION",
        "truth_label": "RESTORED DATA: VERIFIED FACT",
        "anomaly_label": "EXHIBIT C: ANOMALOUS OVERRIDE",
        "subtitle_color": (255, 255, 255),
        "highlight_bg": (0, 242, 254),
        "highlight_text": (10, 15, 30),
        "grid_color": (255, 0, 128, 20),
        "watermark_color": (255, 0, 128),
        "timer_bar_color": (0, 242, 254),
    },
    "retro_vhs": {
        "bg_prompt_suffix": "Style of an 80s VHS tracking screen, dark purple and magenta scanline overlay, glowing grid, synthesizer aesthetic, highly detailed.",
        "card_bg": (20, 15, 30),
        "card_myth_outline": (255, 100, 0),
        "card_truth_outline": (255, 0, 255),
        "card_myth_header_bg": (255, 100, 0),
        "card_truth_header_bg": (255, 0, 255),
        "card_myth_header_text": (255, 255, 255),
        "card_truth_header_text": (255, 255, 255),
        "myth_label": "VHS RECORD: ANALOG ERROR",
        "truth_label": "VHS DECODED: DECLASSIFIED",
        "anomaly_label": "VHS DECODED: UNIDENTIFIED FILE",
        "subtitle_color": (240, 240, 250),
        "highlight_bg": (255, 0, 255),
        "highlight_text": (255, 255, 255),
        "grid_color": (255, 0, 255, 20),
        "watermark_color": (255, 100, 0),
        "timer_bar_color": (255, 0, 255),
    },
    "terminal": {
        "bg_prompt_suffix": "Style of an early 80s computer terminal, monochrome amber-green phosphors, command line telemetry coordinates, digital scanlines.",
        "card_bg": (10, 25, 10),
        "card_myth_outline": (0, 255, 100),
        "card_truth_outline": (0, 255, 100),
        "card_myth_header_bg": (0, 255, 100),
        "card_truth_header_bg": (0, 255, 100),
        "card_myth_header_text": (10, 25, 10),
        "card_truth_header_text": (10, 25, 10),
        "myth_label": "SYSTEM WARNING: FALSE ENTRY",
        "truth_label": "SYS_VAL // ENCRYPTED_TRUTH",
        "anomaly_label": "SYS_VAL // ANOMALOUS_LOG",
        "subtitle_color": (150, 255, 180),
        "highlight_bg": (0, 255, 100),
        "highlight_text": (10, 25, 10),
        "grid_color": (0, 255, 100, 20),
        "watermark_color": (0, 255, 100),
        "timer_bar_color": (0, 255, 100),
    },
}


# =============================================================================
# STATIC MASCOT — CRT noise cloud
# =============================================================================
def render_static(size: int = 90, expression: str = "neutral") -> Image.Image:
    """
    Renders 'Static' — the channel mascot. A living cloud of CRT TV static
    noise with glowing dot eyes and a flickering smile.
    Returns an RGBA PIL Image ready for compositing.

    Expressions: 'neutral' (default), 'shocked', 'happy', 'wink'
    """
    canvas = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(canvas)
    rng = random.Random(42)  # deterministic noise seed for consistency

    cx, cy = size // 2, size // 2
    body_r = int(size * 0.40)

    # --- Step 1: Generate noise cloud (static field) ---
    noise_canvas = Image.new("L", (size, size), 0)
    noise_draw = ImageDraw.Draw(noise_canvas)

    # Scatter static points in a roughly circular area
    num_points = int(size * 5)
    for _ in range(num_points):
        angle = rng.uniform(0, 2 * 3.14159)
        radius = rng.uniform(0, body_r * 1.1)
        if radius > body_r * 0.8:
            if rng.random() < 0.5:
                continue
        px = cx + int(radius * math.cos(angle))
        py = cy + int(radius * math.sin(angle))
        if 0 <= px < size and 0 <= py < size:
            brightness = rng.randint(60, 255)
            noise_draw.point((px, py), fill=brightness)

    # Blur the noise into a fuzzy cloud
    noise_canvas = noise_canvas.filter(ImageFilter.GaussianBlur(radius=size * 0.08))

    # Create circular mask for soft edges
    mask = Image.new("L", (size, size), 0)
    mask_draw = ImageDraw.Draw(mask)
    mask_draw.ellipse(
        [cx - body_r, cy - body_r, cx + body_r, cy + body_r],
        fill=255
    )
    mask = mask.filter(ImageFilter.GaussianBlur(radius=size * 0.06))

    # Apply mask to noise
    noise_arr = np.array(noise_canvas, dtype=np.float32)
    mask_arr = np.array(mask, dtype=np.float32) / 255.0
    noise_arr = noise_arr * mask_arr
    noise_arr = np.clip(noise_arr, 0, 255).astype(np.uint8)

    # Tint the static: cyan-blue glow (channel's CRT color)
    cloud = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    cloud_arr = np.array(cloud)
    cloud_arr[:, :, 0] = (noise_arr * 0.3).astype(np.uint8)   # R (low)
    cloud_arr[:, :, 1] = (noise_arr * 0.7).astype(np.uint8)   # G (medium - cyan)
    cloud_arr[:, :, 2] = noise_arr.astype(np.uint8)            # B (high - blue)
    cloud_arr[:, :, 3] = np.clip(noise_arr * 1.2, 0, 230).astype(np.uint8)  # alpha

    cloud = Image.fromarray(cloud_arr)

    # --- Step 2: Draw glowing eyes on a separate layer ---
    eye_overlay = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    eye_draw = ImageDraw.Draw(eye_overlay)

    eye_r = max(3, int(size * 0.045))
    eye_spacing = int(size * 0.15)
    eye_y = cy - int(size * 0.03)

    def draw_glow_eye(ex, ey, er, color=(200, 230, 255)):
        """Draw a glowing eye with soft halo."""
        # Outer glow (3 layers)
        for g in range(3, 0, -1):
            glow_r = er * (1 + g * 0.6)
            alpha = 40 // g
            eye_draw.ellipse(
                [ex - glow_r, ey - glow_r, ex + glow_r, ey + glow_r],
                fill=color + (alpha,)
            )
        # Bright core
        eye_draw.ellipse(
            [ex - er, ey - er, ex + er, ey + er],
            fill=(255, 255, 255, 240)
        )

    def draw_eye_line(ex, ey, length, color=(200, 230, 255)):
        """Draw a wink line with glow."""
        for g in range(2, 0, -1):
            glow_len = length + g * 4
            alpha = 30 // g
            eye_draw.line(
                [(ex - glow_len // 2, ey), (ex + glow_len // 2, ey)],
                fill=color + (alpha,), width=max(2, int(size * 0.03))
            )
        eye_draw.line(
            [(ex - length // 2, ey), (ex + length // 2, ey)],
            fill=(255, 255, 255, 240), width=max(2, int(size * 0.035))
        )

    # --- Step 3: Draw mouth ---
    mouth_y = cy + int(size * 0.08)

    def draw_mouth_glow(start_a, end_a, r_x, r_y):
        """Draw a mouth arc with glow."""
        for g in range(2, 0, -1):
            glow_rx = r_x + g * 3
            glow_ry = r_y + g * 2
            alpha = 35 // g
            eye_draw.arc(
                [cx - glow_rx, mouth_y - glow_ry, cx + glow_rx, mouth_y + glow_ry],
                start=start_a, end=end_a, fill=(200, 230, 255, alpha),
                width=max(1, int(size * 0.02))
            )
        eye_draw.arc(
            [cx - r_x, mouth_y - r_y, cx + r_x, mouth_y + r_y],
            start=start_a, end=end_a, fill=(255, 255, 255, 230),
            width=max(2, int(size * 0.04))
        )

    # --- Expression dispatch ---
    if expression == "shocked":
        draw_glow_eye(cx - eye_spacing, eye_y, int(eye_r * 1.4))
        draw_glow_eye(cx + eye_spacing, eye_y, int(eye_r * 1.4))
        mouth_r = max(3, int(size * 0.055))
        for g in range(2, 0, -1):
            gr = mouth_r + g * 3
            alpha = 35 // g
            eye_draw.ellipse(
                [cx - gr, mouth_y - gr, cx + gr, mouth_y + gr],
                fill=(200, 230, 255, alpha)
            )
        eye_draw.ellipse(
            [cx - mouth_r, mouth_y - mouth_r, cx + mouth_r, mouth_y + mouth_r],
            fill=(255, 255, 255, 230)
        )

    elif expression == "happy":
        arc_h = int(size * 0.035)
        eye_draw.arc(
            [cx - eye_spacing - int(size * 0.05), eye_y - arc_h,
             cx - eye_spacing + int(size * 0.05), eye_y + arc_h],
            start=180, end=360, fill=(255, 255, 255, 230),
            width=max(2, int(size * 0.035))
        )
        eye_draw.arc(
            [cx + eye_spacing - int(size * 0.05), eye_y - arc_h,
             cx + eye_spacing + int(size * 0.05), eye_y + arc_h],
            start=180, end=360, fill=(255, 255, 255, 230),
            width=max(2, int(size * 0.035))
        )
        draw_mouth_glow(0, 180, int(size * 0.10), int(size * 0.06))

    elif expression == "wink":
        draw_glow_eye(cx - eye_spacing, eye_y, eye_r)
        draw_eye_line(cx + eye_spacing, eye_y, int(size * 0.08))
        draw_mouth_glow(0, 160, int(size * 0.07), int(size * 0.05))

    else:  # neutral (default)
        draw_glow_eye(cx - eye_spacing, eye_y, eye_r)
        draw_glow_eye(cx + eye_spacing, eye_y, eye_r)
        draw_mouth_glow(0, 160, int(size * 0.06), int(size * 0.04))

    # --- Step 4: Composite eyes/mouth onto the noise cloud ---
    cloud = Image.alpha_composite(cloud, eye_overlay)

    # Add a few flicker dots on the surface (random bright static sparks)
    spark_draw = ImageDraw.Draw(cloud)
    for _ in range(int(size * 0.3)):
        sx = cx + rng.randint(-body_r, body_r)
        sy = cy + rng.randint(-body_r, body_r)
        dist = math.sqrt((sx - cx)**2 + (sy - cy)**2)
        if dist < body_r * 0.8:
            brightness = rng.randint(180, 255)
            spark_draw.point((sx, sy), fill=(brightness, brightness, brightness, rng.randint(80, 200)))

    return cloud


def generate_mascot(size: int = 70, expression: str = "neutral") -> Image.Image:
    """
    Renders the Static mascot — a living CRT noise cloud with glowing eyes.
    Returns an RGBA PIL Image for compositing as easter egg.
    """
    return render_static(size=size, expression=expression)


# =============================================================================
# FORENSIC CARD GENERATION
# =============================================================================
def _load_font(font_path: Optional[str], size: int) -> ImageFont.FreeTypeFont:
    """Load a TTF font or fall back to default."""
    if font_path and os.path.exists(font_path):
        try:
            return ImageFont.truetype(font_path, size)
        except Exception:
            pass
    return ImageFont.load_default()


def generate_card(
    image_path: str,
    label_text: str,
    status_text: str,
    is_truth: bool,
    style_dict: dict,
    topic: str = "",
    add_redactions: bool = False,
    font_path: Optional[str] = None,
) -> Optional[Image.Image]:
    """
    Generates a premium forensic card with:
      - 2-layer drop shadow (dense inner + soft outer)
      - Card outline with colored accent stripe
      - Double image border (colored + white subtle inner)
      - Glowing status dot with outer glow ring
      - Dashed separator stroke
      - Footer metadata with subtle background pill
      - Optional redaction bars with [REDACTED] stamps

    Args:
        image_path: Path to source image
        label_text: Header label (e.g. 'EXHIBIT A')
        status_text: Status text (e.g. 'STATUS: DEBUNKED')
        is_truth: True for truth-side card, False for myth
        style_dict: Dict of colors from STYLE_PRESETS entries
        topic: Topic string for display below image
        add_redactions: Whether to add redaction bars over image area
        font_path: Path to TTF font file (falls back to default)

    Returns:
        RGBA PIL Image of the card or None on failure
    """
    if not image_path or not os.path.exists(image_path):
        return None
    try:
        img = Image.open(image_path).convert("RGB")
        w, h = img.size
        min_dim = min(w, h)
        crop_x = (w - min_dim) // 2
        crop_y = (h - min_dim) // 2
        square_img = img.crop((crop_x, crop_y, crop_x + min_dim, crop_y + min_dim))

        canvas_w, canvas_h = 840, 890
        card_canvas = Image.new("RGBA", (canvas_w, canvas_h), (0, 0, 0, 0))
        draw_card = ImageDraw.Draw(card_canvas)

        # Premium 2-layer drop shadow (dense inner + soft outer)
        draw_card.rounded_rectangle([18, 18, 822, 872], radius=16, fill=(5, 10, 20, 200))
        draw_card.rounded_rectangle([22, 22, 818, 868], radius=14, fill=(10, 12, 25, 100))

        # Card outline (rounded rectangle for a premium feel)
        outline_color = style_dict["card_truth_outline"] if is_truth else style_dict["card_myth_outline"]
        draw_card.rounded_rectangle([10, 10, 810, 860], radius=16, fill=style_dict["card_bg"] + (255,), outline=outline_color + (255,), width=4)

        # Left accent stripe (colored indicator of status)
        draw_card.rectangle([14, 25, 20, 845], fill=outline_color + (255,))

        # Header with subtle underline bar
        header_font = _load_font(font_path, 28)
        draw_card.text((34, 30), label_text.upper(), fill=outline_color + (255,), font=header_font)
        # Subtle header underline (thinner, faded)
        header_underline_y = 64
        header_text_w = draw_card.textlength(label_text.upper(), font=header_font) if hasattr(draw_card, 'textlength') else 300
        draw_card.line([(34, header_underline_y), (34 + int(header_text_w) + 10, header_underline_y)], fill=outline_color + (60,), width=1)

        # Paste body image with rounded corners
        img_w, img_h = 762, 550
        inner_img = square_img.resize((img_w, img_h), Image.Resampling.LANCZOS)

        # Create rounded corner mask for the inner image
        mask = Image.new("L", (img_w, img_h), 0)
        draw_mask = ImageDraw.Draw(mask)
        draw_mask.rounded_rectangle([0, 0, img_w, img_h], radius=12, fill=255)

        # Paste using mask
        card_canvas.paste(inner_img, (34, 78), mask=mask)

        # Premium double border around the image
        draw_card.rounded_rectangle([34, 78, 34 + img_w, 78 + img_h], radius=12, outline=outline_color + (50,), width=1)
        draw_card.rounded_rectangle([36, 80, 34 + img_w - 2, 78 + img_h - 2], radius=10, outline=(255, 255, 255, 25), width=1)

        # Topic text with separator line above
        topic_font = _load_font(font_path, 32)
        display_topic = (topic or label_text).upper()
        if len(display_topic) > 34:
            display_topic = display_topic[:31] + "..."

        # Subtle separator line above topic
        topic_sep_y = 648
        draw_card.line([(34, topic_sep_y), (796, topic_sep_y)], fill=(255, 255, 255, 25), width=1)
        draw_card.text((34, 658), display_topic, fill=(255, 255, 255, 240), font=topic_font)

        # Status dot & label
        status_y = 708
        is_debunked = ("DEBUNKED" in status_text.upper() or "ANOMALOUS" in status_text.upper())
        dot_color = (255, 60, 60) if is_debunked else (0, 242, 254)
        # Draw glowing status dot with outer glow ring
        glow_radius = 12
        dot_cx, dot_cy = 40, status_y + 12
        draw_card.ellipse([dot_cx - glow_radius, dot_cy - glow_radius, dot_cx + glow_radius, dot_cy + glow_radius], fill=dot_color + (40,))
        draw_card.ellipse([34, status_y + 6, 46, status_y + 18], fill=dot_color + (255,))
        status_font = _load_font(font_path, 20)
        draw_card.text((56, status_y), status_text.upper(), fill=outline_color + (255,), font=status_font)

        # Dashed/Subtle separator
        sep_y = 750
        for dash_x in range(34, 796, 20):
            draw_card.line([(dash_x, sep_y), (min(dash_x + 10, 796), sep_y)], fill=(255, 255, 255, 30), width=1)

        # Footer metadata with subtle background pill
        footer_y = 770
        case_num = f"CASE #{abs(hash(topic or label_text)) % 9999:04d}"
        footer_font = _load_font(font_path, 18)
        footer_text = f"{case_num}  |  THE DAILY AUDIT"
        fw = int(draw_card.textlength(footer_text, font=footer_font)) if hasattr(draw_card, 'textlength') else 0
        # Subtle background pill behind footer
        pill_pad = 12
        pill_x1 = 34 - 4
        pill_y1 = footer_y - 4
        pill_x2 = 34 + fw + pill_pad + 4
        pill_y2 = footer_y + 24 + 4
        draw_card.rounded_rectangle([pill_x1, pill_y1, pill_x2, pill_y2], radius=6, fill=(255, 255, 255, 12))
        draw_card.text((34, footer_y), footer_text, fill=(255, 255, 255, 100), font=footer_font)

        # Redaction bars for Scene 1 — curiosity gap (black bars with [REDACTED] stamps over the image)
        if add_redactions:
            seed_str = (topic or label_text or str(style_dict.get("myth_label", "")))
            rng_seed = int(hashlib.md5(seed_str.encode()).hexdigest(), 16) % 999999
            rng = random.Random(rng_seed)

            num_bars = rng.randint(2, 3)
            redaction_draw = ImageDraw.Draw(card_canvas)

            bar_left = 34
            bar_right = 796
            bar_width = bar_right - bar_left

            img_top = 85
            img_bottom = 85 + 540
            img_height = 540

            used_regions = []

            for b in range(num_bars):
                bar_height = rng.randint(35, 75)
                for attempt in range(20):
                    bar_y = rng.randint(img_top + 10, img_bottom - bar_height - 10)
                    overlap = False
                    for (used_y, used_h) in used_regions:
                        if bar_y < used_y + used_h and bar_y + bar_height > used_y:
                            overlap = True
                            break
                    if not overlap:
                        break

                used_regions.append((bar_y, bar_height))

                # Black bar with slight transparency for subtle CRT feel
                redaction_draw.rectangle(
                    [bar_left, bar_y, bar_right, bar_y + bar_height],
                    fill=(0, 0, 0, 230)
                )
                # Thin red top border on the bar (classified stamp aesthetic)
                redaction_draw.rectangle(
                    [bar_left, bar_y, bar_right, bar_y + 2],
                    fill=(180, 40, 40, 200)
                )
                # "[REDACTED]" text centered in the bar
                redacted_text = "[REDACTED]"
                red_font = _load_font(font_path, max(14, bar_height // 3))
                rt_w = int(draw_card.textlength(redacted_text, font=red_font)) if hasattr(draw_card, 'textlength') else 0
                red_x = (bar_left + bar_right - rt_w) // 2 if rt_w else bar_left + 30
                red_y = bar_y + (bar_height - max(14, bar_height // 3)) // 2
                redaction_draw.text((red_x, red_y), redacted_text, fill=(180, 40, 40, 200), font=red_font)

        return card_canvas
    except Exception as e:
        print(f"[cards.py] WARNING: Failed to generate forensic card for {image_path}: {e}")
        return None


def generate_dynamic_cards(
    image_paths: List[str],
    scene_count: int,
    style_dict: dict,
    font_path: Optional[str] = None,
) -> List[Optional[Image.Image]]:
    """
    Generates N forensic cards with sequential exhibit labels
    (EXHIBIT A, EXHIBIT B, ...).

    Args:
        image_paths: List of image file paths
        scene_count: Number of cards to generate
        style_dict: Dict of colors from STYLE_PRESETS entries
        font_path: Path to TTF font file (falls back to default)

    Returns:
        List of RGBA PIL Images (None for failed cards)
    """
    cards = []
    for i in range(scene_count):
        label = f"EXHIBIT {chr(65 + i)}"
        img_path = image_paths[i] if i < len(image_paths) else (image_paths[-1] if image_paths else "")
        card = generate_card(
            image_path=img_path,
            label_text=label,
            status_text=f"STATUS: SCENE {i+1} EVIDENCE",
            is_truth=True,
            style_dict=style_dict,
            font_path=font_path,
        )
        cards.append(card)
    return cards


# =============================================================================
# THUMBNAIL GENERATION
# =============================================================================
def generate_thumbnail(
    topic: str,
    hook: str,
    output_name: str,
    style: str = "blueprint",
    img_myth_path: Optional[str] = None,
    img_truth_path: Optional[str] = None,
    bizarre_mode: bool = False,
    episode_num: Optional[int] = None,
    font_path: Optional[str] = None,
    assets_dir: Optional[str] = None,
) -> Optional[str]:
    """
    Generates a thumbnail using actual video images. Supports myth/truth
    diagonal, bizarre anomaly, and fallback blueprint.

    If thumbnail_generator module is available, delegates to it for
    image-based thumbnails. Otherwise falls back to a PIL-based blueprint
    with the Static mascot on the right side.

    Args:
        topic: Topic label text
        hook: Title/hook text for the thumbnail
        output_name: Base filename for output (without extension)
        style: Style preset key ('blueprint', 'chalkboard', etc.)
        img_myth_path: Path to myth-side image
        img_truth_path: Path to truth-side image
        bizarre_mode: Enable bizarre/anomaly thumbnail mode
        episode_num: Episode number for display
        font_path: Path to TTF font file
        assets_dir: Directory to save thumbnail output

    Returns:
        Path to saved thumbnail image, or None on failure
    """
    title = hook if hook else topic

    # Try to use thumbnail_generator module if available
    try:
        from thumbnail_generator import ThumbnailDesigner

        if bizarre_mode:
            img_path = img_myth_path or img_truth_path
            hd = ThumbnailDesigner(width=1280, height=720)
            thumb = hd.generate_bizarre_thumbnail(bg_image_path=img_path, title_text=title, topic_label=topic, episode_num=episode_num)
            out_dir = assets_dir or os.path.dirname(output_name) or "."
            out_path = os.path.join(out_dir, f"{output_name}_thumb.png")
            thumb.save(out_path, "PNG", optimize=True)
            print(f"[cards.py] Bizarre thumbnail (16:9) saved: {out_path}")
            short = ThumbnailDesigner(width=1080, height=1920)
            thumb_short = short.generate_bizarre_thumbnail(bg_image_path=img_path, title_text=title, topic_label=topic, episode_num=episode_num)
            short_out = os.path.join(out_dir, f"{output_name}_thumb_shorts.png")
            thumb_short.save(short_out, "PNG", optimize=True)
            print(f"[cards.py] Bizarre thumbnail (9:16) saved: {short_out}")
            return out_path

        if img_myth_path and img_truth_path and os.path.exists(img_myth_path) and os.path.exists(img_truth_path):
            hd = ThumbnailDesigner(width=1280, height=720)
            thumb = hd.generate_from_images(img_myth_path, img_truth_path, title_text=title, topic_label=topic, episode_num=episode_num)
            out_dir = assets_dir or os.path.dirname(output_name) or "."
            out_path = os.path.join(out_dir, f"{output_name}_thumb.png")
            thumb.save(out_path, "PNG", optimize=True)
            print(f"[cards.py] Diagonal myth/truth thumbnail (16:9) saved: {out_path}")
            short = ThumbnailDesigner(width=1080, height=1920)
            thumb_short = short.generate_from_images(img_myth_path, img_truth_path, title_text=title, topic_label=topic, episode_num=episode_num)
            short_out = os.path.join(out_dir, f"{output_name}_thumb_shorts.png")
            thumb_short.save(short_out, "PNG", optimize=True)
            print(f"[cards.py] Diagonal myth/truth thumbnail (9:16) saved: {short_out}")
            return out_path
    except ImportError:
        pass  # Fall through to PIL-based fallback below

    # Fallback: PIL-based blueprint thumbnail with Static mascot
    st = STYLE_PRESETS.get(style, STYLE_PRESETS["blueprint"])
    thumb_w, thumb_h = 1280, 720
    img = Image.new("RGB", (thumb_w, thumb_h), (10, 15, 30))
    draw = ImageDraw.Draw(img)

    # Grid overlay
    for x in range(0, thumb_w, 40):
        draw.line([(x, 0), (x, thumb_h)], fill=st["grid_color"], width=1)
    for y in range(0, thumb_h, 40):
        draw.line([(0, y), (thumb_w, y)], fill=st["grid_color"], width=1)

    # Border frame
    draw.rectangle([30, 30, thumb_w - 30, thumb_h - 30], outline=st["card_myth_outline"] + (200,), width=4)

    # Load fonts
    font_large = _load_font(font_path, 52)
    font_medium = _load_font(font_path, 36)
    font_small = _load_font(font_path, 22)

    # Channel label
    label = "THE DAILY AUDIT"
    lw = draw.textlength(label, font=font_medium)
    draw.text(((thumb_w - lw) // 2, 60), label, fill=st["highlight_bg"] + (255,), font=font_medium)
    draw.line([(thumb_w // 4, 110), (3 * thumb_w // 4, 110)], fill=st["highlight_bg"] + (255,), width=2)

    # Word-wrap the hook
    words = hook.split()
    lines = []
    current = []
    max_w = thumb_w - 120
    for w in words:
        test = " ".join(current + [w])
        if draw.textlength(test, font=font_large) <= max_w:
            current.append(w)
        else:
            lines.append(" ".join(current))
            current = [w]
    if current:
        lines.append(" ".join(current))

    y_center = thumb_h // 2 - (len(lines) * 40)
    for line in lines:
        lw = draw.textlength(line, font=font_large)
        draw.text(((thumb_w - lw) // 2, y_center), line, fill=(255, 255, 255), font=font_large)
        y_center += 60

    # Badge
    badge_text = "CLASSIFIED TRUTH FILE"
    badge_w = draw.textlength(badge_text, font=font_small) + 30
    badge_x = (thumb_w - badge_w) // 2
    badge_y = thumb_h - 100
    draw.rounded_rectangle([badge_x, badge_y, badge_x + badge_w, badge_y + 40], radius=6, fill=st["card_myth_outline"] + (255,))
    draw.text((badge_x + 15, badge_y + 8), badge_text, fill=(255, 255, 255), font=font_small)

    # --- Composite Static mascot on the right side ---
    mascot = render_static(size=90, expression="wink")
    mascot_x = thumb_w - 120
    mascot_y = thumb_h - 190
    img.paste(mascot, (mascot_x, mascot_y), mascot)

    # Save
    out_dir = assets_dir or os.path.dirname(output_name) or "."
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, f"{output_name}_thumb.png")
    img.save(out_path, "PNG")
    print(f"[cards.py] Thumbnail saved: {out_path}")
    return out_path

# =============================================================================
# Kinetic Subtitle Module — Standalone functions extracted from video_engine.py
# =============================================================================
import os
import re
import math
import xml.etree.ElementTree as ET
from typing import List, Dict, Any, Optional

import numpy as np
from PIL import Image, ImageDraw, ImageFont

# ---------------------------------------------------------------------------
# Shared constants
# ---------------------------------------------------------------------------
CHARS_PER_SECOND = 33
Y_POS_DEFAULT = 1680
MAX_LINES = 2
LOOKAHEAD_MS = 200

# ---------------------------------------------------------------------------
# Style presets (mirrored from video_engine.STYLE_PRESETS)
# ---------------------------------------------------------------------------
STYLE_PRESETS = {
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
        "card_myth_header_text": (5, 15, 5),
        "card_truth_header_text": (5, 15, 5),
        "myth_label": "TERMINAL 0x01: FLOATING SIGNAL",
        "truth_label": "TERMINAL 0x02: VERIFIED DATA",
        "anomaly_label": "TERMINAL 0x03: ANOMALOUS ENTRY",
        "subtitle_color": (0, 255, 100),
        "highlight_bg": (0, 255, 100),
        "highlight_text": (5, 15, 5),
        "grid_color": (0, 255, 100, 20),
        "watermark_color": (0, 255, 100),
        "timer_bar_color": (0, 255, 100),
    },
}


# ===========================================================================
# 1. SRT file parser
# ===========================================================================
def parse_srt_file(srt_path: str) -> list:
    """
    Parse an SRT subtitle file and return a list of dicts:
        [{"start_ms": int, "end_ms": int, "text": str}, ...]
    Returns empty list on failure.
    """
    if not os.path.exists(srt_path):
        return []
    try:
        with open(srt_path, "r", encoding="utf-8") as f:
            content = f.read()
        blocks = []
        entries = re.split(r"\n\s*\n", content.strip())
        for entry in entries:
            lines = [l.strip() for l in entry.strip().split("\n") if l.strip()]
            if len(lines) >= 3:
                times = lines[1]
                text = "\n".join(lines[2:])
                match = re.match(
                    r"(\d+):(\d+):(\d+),(\d+)\s*-->\s*(\d+):(\d+):(\d+),(\d+)", times
                )
                if match:
                    h1, m1, s1, ms1, h2, m2, s2, ms2 = map(int, match.groups())
                    start_ms = ((h1 * 3600 + m1 * 60 + s1) * 1000) + ms1
                    end_ms = ((h2 * 3600 + m2 * 60 + s2) * 1000) + ms2
                    blocks.append(
                        {"start_ms": start_ms, "end_ms": end_ms, "text": text}
                    )
        return blocks
    except Exception as e:
        print(f"[subtitles] Error parsing SRT file {srt_path}: {e}")
        return []


# ===========================================================================
# 2. Static SRT subtitle block renderer
# ===========================================================================
def render_srt_subtitle_block(
    draw: ImageDraw.Draw,
    font: ImageFont.FreeTypeFont,
    text: str,
    y_pos: int = 1450,
):
    """
    Render a static SRT subtitle block. Wraps text to 960 px max width,
    centred horizontally, with a 4 px drop shadow and 2 px black stroke.
    """
    max_width = 960
    wrapped_lines = []

    raw_lines = text.split("\n")
    for raw_line in raw_lines:
        words = raw_line.split()
        current_line = []
        for word in words:
            test_line = " ".join(current_line + [word])
            line_w = draw.textlength(test_line, font=font)
            if line_w <= max_width:
                current_line.append(word)
            else:
                if current_line:
                    wrapped_lines.append(" ".join(current_line))
                current_line = [word]
        if current_line:
            wrapped_lines.append(" ".join(current_line))

    line_height = 70
    for i, line in enumerate(wrapped_lines):
        line_w = draw.textlength(line, font=font)
        x = (1080 - line_w) // 2
        y = y_pos + (i * line_height)
        # 4 px offset drop shadow (50 % opacity black)
        draw.text((x + 4, y + 4), line, fill=(0, 0, 0, 128), font=font)
        # 2 px black stroke, white fill, no background box
        draw.text(
            (x, y),
            line,
            fill=(255, 255, 255),
            font=font,
            stroke_width=2,
            stroke_fill=(0, 0, 0),
        )


# ===========================================================================
# 3. Kinetic SRT block (word-level highlighting via word_boundaries)
# ===========================================================================
def render_kinetic_srt_block(
    draw: ImageDraw.Draw,
    font: ImageFont.FreeTypeFont,
    emphasis_font: ImageFont.FreeTypeFont,
    block_text: str,
    t_audio_ms: float,
    word_boundaries: list,
    y_pos: int = Y_POS_DEFAULT,
    style: dict = None,
    block_start_ms: float = None,
):
    """
    Render an SRT subtitle block with word-level kinetic highlighting.

    Uses real word-level timestamps (from word_boundaries) to highlight the
    currently spoken word with a yellow background pill. Emphasis words are
    rendered at 130% font size (supplied as emphasis_font) with accent colour
    background. Output is capped at 2 lines; y=1840 guard prevents overflow
    past frame bottom (1920 px).
    """
    if style is None:
        style = STYLE_PRESETS["blueprint"]

    highlight_bg = style.get("highlight_bg", (255, 242, 0))
    accent_color = style.get("card_myth_outline", (255, 75, 75))

    block_words = block_text.split()

    # ── Determine which word in the block is currently spoken ──────────
    active_word_index_in_block = -1
    if word_boundaries:
        active_word_idx_global = -1
        for idx, wb in enumerate(word_boundaries):
            wb_start = wb["offset_ms"]
            wb_end = wb["offset_ms"] + wb["duration_ms"]
            if wb_start <= t_audio_ms < wb_end:
                active_word_idx_global = idx
                break
        
        if active_word_idx_global != -1:
            if block_start_ms is not None:
                block_start_global_idx = -1
                min_diff = 999999.0
                for idx, wb in enumerate(word_boundaries):
                    diff = abs(wb["offset_ms"] - block_start_ms)
                    if diff < min_diff:
                        min_diff = diff
                        block_start_global_idx = idx
                if block_start_global_idx != -1:
                    active_word_index_in_block = active_word_idx_global - block_start_global_idx
            else:
                # Fallback text alignment
                active_word_str = word_boundaries[active_word_idx_global]["word"]
                active_word_clean = re.sub(r'[^\w]', '', active_word_str).lower()
                for w_idx, word in enumerate(block_words):
                    word_clean = re.sub(r'[^\w]', '', word).lower()
                    if word_clean == active_word_clean:
                        active_word_index_in_block = w_idx
                        break

    # ── Emphasis word indices ──────────────────────────────────────────
    emphasis_indices = set()
    if len(block_words) >= 4:
        for ei in range(3, len(block_words), 5):
            emphasis_indices.add(ei)
        emphasis_indices.add(len(block_words) - 1)

    # ── Word-wrap with per-word metadata ───────────────────────────────
    max_width = 800
    wrapped_line_words = []  # list of lists: (word, is_active, is_emphasis, use_font, w_width)
    current_line = []
    current_width = 0.0
    space_width = draw.textlength(" ", font=font)

    for word_idx, word in enumerate(block_words):
        is_active = word_idx == active_word_index_in_block
        is_emphasis = word_idx in emphasis_indices
        use_font = emphasis_font if is_emphasis else font
        w_width = draw.textlength(word, font=use_font)

        if not current_line:
            current_line = [(word, is_active, is_emphasis, use_font, w_width)]
            current_width = w_width
        else:
            new_width = current_width + space_width + w_width
            if new_width <= max_width:
                current_line.append((word, is_active, is_emphasis, use_font, w_width))
                current_width = new_width
            else:
                wrapped_line_words.append(current_line)
                current_line = [(word, is_active, is_emphasis, use_font, w_width)]
                current_width = w_width

    if current_line:
        wrapped_line_words.append(current_line)

    # SAFETY: cap at max 2 lines
    if len(wrapped_line_words) > MAX_LINES:
        wrapped_line_words = wrapped_line_words[:MAX_LINES]

    line_height = 80  # taller to accommodate 68 px emphasis font
    y_cursor = y_pos

    for line_words in wrapped_line_words:
        # y=1840 guard: skip if this line would go past frame bottom (1920 px)
        if y_cursor + line_height + 10 > 1920:
            break

        total_w = sum(w[4] for w in line_words) + space_width * (len(line_words) - 1)
        x_cursor = (1080 - int(total_w)) // 2

        for word_info in line_words:
            w_text, w_active, w_emphasis, w_font, w_width = word_info

            if w_active:
                # Active word: yellow highlight pill with rounded corners
                h_padding = 8
                v_padding = 6
                pill_x1 = x_cursor - h_padding
                pill_y1 = y_cursor - v_padding
                pill_x2 = x_cursor + int(w_width) + h_padding
                pill_y2 = y_cursor + line_height + v_padding
                draw.rounded_rectangle(
                    [pill_x1, pill_y1, pill_x2, pill_y2],
                    radius=6,
                    fill=highlight_bg + (255,),
                )
                draw.text(
                    (x_cursor, y_cursor), w_text, fill=(10, 15, 30), font=w_font
                )
            elif w_emphasis:
                # Emphasis word: accent colour with subtle glow
                draw.text(
                    (x_cursor + 3, y_cursor + 3),
                    w_text,
                    fill=(0, 0, 0, 80),
                    font=w_font,
                )
                draw.text(
                    (x_cursor, y_cursor),
                    w_text,
                    fill=accent_color + (255,),
                    font=w_font,
                )
            else:
                # Normal word: white with 1 px stroke
                draw.text(
                    (x_cursor + 2, y_cursor + 2),
                    w_text,
                    fill=(0, 0, 0, 60),
                    font=w_font,
                )
                draw.text(
                    (x_cursor, y_cursor),
                    w_text,
                    fill=(255, 255, 255),
                    font=w_font,
                    stroke_width=1,
                    stroke_fill=(0, 0, 0),
                )

            x_cursor += int(w_width) + int(space_width)

        y_cursor += line_height


# ===========================================================================
# 4. Highlighted subtitles (full kinetic renderer with style & animations)
# ===========================================================================
def render_highlighted_subtitles(
    draw: ImageDraw.Draw,
    font: ImageFont.FreeTypeFont,
    words: List[Dict[str, Any]],
    t: float,
    style: dict = None,
    y_pos: int = 330,
    font_px_height: int = 52,
):
    """
    Draw phrase lines with word-level kinetic highlights onto a PIL ImageDraw
    context. Subtitles are wrapped to stay within safe margins (width <= 900 px)
    and centred. y_pos defaults to ~330 px to avoid Shorts UI overlap.

    Active words receive a pill highlight box with optional elastic bounce scale,
    rotation sweep, and mid-roll / emphasis variant styling.
    """
    if style is None:
        style = STYLE_PRESETS["blueprint"]

    # ── Find the active word index ─────────────────────────────────────
    active_word_idx = -1
    for idx, w in enumerate(words):
        if w["start_time"] <= t <= w["end_time"]:
            active_word_idx = idx
            break

    if active_word_idx == -1:
        for idx in range(len(words) - 1, -1, -1):
            if words[idx]["end_time"] <= t:
                active_word_idx = idx
                break
        if active_word_idx == -1:
            active_word_idx = 0

    active_word = words[active_word_idx]
    active_phrase_idx = active_word["phrase_idx"]

    # Filter all words belonging to this active phrase
    phrase_words = [w for w in words if w["phrase_idx"] == active_phrase_idx]

    space_width = draw.textlength(" ", font=font)

    # ── Build wrapped lines (max 800 px) ───────────────────────────────
    max_width = 800
    lines = []
    current_line = []
    current_width = 0.0

    for w in phrase_words:
        w_str = w["word"]
        w_width = draw.textlength(w_str, font=font)
        if not current_line:
            current_line.append(w)
            current_width = w_width
        else:
            new_width = current_width + space_width + w_width
            if new_width <= max_width:
                current_line.append(w)
                current_width = new_width
            else:
                lines.append(current_line)
                current_line = [w]
                current_width = w_width
    if current_line:
        lines.append(current_line)

    line_height = max(70, int(font_px_height * 1.35))

    # ── Render each line ──────────────────────────────────────────────
    for line in lines:
        line_width = sum(
            draw.textlength(w["word"], font=font) for w in line
        ) + space_width * (len(line) - 1)
        current_x = (1080 - line_width) // 2

        for w in line:
            word_str = w["word"]
            word_width = draw.textlength(word_str, font=font)

            is_active = words.index(w) == active_word_idx

            if is_active:
                is_mid_roll = w.get("is_mid_roll", False)
                is_emp = w.get("is_emphasized", False)
                box_padding_x = 10
                box_padding_y = int(font_px_height * 0.12)
                canvas_w = int(word_width) + 2 * box_padding_x
                canvas_h = font_px_height + 2 * box_padding_y

                # Mid-roll active word: pulse to 1.1x
                if is_mid_roll:
                    pulse_scale = 1.0 + 0.10 * math.sin((t - w["start_time"]) * 8.0)
                    canvas_w = int(canvas_w * pulse_scale)
                    canvas_h = int(canvas_h * pulse_scale)

                # Create temporary RGBA canvas for active word highlight
                word_canvas = Image.new("RGBA", (canvas_w, canvas_h), (0, 0, 0, 0))
                word_draw = ImageDraw.Draw(word_canvas)

                # Pill fill & text colour
                pill_fill = (
                    style.get("card_myth_outline", (255, 75, 75)) + (255,)
                    if is_emp
                    else style["highlight_bg"] + (255,)
                )
                text_fill = (
                    (255, 255, 255, 255)
                    if is_emp
                    else style["highlight_text"] + (255,)
                )

                word_draw.rounded_rectangle(
                    [0, 0, canvas_w, canvas_h], radius=10, fill=pill_fill
                )
                word_draw.text(
                    (box_padding_x, box_padding_y), word_str, fill=text_fill, font=font
                )

                # Elastic bounce scale & rotation sweep
                word_dur = max(0.01, w["end_time"] - w["start_time"])
                progress = min(1.0, max(0.0, (t - w["start_time"]) / word_dur))
                pulse_scale = 1.0 + 0.12 * math.sin(progress * math.pi)
                if is_emp:
                    pulse_scale *= 1.2
                angle = -2.0 + 4.0 * progress

                new_w = int(canvas_w * pulse_scale)
                new_h = int(canvas_h * pulse_scale)

                if new_w > 5 and new_h > 5:
                    word_canvas = word_canvas.resize(
                        (new_w, new_h), Image.Resampling.BILINEAR
                    )
                    word_canvas = word_canvas.rotate(
                        angle, expand=True, resample=Image.Resampling.BICUBIC
                    )

                    orig_center_x = current_x + word_width / 2
                    orig_center_y = y_pos + font_px_height / 2
                    rot_w, rot_h = word_canvas.size
                    paste_x = int(orig_center_x - rot_w / 2)
                    paste_y = int(orig_center_y - rot_h / 2)

                    if hasattr(draw, "_image"):
                        draw._image.paste(word_canvas, (paste_x, paste_y), word_canvas)
                    else:
                        draw.text(
                            (current_x, y_pos), word_str, fill=text_fill, font=font
                        )
                else:
                    draw.text(
                        (current_x, y_pos), word_str, fill=text_fill, font=font
                    )
            else:
                is_mid_roll = w.get("is_mid_roll", False)
                is_emp = w.get("is_emphasized", False)
                shadow_color = (0, 0, 0)
                shadow_offset = 3

                if is_mid_roll:
                    mid_tint = style["watermark_color"] + (77,)  # 30 % opacity
                    draw.text(
                        (current_x + shadow_offset, y_pos + shadow_offset),
                        word_str,
                        fill=shadow_color,
                        font=font,
                    )
                    draw.text(
                        (current_x, y_pos),
                        word_str,
                        fill=mid_tint,
                        font=font,
                    )
                    draw.line(
                        [
                            (current_x, y_pos + font_px_height + 2),
                            (current_x + word_width, y_pos + font_px_height + 2),
                        ],
                        fill=style["watermark_color"] + (180,),
                        width=2,
                    )
                elif is_emp:
                    draw.text(
                        (current_x + shadow_offset, y_pos + shadow_offset),
                        word_str,
                        fill=shadow_color,
                        font=font,
                    )
                    draw.text(
                        (current_x, y_pos),
                        word_str,
                        fill=style["highlight_bg"] + (255,),
                        font=font,
                    )
                else:
                    draw.text(
                        (current_x + shadow_offset, y_pos + shadow_offset),
                        word_str,
                        fill=shadow_color,
                        font=font,
                    )
                    draw.text(
                        (current_x, y_pos),
                        word_str,
                        fill=style["subtitle_color"] + (255,),
                        font=font,
                    )

            # Active mid-roll word: extra underline
            if is_active and w.get("is_mid_roll", False):
                draw.line(
                    [
                        (current_x, y_pos + font_px_height + 4),
                        (current_x + word_width, y_pos + font_px_height + 4),
                    ],
                    fill=style["watermark_color"] + (220,),
                    width=3,
                )

            current_x += word_width + space_width

        y_pos += line_height


# ===========================================================================
# 5. Word timing calculation from script text
# ===========================================================================
def calculate_word_timings(
    payload: Dict[str, Any],
    duration: float,
    chars_per_second: float = CHARS_PER_SECOND,
) -> List[Dict[str, Any]]:
    """
    Estimate character-level timing bounds for every word in the script,
    accounting for phrase boundaries and break intervals to ensure
    approximate sync with TTS output.

    Returns a list of dicts:
        [{"word": str, "phrase_idx": int, "length": int,
          "start_time": float, "end_time": float}, ...]
    """
    is_new_style = "ssml_script" in payload or payload.get("is_new_prompt_style", False)

    if is_new_style:
        hook = (payload.get("hook") or "").strip()
        context = (payload.get("context") or "").strip()
        fact = (payload.get("fact") or "").strip()

        fact_sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", fact) if s.strip()]
        if len(fact_sentences) >= 2:
            truth_reveal = fact_sentences[0]
            supporting_fact = " ".join(fact_sentences[1:])
        elif len(fact_sentences) == 1:
            truth_reveal = fact_sentences[0]
            supporting_fact = ""
        else:
            truth_reveal = ""
            supporting_fact = ""

        phrases = [hook, context, truth_reveal]
        if supporting_fact:
            phrases.append(supporting_fact)

        # Break durations between phrases (seconds)
        break_durations = [0.70, 1.20]
        if supporting_fact:
            break_durations.append(0.70)

        cta_text = (payload.get("cta") or "").strip()
        if cta_text:
            phrases.append(cta_text)
            break_durations.append(0.80)
            break_durations.append(0.55)
        else:
            break_durations.append(1.00)

        phrases.append((payload.get("sign_off") or "").strip())
    else:
        # Legacy formatting
        phrases = [
            (payload.get("hook") or "").strip(),
            (payload.get("context") or "").strip(),
            (payload.get("fact") or "").strip(),
        ]
        cta_text = (payload.get("cta") or "").strip()
        if cta_text:
            phrases.append(cta_text)
        phrases.append((payload.get("sign_off") or "").strip())

        break_durations = [0.55, 0.55, 0.80]
        if cta_text:
            break_durations.append(0.55)

    # Build flat word list with phrase indices
    words = []
    for p_idx, phrase in enumerate(phrases):
        phrase_words = phrase.split()
        for w in phrase_words:
            words.append({"word": w, "phrase_idx": p_idx, "length": len(w)})

    total_chars = sum(w["length"] for w in words)
    total_break_time = sum(break_durations)
    active_duration = max(0.1, duration - total_break_time)
    sec_per_char = active_duration / total_chars if total_chars > 0 else 0.1

    current_time = 0.0
    last_phrase_idx = 0

    for w in words:
        p_idx = w["phrase_idx"]
        if p_idx > last_phrase_idx:
            break_idx = last_phrase_idx
            if 0 <= break_idx < len(break_durations):
                current_time += break_durations[break_idx]
            last_phrase_idx = p_idx

        word_dur = w["length"] * sec_per_char
        w["start_time"] = current_time
        w["end_time"] = current_time + word_dur
        current_time = w["end_time"]

    return words


# ===========================================================================
# 6. SSML word emphasis parser
# ===========================================================================
def parse_ssml_words_emphasis(ssml_text: str) -> list:
    """
    Parse an SSML string (potentially containing ``<emphasis>`` tags) and
    return a list of dicts:
        [{"word": clean_word_string, "is_emphasized": bool}]

    Uses xml.etree.ElementTree with a fallback to regex. Bracket cues
    (e.g. ``[sigh]``, ``[whispering]``) are stripped before parsing.
    """
    # Strip bracket cues like [sigh], [whispering], [/whispering]
    ssml_text = re.sub(r"\[[\w\s_/-]+\]", "", ssml_text)

    # Clean text of basic break tags before wrapping
    cleaned_ssml = ssml_text.replace("&", "&amp;")
    wrapped = f"<root>{cleaned_ssml}</root>"

    try:
        root = ET.fromstring(wrapped)
        words_info = []

        def recurse(node, in_emphasis=False):
            is_emp = in_emphasis or (node.tag == "emphasis")

            if node.text:
                for w in node.text.split():
                    words_info.append({"word": w, "is_emphasized": is_emp})

            for child in node:
                recurse(child, is_emp)
                if child.tail:
                    for w in child.tail.split():
                        words_info.append({"word": w, "is_emphasized": in_emphasis})

        recurse(root)
        if words_info:
            return words_info
    except Exception:
        pass

    # Fallback to regex
    emphasis_pattern = re.compile(
        r"<emphasis[^>]*>(.*?)</emphasis>", re.IGNORECASE
    )
    emphasized_words = set()
    for match in emphasis_pattern.finditer(ssml_text):
        for w in match.group(1).split():
            clean = re.sub(r"[^\w]", "", w).lower()
            if clean:
                emphasized_words.add(clean)

    clean_text = re.sub(r"<[^>]+>", "", ssml_text)
    words_info = []
    for w in clean_text.split():
        clean = re.sub(r"[^\w]", "", w).lower()
        is_emp = clean in emphasized_words
        words_info.append({"word": w, "is_emphasized": is_emp})
    return words_info

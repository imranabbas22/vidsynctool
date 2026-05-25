# =============================================================================
# Background Processing Module
# =============================================================================
# Standalone functions extracted from video_engine.py for background video
# frame processing, category theme overlays, blueprint selection, and
# theme music resolution.
# =============================================================================
import os
import random
import re
from typing import Optional, List, Dict, Any, Tuple

import numpy as np
from PIL import Image, ImageFilter

# ---------------------------------------------------------------------------
# Category Theme Registry
# ---------------------------------------------------------------------------
# Each entry defines a tint color (RGB), tint strength (0.0-1.0), and a
# pattern label for optional use in overlay generation.
CATEGORY_THEMES: Dict[str, Dict[str, Any]] = {
    "biology":      {"tint": (20, 100, 30),  "strength": 0.08, "pattern": "cells"},
    "history":      {"tint": (80, 60, 20),   "strength": 0.12, "pattern": "paper"},
    "astronomy":    {"tint": (20, 10, 80),   "strength": 0.10, "pattern": "stars"},
    "physics":      {"tint": (10, 30, 80),   "strength": 0.10, "pattern": "grid"},
    "neuroscience": {"tint": (60, 20, 60),   "strength": 0.08, "pattern": "waves"},
    "psychology":   {"tint": (60, 30, 50),   "strength": 0.08, "pattern": "waves"},
    "technology":   {"tint": (10, 60, 70),   "strength": 0.10, "pattern": "grid"},
    "geology":      {"tint": (50, 40, 10),   "strength": 0.10, "pattern": "dots"},
    "chemistry":    {"tint": (30, 50, 20),   "strength": 0.08, "pattern": "dots"},
    "economics":    {"tint": (40, 40, 60),   "strength": 0.06, "pattern": "lines"},
    "linguistics":  {"tint": (40, 20, 50),   "strength": 0.06, "pattern": "lines"},
    "anthropology": {"tint": (60, 40, 20),   "strength": 0.08, "pattern": "dots"},
}


# ---------------------------------------------------------------------------
# Frame processing
# ---------------------------------------------------------------------------
def process_bg_frame(
    bg_arr: np.ndarray,
    target_w: int = 1080,
    target_h: int = 1920,
    blur_radius: float = 6.0,
    darken_factor: float = 0.45,
) -> np.ndarray:
    """
    Resizes, center-crops, blurs, and darkens a background video frame.

    Parameters
    ----------
    bg_arr : np.ndarray
        Input frame as a numpy array (H, W, 3).
    target_w : int
        Desired width in pixels (default 1080).
    target_h : int
        Desired height in pixels (default 1920).
    blur_radius : float
        Gaussian blur radius in pixels.  Disabled when <= 0.1.
    darken_factor : float
        Blend factor for a dark overlay (10, 15, 30).  Disabled when <= 0.0.

    Returns
    -------
    np.ndarray
        Processed frame with shape (target_h, target_w, 3), dtype uint8.
    """
    h, w, c = bg_arr.shape
    target_aspect = target_w / target_h
    current_aspect = w / h

    # Center-crop to target aspect ratio
    if current_aspect > target_aspect:
        # Too wide – crop sides
        new_w = int(h * target_aspect)
        left = (w - new_w) // 2
        bg_arr_cropped = bg_arr[:, left:left + new_w]
    else:
        # Too tall – crop top/bottom
        new_h = int(w / target_aspect)
        top = (h - new_h) // 2
        bg_arr_cropped = bg_arr[top:top + new_h, :]

    img_pil = Image.fromarray(bg_arr_cropped)
    if img_pil.size != (target_w, target_h):
        img_pil = img_pil.resize((target_w, target_h), Image.Resampling.BILINEAR)

    if blur_radius > 0.1:
        img_pil = img_pil.filter(ImageFilter.GaussianBlur(radius=blur_radius))

    if darken_factor > 0.0:
        dark_overlay = Image.new("RGB", (target_w, target_h), (10, 15, 30))
        img_pil = Image.blend(img_pil, dark_overlay, darken_factor)

    return np.array(img_pil)


# ---------------------------------------------------------------------------
# Category overlay
# ---------------------------------------------------------------------------
def apply_category_overlay(
    frame: np.ndarray,
    category: str,
    t: float,  # kept for API compatibility; not currently used by the tint logic
) -> np.ndarray:
    """
    Apply a subtle category-themed tint overlay to the frame.

    Matches the provided *category* string against :data:`CATEGORY_THEMES`
    keys and blends the matching tint colour into the frame.

    Parameters
    ----------
    frame : np.ndarray
        Input frame (H, W, 3), dtype uint8.
    category : str
        Category key (case-insensitive, fuzzy-matched).
    t : float
        Time value (reserved for future animated overlays).

    Returns
    -------
    np.ndarray
        Tinted frame, or the original frame if no theme matches.
    """
    if not category:
        return frame

    cat_lower = category.lower().strip()
    theme = None
    for key, val in CATEGORY_THEMES.items():
        if key in cat_lower or cat_lower in key:
            theme = val
            break

    if theme is None:
        return frame

    tint_arr = np.array(theme["tint"], dtype=np.float32).reshape(1, 1, 3)
    frame_f = frame.astype(np.float32)
    frame_f = frame_f * (1.0 - theme["strength"]) + tint_arr * theme["strength"]
    return np.clip(frame_f, 0, 255).astype(np.uint8)


# ---------------------------------------------------------------------------
# Blueprint video selection  (from assets/video_blueprints/)
# ---------------------------------------------------------------------------
def select_blueprint_video(search_text: str, assets_dir: str) -> Optional[str]:
    """
    Scan the *video_blueprints* subdirectory under *assets_dir* and select a
    background video whose filename matches keywords extracted from
    *search_text*.

    Falls back to *particles_in_light* or the first available MP4.

    Parameters
    ----------
    search_text : str
        Text to extract keywords from (HTML tags are stripped).
    assets_dir : str
        Path to the root assets directory.

    Returns
    -------
    Optional[str]
        Absolute path to the selected MP4, or None if the directory is
        missing / empty.
    """
    blueprint_dir = os.path.join(assets_dir, "video_blueprints")
    if not os.path.exists(blueprint_dir):
        return None

    mp4_files = []
    for root, dirs, files in os.walk(blueprint_dir):
        for f in files:
            if f.endswith(".mp4"):
                mp4_files.append(os.path.join(root, f))
    if not mp4_files:
        return None

    search_text_clean = re.sub(r"<[^>]+>", "", search_text) if search_text else ""
    search_lower = search_text_clean.lower()

    keyword_mapping = {
        "dna": "DNA_double_helix",
        "genetics": "DNA_double_helix",
        "gene": "DNA_double_helix",
        "cell": "Glowing_cell_divides",
        "mitosis": "Glowing_cell_divides",
        "microchip": "Computer_microchip",
        "circuit": "circuit",
        "server": "Server_room",
        "network": "Neural_network" if "neural" in search_lower or "brain" in search_lower else "circuit",
        "neural": "Neural_network",
        "brain": "Neural_network",
        "book": "Ancient_book_falling",
        "parchment": "Ancient_parchment",
        "scroll": "Ancient_parchment",
        "hourglass": "Antique_hourglass",
        "pendulum": "Brass_pendulum",
        "dismissed": "CLASS_DISMISSED",
        "class": "CLASS_DISMISSED",
        "prism": "Crystal_prism",
        "crystals": "Crystals_growing",
        "chemical": "changes_liquid_color",
        "reaction": "changes_liquid_color",
        "liquid": "changes_liquid_color",
        "gavel": "Gavel_striking",
        "court": "Gavel_striking",
        "judge": "Gavel_striking",
        "law": "Gavel_striking",
        "legal": "Gavel_striking",
        "chair": "Empty_chair",
        "curtains": "velvet_curtains",
        "velvet": "velvet_curtains",
        "wax": "seal_wax",
        "seal": "seal_wax",
        "question": "question_mark_chalk",
        "mark": "question_mark_chalk",
        "ink": "Ink_drop",
        "magnifying": "Magnifying_glass",
        "match": "Match_head_striking",
        "fire": "Match_head_striking",
        "spark": "Match_head_striking",
        "heartbeat": "showing_heartbeat",
        "pulse": "showing_heartbeat",
        "medical": "showing_heartbeat",
        "microscope": "Microscope_eyepiece",
        "collision": "streams_collide",
        "particles": "particles_in_light",
        "smoke": "smoke_rising",
        "stamp": "stamp_debunks",
        "debunk": "stamp_debunks",
        "fabric": "fabric_grid",
        "grid": "fabric_grid",
        "space": "nebula_drift",
        "spiral": "nebula_drift",
        "nebula": "nebula_drift",
        "galaxy": "nebula_drift",
        "saturn": "saturn_ring",
        "orbit": "saturn_ring",
        "planet": "saturn_ring",
        "gravity": "gravitational_lens",
        "evolution": "evolution_tree",
        "ancestor": "evolution_tree",
        "darwin": "evolution_tree",
        "dinosaur": "t_rex_skeleton",
        "skeleton": "t_rex_skeleton",
        "fossil": "t_rex_skeleton",
        "bone": "t_rex_skeleton",
        "virus": "virus_capsid",
        "bacteria": "bacteria_colony",
        "bacterial": "bacteria_colony",
        "antibiotic": "bacteria_colony",
        "gear": "brass_gears",
        "machine": "brass_gears",
        "mechanical": "brass_gears",
        "engine": "steam_piston",
        "globe": "globe_grid",
        "earth": "globe_grid",
        "crust": "crystal_cave",
        "geology": "crystal_cave",
        "scales": "scales_justice",
        "justice": "scales_justice",
        "typewriter": "old_typewriter",
        "compass": "ancient_compass",
        "candle": "candle_flame",
        "flame": "candle_flame",
        "crack": "surface_cracking",
    }

    # Try to find a matching keyword in search_text
    matched_pattern = None
    for kw, pattern in keyword_mapping.items():
        if kw in search_lower:
            matched_pattern = pattern
            break

    if matched_pattern:
        for f in mp4_files:
            if matched_pattern.lower() in os.path.basename(f).lower():
                return f

    # Fallback to Golden_dust_particles_in_light
    for f in mp4_files:
        if "particles_in_light" in os.path.basename(f).lower():
            return f

    # Absolute fallback
    return mp4_files[0]


def select_starting_blueprint(video_type: str, assets_dir: str) -> Optional[str]:
    """
    Selects a starting bumper blueprint from ``{assets_dir}/video_blueprints/starting/``.

    Filters by *myth* or *bizarre* keyword in filename depending on
    *video_type*; falls back to any MP4 in the directory.

    Parameters
    ----------
    video_type : str
        Either ``"myth"`` or ``"bizarre"`` to influence keyword match.
    assets_dir : str
        Path to the root assets directory.

    Returns
    -------
    Optional[str]
        Absolute path to the selected MP4, or None if the directory is
        missing or empty.
    """
    # Try a project-root-level path first, then fall back to assets_dir
    base_dir = os.path.dirname(os.path.abspath(__file__))
    root_start_dir = os.path.join(os.path.dirname(base_dir), "assets", "video_blueprints", "starting")
    if os.path.exists(root_start_dir) and any(f.endswith(".mp4") for f in os.listdir(root_start_dir)):
        start_dir = root_start_dir
    else:
        start_dir = os.path.join(assets_dir, "video_blueprints", "starting")

    if not os.path.exists(start_dir):
        return None

    files = [f for f in os.listdir(start_dir) if f.endswith(".mp4")]
    if not files:
        return None

    keyword = "myth" if video_type == "myth" else "bizarre"
    matched = [f for f in files if keyword in f.lower()]
    if matched:
        return os.path.join(start_dir, random.choice(matched))
    return os.path.join(start_dir, random.choice(files))


def select_ending_blueprint(assets_dir: str) -> Optional[str]:
    """
    Selects an ending bumper blueprint from ``{assets_dir}/video_blueprints/ending/``.

    Prefers files with *class* or *dismissed* in the name.

    Parameters
    ----------
    assets_dir : str
        Path to the root assets directory.

    Returns
    -------
    Optional[str]
        Absolute path to the selected MP4, or None if the directory is
        missing or empty.
    """
    base_dir = os.path.dirname(os.path.abspath(__file__))
    root_end_dir = os.path.join(os.path.dirname(base_dir), "assets", "video_blueprints", "ending")
    if os.path.exists(root_end_dir) and any(f.endswith(".mp4") for f in os.listdir(root_end_dir)):
        end_dir = root_end_dir
    else:
        end_dir = os.path.join(assets_dir, "video_blueprints", "ending")

    if not os.path.exists(end_dir):
        return None

    files = [f for f in os.listdir(end_dir) if f.endswith(".mp4")]
    if not files:
        return None

    dismissed = [f for f in files if "class" in f.lower() or "dismissed" in f.lower()]
    if dismissed:
        return os.path.join(end_dir, random.choice(dismissed))
    return os.path.join(end_dir, random.choice(files))


# ---------------------------------------------------------------------------
# Theme music resolution
# ---------------------------------------------------------------------------
def resolve_theme_music(category: str, assets_dir: str) -> Optional[str]:
    """
    Resolve background music file based on *category*, falling back to
    generic background music in the root ``background_music/`` directory.

    Parameters
    ----------
    category : str
        Category name (e.g. ``"physics"``, ``"history"``).
    assets_dir : str
        Path to the root assets directory.

    Returns
    -------
    Optional[str]
        Absolute path to a random matching MP3, or None if none found.
    """
    music_dir = os.path.join(assets_dir, "background_music")

    # Ensure all category subdirectories exist
    for cat in [
        "physics", "biology", "history", "astronomy", "neuroscience",
        "psychology", "economics", "geology", "chemistry", "technology",
        "linguistics", "anthropology",
    ]:
        os.makedirs(os.path.join(music_dir, cat), exist_ok=True)

    category_clean = category.strip().lower() if category else ""
    cat_music_dir = os.path.join(music_dir, category_clean)
    music_files: List[str] = []
    if category_clean and os.path.exists(cat_music_dir):
        music_files = [
            os.path.join(cat_music_dir, f)
            for f in os.listdir(cat_music_dir)
            if f.endswith(".mp3")
        ]

    if not music_files:
        if os.path.exists(music_dir):
            music_files = [
                os.path.join(music_dir, f)
                for f in os.listdir(music_dir)
                if f.endswith(".mp3") and os.path.isfile(os.path.join(music_dir, f))
            ]

    if music_files:
        return random.choice(music_files)
    return None

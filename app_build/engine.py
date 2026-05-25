# =============================================================================
# "The Daily Audit" — Video Engine (Modular Edition)
# =============================================================================
"""
Clean, modular video compilation engine for The Daily Audit.

All rendering logic lives in renderer/ modules:
  renderer/cards.py       — Card generation, Static mascot, thumbnails
  renderer/subtitles.py   — SRT parsing, kinetic subtitles, word boundaries
  renderer/transitions.py — Burn/glitch transitions, scanline, file stamp
  renderer/background.py  — Background processing, parallax, category overlay
  renderer/audio.py       — SFX synthesis, audio normalization

Usage:
    from engine import VideoEngine, STYLE_PRESETS
    engine = VideoEngine()
    path = engine.compile_short(...)

Config:
    config.yaml — all tunable parameters (subtitles speed, vignette, etc.)
"""
import os
import sys
import math
import gc
import json
import random
import tempfile
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import numpy as np
from typing import List, Dict, Any, Tuple, Optional
import subprocess

from moviepy.editor import (
    AudioClip, AudioFileClip, VideoClip, VideoFileClip,
    CompositeAudioClip, clips_array, concatenate_videoclips
)

# MoviePy v2.x compatibility layer
for clip_class in [AudioClip, AudioFileClip, VideoClip, VideoFileClip, CompositeAudioClip]:
    if not hasattr(clip_class, 'volumex') and hasattr(clip_class, 'with_volume_scaled'):
        clip_class.volumex = clip_class.with_volume_scaled
    if not hasattr(clip_class, 'fl') and hasattr(clip_class, 'transform'):
        clip_class.fl = clip_class.transform
    if not hasattr(clip_class, 'set_start') and hasattr(clip_class, 'with_start'):
        clip_class.set_start = clip_class.with_start
    if not hasattr(clip_class, 'subclip') and hasattr(clip_class, 'subclipped'):
        clip_class.subclip = clip_class.subclipped

# ── Import Renderer Modules ───────────────────────────────────────────────────
from renderer.cards import (
    render_static, generate_mascot, generate_card,
    generate_dynamic_cards, generate_thumbnail as render_thumbnail,
    STYLE_PRESETS,
)
from renderer.subtitles import (
    parse_srt_file, render_srt_subtitle_block,
    render_kinetic_srt_block, render_highlighted_subtitles,
    calculate_word_timings, parse_ssml_words_emphasis,
)
from renderer.transitions import (
    value_noise_2d, generate_burn_mask,
    create_burn_transition_clip, create_transition_clip,
    add_global_progress_bar, create_scanline_overlay, render_stamp,
)
from renderer.background import (
    process_bg_frame, apply_category_overlay,
    select_blueprint_video, select_starting_blueprint,
    select_ending_blueprint, resolve_theme_music,
)
from renderer.audio import (
    ensure_sfx_exist, normalize_and_attach_audio,
)


# ── Config Loader ─────────────────────────────────────────────────────────────

def load_config(path: Optional[str] = None) -> dict:
    """Load config.yaml with fallback defaults."""
    if path is None:
        path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.yaml")

    defaults = {
        "general": {"canvas_width": 1080, "canvas_height": 1920, "fps": 30},
        "subtitles": {"chars_per_second": 33, "y_position": 1540, "max_lines": 2,
                       "lookahead_ms": 200, "font_size": 52, "emphasis_scale_factor": 68},
        "vignette": {"max_darken": 0.35, "power_curve": 1.8, "edge_distance_factor": 1.8},
        "static": {"appearance_chance": 0.75, "default_size": 70, "easter_egg_size": 90},
        "card": {"label_char_limit": 60},
        "scene_timing": {"transition_duration": 0.5, "burn_transition_duration": 0.8,
                          "stamp_animation_duration": 0.15, "stamp_delay": 0.4},
        "emotion_beats": {"scene_1_shocked_weight": 0.45, "scene_3_happy_weight": 0.40,
                           "scene_3_beat_duration": 1.5},
        "audio": {"volume_reduction_during_fact": 0.4, "heartbeat_volume": 0.12},
    }

    if not os.path.exists(path):
        return defaults

    try:
        import yaml
        with open(path, "r", encoding="utf-8") as f:
            loaded = yaml.safe_load(f) or {}
        # Merge loaded values over defaults
        for section, values in loaded.items():
            if section in defaults and isinstance(values, dict):
                defaults[section].update(values)
            else:
                defaults[section] = values
    except Exception:
        pass  # Return defaults on error

    return defaults


# ── VideoEngine Class ─────────────────────────────────────────────────────────

class VideoEngine:
    """
    Stitches images and audio into a vertical YouTube Short video.
    Uses modular renderer/ components for all rendering.
    """

    def __init__(self, font_path: Optional[str] = None, video_seed: Optional[int] = None):
        self.config = load_config()
        base_dir = os.path.dirname(os.path.abspath(__file__))

        self.fonts_dir = os.path.join(base_dir, "fonts")
        self.assets_dir = os.path.join(base_dir, "assets")
        os.makedirs(self.fonts_dir, exist_ok=True)
        os.makedirs(self.assets_dir, exist_ok=True)

        # Font
        self.font_path = font_path or os.path.join(self.fonts_dir, "Montserrat-Bold.ttf")
        self._ensure_font_exists()

        # Video seed for deterministic randomization
        self.video_seed = video_seed

        # Pre-generate mascot
        self.mascot_img = generate_mascot(70, "neutral")

        # CUDA detection
        self.has_cuda = self._detect_cuda_support()

        # Subtitle lookahead
        self.subtitle_lookahead_ms = self.config.get("subtitles", {}).get("lookahead_ms", 200.0)

    def _detect_cuda_support(self) -> bool:
        """Check if NVIDIA NVENC is available."""
        try:
            import imageio_ffmpeg
            ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
        except ImportError:
            ffmpeg_exe = "ffmpeg"
        try:
            startupinfo = None
            if os.name == 'nt':
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            res = subprocess.run(
                [ffmpeg_exe, "-encoders"],
                stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                text=True, startupinfo=startupinfo, timeout=5.0
            )
            if "h264_nvenc" in res.stdout:
                test = subprocess.run(
                    [ffmpeg_exe, "-f", "lavfi", "-i",
                     "color=c=black:s=1080x1920:d=0.1",
                     "-c:v", "h264_nvenc", "-preset", "p7",
                     "-t", "0.1", "-y", os.devnull],
                    stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                    text=True, startupinfo=startupinfo, timeout=10.0
                )
                return test.returncode == 0
            return False
        except Exception:
            return False

    def _ensure_font_exists(self):
        """Download Montserrat Bold if not present."""
        if os.path.exists(self.font_path):
            return
        font_url = ("https://raw.githubusercontent.com/ImranRiazKhan/"
                    "auto-youtube-project/main/app_build/fonts/Montserrat-Bold.ttf")
        print("[Engine] Downloading Montserrat-Bold.ttf...")
        try:
            import urllib.request
            urllib.request.urlretrieve(font_url, self.font_path)
            print("[Engine] Font downloaded successfully.")
        except Exception as e:
            print(f"[Engine] WARNING: Font download failed: {e}")

    # ── Public API ────────────────────────────────────────────────────────────

    def compile_short(self, image_myth_path: str, image_truth_path: str,
                       audio_path: Any, script_payload: Dict[str, Any],
                       output_name: str, category: str = "history",
                       style: str = "blueprint", video_type: str = "myth",
                       image_paths_override: Optional[List[str]] = None) -> str:
        """
        Compile a 3-scene myth-busting Short.
        Delegates to legacy VideoEngine for orchestration.
        """
        from video_engine import VideoEngine as V
        eng = V(font_path=self.font_path, video_seed=self.video_seed)
        eng.mascot_img = self.mascot_img
        eng.subtitle_lookahead_ms = self.subtitle_lookahead_ms
        return eng.compile_short(
            image_myth_path, image_truth_path, audio_path, script_payload,
            output_name, category, style, video_type, image_paths_override
        )

    def compile_bizarre(self, image_paths: List[str], audio_path: Any,
                         script_payload: Dict[str, Any], output_name: str,
                         category: str = "history", style: str = "blueprint",
                         video_type: str = "bizarre") -> str:
        """Compile a 3-scene bizarre Short. Delegates to legacy engine."""
        from video_engine import VideoEngine as LegacyEngine
        legacy = LegacyEngine(font_path=self.font_path, video_seed=self.video_seed)
        legacy.font_path = self.font_path
        legacy.assets_dir = self.assets_dir
        legacy.mascot_img = self.mascot_img
        legacy.subtitle_lookahead_ms = self.subtitle_lookahead_ms
        return legacy.compile_bizarre(
            image_paths, audio_path, script_payload, output_name,
            category, style, video_type
        )

    def compile_dynamic_video(self, image_paths: List[str], audio_paths: List[str],
                               scene_texts: List[str], scene_labels: List[str],
                               scene_titles: List[str], output_name: str,
                               category: str = "history", style: str = "blueprint",
                               video_type: str = "myth",
                               starting_text: Optional[str] = None,
                               ending_text: Optional[str] = None,
                               topic: Optional[str] = None,
                               episode_num: Optional[int] = None) -> str:
        """Compile a dynamic multi-scene video. Delegates to legacy engine."""
        from video_engine import VideoEngine as LegacyEngine
        legacy = LegacyEngine(font_path=self.font_path, video_seed=self.video_seed)
        legacy.font_path = self.font_path
        legacy.assets_dir = self.assets_dir
        legacy.mascot_img = self.mascot_img
        legacy.subtitle_lookahead_ms = self.subtitle_lookahead_ms
        return legacy.compile_dynamic_video(
            image_paths, audio_paths, scene_texts, scene_labels, scene_titles,
            output_name, category, style, video_type,
            starting_text=starting_text, ending_text=ending_text,
            topic=topic, episode_num=episode_num
        )

    def generate_thumbnail(self, topic: str, hook: str, output_name: str,
                            style: str = "blueprint",
                            img_myth_path: str = None,
                            img_truth_path: str = None,
                            bizarre_mode: bool = False,
                            episode_num: Optional[int] = None) -> str:
        """Generate a thumbnail with Static mascot. Uses renderer module."""
        return render_thumbnail(
            topic=topic, hook=hook, output_name=output_name,
            style=style, img_myth_path=img_myth_path,
            img_truth_path=img_truth_path,
            bizarre_mode=bizarre_mode, episode_num=episode_num,
            font_path=self.font_path, assets_dir=self.assets_dir
        )

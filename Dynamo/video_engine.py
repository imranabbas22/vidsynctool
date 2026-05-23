# =============================================================================
# "The Daily Audit" - Video Compilation & Special Effects Engine
# =============================================================================
import os
import sys
import math
import gc
import urllib.request
import random
from typing import List, Dict, Any, Tuple, Optional
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter
try:
    from moviepy.editor import AudioFileClip
except ImportError:
    from moviepy import AudioFileClip

# MoviePy v2.x removed set_start in favour of with_start; patch for compatibility
if not hasattr(AudioFileClip, 'set_start') and hasattr(AudioFileClip, 'with_start'):
    AudioFileClip.set_start = AudioFileClip.with_start

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
}


class VideoEngine:
    """Stitches images and audio into a vertical video applying CRT scanlines, slow zoom, and yellow word-level highlighted subtitles."""

    def __init__(self, font_path: Optional[str] = None, video_seed: Optional[int] = None):
        base_dir = os.path.dirname(os.path.abspath(__file__))
        
        # Create folders
        self.fonts_dir = os.path.join(base_dir, "fonts")
        os.makedirs(self.fonts_dir, exist_ok=True)
        
        self.assets_dir = os.path.join(base_dir, "assets")
        os.makedirs(self.assets_dir, exist_ok=True)

        # Set or download Montserrat Bold font
        self.font_path = font_path or os.path.join(self.fonts_dir, "Montserrat-Bold.ttf")
        self._ensure_font_exists()
        
        # Detect CUDA support once on startup
        self.has_cuda = self._detect_cuda_support()

        # Per-video seed for deterministic randomization (rhythm dict)
        self.video_seed = video_seed
        # Pre-generate mascot easter egg image (always — tiny 80×100 RGBA)
        self.mascot_img = self._generate_mascot()

    def _detect_cuda_support(self) -> bool:
        """
        Queries FFmpeg's available encoders to check if the NVIDIA NVENC H.264
        hardware encoder (h264_nvenc) is supported.
        """
        import subprocess
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
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                startupinfo=startupinfo,
                timeout=5.0
            )
            if "h264_nvenc" in res.stdout:
                # Perform a dry-run encoding check with standard vertical resolution
                # to verify that NVIDIA drivers and CUDA are fully functional
                test_cmd = [
                    ffmpeg_exe, "-y",
                    "-f", "lavfi", "-i", "color=c=black:s=1080x1920:d=0.1",
                    "-c:v", "h264_nvenc",
                    "-f", "null", "-"
                ]
                test_res = subprocess.run(
                    test_cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    startupinfo=startupinfo,
                    timeout=5.0
                )
                if test_res.returncode == 0:
                    print("[VideoEngine] CUDA GPU Acceleration detected and verified (h264_nvenc)!")
                    return True
                else:
                    print("[VideoEngine] h264_nvenc encoder found, but CUDA dry-run encoding failed. Falling back to CPU.")
        except Exception as e:
            print(f"[VideoEngine] Subprocess verification of CUDA failed: {e}. Falling back to CPU.")
        return False

    def _generate_video_rhythm(self, scene_count: int, style: str) -> dict:
        """
        Generates a dict of per-video randomized visual parameters.
        If self.video_seed is set, uses a local Random for deterministic jitter.
        If None, returns dict with current hardcoded defaults (preserves old behaviour).
        """
        rng = random.Random(self.video_seed) if self.video_seed is not None else None

        def _v(key, default, low=None, high=None):
            if rng is None:
                return default
            if isinstance(default, int):
                return rng.randint(low, high) if low is not None else default
            if isinstance(default, float):
                return round(rng.uniform(low, high), 2) if low is not None else default
            return default

        return {
            # Timing
            "card_delay":                _v("card_delay", 1.75, 1.3, 2.2),
            "transition_dur":            _v("transition_dur", 0.5, 0.35, 0.7),
            "card_pop_time":             _v("card_pop_time", 0.2, 0.12, 0.35),
            # Elastic card spring
            "elastic_k":                 _v("elastic_k", 6, 4, 8),
            "elastic_freq":              _v("elastic_freq", 12, 8, 14),
            # Watermark stamp
            "stamp_start":               _v("stamp_start", 0.4, 0.3, 0.7),
            "stamp_end":                 _v("stamp_end", 3.5, 2.5, 5.0),
            "stamp_slam_dur":            _v("stamp_slam_dur", 0.15, 0.1, 0.25),
            "stamp_initial_scale":       _v("stamp_initial_scale", 3.0, 2.0, 4.0),
            # Scanlines & grit
            "scanline_speed":            _v("scanline_speed", 120, 80, 160),
            "grit_fps":                  _v("grit_fps", 15, 8, 24),
            # Background zoom
            "zoom_max":                  _v("zoom_max", 0.12, 0.08, 0.18),
            # Ticking clock
            "tick_interval":             _v("tick_interval", 0.6, 0.4, 1.0),
            # Subtitle positions
            "subtitle_y_top":            _v("subtitle_y_top", 330, 290, 370),
            "subtitle_y_bottom":         _v("subtitle_y_bottom", 1400, 1340, 1460),
            "subtitle_font_size":        _v("subtitle_font_size", 52, 46, 56),
            # Bumper text
            "bumper_font_size":          _v("bumper_font_size", 78, 70, 86),
            "bumper_y_pos":              _v("bumper_y_pos", 800, 740, 860),
            # Glitch transition
            "glitch_window":             _v("glitch_window", 0.20, 0.12, 0.40),
            "glitch_max_shift":          _v("glitch_max_shift", 50, 30, 80),
            "glitch_max_chroma":         _v("glitch_max_chroma", 12, 8, 24),
            "pre_transition_glitch_dur": _v("pre_transition_glitch_dur", 0.15, 0.08, 0.25),
            # HUD
            "radar_speed":               _v("radar_speed", 2.0, 1.5, 3.5),
            # Post-processing
            "blur_radius":               _v("blur_radius", 6.0, 4.0, 8.0),
            "darken_factor":             _v("darken_factor", 0.45, 0.35, 0.55),
            "bumper_zoom":               _v("bumper_zoom", 0.08, 0.05, 0.14),
            # SFX volumes
            "impact_volume":             _v("impact_volume", 0.25, 0.15, 0.35),
            "pop_volume":                _v("pop_volume", 0.15, 0.08, 0.25),
            "zap_volume":                _v("zap_volume", 0.08, 0.04, 0.15),
            # Mascot easter egg
            "mascot_enabled":            rng.random() < 0.30 if rng else False,
            "mascot_scene":              rng.randint(0, max(0, scene_count - 1)) if rng else 0,
            "mascot_start":              round(rng.uniform(0.5, 2.0), 2) if rng else 0.0,
            "mascot_duration":           round(rng.uniform(0.8, 2.5), 2) if rng else 0.0,
            "mascot_x":                  rng.choice([60, 960]) if rng else 0,
            "mascot_y":                  rng.randint(100, 300) if rng else 0,
            "mascot_opacity":            round(rng.uniform(0.40, 0.70), 2) if rng else 0.0,
            # Burn transition
            "burn_chance":               _v("burn_chance", 0.5, 0.3, 0.7),
        }

    def _generate_mascot(self) -> Image.Image:
        """
        Draws the "Audit Agent" — an 80×100px RGBA magnifying glass with eyes.
        Returns a pre-rendered PIL Image for compositing into video frames.
        """
        canvas = Image.new("RGBA", (80, 100), (0, 0, 0, 0))
        draw = ImageDraw.Draw(canvas)

        # Outer glow (slightly larger cyan circle, semi-transparent)
        draw.ellipse([2, 2, 66, 66], fill=(0, 242, 254, 40))

        # Lens outer ring (thick steel-cyan circle)
        draw.ellipse([6, 6, 62, 62], outline=(0, 200, 255, 200), width=3)

        # Lens inner glass (subtle dark blue tint fill)
        draw.ellipse([10, 10, 58, 58], fill=(0, 30, 60, 100))

        # Eyes (two white dots, slightly different sizes for character)
        draw.ellipse([24, 26, 30, 32], fill=(255, 255, 255, 230))
        draw.ellipse([38, 26, 44, 32], fill=(255, 255, 255, 230))

        # Tiny smile arc
        draw.arc([28, 34, 42, 46], start=0, end=180, fill=(0, 200, 255, 180), width=2)

        # Handle (rectangle extending downward from lens bottom-centre)
        hx = (80 - 6) // 2
        draw.rectangle([hx, 64, hx + 6, 64 + 26], fill=(40, 50, 70, 220))

        # Handle crossbar (small horizontal bar at bottom)
        bx = (80 - 20) // 2
        draw.rectangle([bx, 64 + 26 - 2, bx + 20, 64 + 26 + 2], fill=(40, 50, 70, 220))

        # Subtle Gaussian blur to soften edges
        canvas = canvas.filter(ImageFilter.GaussianBlur(radius=0.5))
        return canvas

    def _select_blueprint_video(self, search_text: str) -> Optional[str]:
        """
        Scans the assets/video_blueprints directory and selects a video matching the keyword.
        Falls back to 'Golden_dust_particles_in_light' or the first available video.
        """
        blueprint_dir = os.path.join(self.assets_dir, "video_blueprints")
        if not os.path.exists(blueprint_dir):
            return None
            
        files = os.listdir(blueprint_dir)
        mp4_files = [f for f in files if f.endswith(".mp4")]
        if not mp4_files:
            return None
            
        search_lower = search_text.lower() if search_text else ""
        
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
                if matched_pattern.lower() in f.lower():
                    return os.path.join(blueprint_dir, f)
                    
        # Fallback to Golden_dust_particles_in_light
        for f in mp4_files:
            if "particles_in_light" in f.lower():
                return os.path.join(blueprint_dir, f)
                
        # Absolute fallback
        return os.path.join(blueprint_dir, mp4_files[0])

    def _select_starting_blueprint(self, video_type: str) -> Optional[str]:
        """
        Selects a starting bumper blueprint from assets/video_blueprints/starting/.
        Filters by 'myth' or 'bizarre' keyword in filename; falls back to any MP4.
        Returns None if the directory is missing or empty.
        """
        start_dir = os.path.join(self.assets_dir, "video_blueprints", "starting")
        if not os.path.exists(start_dir):
            return None
        files = [f for f in os.listdir(start_dir) if f.endswith(".mp4")]
        if not files:
            return None
        # Match by video_type keyword
        keyword = "myth" if video_type == "myth" else "bizarre"
        matched = [f for f in files if keyword in f.lower()]
        if matched:
            return os.path.join(start_dir, random.choice(matched))
        return os.path.join(start_dir, random.choice(files))

    def _select_ending_blueprint(self) -> Optional[str]:
        """
        Selects an ending bumper blueprint from assets/video_blueprints/ending/.
        Prefers files with 'class' or 'dismissed' in the name.
        Returns None if the directory is missing or empty.
        """
        end_dir = os.path.join(self.assets_dir, "video_blueprints", "ending")
        if not os.path.exists(end_dir):
            return None
        files = [f for f in os.listdir(end_dir) if f.endswith(".mp4")]
        if not files:
            return None
        dismissed = [f for f in files if "class" in f.lower() or "dismissed" in f.lower()]
        if dismissed:
            return os.path.join(end_dir, random.choice(dismissed))
        return os.path.join(end_dir, random.choice(files))

    def _process_bg_frame(self, bg_arr: np.ndarray, target_w=1080, target_h=1920, blur_radius=6.0, darken_factor=0.45) -> np.ndarray:
        """
        Resizes, center-crops, blurs, and darkens a background video frame.
        """
        h, w, c = bg_arr.shape
        target_aspect = target_w / target_h
        current_aspect = w / h
        
        if current_aspect > target_aspect:
            # Too wide, crop sides
            new_w = int(h * target_aspect)
            left = (w - new_w) // 2
            bg_arr_cropped = bg_arr[:, left:left+new_w]
        else:
            # Too tall, crop top/bottom
            new_h = int(w / target_aspect)
            top = (h - new_h) // 2
            bg_arr_cropped = bg_arr[top:top+new_h, :]
            
        img_pil = Image.fromarray(bg_arr_cropped)
        if img_pil.size != (target_w, target_h):
            img_pil = img_pil.resize((target_w, target_h), Image.Resampling.BILINEAR)
            
        if blur_radius > 0.1:
            img_pil = img_pil.filter(ImageFilter.GaussianBlur(radius=blur_radius))
            
        if darken_factor > 0.0:
            dark_overlay = Image.new("RGB", (target_w, target_h), (10, 15, 30))
            img_pil = Image.blend(img_pil, dark_overlay, darken_factor)
            
        return np.array(img_pil)

    def _ensure_font_exists(self):
        """Downloads Montserrat Bold font programmatically from Google Fonts if not present locally."""
        if not os.path.exists(self.font_path):
            print(f"[VideoEngine] Subtitle font not found. Downloading Montserrat-Bold.ttf from Google Fonts...")
            try:
                url = "https://raw.githubusercontent.com/JulietaUla/Montserrat/master/fonts/ttf/Montserrat-Bold.ttf"
                urllib.request.urlretrieve(url, self.font_path)
                print(f"[VideoEngine] Font downloaded successfully to: {self.font_path}")
            except Exception as e:
                print(f"[VideoEngine] Failed to download font: {e}. Falling back to standard system font.")
                # Fallback to Arial or default system font path if download fails
                if sys.platform.startswith("win"):
                    self.font_path = "C:\\Windows\\Fonts\\arialbd.ttf"
                else:
                    self.font_path = "dejavu-sans-bold"

    def _ensure_sfx_exist(self):
        """Ensures that zap.mp3, pop.mp3, stamp.mp3, tick.mp3, impact.mp3, and riser.mp3 exist. Generates high-quality synthesized versions programmatically."""
        sfx_dir = os.path.join(self.assets_dir, "sfx")
        os.makedirs(sfx_dir, exist_ok=True)
        
        import subprocess
        try:
            import imageio_ffmpeg
            ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
        except ImportError:
            ffmpeg_exe = "ffmpeg"
            
        startupinfo = None
        if os.name == 'nt':
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            
        import wave
        import struct
        import random
        
        sample_rate = 44100
        
        def synthesize_and_save(filename_base, samples):
            wav_path = os.path.join(sfx_dir, f"{filename_base}.wav")
            mp3_path = os.path.join(sfx_dir, f"{filename_base}.mp3")
            
            # Skip if mp3 already exists
            if os.path.exists(mp3_path):
                return
                
            # Write WAV file
            with wave.open(wav_path, 'w') as f:
                f.setnchannels(1)
                f.setsampwidth(2)
                f.setframerate(sample_rate)
                for s in samples:
                    val = int(s * 32767)
                    val = max(-32768, min(32767, val))
                    f.writeframes(struct.pack('<h', val))
            
            # Convert WAV to MP3 using FFmpeg
            cmd = [ffmpeg_exe, "-y", "-i", wav_path, "-acodec", "libmp3lame", "-aq", "4", mp3_path]
            try:
                subprocess.run(cmd, startupinfo=startupinfo, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
                # Remove temporary WAV file if conversion succeeded
                if os.path.exists(wav_path):
                    os.remove(wav_path)
            except Exception as e:
                print(f"[VideoEngine] FFmpeg conversion failed for {filename_base}, using WAV data with .mp3 extension as failover: {e}")
                if os.path.exists(mp3_path):
                    os.remove(mp3_path)
                os.rename(wav_path, mp3_path)

        # 1. tick.mp3: Mechanical ticking clock sound
        tick_samples = []
        for i in range(int(0.08 * sample_rate)):
            t = i / sample_rate
            s = 0.8 * math.sin(2 * math.pi * 1000 * t) * math.exp(-150 * t) + \
                0.2 * math.sin(2 * math.pi * 500 * t) * math.exp(-100 * t)
            tick_samples.append(s)
        synthesize_and_save("tick", tick_samples)

        # 2. pop.mp3: Organic card reveal sound
        pop_samples = []
        for i in range(int(0.25 * sample_rate)):
            t = i / sample_rate
            freq = 300 + 400 * (t / 0.25)
            s = math.sin(2 * math.pi * freq * t) * math.exp(-20 * t)
            pop_samples.append(s)
        synthesize_and_save("pop", pop_samples)

        # Force regeneration of zap.mp3 if it contains the old sharp sound
        zap_mp3_path = os.path.join(sfx_dir, "zap.mp3")
        if os.path.exists(zap_mp3_path):
            try:
                os.remove(zap_mp3_path)
            except Exception:
                pass

        # 3. zap.mp3: CRT Analog glitch sound (filtered down & reduced volume)
        zap_samples = []
        for i in range(int(0.40 * sample_rate)):
            t = i / sample_rate
            # Start at a lower 450Hz (instead of 900Hz) and sweep down to 150Hz
            freq = 450 - 300 * (t / 0.40) + 50 * math.sin(2 * math.pi * 20 * t)
            noise = random.uniform(-1.0, 1.0)
            # Reduce primary gain by 57% (0.7 down to 0.3) and noise by 83% (0.3 down to 0.05)
            s = (0.3 * math.sin(2 * math.pi * freq * t) + 0.05 * noise) * math.exp(-10 * t)
            zap_samples.append(s)
        synthesize_and_save("zap", zap_samples)

        # 4. stamp.mp3: Forensic watermark stamp slam sound
        stamp_samples = []
        for i in range(int(0.50 * sample_rate)):
            t = i / sample_rate
            s = (0.6 * math.sin(2 * math.pi * 75 * t) * math.exp(-15 * t) + \
                 0.4 * math.sin(2 * math.pi * 1000 * t) * math.exp(-45 * t)) * math.exp(-6 * t)
            stamp_samples.append(s)
        synthesize_and_save("stamp", stamp_samples)

        # 5. impact.mp3: Deep cinematic impact boom
        impact_samples = []
        for i in range(int(2.0 * sample_rate)):
            t = i / sample_rate
            freq = 110 - 85 * (t / 2.0)
            noise = random.uniform(-1.0, 1.0)
            s = (math.sin(2 * math.pi * freq * t) + 0.15 * noise) * math.exp(-3.0 * t)
            impact_samples.append(s)
        synthesize_and_save("impact", impact_samples)

        # 6. riser.mp3: Low sub-bass riser sweep
        riser_samples = []
        for i in range(int(10.0 * sample_rate)):
            t = i / sample_rate
            freq = 50 + 200 * (t / 10.0)
            amp = 0.05 + 0.95 * (t / 10.0)
            s = amp * math.sin(2 * math.pi * freq * t)
            riser_samples.append(s)
        synthesize_and_save("riser", riser_samples)

    def _resolve_theme_music(self, category: str) -> Optional[str]:
        """Resolves background music file based on category, falling back to general background music."""
        music_dir = os.path.join(self.assets_dir, "background_music")
        for cat in ["physics", "biology", "history", "astronomy", "neuroscience",
                     "psychology", "economics", "geology", "chemistry", "technology",
                     "linguistics", "anthropology"]:
            os.makedirs(os.path.join(music_dir, cat), exist_ok=True)
            
        category_clean = category.strip().lower() if category else ""
        cat_music_dir = os.path.join(music_dir, category_clean)
        music_files = []
        if category_clean and os.path.exists(cat_music_dir):
            music_files = [os.path.join(cat_music_dir, f) for f in os.listdir(cat_music_dir) if f.endswith(".mp3")]
            
        if not music_files:
            if os.path.exists(music_dir):
                music_files = [os.path.join(music_dir, f) for f in os.listdir(music_dir) if f.endswith(".mp3") and os.path.isfile(os.path.join(music_dir, f))]
            
        if music_files:
            return random.choice(music_files)
        return None

    def compile_short(self, image_myth_path: str, image_truth_path: str, audio_path: Any, script_payload: Dict[str, Any], output_name: str, category: str = "history", style: str = "blueprint", video_type: str = "myth") -> str:
        """
        Compiles the assets into a finished 9:16 vertical MP4 video.
        Applies visual drift scanlines, organic grit, CRT glitch transitions, elastic card pop-ins,
        category-routed music, and dynamic audio ducking.
        audio_path is a 5-element list: [starting_tts, s1_tts, s2_tts, s3_tts, ending_tts]
        """
        rhythm = self._generate_video_rhythm(3, style)
        if isinstance(audio_path, list):
            hook = script_payload.get("hook", "").strip()
            context = script_payload.get("context", "").strip()
            fact = script_payload.get("fact", "").strip()
            
            scene_texts = [
                hook,
                context,
                fact
            ]
            scene_labels = [
                "[ DECLASSIFIED MYTH ]",
                "[ VERIFIED FACT ]",
                "[ FINAL LESSON ]"
            ]
            scene_titles = [
                "THE MYTH",
                "THE TRUTH",
                "THE VERDICT"
            ]
            image_paths = [
                image_myth_path,
                image_truth_path or image_myth_path,
                image_truth_path or image_myth_path
            ]
            return self._compile_scene_based_video(
                image_paths=image_paths,
                audio_paths=audio_path,
                scene_texts=scene_texts,
                scene_labels=scene_labels,
                scene_titles=scene_titles,
                output_name=output_name,
                category=category,
                style=style,
                is_bizarre=False,
                video_type=video_type,
                rhythm=rhythm
            )

        st = STYLE_PRESETS.get(style, STYLE_PRESETS["blueprint"])
        try:
            from moviepy.editor import ImageClip, AudioFileClip, VideoClip, CompositeAudioClip
        except ImportError:
            from moviepy import ImageClip, AudioFileClip, VideoClip, CompositeAudioClip
        
        import random
        
        output_video_path = os.path.join(self.assets_dir, f"{output_name}.mp4")
        print(f"[VideoEngine] Initializing video compilation for: {output_video_path}")
        
        # 0. Ensure sound effects exist
        self._ensure_sfx_exist()
        
        # 1. Load TTS Audio to determine total video duration
        audio_clip = AudioFileClip(audio_path)
        duration = audio_clip.duration
        print(f"[VideoEngine] Video Duration: {duration:.2f} seconds")

        # 2. Setup Word timing calculations
        words_timing = self._calculate_word_timings(script_payload, duration)

        # Find transition time of when the "Fact" begins (phrase_idx == 2 represents the fact)
        fact_start_time = 0.0
        for w in words_timing:
            if w["phrase_idx"] == 2:
                fact_start_time = w["start_time"]
                break
        print(f"[VideoEngine] Subtitles transition to FACT at: {fact_start_time:.2f}s")

        # Define speaking blocks from phrases for dynamic audio ducking
        speaking_blocks = []
        num_phrases = max((w.get("phrase_idx", 0) for w in words_timing), default=0) + 1
        phrases = [[] for _ in range(num_phrases)]
        for w in words_timing:
            p_idx = w.get("phrase_idx", 0)
            if 0 <= p_idx < num_phrases:
                phrases[p_idx].append(w)
                
        for p in phrases:
            if p:
                speaking_blocks.append((p[0]["start_time"], p[-1]["end_time"]))

        # 3. Create a Custom Video Clip via frame-by-frame transformation
        # 3. Create a Custom Video Clip via frame-by-frame transformation
        # Load blueprint base images for Myth
        base_img_myth = Image.open(image_myth_path).convert("RGB")
        if base_img_myth.size != (1080, 1920):
            base_img_myth = base_img_myth.resize((1080, 1920), Image.Resampling.LANCZOS)
        
        # Apply soft Gaussian blur (radius=3) once outside the loop to give an analog glow to blueprint lines
        glow_myth_base = base_img_myth.filter(ImageFilter.GaussianBlur(radius=3))
        
        # Darken the background by 45% (to make subtitles and foreground card stand out)
        dark_overlay = Image.new("RGB", (1080, 1920), (10, 15, 30))
        glow_myth_base = Image.blend(glow_myth_base, dark_overlay, 0.45)
        
        # Base Myth array for zoom operation inside make_frame(t)
        base_arr_myth = np.array(glow_myth_base)
        
        # Load and prepare Truth background image (blurred radius=15 for immersive photo depth)
        base_arr_truth = None
        if image_truth_path and os.path.exists(image_truth_path):
            try:
                base_img_truth = Image.open(image_truth_path).convert("RGB")
                if base_img_truth.size != (1080, 1920):
                    base_img_truth = base_img_truth.resize((1080, 1920), Image.Resampling.LANCZOS)
                glow_truth_base = base_img_truth.filter(ImageFilter.GaussianBlur(radius=15))
                glow_truth_base = Image.blend(glow_truth_base, dark_overlay, 0.45)
                base_arr_truth = np.array(glow_truth_base)
            except Exception as e:
                print(f"[VideoEngine] WARNING: Failed to prepare truth background ({e}). Using myth background throughout.")

        # Prepare the centered foreground myth card (Exhibit A)
        foreground_myth_card = None
        if image_myth_path and os.path.exists(image_myth_path):
            try:
                myth_img = Image.open(image_myth_path).convert("RGB")
                myth_w, myth_h = myth_img.size
                min_dim = min(myth_w, myth_h)
                crop_x = (myth_w - min_dim) // 2
                crop_y = (myth_h - min_dim) // 2
                myth_square = myth_img.crop((crop_x, crop_y, crop_x + min_dim, crop_y + min_dim))
                
                # Pre-render a styled declassified forensic tech card (canvas size: 840x890)
                canvas_w, canvas_h = 840, 890
                card_canvas = Image.new("RGBA", (canvas_w, canvas_h), (0, 0, 0, 0))
                draw_card = ImageDraw.Draw(card_canvas)
                
                # 1. Drop shadow
                draw_card.rectangle([20, 20, 820, 870], fill=(10, 15, 30, 180))
                
                # 2. Steel-blue card background and red outline warning border
                draw_card.rectangle([10, 10, 810, 860], fill=st["card_bg"] + (255,), outline=st["card_myth_outline"] + (255,), width=4)
                
                # 3. Red warning header band
                draw_card.rectangle([14, 14, 806, 90], fill=st["card_myth_header_bg"] + (255,))
                
                # 4. Header text
                try:
                    header_font = ImageFont.truetype(self.font_path, 34)
                except Exception:
                    header_font = ImageFont.load_default()
                
                is_anomaly = script_payload.get("is_anomaly", False)
                text_str = st["anomaly_label"] if is_anomaly else st["myth_label"]
                t_w = draw_card.textlength(text_str, font=header_font)
                tx = (820 - t_w) // 2
                ty = 32
                draw_card.text((tx, ty), text_str, fill=st["card_myth_header_text"] + (255,), font=header_font)
                
                # 5. Paste the myth image in the body with outline border
                myth_card_inner = myth_square.resize((778, 742), Image.Resampling.LANCZOS)
                card_canvas.paste(myth_card_inner, (21, 104))
                draw_card.rectangle([21, 104, 799, 846], outline=st["card_myth_outline"] + (255,), width=2)
                
                # 6. Tech tick lines and status labels
                draw_card.line([(25, 852), (100, 852)], fill=st["card_myth_outline"] + (255,), width=1)
                draw_card.line([(715, 852), (790, 852)], fill=st["card_myth_outline"] + (255,), width=1)
                try:
                    small_font = ImageFont.truetype(self.font_path, 18)
                    status_str = "STATUS: ANOMALOUS RECORD" if is_anomaly else "STATUS: DEBUNKED MYTH"
                    draw_card.text((115, 848), status_str, fill=st["card_myth_outline"] + (255,), font=small_font)
                    draw_card.text((550, 848), "DEPT OF AUDIT", fill=st["card_myth_header_text"] + (255,), font=small_font)
                except Exception:
                    pass
                
                foreground_myth_card = card_canvas
                print("[VideoEngine] Successfully prepared 'Exhibit A' myth card layout.")
            except Exception as e:
                print(f"[VideoEngine] WARNING: Failed to prepare foreground myth card ({e}).")

        # Prepare the centered foreground truth card (Exhibit B)
        foreground_truth_card = None
        if image_truth_path and os.path.exists(image_truth_path):
            try:
                fg_img = Image.open(image_truth_path).convert("RGB")
                # Scale fact down to an 800x800 square card
                fg_w, fg_h = fg_img.size
                min_dim = min(fg_w, fg_h)
                crop_x = (fg_w - min_dim) // 2
                crop_y = (fg_h - min_dim) // 2
                fg_square = fg_img.crop((crop_x, crop_y, crop_x + min_dim, crop_y + min_dim))
                
                # Pre-render a styled declassified forensic tech card (canvas size: 840x890)
                canvas_w, canvas_h = 840, 890
                card_canvas = Image.new("RGBA", (canvas_w, canvas_h), (0, 0, 0, 0))
                draw_card = ImageDraw.Draw(card_canvas)
                
                # 1. Drop shadow
                draw_card.rectangle([20, 20, 820, 870], fill=(10, 15, 30, 180))
                
                # 2. Steel-blue card background and outline border
                draw_card.rectangle([10, 10, 810, 860], fill=st["card_bg"] + (255,), outline=st["card_truth_outline"] + (255,), width=4)
                
                # 3. Header band
                draw_card.rectangle([14, 14, 806, 90], fill=st["card_truth_header_bg"] + (255,))
                
                # 4. Header text
                try:
                    header_font = ImageFont.truetype(self.font_path, 34)
                except Exception:
                    header_font = ImageFont.load_default()
                
                text_str = st["truth_label"]
                t_w = draw_card.textlength(text_str, font=header_font)
                tx = (820 - t_w) // 2
                ty = 32
                draw_card.text((tx, ty), text_str, fill=st["card_truth_header_text"] + (255,), font=header_font)
                
                # 5. Paste the fact image in the body with outline border
                fg_card_inner = fg_square.resize((778, 742), Image.Resampling.LANCZOS)
                card_canvas.paste(fg_card_inner, (21, 104))
                draw_card.rectangle([21, 104, 799, 846], outline=st["card_truth_outline"] + (255,), width=2)
                
                # 6. Tech tick lines and status labels
                draw_card.line([(25, 852), (100, 852)], fill=st["card_truth_outline"] + (255,), width=1)
                draw_card.line([(715, 852), (790, 852)], fill=st["card_truth_outline"] + (255,), width=1)
                try:
                    small_font = ImageFont.truetype(self.font_path, 18)
                    draw_card.text((115, 848), "STATUS: VERIFIED FACT", fill=st["card_truth_header_bg"] + (255,), font=small_font)
                    draw_card.text((550, 848), "DEPT OF AUDIT", fill=st["card_myth_header_text"] + (255,), font=small_font)
                except Exception:
                    pass
                
                foreground_truth_card = card_canvas
                print("[VideoEngine] Successfully prepared 'Exhibit B' forensic card layout.")
            except Exception as e:
                print(f"[VideoEngine] WARNING: Failed to prepare foreground fact card ({e}).")
        
        # Load TrueType font for subtitle rendering (Size: 52px for high legibility)
        font_size = 52
        try:
            sub_font = ImageFont.truetype(self.font_path, font_size)
        except Exception:
            sub_font = ImageFont.load_default()

        # Pre-render a semi-transparent horizontal CRT scanline overlay array
        scanline_overlay = self._create_scanline_overlay(1080, 1920, opacity=0.12)

        # Pre-generate 10 organic film grit/dust frames to keep CPU overhead low
        grit_frames = []
        for _ in range(10):
            grit_img = Image.new("RGB", (1080, 1920), (0, 0, 0))
            draw_grit = ImageDraw.Draw(grit_img)
            # Specks
            for _ in range(random.randint(6, 14)):
                rx = random.randint(0, 1079)
                ry = random.randint(0, 1919)
                r_size = random.randint(1, 3)
                draw_grit.ellipse([rx, ry, rx + r_size, ry + r_size], fill=(random.randint(90, 200),) * 3)
            # Hair/scratches
            for _ in range(random.randint(1, 3)):
                x1 = random.randint(0, 1079)
                y1 = random.randint(0, 1919)
                length = random.randint(10, 45)
                angle = random.uniform(0, 2 * math.pi)
                x2 = int(x1 + length * math.cos(angle))
                y2 = int(y1 + length * math.sin(angle))
                draw_grit.line([(x1, y1), (x2, y2)], fill=(random.randint(70, 150),) * 3, width=random.randint(1, 2))
            grit_img = grit_img.filter(ImageFilter.GaussianBlur(radius=0.5))
            grit_frames.append(np.array(grit_img))

        # Pre-render the CLASSIFIED watermark once to optimize performance
        watermark_img = Image.new("RGBA", (1080, 1920), (0, 0, 0, 0))
        draw_wm = ImageDraw.Draw(watermark_img)
        try:
            wm_font = ImageFont.truetype(self.font_path, 60)
        except Exception:
            wm_font = ImageFont.load_default()
        
        stamp_txt = "CLASSIFIED AUDIT FILE"
        sw = draw_wm.textlength(stamp_txt, font=wm_font)
        sh = 90
        
        stamp_canvas = Image.new("RGBA", (int(sw) + 40, sh), (0, 0, 0, 0))
        draw_stamp = ImageDraw.Draw(stamp_canvas)
        draw_stamp.rectangle([4, 4, sw + 36, sh - 4], outline=st["watermark_color"] + (140,), width=4)
        draw_stamp.text((20, 15), stamp_txt, fill=st["watermark_color"] + (140,), font=wm_font)
        
        rotated_stamp = stamp_canvas.rotate(25, expand=True, resample=Image.Resampling.BICUBIC)

        def make_frame(t):
            """
            Frame generator function applying slow zoom, scrolling CRT scanlines, organic grit,
            subtitles in the upper third, analog glitch transition, and elastic card zoom.
            """
            # 1. Slow Zoom calculation (100% to 112% over the total duration)
            zoom_factor = 1.0 + 0.12 * (t / duration)
            
            # Crop and scale base array for background zoom (using either myth or truth background)
            if t >= fact_start_time and base_arr_truth is not None:
                h, w, c = base_arr_truth.shape
                new_h, new_w = int(h / zoom_factor), int(w / zoom_factor)
                top = (h - new_h) // 2
                left = (w - new_w) // 2
                cropped_bg = base_arr_truth[top:top+new_h, left:left+new_w]
            else:
                h, w, c = base_arr_myth.shape
                new_h, new_w = int(h / zoom_factor), int(w / zoom_factor)
                top = (h - new_h) // 2
                left = (w - new_w) // 2
                cropped_bg = base_arr_myth[top:top+new_h, left:left+new_w]
                
            bg_frame_img = Image.fromarray(cropped_bg).resize((w, h), Image.Resampling.LANCZOS)
            
            # --- Dynamic Procedural Vector Animations on Background ---
            draw_bg = ImageDraw.Draw(bg_frame_img)
            
            # A. Oscilloscope Audio Waveform (fluctuating at the bottom, e.g., y=1580)
            wave_points = []
            for wx in range(60, 1020, 15):
                wy = 1580 + int(35 * math.sin(wx * 0.02 + t * 12) * math.cos(wx * 0.007 - t * 4))
                wave_points.append((wx, wy))
            draw_bg.line(wave_points, fill=(0, 242, 254, 180), width=3) # Cyan wave
            
            try:
                wave_font = ImageFont.truetype(self.font_path, 16)
                draw_bg.text((60, 1535), "AUDIO TELEMETRY / FREQUENCY RESPONSE", fill=(0, 242, 254, 120), font=wave_font)
            except:
                pass

            # B. Sweeping Radar Line inside Target Calibration Circle (center: 540, 960, radius: 240)
            center_x, center_y = 540, 960
            radar_radius = 240
            sweep_angle = t * 2.0
            for offset_idx, opacity_val in enumerate([255, 140, 70, 30]):
                angle_offset = sweep_angle - offset_idx * 0.08
                rx = center_x + int(radar_radius * math.cos(angle_offset))
                ry = center_y + int(radar_radius * math.sin(angle_offset))
                draw_bg.line([(center_x, center_y), (rx, ry)], fill=(0, 200 - offset_idx * 40, 220 - offset_idx * 40), width=2)

            # C. Scrolling Telemetry Text/Coordinates in upper margins
            try:
                tel_font = ImageFont.truetype(self.font_path, 18)
                draw_bg.text((60, 320), f"SYS_OK // ACT_FRQ: {142.8 + math.sin(t)*0.5:.2f} MHz", fill=(0, 242, 254, 120), font=tel_font)
                draw_bg.text((60, 350), f"SEC_REF: [AX-{int(t * 15) % 100:02d}]", fill=(0, 242, 254, 120), font=tel_font)
                draw_bg.text((820, 320), f"TIME_ELAPSED: {t:.3f}s", fill=(0, 242, 254, 120), font=tel_font)
                draw_bg.text((820, 350), "DEPT_AUDIT: LNK-OK", fill=(0, 242, 254, 120), font=tel_font)
            except:
                pass

            # 1.5 Draw CLASSIFIED watermark with "stamp-down slam" scaling animation starting at t=0.4s
            if 0.4 <= t <= 3.5:
                t_stamp = t - 0.4
                if t_stamp < 0.15:
                    scale = 3.0 - 2.0 * (t_stamp / 0.15)
                    opacity = int(255 * (t_stamp / 0.15))
                else:
                    scale = 1.0
                    opacity = 255
                    
                rw_s, rh_s = rotated_stamp.size
                new_w = int(rw_s * scale)
                new_h = int(rh_s * scale)
                if new_w > 10 and new_h > 10:
                    scaled_stamp = rotated_stamp.resize((new_w, new_h), Image.Resampling.LANCZOS)
                    wpx = (1080 - new_w) // 2
                    wpy = (1920 - new_h) // 2 - 250
                    
                    if opacity < 255:
                        r_arr = np.array(scaled_stamp)
                        r_arr[:, :, 3] = (r_arr[:, :, 3] * (opacity / 255.0)).astype(np.uint8)
                        scaled_stamp = Image.fromarray(r_arr)
                        
                    bg_frame_img.paste(scaled_stamp, (wpx, wpy), scaled_stamp)
            
            # Convert background image to NumPy array for manipulation
            fused_arr = np.array(bg_frame_img)
            
            # 2. Scrolling Scanline Drift: shift the scanlines overlay vertically based on time
            drift_offset = int(t * 120) % 4
            drift_scanlines = np.roll(scanline_overlay, drift_offset, axis=0)
            
            # Apply drifting scanlines
            fused_arr = (fused_arr * (1 - drift_scanlines) + (drift_scanlines * 0)).astype(np.uint8)
            
            # 3. Additive Organic Grit Overlay (running at 15 FPS loops)
            grit_idx = int(t * 15) % 10
            fused_arr = np.clip(fused_arr.astype(np.int16) + grit_frames[grit_idx].astype(np.int16), 0, 255).astype(np.uint8)
            
            # 4. Elastic Card Reveal (Myth Card vs Truth Card)
            active_card = None
            card_start = 0.0
            
            if t >= fact_start_time and foreground_truth_card is not None:
                active_card = foreground_truth_card
                card_start = fact_start_time
            elif t >= 0.2 and foreground_myth_card is not None:
                # Show myth card starting at t=0.2s
                active_card = foreground_myth_card
                card_start = 0.2
                
            if active_card is not None:
                t_elapsed = t - card_start
                if t_elapsed < 1.0:
                    s_factor = 1.0 - math.exp(-6 * t_elapsed) * math.cos(12 * t_elapsed)
                else:
                    s_factor = 1.0
                
                # Resize card based on elastic zoom factor
                new_w = int(840 * s_factor)
                new_h = int(890 * s_factor)
                if new_w > 10 and new_h > 10:
                    scaled_card = active_card.resize((new_w, new_h), Image.Resampling.LANCZOS)
                    # Centered on anchor point: cx=540, cy=1040 (matches 120, 620 offset of 840x840 card)
                    px = 540 - new_w // 2
                    py = 1040 - new_h // 2
                    
                    # Temporarily paste using PIL
                    fused_img = Image.fromarray(fused_arr)
                    fused_img.paste(scaled_card, (px, py), scaled_card)
                    fused_arr = np.array(fused_img)

            # 5. Analog Glitch Transition & Camera Shake (active in a 0.4s window around fact_start_time)
            if fact_start_time - 0.20 <= t <= fact_start_time + 0.20:
                # Horizontal row displacement
                num_strips = random.randint(4, 10)
                for _ in range(num_strips):
                    y_start = random.randint(0, 1919)
                    y_end = min(1920, y_start + random.randint(15, 90))
                    shift = random.randint(-50, 50)
                    fused_arr[y_start:y_end, :, :] = np.roll(fused_arr[y_start:y_end, :, :], shift, axis=1)
                
                # Chromatic Aberration
                shift_r = random.randint(-12, 12)
                shift_b = random.randint(-12, 12)
                if shift_r != 0:
                    fused_arr[:, :, 0] = np.roll(fused_arr[:, :, 0], shift_r, axis=1)
                if shift_b != 0:
                    fused_arr[:, :, 2] = np.roll(fused_arr[:, :, 2], shift_b, axis=1)
                
                # Brightness flicker
                flicker_factor = random.uniform(0.75, 1.25)
                fused_arr = np.clip(fused_arr.astype(np.float32) * flicker_factor, 0, 255).astype(np.uint8)
                
                # Camera shake offset
                dx = random.randint(-15, 15)
                dy = random.randint(-15, 15)
                fused_arr = np.roll(fused_arr, dx, axis=1)
                fused_arr = np.roll(fused_arr, dy, axis=0)

            # 6. Render Subtitles using PIL draw
            fused_img = Image.fromarray(fused_arr)
            draw_subs = ImageDraw.Draw(fused_img)
            self._render_highlighted_subtitles(draw_subs, sub_font, words_timing, t, st)
            
            return np.array(fused_img)

        # Create video clip from generator
        video_clip = VideoClip(make_frame, duration=duration)
        
        # 6. Set up Sound Effects & Ducked Background Music
        audio_clips_to_mix = [audio_clip]
        
        sfx_dir = os.path.join(self.assets_dir, "sfx")
        zap_path = os.path.join(sfx_dir, "zap.mp3")
        pop_path = os.path.join(sfx_dir, "pop.mp3")
        stamp_path = os.path.join(sfx_dir, "stamp.mp3")
        tick_path = os.path.join(sfx_dir, "tick.mp3")
        impact_path = os.path.join(sfx_dir, "impact.mp3")
        riser_path = os.path.join(sfx_dir, "riser.mp3")
        
        zap_clip = None
        pop_clip = None
        stamp_clip = None
        tick_clip = None
        impact_clip = None
        riser_clip = None
        
        # A. Watermark Stamp SFX at t=0.4s (to match slam animation)
        if os.path.exists(stamp_path):
            try:
                stamp_clip = AudioFileClip(stamp_path)
                stamp_clip = stamp_clip.set_start(0.4)
                stamp_clip = stamp_clip.multiply_volume(0.25) if hasattr(stamp_clip, "multiply_volume") else stamp_clip.volumex(0.25)
                audio_clips_to_mix.append(stamp_clip)
                print(f"[VideoEngine] Mixed stamp.mp3 slam SFX at 0.4s")
            except Exception as e:
                print(f"[VideoEngine] WARNING: Failed to mix stamp SFX: {e}")

        # B. Ticking Clock Loop during Hook/Context (every 0.6s until fact_start_time)
        if os.path.exists(tick_path):
            try:
                tick_clip = AudioFileClip(tick_path)
                tick_interval = 0.6
                t_tick = 0.0
                while t_tick < fact_start_time - 0.2:
                    tick_instance = tick_clip.set_start(t_tick)
                    tick_instance = tick_instance.multiply_volume(0.06) if hasattr(tick_instance, "multiply_volume") else tick_instance.volumex(0.06)
                    audio_clips_to_mix.append(tick_instance)
                    t_tick += tick_interval
                print(f"[VideoEngine] Mixed mechanical clock ticking SFX loop up to {fact_start_time:.2f}s")
            except Exception as e:
                print(f"[VideoEngine] WARNING: Failed to mix clock ticks: {e}")

        # C. Sub-bass Riser build-up during Hook/Context (rises to max pitch at fact_start_time)
        if os.path.exists(riser_path):
            try:
                riser_clip = AudioFileClip(riser_path)
                riser_dur = min(10.0, fact_start_time)
                riser_sub = riser_clip.subclip(10.0 - riser_dur, 10.0).set_start(max(0.0, fact_start_time - riser_dur))
                riser_sub = riser_sub.multiply_volume(0.15) if hasattr(riser_sub, "multiply_volume") else riser_sub.volumex(0.15)
                audio_clips_to_mix.append(riser_sub)
                print(f"[VideoEngine] Mixed sub-bass riser build-up SFX")
            except Exception as e:
                print(f"[VideoEngine] WARNING: Failed to mix riser SFX: {e}")

        # D. Glitch Zap SFX right before truth card reveal
        if os.path.exists(zap_path):
            try:
                zap_clip = AudioFileClip(zap_path)
                zap_start = max(0.0, fact_start_time - 0.15)
                zap_clip = zap_clip.set_start(zap_start)
                zap_clip = zap_clip.multiply_volume(0.08) if hasattr(zap_clip, "multiply_volume") else zap_clip.volumex(0.08)
                audio_clips_to_mix.append(zap_clip)
                print(f"[VideoEngine] Mixed zap.mp3 glitch SFX at {zap_start:.2f}s")
            except Exception as e:
                print(f"[VideoEngine] WARNING: Failed to mix zap SFX: {e}")
                
        # E. Card Reveal Pop SFX at fact_start_time
        if os.path.exists(pop_path):
            try:
                pop_clip = AudioFileClip(pop_path)
                pop_clip = pop_clip.set_start(fact_start_time)
                pop_clip = pop_clip.multiply_volume(0.15) if hasattr(pop_clip, "multiply_volume") else pop_clip.volumex(0.15)
                audio_clips_to_mix.append(pop_clip)
                print(f"[VideoEngine] Mixed pop.mp3 card reveal SFX at {fact_start_time:.2f}s")
            except Exception as e:
                print(f"[VideoEngine] WARNING: Failed to mix pop SFX: {e}")

        # F. Cinematic Impact Boom SFX at fact_start_time
        if os.path.exists(impact_path):
            try:
                impact_clip = AudioFileClip(impact_path)
                impact_clip = impact_clip.set_start(fact_start_time)
                impact_clip = impact_clip.multiply_volume(0.25) if hasattr(impact_clip, "multiply_volume") else impact_clip.volumex(0.25)
                audio_clips_to_mix.append(impact_clip)
                print(f"[VideoEngine] Mixed impact.mp3 sub-bass boom SFX at {fact_start_time:.2f}s")
            except Exception as e:
                print(f"[VideoEngine] WARNING: Failed to mix impact SFX: {e}")

        # Choose background music dynamically based on category
        bg_music_path = self._resolve_theme_music(category)
        bg_music_clip = None
        bg_music_sub = None
        mixed_audio = None
        
        if bg_music_path:
            print(f"[VideoEngine] Category '{category}' mapped to soundtrack: {bg_music_path}")
            try:
                bg_music_clip = AudioFileClip(bg_music_path)
                bg_duration = bg_music_clip.duration
                
                max_start = max(0.0, bg_duration - duration - 2.0)
                start_t = random.uniform(0.0, max_start)
                print(f"[VideoEngine] Randomizing BG music start at: {start_t:.2f}s (Total: {bg_duration:.2f}s)")
                
                if hasattr(bg_music_clip, "subclipped"):
                    bg_music_sub = bg_music_clip.subclipped(start_t, start_t + duration)
                else:
                    bg_music_sub = bg_music_clip.subclip(start_t, start_t + duration)
                
                def get_ducking_factor(t_val):
                    vol_min = 0.05
                    vol_max = 0.20
                    ramp_up = 0.2
                    ramp_down = 0.1
                    
                    if not speaking_blocks:
                        return vol_min
                    for start, end in speaking_blocks:
                        if start <= t_val <= end:
                            return vol_min
                            
                    for i in range(len(speaking_blocks) - 1):
                        end_i = speaking_blocks[i][1]
                        start_next = speaking_blocks[i+1][0]
                        if end_i < t_val < start_next:
                            pause_dur = start_next - end_i
                            if pause_dur <= (ramp_up + ramp_down):
                                return vol_min
                            if t_val < end_i + ramp_up:
                                return vol_min + (vol_max - vol_min) * ((t_val - end_i) / ramp_up)
                            elif t_val > start_next - ramp_down:
                                return vol_max - (vol_max - vol_min) * ((t_val - (start_next - ramp_down)) / ramp_down)
                            else:
                                return vol_max
                                
                    end_last = speaking_blocks[-1][1]
                    if t_val > end_last:
                        if t_val < end_last + ramp_up:
                            return vol_min + (vol_max - vol_min) * ((t_val - end_last) / ramp_up)
                        else:
                            return vol_max
                    return vol_min

                def duck_audio(gf, t):
                    factors = np.vectorize(get_ducking_factor)(t)
                    if len(factors.shape) > 0:
                        return gf(t) * factors[:, np.newaxis]
                    else:
                        return gf(t) * factors
                        
                bg_music_sub = bg_music_sub.fl(duck_audio)
                audio_clips_to_mix.append(bg_music_sub)
            except Exception as bg_err:
                print(f"[VideoEngine] WARNING: Failed to mix background music ({bg_err}). Proceeding with TTS audio only.")
        else:
            print("[VideoEngine] No background music files detected. Proceeding with TTS/SFX audio only.")

        mixed_audio = CompositeAudioClip(audio_clips_to_mix)
        video_clip = video_clip.with_audio(mixed_audio)

        codec = "h264_nvenc" if self.has_cuda else "libx264"
        threads = os.cpu_count() or 4
        print(f"[VideoEngine] Starting rendering process (codec={codec}, threads={threads})...")
        video_clip.write_videofile(
            output_video_path,
            fps=30,
            codec=codec,
            audio_codec="aac",
            threads=threads
        )
        
        video_clip.close()
        audio_clip.close()
        if bg_music_clip:
            bg_music_clip.close()
        if bg_music_sub:
            bg_music_sub.close()
        if zap_clip:
            zap_clip.close()
        if pop_clip:
            pop_clip.close()
        if stamp_clip:
            stamp_clip.close()
        if tick_clip:
            tick_clip.close()
        if impact_clip:
            impact_clip.close()
        if riser_clip:
            riser_clip.close()
        if mixed_audio:
            mixed_audio.close()
        gc.collect()
        print(f"[VideoEngine] Render complete: {output_video_path}")
        return output_video_path

    def compile_bizarre(self, image_paths: List[str], audio_path: Any, script_payload: Dict[str, Any], output_name: str, category: str = "history", style: str = "blueprint", video_type: str = "bizarre") -> str:
        """
        Compiles a Declassified Anomalies video with 3 immersive scenes:
        Scene 1: Hook/claim
        Scene 2: Why it's bizarre
        Scene 3: Closing statement
        audio_path is a 5-element list: [starting_tts, s1_tts, s2_tts, s3_tts, ending_tts]
        """
        rhythm = self._generate_video_rhythm(3, style)
        if isinstance(audio_path, list):
            hook = script_payload.get("hook", "").strip()
            why_bizarre = script_payload.get("why_bizarre", "").strip()
            closing = script_payload.get("closing_statement", "").strip()
            
            scene_texts = [
                hook,
                why_bizarre,
                closing
            ]
            scene_labels = [
                "[ THE STORY ]",
                "[ WHY IT IS BIZARRE ]",
                "[ FINAL VERDICT ]"
            ]
            scene_titles = [
                "THE STORY",
                "WHY IT'S BIZARRE",
                "THE VERDICT"
            ]
            
            # Pad images
            imgs = list(image_paths)
            while len(imgs) < 3:
                imgs.append(imgs[-1] if imgs else "")
            
            return self._compile_scene_based_video(
                image_paths=imgs,
                audio_paths=audio_path,
                scene_texts=scene_texts,
                scene_labels=scene_labels,
                scene_titles=scene_titles,
                output_name=output_name,
                category=category,
                style=style,
                is_bizarre=True,
                video_type=video_type,
                rhythm=rhythm
            )

        st = STYLE_PRESETS.get(style, STYLE_PRESETS["blueprint"])
        try:
            from moviepy.editor import ImageClip, AudioFileClip, VideoClip, CompositeAudioClip
        except ImportError:
            from moviepy import ImageClip, AudioFileClip, VideoClip, CompositeAudioClip

        output_video_path = os.path.join(self.assets_dir, f"{output_name}.mp4")
        print(f"[VideoEngine] Initializing immersive bizarre compilation for: {output_video_path}")

        self._ensure_sfx_exist()

        audio_clip = AudioFileClip(audio_path)
        duration = audio_clip.duration
        print(f"[VideoEngine] Bizarre video duration: {duration:.2f}s")

        # Load available background images (up to 3)
        bg_images = []
        for p in image_paths:
            if p and os.path.exists(p):
                try:
                    img = Image.open(p).convert("RGB").resize((1080, 1920), Image.Resampling.LANCZOS)
                    bg_images.append(np.array(img))
                except Exception:
                    pass
        if not bg_images:
            fallback = np.array(Image.new("RGB", (1080, 1920), (10, 8, 15)))
            bg_images = [fallback, fallback, fallback]
        # Pad to exactly 3 images (reuse last if needed)
        while len(bg_images) < 3:
            bg_images.append(bg_images[-1])

        # Script parts
        hook = script_payload.get("hook", "").strip()
        story_brief = script_payload.get("story_brief", "").strip()
        why_bizarre = script_payload.get("why_bizarre", "").strip()
        closing = script_payload.get("closing_statement", "").strip()
        cta = script_payload.get("cta", "").strip()
        sign_off = script_payload.get("sign_off", "Class dismissed.").strip()

        # Build 3 scenes: hook+story | why_bizarre | closing+cta+sign_off
        scenes_text = [
            f"{hook} {story_brief}" if hook and story_brief else (hook or story_brief),
            why_bizarre,
            f"{closing} {cta} {sign_off}" if closing and cta else f"{closing} {sign_off}".strip(),
        ]
        # remove empty scenes
        scenes_text = [s for s in scenes_text if s]
        if not scenes_text:
            scenes_text = ["Class dismissed."]

        scene_labels = [
            "[ THE STORY ]",
            "[ WHY IT IS BIZARRE ]",
            "[ FINAL VERDICT ]",
        ]
        # Pad labels
        while len(scene_labels) < len(scenes_text):
            scene_labels.append(f"[ SCENE {len(scene_labels)+1} ]")
        scene_labels = scene_labels[:len(scenes_text)]

        total_chars = sum(len(s) for s in scenes_text)
        # SSML breaks between scenes:
        is_new_style = "ssml_script" in script_payload or script_payload.get("is_new_prompt_style", False)
        if is_new_style:
            scene_breaks = [1.20, 0.70]
            internal_break = 0.70 if hook and story_brief else 0.0
        else:
            scene_breaks = [0.60, 0.70]
            internal_break = 0.0

        total_break_time = sum(scene_breaks[:len(scenes_text) - 1]) + internal_break
        spoken_duration = max(0.1, duration - total_break_time)
        sec_per_char = max(0.01, spoken_duration / total_chars) if total_chars > 0 else 0.1

        # Build precise word timing list across all scenes with breaks accounted for
        word_timings = []  # list of dicts: {word, start, end, scene_idx}
        current_time = 0.0
        for s_idx, s_text in enumerate(scenes_text):
            if s_idx == 0 and is_new_style and hook and story_brief:
                # Split hook and story_brief to insert internal break timing
                hook_words = hook.split()
                story_words = story_brief.split()
                
                for w in hook_words:
                    word_dur = len(w) * sec_per_char
                    word_timings.append({"word": w, "start": current_time, "end": current_time + word_dur, "scene": s_idx})
                    current_time += word_dur
                    
                current_time += 0.70  # Internal hook break
                
                for w in story_words:
                    word_dur = len(w) * sec_per_char
                    word_timings.append({"word": w, "start": current_time, "end": current_time + word_dur, "scene": s_idx})
                    current_time += word_dur
            else:
                for w in s_text.split():
                    word_dur = len(w) * sec_per_char
                    word_timings.append({"word": w, "start": current_time, "end": current_time + word_dur, "scene": s_idx})
                    current_time += word_dur
            # Insert SSML break after this scene (except after the last scene)
            if s_idx < len(scenes_text) - 1 and s_idx < len(scene_breaks):
                current_time += scene_breaks[s_idx]

        # Scene time boundaries (for background transitions)
        # Each scene's duration includes its following SSML break so boundaries are
        # continuous — no gaps. This prevents the frame generator from defaulting
        # to scene 0 during breaks and keeps scenes in sync with the narration.
        scene_boundaries = []
        cur = 0.0
        for s_idx, s_text in enumerate(scenes_text):
            scene_chars = len(s_text)
            seg_dur = scene_chars * sec_per_char
            if s_idx == 0 and is_new_style and hook and story_brief:
                seg_dur += 0.70  # Account for internal break
            # Include the following SSML break as part of this scene's visual duration
            if s_idx < len(scenes_text) - 1 and s_idx < len(scene_breaks):
                seg_dur += scene_breaks[s_idx]
            scene_boundaries.append((cur, cur + seg_dur))
            cur += seg_dur

        scanline_overlay = self._create_scanline_overlay(1080, 1920, opacity=0.10)

        try:
            sub_font = ImageFont.truetype(self.font_path, 44)
        except Exception:
            sub_font = ImageFont.load_default()
        try:
            label_font = ImageFont.truetype(self.font_path, 24)
        except Exception:
            label_font = ImageFont.load_default()
        try:
            scene_title_font = ImageFont.truetype(self.font_path, 52)
        except Exception:
            scene_title_font = ImageFont.load_default()

        def make_frame(t: float) -> np.ndarray:
            # Determine which scene we are in
            scene_idx = 0
            for idx, (s_start, s_end) in enumerate(scene_boundaries):
                if s_start <= t < s_end or (idx == len(scene_boundaries) - 1 and t >= s_end):
                    scene_idx = idx
                    break

            # Choose background image based on scene index (cycle through available images)
            img_idx = min(scene_idx, len(bg_images) - 1)
            base_arr = bg_images[img_idx].copy()

            # Apply blur + darken to the raw image
            frame_pil = Image.fromarray(base_arr).filter(ImageFilter.GaussianBlur(radius=6))
            dark_overlay = Image.new("RGB", (1080, 1920), (10, 8, 15))
            frame_pil = Image.blend(frame_pil, dark_overlay, 0.35)
            frame_arr = np.array(frame_pil)

            # Scanlines
            drift = int(t * 120) % 4
            scanlines = np.roll(scanline_overlay, drift, axis=0)
            frame_arr = (frame_arr * (1 - scanlines) + (scanlines * 0)).astype(np.uint8)
            frame_img = Image.fromarray(frame_arr)
            draw = ImageDraw.Draw(frame_img)

            # --- Scene Label Banner (top) ---
            label = scene_labels[scene_idx]
            lw = draw.textlength(label, font=label_font)
            draw.text((60, 60), label, fill=(180, 60, 60), font=label_font)
            # Underline
            draw.line([(60, 90), (60 + int(lw), 90)], fill=(180, 60, 60, 150), width=2)

            # --- Scene Title (top center, large) ---
            if scene_idx == 0:
                scene_title = "THE STORY"
            elif scene_idx == 1:
                scene_title = "WHY IT'S BIZARRE"
            else:
                scene_title = "THE VERDICT"
            stw = draw.textlength(scene_title, font=scene_title_font)
            draw.text(((1080 - stw) // 2, 120), scene_title, fill=(255, 255, 255, 200), font=scene_title_font)

            # --- Photo Credit / Context badge ---
            if img_idx < len(image_paths) and scene_idx < len(scene_labels):
                credit_text = f"SCENE {scene_idx + 1} PHOTO"
                cf = label_font
                cw = draw.textlength(credit_text, font=cf)
                draw.text((1080 - cw - 30, 60), credit_text, fill=(200, 200, 200, 120), font=cf)

            # --- Subtitle text (wrapped, bottom area) ---
            active_text = scenes_text[scene_idx]
            words = active_text.split()
            max_width = 920
            space_w = draw.textlength(" ", font=sub_font)

            # Find active word index from precise word timings (syncs with TTS narration)
            active_word_idx = -1
            for wi, wt in enumerate(word_timings):
                if wt["scene"] == scene_idx:
                    if wt["start"] <= t < wt["end"]:
                        active_word_idx = sum(1 for w2 in word_timings[:wi] if w2["scene"] == scene_idx)
                        break
            # If past the last word in this scene, stay on last word
            if active_word_idx == -1 and any(wt["scene"] == scene_idx for wt in word_timings):
                scene_wts = [wt for wt in word_timings if wt["scene"] == scene_idx]
                if t >= scene_wts[-1]["end"]:
                    active_word_idx = len(scene_wts) - 1
            # Fallback: linear within scene
            if active_word_idx == -1 and words:
                sc_start, sc_end = scene_boundaries[scene_idx]
                local_t = max(0, t - sc_start)
                active_word_idx = min(int(local_t / max(0.01, sc_end - sc_start) * len(words)), len(words) - 1)

            lines = []
            cur_l = []
            cur_w = 0.0
            for wi, w in enumerate(words):
                ww = draw.textlength(w, font=sub_font)
                if not cur_l:
                    cur_l.append(wi)
                    cur_w = ww
                elif cur_w + space_w + ww <= max_width:
                    cur_l.append(wi)
                    cur_w += space_w + ww
                else:
                    lines.append(cur_l)
                    cur_l = [wi]
                    cur_w = ww
            if cur_l:
                lines.append(cur_l)

            y_pos = 1400  # Bottom third of the screen for subtitles
            lh = 58
            for line in lines:
                l_str = " ".join(words[wi] for wi in line)
                l_w = draw.textlength(l_str, font=sub_font)
                start_x = (1080 - l_w) // 2
                x_cur = start_x
                for wi in line:
                    w = words[wi]
                    w_w = draw.textlength(w, font=sub_font)
                    is_active = (wi == active_word_idx)
                    if is_active:
                        pad = 8
                        draw.rounded_rectangle(
                            [x_cur - pad, y_pos - 5, x_cur + w_w + pad, y_pos + 42 + 5],
                            radius=8, fill=st["highlight_bg"] + (255,),
                        )
                        draw.text((x_cur, y_pos), w, fill=st["highlight_text"] + (255,), font=sub_font)
                    else:
                        draw.text((x_cur + 2, y_pos + 2), w, fill=(0, 0, 0), font=sub_font)
                        draw.text((x_cur, y_pos), w, fill=(255, 255, 255), font=sub_font)
                    x_cur += w_w + space_w
                y_pos += lh

            # --- Scene transition indicator (bottom dots) ---
            dot_y = 1780
            dot_r = 8
            total_dots = len(scenes_text)
            dot_gap = 30
            dots_total_w = total_dots * (2 * dot_r) + (total_dots - 1) * dot_gap
            dots_start_x = (1080 - dots_total_w) // 2
            for di in range(total_dots):
                dx = dots_start_x + di * (2 * dot_r + dot_gap)
                if di == scene_idx:
                    draw.ellipse([(dx, dot_y), (dx + 2 * dot_r, dot_y + 2 * dot_r)], fill=(255, 60, 60), outline=(255, 255, 255), width=1)
                else:
                    draw.ellipse([(dx, dot_y), (dx + 2 * dot_r, dot_y + 2 * dot_r)], fill=(60, 60, 60), outline=(150, 150, 150), width=1)

            # --- CLASSIFIED stamp (only in scene 0) ---
            if scene_idx == 0 and 0.5 <= t <= 3.0:
                try:
                    stamp_f = ImageFont.truetype(self.font_path, 36)
                except Exception:
                    stamp_f = ImageFont.load_default()
                stamp_t = "CLASSIFIED"
                sw = draw.textlength(stamp_t, font=stamp_f)
                stamp_canvas = Image.new("RGBA", (int(sw) + 24, 50), (0, 0, 0, 0))
                sd = ImageDraw.Draw(stamp_canvas)
                sd.rounded_rectangle([3, 3, int(sw) + 21, 47], outline=(180, 60, 60, 100), width=2)
                sd.text((12, 8), stamp_t, fill=(180, 60, 60, 100), font=stamp_f)
                rotated = stamp_canvas.rotate(20, expand=True, resample=Image.Resampling.BICUBIC)
                frame_img.paste(rotated, (80, 500), rotated)

            return np.array(frame_img)

        video_clip = VideoClip(make_frame, duration=duration)

        sfx_dir = os.path.join(self.assets_dir, "sfx")
        audio_clips = [audio_clip]
        stamp_path = os.path.join(sfx_dir, "stamp.mp3")
        if os.path.exists(stamp_path):
            try:
                sc = AudioFileClip(stamp_path).set_start(0.5)
                sc = sc.multiply_volume(0.25) if hasattr(sc, "multiply_volume") else sc.volumex(0.25)
                audio_clips.append(sc)
            except Exception:
                pass

        music_path = self._resolve_theme_music(category)
        if music_path and os.path.exists(music_path):
            try:
                bgm = AudioFileClip(music_path)
                bgm_dur = bgm.duration
                if bgm_dur >= duration:
                    bgm_sub = bgm.subclip(0, duration)
                    bgm_sub = bgm_sub.multiply_volume(0.08) if hasattr(bgm_sub, "multiply_volume") else bgm_sub.volumex(0.08)
                else:
                    clips = [bgm.set_start(i * bgm_dur) for i in range(int(math.ceil(duration / bgm_dur)))]
                    bgm_sub = CompositeAudioClip(clips).set_duration(duration)
                    bgm_sub = bgm_sub.multiply_volume(0.08) if hasattr(bgm_sub, "multiply_volume") else bgm_sub.volumex(0.08)
                audio_clips.append(bgm_sub)
            except Exception:
                pass

        mixed = CompositeAudioClip(audio_clips)
        video_clip = video_clip.with_audio(mixed)

        codec = "h264_nvenc" if self.has_cuda else "libx264"
        threads = os.cpu_count() or 4
        print(f"[VideoEngine] Rendering immersive bizarre anomaly video (codec={codec}, threads={threads})...")
        video_clip.write_videofile(output_video_path, fps=30, codec=codec, audio_codec="aac", threads=threads)

        video_clip.close()
        audio_clip.close()
        mixed.close()
        gc.collect()

        print(f"[VideoEngine] Bizarre compilation complete: {output_video_path}")
        return output_video_path

    def _calculate_word_timings(self, payload: Dict[str, Any], duration: float) -> List[Dict[str, Any]]:
        """
        Estimates character-level timing bounds for every word in the script,
        accounting for the structured SSML break intervals to ensure exact sync with TTS.
        """
        is_new_style = "ssml_script" in payload or payload.get("is_new_prompt_style", False)
        
        if is_new_style:
            # New prompt style splits the fact into truth_reveal and supporting_fact
            hook = payload.get("hook", "").strip()
            context = payload.get("context", "").strip()
            fact = payload.get("fact", "").strip()
            
            # Split fact into sentences to align with the SSML breaks
            import re
            fact_sentences = [s.strip() for s in re.split(r'(?<=[.!?])\s+', fact) if s.strip()]
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
                
            # Break durations:
            # - hook -> context: 0.70s
            # - context -> truth_reveal: 1.20s
            # - truth_reveal -> supporting_fact: 0.70s
            # - supporting_fact -> cta: 0.80s
            # - cta -> sign_off: 0.55s (if no cta: 1.00s before sign-off)
            break_durations = [0.70, 1.20]
            if supporting_fact:
                break_durations.append(0.70)
                
            cta_text = payload.get("cta", "").strip()
            if cta_text:
                phrases.append(cta_text)
                break_durations.append(0.80)
                break_durations.append(0.55)
            else:
                break_durations.append(1.00)
                
            phrases.append(payload.get("sign_off", "").strip())
        else:
            # Legacy formatting
            phrases = [
                payload.get("hook", "").strip(),
                payload.get("context", "").strip(),
                payload.get("fact", "").strip(),
            ]
            cta_text = payload.get("cta", "").strip()
            if cta_text:
                phrases.append(cta_text)
            phrases.append(payload.get("sign_off", "").strip())

            # Break durations corresponding to SSML break times (one per transition)
            break_durations = [0.55, 0.55, 0.80]
            if cta_text:
                break_durations.append(0.55)

        # Parse into a list of words, maintaining phrase structures
        words = []
        for p_idx, phrase in enumerate(phrases):
            phrase_words = phrase.split()
            for w in phrase_words:
                words.append({"word": w, "phrase_idx": p_idx, "length": len(w)})

        total_chars = sum(w["length"] for w in words)
        total_break_time = sum(break_durations)
        
        # Avoid division by zero or negative active duration
        active_duration = max(0.1, duration - total_break_time)
        sec_per_char = active_duration / total_chars if total_chars > 0 else 0.1
        
        current_time = 0.0
        last_phrase_idx = 0
        
        for w in words:
            p_idx = w["phrase_idx"]
            if p_idx > last_phrase_idx:
                # We transitioned to a new phrase, inject the corresponding break duration
                break_idx = last_phrase_idx
                if 0 <= break_idx < len(break_durations):
                    current_time += break_durations[break_idx]
                last_phrase_idx = p_idx
                
            word_dur = w["length"] * sec_per_char
            w["start_time"] = current_time
            w["end_time"] = current_time + word_dur
            current_time = w["end_time"]
            
        return words

    def _create_scanline_overlay(self, width: int, height: int, opacity: float) -> np.ndarray:
        """Generates a static horizontal CRT scanline mesh overlay matrix."""
        # 1-pixel dark line every 4 pixels
        overlay = np.zeros((height, width, 3), dtype=np.float32)
        for y in range(0, height, 4):
            overlay[y, :, :] = opacity
        return overlay

    def _render_highlighted_subtitles(self, draw: ImageDraw.Draw, font: ImageFont.FreeTypeFont, words: List[Dict[str, Any]], t: float, style: dict = None, y_pos: int = 330, font_px_height: int = 52):
        """
        Draws phrase lines with word-level highlights onto the PIL ImageDraw context.
        Subtitles are wrapped to stay within safe margins (width <= 900px) and centered.
        Placing starting y at ~330px to prevent overlap with Shorts UI elements.
        font_px_height adjusts the highlight box height and line spacing for larger fonts.
        """
        if style is None:
            style = STYLE_PRESETS["blueprint"]
        # Group words into logical segments (phrases)
        # Find which word is currently active. If t falls inside a pause, highlight the last word of the previous phrase.
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

        # Determine active phrase context
        active_word = words[active_word_idx]
        active_phrase_idx = active_word["phrase_idx"]
        
        # Filter all words belonging to this active phrase
        phrase_words = [w for w in words if w["phrase_idx"] == active_phrase_idx]
        
        # Space width
        space_width = draw.textlength(" ", font=font)
        
        # Build lines of words that fit within max width (900px)
        max_width = 900
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
            
        # Draw each line centered horizontally
        line_height = max(70, int(font_px_height * 1.35))  # Scale line spacing to font size
        
        for line in lines:
            # Measure line width
            line_width = 0.0
            for w in line:
                line_width += draw.textlength(w["word"], font=font)
            line_width += space_width * (len(line) - 1)
            
            # Start X for this line to be centered
            start_x = (1080 - line_width) // 2
            current_x = start_x
            
            for w in line:
                word_str = w["word"]
                word_width = draw.textlength(word_str, font=font)
                
                # Active word check: check if it matches the overall absolute active word index
                is_active = (words.index(w) == active_word_idx)
                
                # Draw highlighter box or text
                if is_active:
                    box_padding_x = 10
                    box_padding_y = int(font_px_height * 0.12)
                    draw.rounded_rectangle(
                        [current_x - box_padding_x, y_pos - box_padding_y, 
                         current_x + word_width + box_padding_x, y_pos + font_px_height + box_padding_y],
                        radius=10,
                        fill=style["highlight_bg"] + (255,)
                    )
                    draw.text((current_x, y_pos), word_str, fill=style["highlight_text"] + (255,), font=font)
                else:
                    shadow_color = (0, 0, 0)
                    shadow_offset = 3
                    draw.text((current_x + shadow_offset, y_pos + shadow_offset), word_str, fill=shadow_color, font=font)
                    
                    draw.text((current_x, y_pos), word_str, fill=style["subtitle_color"] + (255,), font=font)
                
                # Advance pointer
                current_x += word_width + space_width
                
            # Move to next line's y coordinate
            y_pos += line_height

    def generate_thumbnail(self, topic: str, hook: str, output_name: str, style: str = "blueprint", img_myth_path: str = None, img_truth_path: str = None, bizarre_mode: bool = False) -> str:
        """Generates a thumbnail using actual video images. Supports myth/truth diagonal, bizarre anomaly, and fallback blueprint."""
        from thumbnail_generator import ThumbnailDesigner
        title = hook if hook else topic

        if bizarre_mode:
            img_path = img_myth_path or img_truth_path
            hd = ThumbnailDesigner(width=1280, height=720)
            thumb = hd.generate_bizarre_thumbnail(bg_image_path=img_path, title_text=title, topic_label=topic)
            out_path = os.path.join(self.assets_dir, f"{output_name}_thumb.png")
            thumb.save(out_path, "PNG", optimize=True)
            print(f"[VideoEngine] Bizarre thumbnail (16:9) saved: {out_path}")
            short = ThumbnailDesigner(width=1080, height=1920)
            thumb_short = short.generate_bizarre_thumbnail(bg_image_path=img_path, title_text=title, topic_label=topic)
            short_out = os.path.join(self.assets_dir, f"{output_name}_thumb_shorts.png")
            thumb_short.save(short_out, "PNG", optimize=True)
            print(f"[VideoEngine] Bizarre thumbnail (9:16) saved: {short_out}")
            return out_path

        if img_myth_path and img_truth_path and os.path.exists(img_myth_path) and os.path.exists(img_truth_path):
            hd = ThumbnailDesigner(width=1280, height=720)
            thumb = hd.generate_from_images(img_myth_path, img_truth_path, title)
            out_path = os.path.join(self.assets_dir, f"{output_name}_thumb.png")
            thumb.save(out_path, "PNG", optimize=True)
            print(f"[VideoEngine] Diagonal myth/truth thumbnail (16:9) saved: {out_path}")
            short = ThumbnailDesigner(width=1080, height=1920)
            thumb_short = short.generate_from_images(img_myth_path, img_truth_path, title)
            short_out = os.path.join(self.assets_dir, f"{output_name}_thumb_shorts.png")
            thumb_short.save(short_out, "PNG", optimize=True)
            print(f"[VideoEngine] Diagonal myth/truth thumbnail (9:16) saved: {short_out}")
            return out_path

        st = STYLE_PRESETS.get(style, STYLE_PRESETS["blueprint"])
        thumb_w, thumb_h = 1280, 720
        img = Image.new("RGB", (thumb_w, thumb_h), (10, 15, 30))
        draw = ImageDraw.Draw(img)

        for x in range(0, thumb_w, 40):
            draw.line([(x, 0), (x, thumb_h)], fill=st["grid_color"], width=1)
        for y in range(0, thumb_h, 40):
            draw.line([(0, y), (thumb_w, y)], fill=st["grid_color"], width=1)

        draw.rectangle([30, 30, thumb_w - 30, thumb_h - 30], outline=st["card_myth_outline"] + (200,), width=4)

        try:
            font_large = ImageFont.truetype(self.font_path, 52)
            font_medium = ImageFont.truetype(self.font_path, 36)
            font_small = ImageFont.truetype(self.font_path, 22)
        except Exception:
            font_large = ImageFont.load_default()
            font_medium = ImageFont.load_default()
            font_small = ImageFont.load_default()

        label = "THE DAILY AUDIT"
        lw = draw.textlength(label, font=font_medium)
        draw.text(((thumb_w - lw) // 2, 60), label, fill=st["highlight_bg"] + (255,), font=font_medium)
        draw.line([(thumb_w // 4, 110), (3 * thumb_w // 4, 110)], fill=st["highlight_bg"] + (255,), width=2)

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

        badge_text = "CLASSIFIED TRUTH FILE"
        badge_w = draw.textlength(badge_text, font=font_small) + 30
        badge_x = (thumb_w - badge_w) // 2
        badge_y = thumb_h - 100
        draw.rounded_rectangle([badge_x, badge_y, badge_x + badge_w, badge_y + 40], radius=6, fill=st["card_myth_outline"] + (255,))
        draw.text((badge_x + 15, badge_y + 8), badge_text, fill=(255, 255, 255), font=font_small)

        out_path = os.path.join(self.assets_dir, f"{output_name}_thumb.png")
        img.save(out_path, "PNG")
        print(f"[VideoEngine] Thumbnail saved: {out_path}")
        return out_path

    # New scene-based and flashcard-oriented video compilers
    def _generate_card(self, image_path: str, label_text: str, status_text: str, is_truth: bool, style_dict: dict) -> Optional[Image.Image]:
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
            
            # Drop shadow
            draw_card.rectangle([20, 20, 820, 870], fill=(10, 15, 30, 180))
            
            # Card outline
            outline_color = style_dict["card_truth_outline"] if is_truth else style_dict["card_myth_outline"]
            draw_card.rectangle([10, 10, 810, 860], fill=style_dict["card_bg"] + (255,), outline=outline_color + (255,), width=4)
            
            # Header band
            header_bg = style_dict["card_truth_header_bg"] if is_truth else style_dict["card_myth_header_bg"]
            draw_card.rectangle([14, 14, 806, 90], fill=header_bg + (255,))
            
            # Header text
            try:
                header_font = ImageFont.truetype(self.font_path, 34)
            except Exception:
                header_font = ImageFont.load_default()
                
            t_w = draw_card.textlength(label_text, font=header_font)
            tx = (820 - t_w) // 2
            ty = 32
            header_text_color = style_dict["card_truth_header_text"] if is_truth else style_dict["card_myth_header_text"]
            draw_card.text((tx, ty), label_text, fill=header_text_color + (255,), font=header_font)
            
            # Paste body image
            inner_img = square_img.resize((778, 742), Image.Resampling.LANCZOS)
            card_canvas.paste(inner_img, (21, 104))
            draw_card.rectangle([21, 104, 799, 846], outline=outline_color + (255,), width=2)
            
            # Tech details
            draw_card.line([(25, 852), (100, 852)], fill=outline_color + (255,), width=1)
            draw_card.line([(715, 852), (790, 852)], fill=outline_color + (255,), width=1)
            try:
                small_font = ImageFont.truetype(self.font_path, 18)
                draw_card.text((115, 848), status_text, fill=outline_color + (255,), font=small_font)
                draw_card.text((550, 848), "DEPT OF AUDIT", fill=style_dict["card_myth_header_text"] + (255,), font=small_font)
            except Exception:
                pass
                
            return card_canvas
        except Exception as e:
            print(f"[VideoEngine] WARNING: Failed to generate forensic card for {image_path}: {e}")
            return None

    def _create_scene_clip(self, bg_source: Any, card_image: Optional[Image.Image], audio_duration: float, text: str, delay_offset: float, y_pos: int, scene_idx: int, scene_label: str, scene_title: str, style_dict: dict, rhythm: dict = None) -> 'VideoClip':
        try:
            from moviepy.editor import VideoClip, VideoFileClip
        except ImportError:
            from moviepy import VideoClip, VideoFileClip

        if rhythm is None:
            rhythm = self._generate_video_rhythm(3, "blueprint")

        total_duration = delay_offset + audio_duration
        
        bg_video = None
        base_arr = None
        raw_img_pil = None
        
        if isinstance(bg_source, str):
            if bg_source.lower().endswith(('.mp4', '.avi', '.mov', '.mkv')):
                bg_video = VideoFileClip(bg_source)
            else:
                raw_img_pil = Image.open(bg_source).convert("RGB").resize((1080, 1920), Image.Resampling.LANCZOS)
        elif hasattr(bg_source, "get_frame"):
            bg_video = bg_source
        else:
            base_arr = bg_source
        
        # Fonts
        sub_font_size = rhythm["subtitle_font_size"]
        try:
            sub_font = ImageFont.truetype(self.font_path, sub_font_size)
        except Exception:
            sub_font = ImageFont.load_default()
            
        try:
            label_font = ImageFont.truetype(self.font_path, 24)
        except Exception:
            label_font = ImageFont.load_default()
            
        try:
            scene_title_font = ImageFont.truetype(self.font_path, 48)
        except Exception:
            scene_title_font = ImageFont.load_default()

        # Pre-render rotated stamp for Scene 1
        rotated_stamp = None
        if scene_idx == 0:
            watermark_img = Image.new("RGBA", (1080, 1920), (0, 0, 0, 0))
            draw_wm = ImageDraw.Draw(watermark_img)
            try:
                wm_font = ImageFont.truetype(self.font_path, 60)
            except Exception:
                wm_font = ImageFont.load_default()
            stamp_txt = "CLASSIFIED AUDIT FILE"
            sw = draw_wm.textlength(stamp_txt, font=wm_font)
            sh = 90
            stamp_canvas = Image.new("RGBA", (int(sw) + 40, sh), (0, 0, 0, 0))
            draw_stamp = ImageDraw.Draw(stamp_canvas)
            draw_stamp.rectangle([4, 4, sw + 36, sh - 4], outline=style_dict["watermark_color"] + (140,), width=4)
            draw_stamp.text((20, 15), stamp_txt, fill=style_dict["watermark_color"] + (140,), font=wm_font)
            rotated_stamp = stamp_canvas.rotate(25, expand=True, resample=Image.Resampling.BICUBIC)

        scanline_overlay = self._create_scanline_overlay(1080, 1920, opacity=0.12)
        
        # Pre-generate grit frames
        import random
        grit_frames = []
        for _ in range(10):
            grit_img = Image.new("RGB", (1080, 1920), (0, 0, 0))
            draw_grit = ImageDraw.Draw(grit_img)
            for _ in range(random.randint(6, 14)):
                rx = random.randint(0, 1079)
                ry = random.randint(0, 1919)
                r_size = random.randint(1, 3)
                draw_grit.ellipse([rx, ry, rx + r_size, ry + r_size], fill=(random.randint(90, 200),) * 3)
            for _ in range(random.randint(1, 3)):
                x1 = random.randint(0, 1079)
                y1 = random.randint(0, 1919)
                length = random.randint(10, 45)
                angle = random.uniform(0, 2 * math.pi)
                x2 = int(x1 + length * math.cos(angle))
                y2 = int(y1 + length * math.sin(angle))
                draw_grit.line([(x1, y1), (x2, y2)], fill=(random.randint(70, 150),) * 3, width=random.randint(1, 2))
            grit_img = grit_img.filter(ImageFilter.GaussianBlur(radius=0.5))
            grit_frames.append(np.array(grit_img))

        # Local word timings calculation for this scene
        words = text.split()
        scene_word_timings = []
        if words and audio_duration > 0:
            total_chars = sum(len(w) for w in words)
            sec_per_char = audio_duration / total_chars
            current_time = delay_offset
            for w_idx, w in enumerate(words):
                w_dur = len(w) * sec_per_char
                scene_word_timings.append({
                    "word": w,
                    "start_time": current_time,
                    "end_time": current_time + w_dur,
                    "phrase_idx": 0
                })
                current_time += w_dur

        def make_frame(t):
            blur_base = rhythm["blur_radius"]
            if total_duration > 6.0 and t > 5.0:
                blur_r = max(0.0, blur_base - 6.0 * (t - 5.0))
            else:
                blur_r = blur_base

            if bg_video is not None:
                bg_dur = bg_video.duration
                raw_frame = bg_video.get_frame(t % bg_dur)
                processed_bg = self._process_bg_frame(raw_frame, blur_radius=blur_r, darken_factor=rhythm["darken_factor"])
            elif raw_img_pil is not None:
                img_to_process = np.array(raw_img_pil)
                processed_bg = self._process_bg_frame(img_to_process, blur_radius=blur_r, darken_factor=rhythm["darken_factor"])
            elif base_arr is not None:
                processed_bg = base_arr.copy()
            else:
                processed_bg = np.zeros((1920, 1080, 3), dtype=np.uint8)

            zoom_factor = 1.0 + rhythm["zoom_max"] * (t / total_duration)
            h, w, c = processed_bg.shape
            new_h, new_w = int(h / zoom_factor), int(w / zoom_factor)
            top = (h - new_h) // 2
            left = (w - new_w) // 2
            cropped_bg = processed_bg[top:top+new_h, left:left+new_w]
            bg_frame_img = Image.fromarray(cropped_bg).resize((w, h), Image.Resampling.BILINEAR)
            
            draw_bg = ImageDraw.Draw(bg_frame_img)
            
            # Oscilloscope
            wave_points = []
            for wx in range(60, 1020, 15):
                wy = 1580 + int(35 * math.sin(wx * 0.02 + t * 12) * math.cos(wx * 0.007 - t * 4))
                wave_points.append((wx, wy))
            draw_bg.line(wave_points, fill=(0, 242, 254, 180), width=3)
            
            try:
                wave_font = ImageFont.truetype(self.font_path, 16)
                draw_bg.text((60, 1535), "AUDIO TELEMETRY / FREQUENCY RESPONSE", fill=(0, 242, 254, 120), font=wave_font)
            except:
                pass
                
            # Sweeping Radar
            center_x, center_y = 540, 960
            radar_radius = 240
            sweep_angle = t * rhythm["radar_speed"]
            for offset_idx, opacity_val in enumerate([255, 140, 70, 30]):
                angle_offset = sweep_angle - offset_idx * 0.08
                rx = center_x + int(radar_radius * math.cos(angle_offset))
                ry = center_y + int(radar_radius * math.sin(angle_offset))
                draw_bg.line([(center_x, center_y), (rx, ry)], fill=(0, 200 - offset_idx * 40, 220 - offset_idx * 40), width=2)

            # Telemetry text
            try:
                tel_font = ImageFont.truetype(self.font_path, 18)
                draw_bg.text((60, 320), f"SYS_OK // ACT_FRQ: {142.8 + math.sin(t)*0.5:.2f} MHz", fill=(0, 242, 254, 120), font=tel_font)
                draw_bg.text((60, 350), f"SEC_REF: [AX-{int(t * 15) % 100:02d}]", fill=(0, 242, 254, 120), font=tel_font)
                draw_bg.text((820, 320), f"TIME_ELAPSED: {t:.3f}s", fill=(0, 242, 254, 120), font=tel_font)
                draw_bg.text((820, 350), "DEPT_AUDIT: LNK-OK", fill=(0, 242, 254, 120), font=tel_font)
            except:
                pass

            # Watermark slam for Scene 1
            if scene_idx == 0 and rotated_stamp is not None and rhythm["stamp_start"] <= t <= rhythm["stamp_end"]:
                t_stamp = t - rhythm["stamp_start"]
                if t_stamp < rhythm["stamp_slam_dur"]:
                    scale = rhythm["stamp_initial_scale"] - (rhythm["stamp_initial_scale"] - 1.0) * (t_stamp / rhythm["stamp_slam_dur"])
                    opacity = int(255 * (t_stamp / rhythm["stamp_slam_dur"]))
                else:
                    scale = 1.0
                    opacity = 255
                rw_s, rh_s = rotated_stamp.size
                new_w = int(rw_s * scale)
                new_h = int(rh_s * scale)
                if new_w > 10 and new_h > 10:
                    scaled_stamp = rotated_stamp.resize((new_w, new_h), Image.Resampling.BILINEAR)
                    wpx = (1080 - new_w) // 2
                    wpy = (1920 - new_h) // 2 - 250
                    if opacity < 255:
                        r_arr = np.array(scaled_stamp)
                        r_arr[:, :, 3] = (r_arr[:, :, 3] * (opacity / 255.0)).astype(np.uint8)
                        scaled_stamp = Image.fromarray(r_arr)
                    bg_frame_img.paste(scaled_stamp, (wpx, wpy), scaled_stamp)

            # Scene labels at the top
            if scene_label:
                lw = draw_bg.textlength(scene_label, font=label_font)
                draw_bg.text((60, 60), scene_label, fill=(180, 60, 60), font=label_font)
                draw_bg.line([(60, 90), (60 + int(lw), 90)], fill=(180, 60, 60, 150), width=2)
            if scene_title:
                stw = draw_bg.textlength(scene_title, font=scene_title_font)
                draw_bg.text(((1080 - stw) // 2, 120), scene_title, fill=(255, 255, 255, 200), font=scene_title_font)

            fused_arr = np.array(bg_frame_img)
            
            # Scanlines
            drift_offset = int(t * rhythm["scanline_speed"]) % 4
            drift_scanlines = np.roll(scanline_overlay, drift_offset, axis=0)
            fused_arr = (fused_arr * (1 - drift_scanlines) + (drift_scanlines * 0)).astype(np.uint8)
            
            # Grit
            grit_idx = int(t * rhythm["grit_fps"]) % 10
            fused_arr = np.clip(fused_arr.astype(np.int16) + grit_frames[grit_idx].astype(np.int16), 0, 255).astype(np.uint8)

            # Mascot compositing (subtle easter egg — behind card, scanlines, and grit)
            if rhythm["mascot_enabled"] and scene_idx == rhythm["mascot_scene"]:
                if rhythm["mascot_start"] <= t <= rhythm["mascot_start"] + rhythm["mascot_duration"]:
                    local_t = t - rhythm["mascot_start"]
                    bounce_y = int(2 * math.sin(local_t * 3.0))
                    mx = rhythm["mascot_x"]
                    my = rhythm["mascot_y"] + bounce_y
                    fused_img = Image.fromarray(fused_arr)
                    mascot_paste = self.mascot_img.copy()
                    if rhythm["mascot_opacity"] < 1.0:
                        m_arr = np.array(mascot_paste)
                        m_arr[:, :, 3] = (m_arr[:, :, 3] * rhythm["mascot_opacity"]).astype(np.uint8)
                        mascot_paste = Image.fromarray(m_arr)
                    fused_img.paste(mascot_paste, (mx, my), mascot_paste)
                    fused_arr = np.array(fused_img)
            
            # Elastic Card
            if card_image is not None and t >= rhythm["card_pop_time"]:
                t_elapsed = t - rhythm["card_pop_time"]
                if t_elapsed < 1.0:
                    s_factor = 1.0 - math.exp(-rhythm["elastic_k"] * t_elapsed) * math.cos(rhythm["elastic_freq"] * t_elapsed)
                else:
                    s_factor = 1.0
                new_w = int(840 * s_factor)
                new_h = int(890 * s_factor)
                if new_w > 10 and new_h > 10:
                    scaled_card = card_image.resize((new_w, new_h), Image.Resampling.BILINEAR)
                    px = 540 - new_w // 2
                    py = 1040 - new_h // 2
                    fused_img = Image.fromarray(fused_arr)
                    fused_img.paste(scaled_card, (px, py), scaled_card)
                    fused_arr = np.array(fused_img)

            # Pre-transition cue visual glitch: cued at last pre_transition_glitch_dur of the scene
            if scene_idx < 2 and total_duration - rhythm["pre_transition_glitch_dur"] <= t <= total_duration:
                y_start = random.randint(0, 1919)
                y_end = min(1920, y_start + random.randint(15, 60))
                shift = random.randint(-15, 15)
                fused_arr[y_start:y_end, :, :] = np.roll(fused_arr[y_start:y_end, :, :], shift, axis=1)
                
                shift_r = random.randint(-3, 3)
                if shift_r != 0:
                    fused_arr[:, :, 0] = np.roll(fused_arr[:, :, 0], shift_r, axis=1)

            # Render Subtitles (on top of everything including mascot)
            if t >= delay_offset and scene_word_timings:
                fused_img = Image.fromarray(fused_arr)
                draw_subs = ImageDraw.Draw(fused_img)
                self._render_highlighted_subtitles(draw_subs, sub_font, scene_word_timings, t, style_dict, y_pos)
                fused_arr = np.array(fused_img)
                
            return fused_arr
            
        clip = VideoClip(make_frame, duration=total_duration)
        if isinstance(bg_source, str) and bg_source.lower().endswith(('.mp4', '.avi', '.mov', '.mkv')) and bg_video is not None:
            original_close = clip.close
            def custom_close():
                original_close()
                try:
                    bg_video.close()
                except:
                    pass
            clip.close = custom_close
            
        return clip

    def _create_transition_clip(self, bg_source: Any, duration: float = 0.5) -> 'VideoClip':
        try:
            from moviepy.editor import VideoClip, VideoFileClip
        except ImportError:
            from moviepy import VideoClip, VideoFileClip
            
        bg_video = None
        raw_img_pil = None
        base_arr = None
        
        if isinstance(bg_source, str):
            if bg_source.lower().endswith(('.mp4', '.avi', '.mov', '.mkv')):
                bg_video = VideoFileClip(bg_source)
            else:
                raw_img_pil = Image.open(bg_source).convert("RGB").resize((1080, 1920), Image.Resampling.LANCZOS)
        elif hasattr(bg_source, "get_frame"):
            bg_video = bg_source
        else:
            base_arr = bg_source
            
        scanline_overlay = self._create_scanline_overlay(1080, 1920, opacity=0.15)
        
        import random
        def make_frame(t):
            if bg_video is not None:
                bg_dur = bg_video.duration
                raw_frame = bg_video.get_frame(t % bg_dur)
                base_frame_arr = self._process_bg_frame(raw_frame, blur_radius=15.0, darken_factor=0.45)
            elif raw_img_pil is not None:
                glow_base = raw_img_pil.filter(ImageFilter.GaussianBlur(radius=15))
                dark_overlay = Image.new("RGB", (1080, 1920), (10, 15, 30))
                glow_base = Image.blend(glow_base, dark_overlay, 0.45)
                base_frame_arr = np.array(glow_base)
            else:
                base_frame_arr = base_arr.copy()
                
            fused_arr = base_frame_arr.copy()
            num_strips = random.randint(6, 12)
            for _ in range(num_strips):
                y_start = random.randint(0, 1919)
                y_end = min(1920, y_start + random.randint(20, 120))
                shift = random.randint(-80, 80)
                fused_arr[y_start:y_end, :, :] = np.roll(fused_arr[y_start:y_end, :, :], shift, axis=1)
            
            shift_r = random.randint(-20, 20)
            shift_b = random.randint(-20, 20)
            if shift_r != 0:
                fused_arr[:, :, 0] = np.roll(fused_arr[:, :, 0], shift_r, axis=1)
            if shift_b != 0:
                fused_arr[:, :, 2] = np.roll(fused_arr[:, :, 2], shift_b, axis=1)
                
            flicker_factor = random.uniform(0.6, 1.4)
            fused_arr = np.clip(fused_arr.astype(np.float32) * flicker_factor, 0, 255).astype(np.uint8)
            
            dx = random.randint(-25, 25)
            dy = random.randint(-25, 25)
            fused_arr = np.roll(fused_arr, dx, axis=1)
            fused_arr = np.roll(fused_arr, dy, axis=0)
            
            drift = int(t * 240) % 4
            scanlines = np.roll(scanline_overlay, drift, axis=0)
            fused_arr = (fused_arr * (1 - scanlines)).astype(np.uint8)
            
            return fused_arr
            
        clip = VideoClip(make_frame, duration=duration)
        if isinstance(bg_source, str) and bg_source.lower().endswith(('.mp4', '.avi', '.mov', '.mkv')) and bg_video is not None:
            original_close = clip.close
            def custom_close():
                original_close()
                try:
                    bg_video.close()
                except:
                    pass
            clip.close = custom_close
            
        return clip

    def _create_starting_bumper(self, audio_duration: float, video_type: str, style_dict: dict = None, rhythm: dict = None) -> 'VideoClip':
        """
        Creates the starting bumper video clip.
        Uses a blueprint video from assets/video_blueprints/starting/ (or static fallback),
        renders large bold text with word-level highlighted subtitles synced to the narrator.
        """
        if style_dict is None:
            style_dict = STYLE_PRESETS["blueprint"]
        if rhythm is None:
            rhythm = self._generate_video_rhythm(1, "blueprint")
        try:
            from moviepy.editor import VideoClip, VideoFileClip
        except ImportError:
            from moviepy import VideoClip, VideoFileClip

        # Determine text based on video_type
        if video_type == "myth":
            text = "Now, bringing you the strangest MYTH that will shock you."
        else:
            text = "Now, bringing you the most BIZARRE TRUTH that will shock you."

        total_duration = audio_duration

        bg_video = None
        base_arr = None
        bg_path = self._select_starting_blueprint(video_type)
        if bg_path and os.path.exists(bg_path):
            try:
                bg_video = VideoFileClip(bg_path)
                print(f"[VideoEngine] Starting bumper using blueprint: {bg_path}")
            except Exception as e:
                print(f"[VideoEngine] Failed to load starting blueprint ({e}), using static background.")
                bg_video = None

        if bg_video is None:
            # Static dark fallback
            base_arr = np.array(Image.new("RGB", (1080, 1920), (10, 15, 30)))

        try:
            bumper_font = ImageFont.truetype(self.font_path, rhythm["bumper_font_size"])
        except Exception:
            bumper_font = ImageFont.load_default()

        scanline_overlay = self._create_scanline_overlay(1080, 1920, opacity=0.10)

        # Word timings
        words = text.split()
        word_timings = []
        if words and audio_duration > 0:
            total_chars = sum(len(w) for w in words)
            sec_per_char = audio_duration / total_chars if total_chars > 0 else 0.1
            current_time = 0.0
            for w in words:
                w_dur = len(w) * sec_per_char
                word_timings.append({"word": w, "start_time": current_time, "end_time": current_time + w_dur, "phrase_idx": 0})
                current_time += w_dur

        def make_frame(t):
            # Get background frame
            if bg_video is not None:
                bg_dur = bg_video.duration
                raw_frame = bg_video.get_frame(t % bg_dur)
                bg_arr = self._process_bg_frame(raw_frame, blur_radius=rhythm["blur_radius"], darken_factor=rhythm["darken_factor"])
            else:
                bg_arr = base_arr.copy()

            # Slow zoom
            zoom_factor = 1.0 + rhythm["bumper_zoom"] * (t / max(total_duration, 0.1))
            h, w, c = bg_arr.shape
            new_h, new_w = int(h / zoom_factor), int(w / zoom_factor)
            top = (h - new_h) // 2
            left = (w - new_w) // 2
            cropped = bg_arr[top:top+new_h, left:left+new_w]
            frame = Image.fromarray(cropped).resize((w, h), Image.Resampling.BILINEAR)

            # Grit
            import random
            grit = Image.new("RGB", (1080, 1920), (0, 0, 0))
            dg = ImageDraw.Draw(grit)
            for _ in range(random.randint(3, 8)):
                rx = random.randint(0, 1079)
                ry = random.randint(0, 1919)
                dg.ellipse([rx, ry, rx + random.randint(1, 2), ry + random.randint(1, 2)], fill=(random.randint(80, 180),) * 3)
            grit = grit.filter(ImageFilter.GaussianBlur(radius=0.5))
            grit_arr = np.array(grit)

            fused_arr = np.array(frame)
            # Scanlines
            drift = int(t * rhythm["scanline_speed"]) % 4
            scanlines = np.roll(scanline_overlay, drift, axis=0)
            fused_arr = (fused_arr * (1 - scanlines)).astype(np.uint8)
            # Grit
            fused_arr = np.clip(fused_arr.astype(np.int16) + grit_arr.astype(np.int16), 0, 255).astype(np.uint8)

            # Render highlighted subtitles centered
            if word_timings:
                fused_img = Image.fromarray(fused_arr)
                draw = ImageDraw.Draw(fused_img)
                self._render_highlighted_subtitles(draw, bumper_font, word_timings, t, style_dict, y_pos=rhythm["bumper_y_pos"], font_px_height=rhythm["bumper_font_size"])
                fused_arr = np.array(fused_img)

            return fused_arr

        clip = VideoClip(make_frame, duration=total_duration)
        if bg_video is not None:
            original_close = clip.close
            def custom_close():
                original_close()
                try:
                    bg_video.close()
                except:
                    pass
            clip.close = custom_close
        return clip

    def _create_ending_scene(self, audio_duration: float, style_dict: dict = None, rhythm: dict = None) -> 'VideoClip':
        """
        Creates the ending bumper (Class Dismissed) video clip.
        Uses a blueprint video from assets/video_blueprints/ending/ (or static fallback),
        renders large bold text: "Like, Share, Subscribe\nif you seriously want to know more about myths and bizarre truths. CLASS DISMISSED."
        with word-level highlighted subtitles.
        """
        if style_dict is None:
            style_dict = STYLE_PRESETS["blueprint"]
        if rhythm is None:
            rhythm = self._generate_video_rhythm(1, "blueprint")
        try:
            from moviepy.editor import VideoClip, VideoFileClip
        except ImportError:
            from moviepy import VideoClip, VideoFileClip

        text = "Like, share, subscribe, if you seriously want to know more about myths and bizarre truths. CLASS DISMISSED."
        total_duration = audio_duration

        bg_video = None
        base_arr = None
        bg_path = self._select_ending_blueprint()
        if bg_path and os.path.exists(bg_path):
            try:
                bg_video = VideoFileClip(bg_path)
                print(f"[VideoEngine] Ending bumper using blueprint: {bg_path}")
            except Exception as e:
                print(f"[VideoEngine] Failed to load ending blueprint ({e}), using static background.")
                bg_video = None

        if bg_video is None:
            # Static dark fallback with red-ish tint
            base_arr = np.array(Image.new("RGB", (1080, 1920), (30, 10, 15)))

        try:
            bumper_font = ImageFont.truetype(self.font_path, rhythm["bumper_font_size"])
        except Exception:
            bumper_font = ImageFont.load_default()

        scanline_overlay = self._create_scanline_overlay(1080, 1920, opacity=0.10)

        # Word timings
        words = text.split()
        word_timings = []
        if words and audio_duration > 0:
            total_chars = sum(len(w) for w in words)
            sec_per_char = audio_duration / total_chars if total_chars > 0 else 0.1
            current_time = 0.0
            for w in words:
                w_dur = len(w) * sec_per_char
                word_timings.append({"word": w, "start_time": current_time, "end_time": current_time + w_dur, "phrase_idx": 0})
                current_time += w_dur

        def make_frame(t):
            if bg_video is not None:
                bg_dur = bg_video.duration
                raw_frame = bg_video.get_frame(t % bg_dur)
                bg_arr = self._process_bg_frame(raw_frame, blur_radius=rhythm["blur_radius"], darken_factor=rhythm["darken_factor"])
            else:
                bg_arr = base_arr.copy()

            zoom_factor = 1.0 + rhythm["bumper_zoom"] * (t / max(total_duration, 0.1))
            h, w, c = bg_arr.shape
            new_h, new_w = int(h / zoom_factor), int(w / zoom_factor)
            top = (h - new_h) // 2
            left = (w - new_w) // 2
            cropped = bg_arr[top:top+new_h, left:left+new_w]
            frame = Image.fromarray(cropped).resize((w, h), Image.Resampling.BILINEAR)

            fused_arr = np.array(frame)
            drift = int(t * rhythm["scanline_speed"]) % 4
            scanlines = np.roll(scanline_overlay, drift, axis=0)
            fused_arr = (fused_arr * (1 - scanlines)).astype(np.uint8)

            # Render highlighted subtitles centered
            if word_timings:
                fused_img = Image.fromarray(fused_arr)
                draw = ImageDraw.Draw(fused_img)
                self._render_highlighted_subtitles(draw, bumper_font, word_timings, t, style_dict, y_pos=rhythm["bumper_y_pos"], font_px_height=rhythm["bumper_font_size"])
                fused_arr = np.array(fused_img)

            return fused_arr

        clip = VideoClip(make_frame, duration=total_duration)
        if bg_video is not None:
            original_close = clip.close
            def custom_close():
                original_close()
                try:
                    bg_video.close()
                except:
                    pass
            clip.close = custom_close
        return clip

    def _generate_dynamic_cards(self, image_paths: list[str], scene_count: int, style_dict: dict) -> list:
        """Generates N forensic cards with sequential exhibit labels (EXHIBIT A, EXHIBIT B, ...)."""
        cards = []
        for i in range(scene_count):
            label = f"EXHIBIT {chr(65 + i)}"
            img_path = image_paths[i] if i < len(image_paths) else (image_paths[-1] if image_paths else "")
            card = self._generate_card(
                image_path=img_path,
                label_text=label,
                status_text=f"STATUS: SCENE {i+1} EVIDENCE",
                is_truth=True,
                style_dict=style_dict
            )
            cards.append(card)
        return cards

    def compile_dynamic_video(
        self,
        image_paths: list[str],
        audio_paths: list[str],
        scene_texts: list[str],
        scene_titles: list[str],
        scene_labels: list[str],
        output_name: str,
        category: str,
        style: str = "blueprint",
        video_type: str = "dynamic"
    ) -> str:
        """
        Compiles a dynamic N-scene video.
        N content scenes → (N+2) audio tracks → (N+2)+N-1 video clips:
          [starting bumper] → [scene 1] → [transition] → [scene 2] → ... → [scene N] → [ending bumper]

        audio_paths: N+2 element list [starting_tts, s1_tts, ..., sN_tts, ending_tts]
        scene_texts: N element list
        scene_titles: N element list
        scene_labels: N element list
        """
        scene_count = len(scene_texts)
        st = STYLE_PRESETS.get(style, STYLE_PRESETS["blueprint"])
        rhythm = self._generate_video_rhythm(scene_count, style)

        try:
            from moviepy.editor import AudioFileClip, VideoClip, CompositeAudioClip, concatenate_videoclips, VideoFileClip
        except ImportError:
            from moviepy import AudioFileClip, VideoClip, CompositeAudioClip, concatenate_videoclips, VideoFileClip

        import random

        output_video_path = os.path.join(self.assets_dir, f"{output_name}.mp4")
        print(f"[VideoEngine] Compiling dynamic N-scene video ({scene_count} scenes): {output_video_path}")

        self._ensure_sfx_exist()

        # Resource tracking
        audio_clips = []
        bg_videos = []
        bg_music_clip = None
        bg_music_sub = None
        mixed_audio = None
        video_clip = None
        scene_clips = []
        transition_clips = []
        starting_clip = None
        ending_clip = None

        try:
            # Load N+2 audio tracks [starting, s1..sN, ending]
            audio_clips = [AudioFileClip(p) for p in audio_paths]
            audio_durations = [c.duration for c in audio_clips]
            dur_str = ", ".join([f"s{i+1 if i>0 and i<len(audio_durations)-1 else ('starting' if i==0 else 'ending')}={audio_durations[i]:.2f}s" for i in range(len(audio_durations))])
            print(f"[VideoEngine] Audio durations: {dur_str}")

            # Pad image_paths to scene_count
            imgs = list(image_paths)
            while len(imgs) < scene_count:
                imgs.append(imgs[-1] if imgs else "")
            imgs = imgs[:scene_count]

            # Resolve background sources for each scene
            for i in range(scene_count):
                bg_path = self._select_blueprint_video(scene_texts[i])
                bg_v = None
                if bg_path and os.path.exists(bg_path):
                    try:
                        bg_v = VideoFileClip(bg_path)
                    except Exception as e:
                        print(f"[VideoEngine] Failed to load blueprint video {i}: {e}")
                if bg_v is None:
                    bg_v = imgs[i]
                bg_videos.append(bg_v)

            # Generate N forensic cards
            cards = self._generate_dynamic_cards(imgs, scene_count, st)

            # ---- Clip 1: Starting Bumper ----
            starting_clip = self._create_starting_bumper(
                audio_duration=audio_durations[0],
                video_type=video_type,
                style_dict=st,
                rhythm=rhythm
            )
            starting_audio = audio_clips[0]
            starting_clip = starting_clip.with_audio(starting_audio)
            starting_dur = audio_durations[0]

            # ---- Content Scenes and Transitions ----
            clip_sequence = [starting_clip]

            # Track timeline positions for speaking blocks and SFX
            timeline_events = []  # list of (name, start, end)
            current_start = starting_dur

            # Map of scene audio index → timeline position
            scene_audio_starts = []
            scene_audio_durations = []

            for i in range(scene_count):
                audio_idx = i + 1  # audio_clips[0] is starting, [1..N] are scenes, [N+1] is ending

                delay_offset = rhythm["card_delay"] if i < scene_count - 1 else 0.0
                y_pos = rhythm["subtitle_y_top"] if i < scene_count - 1 else rhythm["subtitle_y_bottom"]

                s_clip = self._create_scene_clip(
                    bg_source=bg_videos[i],
                    card_image=cards[i],
                    audio_duration=audio_durations[audio_idx],
                    text=scene_texts[i],
                    delay_offset=delay_offset,
                    y_pos=y_pos,
                    scene_idx=i,
                    scene_label=scene_labels[i],
                    scene_title=scene_titles[i],
                    style_dict=st,
                    rhythm=rhythm
                )
                s_audio = audio_clips[audio_idx].set_start(delay_offset)
                s_clip = s_clip.with_audio(s_audio)
                scene_clips.append(s_clip)

                s_dur = delay_offset + audio_durations[audio_idx]
                timeline_events.append((f"scene_{i}", current_start, current_start + s_dur))
                scene_audio_starts.append(current_start)
                scene_audio_durations.append(audio_durations[audio_idx])

                clip_sequence.append(s_clip)
                current_start += s_dur

                # Transition clip (except after last scene)
                if i < scene_count - 1:
                    next_bg = bg_videos[i + 1] if (i + 1) < len(bg_videos) else bg_videos[i]
                    t_clip = self._create_transition_clip(bg_source=next_bg, duration=rhythm["transition_dur"])
                    transition_clips.append(t_clip)
                    clip_sequence.append(t_clip)
                    current_start += rhythm["transition_dur"]

            # ---- Last Clip: Ending Bumper ----
            ending_clip = self._create_ending_scene(
                audio_duration=audio_durations[-1],
                style_dict=st,
                rhythm=rhythm
            )
            ending_audio = audio_clips[-1]
            ending_clip = ending_clip.with_audio(ending_audio)
            ending_dur = audio_durations[-1]
            ending_start = current_start
            clip_sequence.append(ending_clip)
            timeline_events.append(("ending", ending_start, ending_start + ending_dur))

            # Concatenate all clips
            video_clip = concatenate_videoclips(clip_sequence)

            # ---- Speaking blocks for ducking ----
            speaking_blocks = [
                (0.0, starting_dur)  # starting bumper
            ]
            # Scene speaking blocks (only actual narration, not card delay)
            for i in range(scene_count):
                sc_start = scene_audio_starts[i]
                s_delay = rhythm["card_delay"] if i < scene_count - 1 else 0.0
                speaking_blocks.append((sc_start + s_delay, sc_start + s_delay + scene_audio_durations[i]))
            # Ending bumper
            speaking_blocks.append((ending_start, ending_start + ending_dur))

            audio_clips_to_mix = [video_clip.audio]

            # ---- SFX Setup ----
            sfx_dir = os.path.join(self.assets_dir, "sfx")
            zap_path = os.path.join(sfx_dir, "zap.mp3")
            pop_path = os.path.join(sfx_dir, "pop.mp3")
            stamp_path = os.path.join(sfx_dir, "stamp.mp3")
            tick_path = os.path.join(sfx_dir, "tick.mp3")
            impact_path = os.path.join(sfx_dir, "impact.mp3")
            riser_path = os.path.join(sfx_dir, "riser.mp3")

            # A. Watermark Stamp SFX at stamp_start and at each scene start + stamp_start
            if os.path.exists(stamp_path):
                try:
                    stamp_clip = AudioFileClip(stamp_path)
                    stamp_vol = rhythm["impact_volume"]
                    stamp_clip = stamp_clip.multiply_volume(stamp_vol) if hasattr(stamp_clip, "multiply_volume") else stamp_clip.volumex(stamp_vol)
                    audio_clips_to_mix.append(stamp_clip.set_start(rhythm["stamp_start"]))
                    for i in range(scene_count):
                        sc_start = scene_audio_starts[i]
                        audio_clips_to_mix.append(stamp_clip.copy().set_start(sc_start + rhythm["stamp_start"]))
                    print(f"[VideoEngine] Mixed stamp.mp3 slam SFX across {scene_count + 1} positions")
                except Exception as e:
                    print(f"[VideoEngine] WARNING: Failed to mix stamp SFX: {e}")

            # B. Ticking mechanical clock loop during card delays
            if os.path.exists(tick_path):
                try:
                    tick_clip = AudioFileClip(tick_path)
                    tick_clip = tick_clip.multiply_volume(0.06) if hasattr(tick_clip, "multiply_volume") else tick_clip.volumex(0.06)
                    for i in range(scene_count):
                        if i < scene_count - 1:  # No tick for the last scene (no card delay)
                            sc_start = scene_audio_starts[i]
                            t_tick = sc_start
                            while t_tick < sc_start + rhythm["card_delay"] - 0.2:
                                audio_clips_to_mix.append(tick_clip.set_start(t_tick))
                                t_tick += rhythm["tick_interval"]
                    print(f"[VideoEngine] Mixed ticking mechanical clock loop across {scene_count - 1} scenes")
                except Exception as e:
                    print(f"[VideoEngine] WARNING: Failed to mix clock ticks: {e}")

            # C. Sub-bass riser build-up before scene narration
            if os.path.exists(riser_path):
                try:
                    riser_clip = AudioFileClip(riser_path)
                    riser_clip = riser_clip.multiply_volume(0.15) if hasattr(riser_clip, "multiply_volume") else riser_clip.volumex(0.15)
                    for i in range(scene_count):
                        sc_start = scene_audio_starts[i]
                        audio_clips_to_mix.append(riser_clip.subclip(10.0 - rhythm["card_delay"], 10.0).set_start(sc_start))
                    print(f"[VideoEngine] Mixed sub-bass riser build-up SFX across {scene_count} scenes")
                except Exception as e:
                    print(f"[VideoEngine] WARNING: Failed to mix riser SFX: {e}")

            # D. Card Pop SFX at card start times
            if os.path.exists(pop_path):
                try:
                    pop_clip = AudioFileClip(pop_path)
                    pop_vol = rhythm["pop_volume"]
                    pop_clip = pop_clip.multiply_volume(pop_vol) if hasattr(pop_clip, "multiply_volume") else pop_clip.volumex(pop_vol)
                    for i in range(scene_count):
                        sc_start = scene_audio_starts[i]
                        audio_clips_to_mix.append(pop_clip.set_start(sc_start + rhythm["card_pop_time"]))
                    print(f"[VideoEngine] Mixed pop.mp3 card pop SFX across {scene_count} scenes")
                except Exception as e:
                    print(f"[VideoEngine] WARNING: Failed to mix pop SFX: {e}")

            # E. Glitch Zap SFX during transitions
            if os.path.exists(zap_path):
                try:
                    zap_clip = AudioFileClip(zap_path)
                    zap_vol = rhythm["zap_volume"]
                    zap_clip = zap_clip.multiply_volume(zap_vol) if hasattr(zap_clip, "multiply_volume") else zap_clip.volumex(zap_vol)
                    for i, t_clip in enumerate(transition_clips):
                        t_start = scene_audio_starts[i] + (rhythm["card_delay"] + scene_audio_durations[i])
                        audio_clips_to_mix.append(zap_clip.set_start(t_start))
                    print(f"[VideoEngine] Mixed zap.mp3 glitch transition SFX across {len(transition_clips)} transitions")
                except Exception as e:
                    print(f"[VideoEngine] WARNING: Failed to mix zap SFX: {e}")

            # F. Cinematic Impact Boom SFX at the start of each scene's narration
            if os.path.exists(impact_path):
                try:
                    impact_clip = AudioFileClip(impact_path)
                    impact_vol = rhythm["impact_volume"]
                    impact_clip = impact_clip.multiply_volume(impact_vol) if hasattr(impact_clip, "multiply_volume") else impact_clip.volumex(impact_vol)
                    for i in range(scene_count):
                        sc_start = scene_audio_starts[i]
                        audio_clips_to_mix.append(impact_clip.set_start(sc_start + rhythm["card_delay"]))
                    print(f"[VideoEngine] Mixed impact.mp3 boom SFX across {scene_count} scenes")
                except Exception as e:
                    print(f"[VideoEngine] WARNING: Failed to mix impact SFX: {e}")

            # ---- Dynamic Ducked Background Music ----
            bg_music_path = self._resolve_theme_music(category)

            if bg_music_path:
                try:
                    bg_music_clip = AudioFileClip(bg_music_path)
                    bg_duration = bg_music_clip.duration
                    max_start = max(0.0, bg_duration - video_clip.duration - 2.0)
                    start_t = random.uniform(0.0, max_start) if max_start > 0 else 0.0

                    if hasattr(bg_music_clip, "subclipped"):
                        bg_music_sub = bg_music_clip.subclipped(start_t, start_t + video_clip.duration)
                    else:
                        bg_music_sub = bg_music_clip.subclip(start_t, start_t + video_clip.duration)

                    def get_ducking_factor(t_val):
                        vol_min = 0.05
                        vol_max = 0.20
                        ramp_up = 0.2
                        ramp_down = 0.1

                        for start, end in speaking_blocks:
                            if start <= t_val <= end:
                                return vol_min

                        for i in range(len(speaking_blocks) - 1):
                            end_i = speaking_blocks[i][1]
                            start_next = speaking_blocks[i + 1][0]
                            if end_i < t_val < start_next:
                                pause_dur = start_next - end_i
                                if pause_dur <= (ramp_up + ramp_down):
                                    return vol_min
                                if t_val < end_i + ramp_up:
                                    return vol_min + (vol_max - vol_min) * ((t_val - end_i) / ramp_up)
                                elif t_val > start_next - ramp_down:
                                    return vol_max - (vol_max - vol_min) * ((t_val - (start_next - ramp_down)) / ramp_down)
                                else:
                                    return vol_max

                        end_last = speaking_blocks[-1][1]
                        if t_val > end_last:
                            if t_val < end_last + ramp_up:
                                return vol_min + (vol_max - vol_min) * ((t_val - end_last) / ramp_up)
                            else:
                                return vol_max
                        return vol_min

                    def duck_audio(gf, t):
                        factors = np.vectorize(get_ducking_factor)(t)
                        if len(factors.shape) > 0:
                            return gf(t) * factors[:, np.newaxis]
                        else:
                            return gf(t) * factors

                    bg_music_sub = bg_music_sub.fl(duck_audio)
                    audio_clips_to_mix.append(bg_music_sub)
                    print("[VideoEngine] Category music routed and ducked dynamically")
                except Exception as bg_err:
                    print(f"[VideoEngine] WARNING: Failed to mix background music ({bg_err}).")

            mixed_audio = CompositeAudioClip(audio_clips_to_mix)
            video_clip = video_clip.with_audio(mixed_audio)

            codec = "h264_nvenc" if self.has_cuda else "libx264"
            threads = os.cpu_count() or 4

            print(f"[VideoEngine] Starting rendering process (codec={codec}, threads={threads})...")
            video_clip.write_videofile(
                output_video_path,
                fps=30,
                codec=codec,
                audio_codec="aac",
                threads=threads
            )

            print(f"[VideoEngine] Dynamic N-scene render complete: {output_video_path}")
            return output_video_path

        finally:
            # Safely clean up all resources
            if video_clip:
                try:
                    video_clip.close()
                except:
                    pass
            for c in audio_clips:
                if c:
                    try:
                        c.close()
                    except:
                        pass
            for clip_ref in [starting_clip, ending_clip] + scene_clips + transition_clips:
                if clip_ref:
                    try:
                        clip_ref.close()
                    except:
                        pass
            if bg_music_clip:
                try:
                    bg_music_clip.close()
                except:
                    pass
            if bg_music_sub:
                try:
                    bg_music_sub.close()
                except:
                    pass
            if mixed_audio:
                try:
                    mixed_audio.close()
                except:
                    pass
            for bg_v in bg_videos:
                if bg_v and hasattr(bg_v, "close"):
                    try:
                        bg_v.close()
                    except:
                        pass
            import gc
            gc.collect()

    def _compile_scene_based_video(self, image_paths: List[str], audio_paths: List[str], scene_texts: List[str], scene_labels: List[str], scene_titles: List[str], output_name: str, category: str, style: str, is_bizarre: bool, video_type: str = "myth", rhythm: dict = None) -> str:
        """
        Compiles a video from 5 audio tracks and 7 video clips:
          [starting bumper] → [scene 1] → [transition 1] → [scene 2] → [transition 2] → [scene 3] → [ending bumper]
        audio_paths: 5-element list [starting_tts, s1_tts, s2_tts, s3_tts, ending_tts]
        scene_texts: 3-element list [s1_text, s2_text, s3_text]  (content scenes only)
        """
        if rhythm is None:
            rhythm = self._generate_video_rhythm(3, style)
        st = STYLE_PRESETS.get(style, STYLE_PRESETS["blueprint"])
        try:
            from moviepy.editor import AudioFileClip, VideoClip, CompositeAudioClip, concatenate_videoclips, VideoFileClip
        except ImportError:
            from moviepy import AudioFileClip, VideoClip, CompositeAudioClip, concatenate_videoclips, VideoFileClip
            
        import random
        
        output_video_path = os.path.join(self.assets_dir, f"{output_name}.mp4")
        print(f"[VideoEngine] Compiling scene-based video (5-scene pipeline): {output_video_path}")
        
        self._ensure_sfx_exist()
        
        # Resource tracking
        audio_clips = []
        bg_video_1 = None
        bg_video_2 = None
        bg_video_3 = None
        bg_music_clip = None
        bg_music_sub = None
        mixed_audio = None
        video_clip = None
        starting_clip = None
        s1_clip = None
        t1_clip = None
        s2_clip = None
        t2_clip = None
        s3_clip = None
        ending_clip = None
        
        try:
            # Load 5 audio tracks [starting, s1, s2, s3, ending]
            audio_clips = [AudioFileClip(p) for p in audio_paths]
            audio_durations = [clip.duration for clip in audio_clips]
            print(f"[VideoEngine] Audio durations: starting={audio_durations[0]:.2f}s, s1={audio_durations[1]:.2f}s, s2={audio_durations[2]:.2f}s, s3={audio_durations[3]:.2f}s, ending={audio_durations[4]:.2f}s")
            
            # Resolve background sources for 3 content scenes
            bg_video_path_1 = self._select_blueprint_video(scene_texts[0])
            bg_video_path_2 = self._select_blueprint_video(scene_texts[1])
            bg_video_path_3 = self._select_blueprint_video(scene_texts[2])
            
            if bg_video_path_1 and os.path.exists(bg_video_path_1):
                try:
                    bg_video_1 = VideoFileClip(bg_video_path_1)
                except Exception as e:
                    print(f"[VideoEngine] Failed to load blueprint video 1: {e}")
            if bg_video_1 is None:
                bg_video_1 = image_paths[0]
                
            if bg_video_path_2 and os.path.exists(bg_video_path_2):
                try:
                    bg_video_2 = VideoFileClip(bg_video_path_2)
                except Exception as e:
                    print(f"[VideoEngine] Failed to load blueprint video 2: {e}")
            if bg_video_2 is None:
                bg_video_2 = image_paths[1]
                
            if bg_video_path_3 and os.path.exists(bg_video_path_3):
                try:
                    bg_video_3 = VideoFileClip(bg_video_path_3)
                except Exception as e:
                    print(f"[VideoEngine] Failed to load blueprint video 3: {e}")
            if bg_video_3 is None:
                bg_video_3 = image_paths[2]
            
            # Generate forensic tech cards for scene 1 and scene 2
            card_1 = self._generate_card(
                image_path=image_paths[0],
                label_text=st["anomaly_label"] if (is_bizarre and category == "bizarre") else st["myth_label"],
                status_text="STATUS: ANOMALOUS RECORD" if is_bizarre else "STATUS: DEBUNKED MYTH",
                is_truth=False,
                style_dict=st
            )
            card_2 = self._generate_card(
                image_path=image_paths[1],
                label_text=st["truth_label"],
                status_text="STATUS: DECLASSIFIED ANOMALY" if is_bizarre else "STATUS: VERIFIED FACT",
                is_truth=True,
                style_dict=st
            )
            
            # ---- Clip 1: Starting Bumper (delay 0s) ----
            starting_clip = self._create_starting_bumper(
                audio_duration=audio_durations[0],
                video_type=video_type,
                style_dict=st,
                rhythm=rhythm
            )
            starting_audio = audio_clips[0]  # starts at 0.0
            starting_clip = starting_clip.with_audio(starting_audio)
            starting_dur = audio_durations[0]
            
            # ---- Clip 2: Scene 1 (delay 1.75s) ----
            s1_clip = self._create_scene_clip(
                bg_source=bg_video_1,
                card_image=card_1,
                audio_duration=audio_durations[1],
                text=scene_texts[0],
                delay_offset=rhythm["card_delay"],
                y_pos=rhythm["subtitle_y_top"],
                scene_idx=0,
                scene_label=scene_labels[0],
                scene_title=scene_titles[0],
                style_dict=st,
                rhythm=rhythm
            )
            s1_audio = audio_clips[1].set_start(rhythm["card_delay"])
            s1_clip = s1_clip.with_audio(s1_audio)
            
            # ---- Clip 3: Transition 1 (0.5s) ----
            t1_clip = self._create_transition_clip(bg_source=bg_video_2, duration=rhythm["transition_dur"])
            
            # ---- Clip 4: Scene 2 (delay 1.75s) ----
            s2_clip = self._create_scene_clip(
                bg_source=bg_video_2,
                card_image=card_2,
                audio_duration=audio_durations[2],
                text=scene_texts[1],
                delay_offset=rhythm["card_delay"],
                y_pos=rhythm["subtitle_y_top"],
                scene_idx=1,
                scene_label=scene_labels[1],
                scene_title=scene_titles[1],
                style_dict=st,
                rhythm=rhythm
            )
            s2_audio = audio_clips[2].set_start(rhythm["card_delay"])
            s2_clip = s2_clip.with_audio(s2_audio)
            
            # ---- Clip 5: Transition 2 (0.5s) ----
            t2_clip = self._create_transition_clip(bg_source=bg_video_3, duration=rhythm["transition_dur"])
            
            # ---- Clip 6: Scene 3 (delay 0s, bottom subtitles) ----
            s3_clip = self._create_scene_clip(
                bg_source=bg_video_3,
                card_image=None,
                audio_duration=audio_durations[3],
                text=scene_texts[2],
                delay_offset=0.0,
                y_pos=rhythm["subtitle_y_bottom"],
                scene_idx=2,
                scene_label=scene_labels[2],
                scene_title=scene_titles[2],
                style_dict=st,
                rhythm=rhythm
            )
            s3_audio = audio_clips[3]
            s3_clip = s3_clip.with_audio(s3_audio)
            
            # ---- Clip 7: Ending Bumper (delay 0s) ----
            ending_clip = self._create_ending_scene(
                audio_duration=audio_durations[4],
                style_dict=st,
                rhythm=rhythm
            )
            ending_audio = audio_clips[4]
            ending_clip = ending_clip.with_audio(ending_audio)
            
            # ---- Concatenate all 7 clips ----
            video_clip = concatenate_videoclips([starting_clip, s1_clip, t1_clip, s2_clip, t2_clip, s3_clip, ending_clip])
            
            # ---- Timeline timestamps ----
            # starting: 0 → starting_dur
            s1_start = starting_dur
            s1_dur = rhythm["card_delay"] + audio_durations[1]
            t1_start = s1_start + s1_dur
            s2_start = t1_start + rhythm["transition_dur"]
            s2_dur = rhythm["card_delay"] + audio_durations[2]
            t2_start = s2_start + s2_dur
            s3_start = t2_start + rhythm["transition_dur"]
            s3_dur = audio_durations[3]
            ending_start = s3_start + s3_dur
            ending_dur = audio_durations[4]
            
            # Speaking blocks for ducking (5 blocks: starting, s1, s2, s3, ending)
            speaking_blocks = [
                (0.0, starting_dur),                              # starting bumper
                (s1_start + rhythm["card_delay"], s1_start + s1_dur),            # scene 1 narration
                (s2_start + rhythm["card_delay"], s2_start + s2_dur),            # scene 2 narration
                (s3_start, s3_start + s3_dur),                   # scene 3 narration
                (ending_start, ending_start + ending_dur),        # ending bumper
            ]
            
            audio_clips_to_mix = [video_clip.audio]
            
            # Load SFX files
            sfx_dir = os.path.join(self.assets_dir, "sfx")
            zap_path = os.path.join(sfx_dir, "zap.mp3")
            pop_path = os.path.join(sfx_dir, "pop.mp3")
            stamp_path = os.path.join(sfx_dir, "stamp.mp3")
            tick_path = os.path.join(sfx_dir, "tick.mp3")
            impact_path = os.path.join(sfx_dir, "impact.mp3")
            riser_path = os.path.join(sfx_dir, "riser.mp3")
            
            # A. Watermark Stamp SFX at stamp_start (in starting bumper) and s2_start + stamp_start
            if os.path.exists(stamp_path):
                try:
                    stamp_clip = AudioFileClip(stamp_path)
                    stamp_vol = rhythm["impact_volume"]
                    stamp_clip = stamp_clip.multiply_volume(stamp_vol) if hasattr(stamp_clip, "multiply_volume") else stamp_clip.volumex(stamp_vol)
                    audio_clips_to_mix.append(stamp_clip.set_start(rhythm["stamp_start"]))
                    audio_clips_to_mix.append(stamp_clip.copy().set_start(s2_start + rhythm["stamp_start"]))
                    print("[VideoEngine] Mixed stamp.mp3 slam SFX")
                except Exception as e:
                    print(f"[VideoEngine] WARNING: Failed to mix stamp SFX: {e}")
                    
            # B. Ticking mechanical clock loop during card scene delays
            if os.path.exists(tick_path):
                try:
                    tick_clip = AudioFileClip(tick_path)
                    tick_clip = tick_clip.multiply_volume(0.06) if hasattr(tick_clip, "multiply_volume") else tick_clip.volumex(0.06)
                    # Scene 1 ticks (during card_delay)
                    t_tick = s1_start
                    while t_tick < s1_start + rhythm["card_delay"] - 0.2:
                        audio_clips_to_mix.append(tick_clip.set_start(t_tick))
                        t_tick += rhythm["tick_interval"]
                    # Scene 2 ticks
                    t_tick = s2_start
                    while t_tick < s2_start + rhythm["card_delay"] - 0.2:
                        audio_clips_to_mix.append(tick_clip.set_start(t_tick))
                        t_tick += rhythm["tick_interval"]
                    print("[VideoEngine] Mixed ticking mechanical clock loop")
                except Exception as e:
                    print(f"[VideoEngine] WARNING: Failed to mix clock ticks: {e}")
                    
            # C. Sub-bass riser build-up before Scene 1 and Scene 2 narration
            if os.path.exists(riser_path):
                try:
                    riser_clip = AudioFileClip(riser_path)
                    riser_clip = riser_clip.multiply_volume(0.15) if hasattr(riser_clip, "multiply_volume") else riser_clip.volumex(0.15)
                    # Scene 1 riser: ends at s1_start + card_delay
                    audio_clips_to_mix.append(riser_clip.subclip(10.0 - rhythm["card_delay"], 10.0).set_start(s1_start))
                    # Scene 2 riser: ends at s2_start + card_delay
                    audio_clips_to_mix.append(riser_clip.subclip(10.0 - rhythm["card_delay"], 10.0).set_start(s2_start))
                    print("[VideoEngine] Mixed sub-bass riser build-up SFX")
                except Exception as e:
                    print(f"[VideoEngine] WARNING: Failed to mix riser SFX: {e}")
                    
            # D. Card Pop SFX at card start times
            if os.path.exists(pop_path):
                try:
                    pop_clip = AudioFileClip(pop_path)
                    pop_vol = rhythm["pop_volume"]
                    pop_clip = pop_clip.multiply_volume(pop_vol) if hasattr(pop_clip, "multiply_volume") else pop_clip.volumex(pop_vol)
                    audio_clips_to_mix.append(pop_clip.set_start(s1_start + rhythm["card_pop_time"]))
                    audio_clips_to_mix.append(pop_clip.copy().set_start(s2_start + rhythm["card_pop_time"]))
                    print("[VideoEngine] Mixed pop.mp3 card pop SFX")
                except Exception as e:
                    print(f"[VideoEngine] WARNING: Failed to mix pop SFX: {e}")
                    
            # E. Glitch Zap SFX during transitions
            if os.path.exists(zap_path):
                try:
                    zap_clip = AudioFileClip(zap_path)
                    zap_vol = rhythm["zap_volume"]
                    zap_clip = zap_clip.multiply_volume(zap_vol) if hasattr(zap_clip, "multiply_volume") else zap_clip.volumex(zap_vol)
                    audio_clips_to_mix.append(zap_clip.set_start(t1_start))
                    audio_clips_to_mix.append(zap_clip.copy().set_start(t2_start))
                    print("[VideoEngine] Mixed zap.mp3 glitch transition SFX")
                except Exception as e:
                    print(f"[VideoEngine] WARNING: Failed to mix zap SFX: {e}")
                    
            # F. Cinematic Impact Boom SFX at the start of Scene 2 truth reveal
            if os.path.exists(impact_path):
                try:
                    impact_clip = AudioFileClip(impact_path)
                    impact_vol = rhythm["impact_volume"]
                    impact_clip = impact_clip.multiply_volume(impact_vol) if hasattr(impact_clip, "multiply_volume") else impact_clip.volumex(impact_vol)
                    audio_clips_to_mix.append(impact_clip.set_start(s2_start + rhythm["card_delay"]))
                    print(f"[VideoEngine] Mixed impact.mp3 boom SFX at {s2_start + rhythm['card_delay']:.2f}s")
                except Exception as e:
                    print(f"[VideoEngine] WARNING: Failed to mix impact SFX: {e}")
                    
            # Dynamic Ducked Background Music
            bg_music_path = self._resolve_theme_music(category)
            
            if bg_music_path:
                try:
                    bg_music_clip = AudioFileClip(bg_music_path)
                    bg_duration = bg_music_clip.duration
                    max_start = max(0.0, bg_duration - video_clip.duration - 2.0)
                    start_t = random.uniform(0.0, max_start)
                    
                    if hasattr(bg_music_clip, "subclipped"):
                        bg_music_sub = bg_music_clip.subclipped(start_t, start_t + video_clip.duration)
                    else:
                        bg_music_sub = bg_music_clip.subclip(start_t, start_t + video_clip.duration)
                        
                    def get_ducking_factor(t_val):
                        vol_min = 0.05
                        vol_max = 0.20
                        ramp_up = 0.2
                        ramp_down = 0.1
                        
                        for start, end in speaking_blocks:
                            if start <= t_val <= end:
                                return vol_min
                                
                        for i in range(len(speaking_blocks) - 1):
                            end_i = speaking_blocks[i][1]
                            start_next = speaking_blocks[i+1][0]
                            if end_i < t_val < start_next:
                                pause_dur = start_next - end_i
                                if pause_dur <= (ramp_up + ramp_down):
                                    return vol_min
                                if t_val < end_i + ramp_up:
                                    return vol_min + (vol_max - vol_min) * ((t_val - end_i) / ramp_up)
                                elif t_val > start_next - ramp_down:
                                    return vol_max - (vol_max - vol_min) * ((t_val - (start_next - ramp_down)) / ramp_down)
                                else:
                                    return vol_max
                                    
                        end_last = speaking_blocks[-1][1]
                        if t_val > end_last:
                            if t_val < end_last + ramp_up:
                                return vol_min + (vol_max - vol_min) * ((t_val - end_last) / ramp_up)
                            else:
                                return vol_max
                        return vol_min
    
                    def duck_audio(gf, t):
                        factors = np.vectorize(get_ducking_factor)(t)
                        if len(factors.shape) > 0:
                            return gf(t) * factors[:, np.newaxis]
                        else:
                            return gf(t) * factors
                            
                    bg_music_sub = bg_music_sub.fl(duck_audio)
                    audio_clips_to_mix.append(bg_music_sub)
                    print("[VideoEngine] Category music routed and ducked dynamically")
                except Exception as bg_err:
                    print(f"[VideoEngine] WARNING: Failed to mix background music ({bg_err}).")
                    
            mixed_audio = CompositeAudioClip(audio_clips_to_mix)
            video_clip = video_clip.with_audio(mixed_audio)
            
            codec = "h264_nvenc" if self.has_cuda else "libx264"
            threads = os.cpu_count() or 4
            
            print(f"[VideoEngine] Starting rendering process (codec={codec}, threads={threads})...")
            video_clip.write_videofile(
                output_video_path,
                fps=30,
                codec=codec,
                audio_codec="aac",
                threads=threads
            )
            
            print(f"[VideoEngine] Render complete: {output_video_path}")
            return output_video_path
            
        finally:
            # Safely clean up all resources to avoid handle leaks on Windows
            if video_clip:
                try:
                    video_clip.close()
                except:
                    pass
            for c in audio_clips:
                if c:
                    try:
                        c.close()
                    except:
                        pass
            for clip_ref in [starting_clip, s1_clip, t1_clip, s2_clip, t2_clip, s3_clip, ending_clip]:
                if clip_ref:
                    try:
                        clip_ref.close()
                    except:
                        pass
            if bg_music_clip:
                try:
                    bg_music_clip.close()
                except:
                    pass
            if bg_music_sub:
                try:
                    bg_music_sub.close()
                except:
                    pass
            if mixed_audio:
                try:
                    mixed_audio.close()
                except:
                    pass
            for bg_v in [bg_video_1, bg_video_2, bg_video_3]:
                if bg_v and hasattr(bg_v, "close"):
                    try:
                        bg_v.close()
                    except:
                        pass
            import gc
            gc.collect()

if __name__ == "__main__":
    # Self-test render block
    mock_payload = {
        "hook": "You've been lied to about glass.",
        "context": "Old church windows are thicker at the bottom.",
        "fact": "This is from medieval manufacturing, not glass flowing.",
        "sign_off": "Class dismissed."
    }
    
    # Create test dummy blueprint and test audio
    base_dir = os.path.dirname(os.path.abspath(__file__))
    img_path = os.path.join(base_dir, "assets", "test_blueprint.png")
    audio_path = os.path.join(base_dir, "assets", "test_speech.mp3")
    
    if os.path.exists(img_path) and os.path.exists(audio_path):
        engine = VideoEngine()
        engine.compile_short(img_path, img_path, audio_path, mock_payload, "test_rendered_short")
    else:
        print("Self-test assets not found. Run asset_generator.py first.")

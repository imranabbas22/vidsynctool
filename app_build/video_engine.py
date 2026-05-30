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
    from moviepy.editor import AudioClip, AudioFileClip, VideoClip, VideoFileClip, CompositeAudioClip
except ImportError:
    from moviepy import AudioClip, AudioFileClip, VideoClip, VideoFileClip, CompositeAudioClip

# Patch clip classes for MoviePy v2.x compatibility with legacy methods
for clip_class in [AudioClip, AudioFileClip, VideoClip, VideoFileClip, CompositeAudioClip]:
    if not hasattr(clip_class, 'volumex') and hasattr(clip_class, 'with_volume_scaled'):
        clip_class.volumex = clip_class.with_volume_scaled
    if not hasattr(clip_class, 'multiply_volume') and hasattr(clip_class, 'with_volume_scaled'):
        clip_class.multiply_volume = clip_class.with_volume_scaled
    if not hasattr(clip_class, 'fl') and hasattr(clip_class, 'transform'):
        clip_class.fl = clip_class.transform
    if not hasattr(clip_class, 'set_start') and hasattr(clip_class, 'with_start'):
        clip_class.set_start = clip_class.with_start
    if not hasattr(clip_class, 'subclip') and hasattr(clip_class, 'subclipped'):
        clip_class.subclip = clip_class.subclipped

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
    "evidence": {
        "bg_prompt_suffix": "Style of a detective case file, cork board with pinned evidence photos, red string connecting clues, warm tungsten lighting.",
        "card_bg": (50, 40, 30),
        "card_myth_outline": (200, 40, 40),
        "card_truth_outline": (40, 180, 80),
        "card_myth_header_bg": (200, 40, 40),
        "card_truth_header_bg": (40, 180, 80),
        "card_myth_header_text": (255, 255, 255),
        "card_truth_header_text": (255, 255, 255),
        "myth_label": "EVIDENCE FILE: MISLEADING CLAIM",
        "truth_label": "EVIDENCE FILE: VERIFIED FACT",
        "anomaly_label": "EVIDENCE FILE: CLASSIFIED ANOMALY",
        "subtitle_color": (220, 210, 190),
        "highlight_bg": (200, 160, 60),
        "highlight_text": (20, 15, 10),
        "grid_color": (120, 100, 80, 20),
        "watermark_color": (200, 40, 40),
        "timer_bar_color": (200, 160, 60),
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

        # Per-video seed for deterministic randomization
        self.video_seed = video_seed
        # Pre-generate mascot easter egg image (always — tiny 80×100 RGBA)
        self.mascot_img = self._generate_mascot()
        
        # Detect CUDA support once on startup
        self.has_cuda = self._detect_cuda_support()

        # Evidence board mode (case-file / detective style)
        self.evidence_mode = False
        self.evidence_captions = []

        # Lookahead offset (in ms) to pull subtitles forward so they match the audio timing.
        self.subtitle_lookahead_ms = 200.0

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

    def _generate_mascot(self) -> Image.Image:
        """
        Renders the Static mascot — a living CRT noise cloud with glowing eyes.
        Returns an RGBA PIL Image for compositing as easter egg.
        """
        return self._render_static(size=70, expression="neutral")

    def _select_blueprint_video(self, search_text: str) -> Optional[str]:
        """
        Scans the assets/video_blueprints directory and selects a video matching the keyword.
        Falls back to 'Golden_dust_particles_in_light' or the first available video.
        """
        blueprint_dir = os.path.join(self.assets_dir, "video_blueprints")
        if not os.path.exists(blueprint_dir):
            return None
            
        mp4_files = []
        for root, dirs, files in os.walk(blueprint_dir):
            for f in files:
                if f.endswith(".mp4"):
                    mp4_files.append(os.path.join(root, f))
        if not mp4_files:
            return None
            
        import re
        search_text_clean = re.sub(r'<[^>]+>', '', search_text) if search_text else ""
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
        return os.path.join(blueprint_dir, mp4_files[0])

    def _select_starting_blueprint(self, video_type: str) -> Optional[str]:
        """
        Selects a starting bumper blueprint from app_build/assets/video_blueprints/starting/.
        Falls back to any MP4 in the video_blueprints directory if starting/ is empty.
        Filters by 'myth' or 'bizarre' keyword in filename; returns random if no match.
        """
        base_dir = os.path.dirname(os.path.abspath(__file__))
        # Check app_build/assets/video_blueprints/starting/ first
        start_dir = os.path.join(self.assets_dir, "video_blueprints", "starting")
        if not os.path.exists(start_dir) or not any(f.endswith(".mp4") for f in os.listdir(start_dir)):
            # Fallback: any video in the parent video_blueprints directory
            blueprint_dir = os.path.join(self.assets_dir, "video_blueprints")
            if os.path.exists(blueprint_dir):
                all_mp4 = []
                for root, dirs, files in os.walk(blueprint_dir):
                    for f in files:
                        if f.endswith(".mp4"):
                            all_mp4.append(os.path.join(root, f))
                if all_mp4:
                    keyword = "myth" if video_type == "myth" else "bizarre"
                    matched = [p for p in all_mp4 if keyword in os.path.basename(p).lower()]
                    if matched:
                        return random.choice(matched)
                    return random.choice(all_mp4)
            return None

        files = [f for f in os.listdir(start_dir) if f.endswith(".mp4")]
        if not files:
            return None
        keyword = "myth" if video_type == "myth" else "bizarre"
        matched = [f for f in files if keyword in f.lower()]
        if matched:
            return os.path.join(start_dir, random.choice(matched))
        return os.path.join(start_dir, random.choice(files))

    def _select_ending_blueprint(self) -> Optional[str]:
        """
        Selects an ending bumper blueprint from app_build/assets/video_blueprints/ending/.
        Falls back to any MP4 in the video_blueprints directory if ending/ is empty.
        Prefers files with 'class' or 'dismissed' in the name.
        """
        base_dir = os.path.dirname(os.path.abspath(__file__))
        # Check app_build/assets/video_blueprints/ending/ first
        end_dir = os.path.join(self.assets_dir, "video_blueprints", "ending")
        if not os.path.exists(end_dir) or not any(f.endswith(".mp4") for f in os.listdir(end_dir)):
            # Fallback: any video in the parent video_blueprints directory
            blueprint_dir = os.path.join(self.assets_dir, "video_blueprints")
            if os.path.exists(blueprint_dir):
                all_mp4 = []
                for root, dirs, files in os.walk(blueprint_dir):
                    for f in files:
                        if f.endswith(".mp4"):
                            all_mp4.append(os.path.join(root, f))
                if all_mp4:
                    dismissed = [p for p in all_mp4 if "class" in os.path.basename(p).lower() or "dismissed" in os.path.basename(p).lower()]
                    if dismissed:
                        return random.choice(dismissed)
                    return random.choice(all_mp4)
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
            s = amp * math.sin(2 * math.pi * 200 * t) # riser frequency sweep
            riser_samples.append(s)
        synthesize_and_save("riser", riser_samples)

        # 7. hum.mp3: Subtle low-frequency CRT hum (60s duration)
        hum_samples = []
        for i in range(int(60.0 * sample_rate)):
            t = i / sample_rate
            s = 0.7 * math.sin(2 * math.pi * 60 * t) + \
                0.25 * math.sin(2 * math.pi * 120 * t) + \
                0.05 * random.uniform(-0.5, 0.5)
            hum_samples.append(s)
        synthesize_and_save("hum", hum_samples)

        # 8. crackle.mp3: Procedural fire crackling sound (2s)
        crackle_samples = []
        for i in range(int(2.0 * sample_rate)):
            t = i / sample_rate
            # White noise pops at random intervals
            pop = 0.0
            if random.random() < 0.03:
                pop = random.uniform(0.3, 1.0) * math.exp(-200 * random.uniform(0.01, 0.03))
            # Low-frequency rumble (60Hz sine with AM modulation)
            rumble = 0.3 * math.sin(2 * math.pi * 60 * t) * (0.5 + 0.5 * math.sin(2 * math.pi * 4 * t))
            crackle_samples.append(pop + rumble)
        synthesize_and_save("crackle", crackle_samples)

        # 9. heartbeat.mp3: Sub-bass heartbeat pulse (double beat, ~70 BPM, 2s duration)
        heartbeat_samples = []
        cycle_len = int(0.857 * sample_rate)
        for i in range(int(2.0 * sample_rate)):
            t = i / sample_rate
            idx_in_cycle = i % cycle_len
            t_in_cycle = idx_in_cycle / sample_rate
            
            # Pulse 1 (lub) starts at 0.0s, Pulse 2 (dub) starts at 0.15s
            val = 0.0
            if 0.0 <= t_in_cycle < 0.15:
                val = 0.7 * math.sin(2 * math.pi * 50 * t_in_cycle) * math.exp(-20 * t_in_cycle)
            elif 0.15 <= t_in_cycle < 0.35:
                t_dub = t_in_cycle - 0.15
                val = 0.5 * math.sin(2 * math.pi * 55 * t_dub) * math.exp(-20 * t_dub)
            
            heartbeat_samples.append(val)
        synthesize_and_save("heartbeat", heartbeat_samples)

        # 10. ambient_science.mp3: Science lab hum & bubbling (60s)
        sci_samples = []
        for i in range(int(60.0 * sample_rate)):
            t = i / sample_rate
            hum = 0.5 * math.sin(2 * math.pi * 100 * t)
            bubble = 0.0
            if random.random() < 0.0005:
                bubble = random.uniform(0.1, 0.4) * math.exp(-80 * random.uniform(0.01, 0.05))
            sci_samples.append(0.8 * hum + 0.2 * bubble)
        synthesize_and_save("ambient_science", sci_samples)

        # 11. ambient_history.mp3: Wind & distant echo noise (60s)
        hist_samples = []
        for i in range(int(60.0 * sample_rate)):
            t = i / sample_rate
            noise = random.uniform(-1.0, 1.0)
            wind_mod = 0.5 + 0.5 * math.sin(2 * math.pi * 0.15 * t + math.sin(2 * math.pi * 0.03 * t))
            hist_samples.append(0.3 * noise * wind_mod)
        synthesize_and_save("ambient_history", hist_samples)

        # 12. ambient_space.mp3: Detuned deep space drone (60s)
        space_samples = []
        for i in range(int(60.0 * sample_rate)):
            t = i / sample_rate
            drone = 0.5 * math.sin(2 * math.pi * 50 * t) + \
                    0.3 * math.sin(2 * math.pi * 75 * t + 0.5) + \
                    0.2 * math.sin(2 * math.pi * 110 * t)
            space_samples.append(drone)
        synthesize_and_save("ambient_space", space_samples)

        # 13. ambient_tech.mp3: Server room ventilation fan & hum (60s)
        tech_samples = []
        for i in range(int(60.0 * sample_rate)):
            t = i / sample_rate
            noise = random.uniform(-0.15, 0.15)
            hum = 0.6 * math.sin(2 * math.pi * 120 * t) + 0.4 * math.sin(2 * math.pi * 60 * t)
            tech_samples.append(0.7 * noise + 0.3 * hum)
        synthesize_and_save("ambient_tech", tech_samples)

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

    def compile_short(self, image_myth_path: str, image_truth_path: str, audio_path: Any, script_payload: Dict[str, Any], output_name: str, category: str = "history", style: str = "blueprint", video_type: str = "myth", image_paths_override: Optional[List[str]] = None) -> str:
        """
        Compiles the assets into a finished 9:16 vertical MP4 video.
        Applies visual drift scanlines, organic grit, CRT glitch transitions, elastic card pop-ins,
        category-routed music, and dynamic audio ducking.
        audio_path is a 5-element list: [starting_tts, s1_tts, s2_tts, s3_tts, ending_tts]
        """
        if isinstance(audio_path, list):
            hook = (script_payload.get("s1_ssml") or script_payload.get("hook_ssml") or script_payload.get("hook") or "").strip()
            context = (script_payload.get("s2_ssml") or script_payload.get("context_ssml") or script_payload.get("context") or "").strip()
            fact = (script_payload.get("s3_ssml") or script_payload.get("fact_ssml") or script_payload.get("fact") or "").strip()
            
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
            if image_paths_override:
                image_paths = list(image_paths_override)
            else:
                image_paths = [
                    image_myth_path,
                    image_truth_path or image_myth_path,
                    image_truth_path or image_myth_path
                ]
            # Build mid_roll word indices from scene 2 text
            mid_roll_hook = (script_payload.get("mid_roll_hook") or "").strip().lower()
            mid_roll_word_indices = None
            if mid_roll_hook and len(scene_texts) > 1:
                hook_words = mid_roll_hook.split()
                s2_words = scene_texts[1].split()
                mid_roll_word_indices = set()
                for hw in hook_words:
                    for i, w in enumerate(s2_words):
                        if w.lower() == hw:
                            mid_roll_word_indices.add(i)
                if not mid_roll_word_indices:
                    mid_roll_word_indices = None

            starting_text = script_payload.get("starting_text")
            ending_text = script_payload.get("ending_text")

            # Evidence board mode
            self.evidence_mode = (style == "evidence")
            if self.evidence_mode:
                self.evidence_captions = [s[:120] for s in scene_texts if s]
                print("[VideoEngine] Evidence board mode ACTIVE")

            import traceback
            try:
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
                    mid_roll_word_indices=mid_roll_word_indices,
                    starting_text=starting_text,
                    ending_text=ending_text,
                    topic=script_payload.get("topic"),
                    episode_num=script_payload.get("episode_num")
                )
            except Exception as e:
                print(f"[VideoEngine] _compile_scene_based_video CRASH: {e}")
                traceback.print_exc()
                raise

        st = STYLE_PRESETS.get(style, STYLE_PRESETS["blueprint"])
        # Evidence board mode
        self.evidence_mode = (style == "evidence")
        if self.evidence_mode:
            self.evidence_captions = [s[:120] for s in scene_texts if s]
            print("[VideoEngine] Evidence board mode ACTIVE")
        try:
            from moviepy.editor import ImageClip, AudioFileClip, VideoClip, CompositeAudioClip
        except ImportError:
            from moviepy import ImageClip, AudioFileClip, VideoClip, CompositeAudioClip
        
        import random
        
        output_video_path = os.path.join(self.assets_dir, f"{output_name}.mp4")
        print(f"[VideoEngine] Initializing video compilation for: {output_video_path}")
        tmp_files = []
        
        # 0. Ensure sound effects exist
        self._ensure_sfx_exist()
        
        # 1. Load TTS Audio to determine total video duration
        audio_clip = AudioFileClip(audio_path)
        duration = audio_clip.duration
        print(f"[VideoEngine] Video Duration: {duration:.2f} seconds")

        # 2. Setup Word timing calculations
        words_timing = self._calculate_word_timings(script_payload, duration)

        # Try to synchronize words_timing with real timestamps from .words.json if available
        words_json_path = os.path.splitext(audio_path)[0] + ".words.json"
        if os.path.exists(words_json_path):
            try:
                import json
                with open(words_json_path, "r", encoding="utf-8") as wf:
                    word_boundaries = json.load(wf)
                
                # Align words_timing (calculated) with word_boundaries (real)
                if len(words_timing) == len(word_boundaries):
                    for w_idx, wb in enumerate(word_boundaries):
                        words_timing[w_idx]["start_time"] = wb["offset_ms"] / 1000.0
                        words_timing[w_idx]["end_time"] = (wb["offset_ms"] + wb["duration_ms"]) / 1000.0
                    print(f"[VideoEngine] Successfully synchronized words_timing with {words_json_path}")
                else:
                    print(f"[VideoEngine] Timing word count ({len(words_timing)}) does not match real word count ({len(word_boundaries)}). Aligning words dynamically...")
                    wb_idx = 0
                    for wt in words_timing:
                        wt_clean = re.sub(r'[^\w]', '', wt["word"]).lower()
                        found = False
                        for j in range(wb_idx, min(wb_idx + 5, len(word_boundaries))):
                            wb_clean = re.sub(r'[^\w]', '', word_boundaries[j]["word"]).lower()
                            if wt_clean == wb_clean:
                                wb = word_boundaries[j]
                                wt["start_time"] = wb["offset_ms"] / 1000.0
                                wt["end_time"] = (wb["offset_ms"] + wb["duration_ms"]) / 1000.0
                                wb_idx = j + 1
                                found = True
                                break
                        if not found and wb_idx < len(word_boundaries):
                            wb = word_boundaries[wb_idx]
                            wt["start_time"] = wb["offset_ms"] / 1000.0
                            wt["end_time"] = (wb["offset_ms"] + wb["duration_ms"]) / 1000.0
                            wb_idx += 1
            except Exception as e:
                print(f"[VideoEngine] WARNING: Failed to sync words_timing with real timestamps: {e}")

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

        use_burn_transition = random.random() < 0.5
        burn_duration = 0.8

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

            # --- Countdown timer bar (compile_short legacy) ---
            bar_y = 8; bar_h = 4; bar_w = 960; bar_x = (1080 - bar_w) // 2
            prog_val = min(1.0, t / max(duration, 0.01))
            draw_bg.rounded_rectangle([bar_x, bar_y, bar_x + bar_w, bar_y + bar_h], radius=2, fill=(255, 255, 255, 20))
            timer_color = st.get("timer_bar_color", st["highlight_bg"])
            fe = int(bar_x + bar_w * prog_val)
            if fe > bar_x:
                draw_bg.rounded_rectangle([bar_x, bar_y, fe, bar_y + bar_h], radius=2, fill=timer_color + (100,))

            # Convert background image to NumPy array for manipulation
            fused_arr = np.array(bg_frame_img)
            
            # 2. Scrolling Scanline Drift: shift the scanlines overlay vertically based on time
            drift_base_speed = 120
            # Power surge: triple scanline drift speed for 0.5s on truth reveal (Scene 3)
            if is_last_scene and t >= delay_offset:
                surge_t = t - delay_offset
                if surge_t < 0.5:
                    drift_base_speed = 360  # 3x speed during power surge
            drift_offset = int(t * drift_base_speed) % 4
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
                    # Centered on anchor point: cx=540, cy=900 (matches 120, 480 offset of 840x840 card)
                    px = 540 - new_w // 2
                    py = 900 - new_h // 2
                    
                    # Temporarily paste using PIL
                    fused_img = Image.fromarray(fused_arr)
                    fused_img.paste(scaled_card, (px, py), scaled_card)
                    fused_arr = np.array(fused_img)

            # 5. Glitch/Burn Transition & Camera Shake (active in a 0.4s window around fact_start_time)
            if fact_start_time - 0.20 <= t <= fact_start_time + 0.20:
                if use_burn_transition:
                    # Overlay burn edge + embers instead of glitch
                    local_t = (t - (fact_start_time - 0.20)) / burn_duration
                    burn_mask = self._generate_burn_mask(1080, 1920, min(1.0, local_t), self.video_seed or 0)
                    fused_arr = (fused_arr * (1 - burn_mask[..., np.newaxis] * 0.8)).astype(np.uint8)
                else:
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

            # 6. Power Surge on Truth Reveal — CRT overload effect (Scene 3 only)
            # Apply brightness surge BEFORE subtitles so the whole frame overflows together
            if is_last_scene and t >= delay_offset:
                surge_t = t - delay_offset
                if surge_t < 0.3:
                    # Brightness decay: starts at 3.0x, decays to 1.0x over 0.25s
                    if surge_t < 0.25:
                        decay = 1.0 - surge_t / 0.25
                        brightness = 1.0 + 2.0 * decay  # 3.0 → 1.0
                    else:
                        brightness = 1.0
                    fused_arr = np.clip(fused_arr.astype(np.float32) * brightness, 0, 255).astype(np.uint8)

            # 7. Render Subtitles using PIL draw
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

        # BB. Sub-bass Heartbeat Pulse during card delay (lub-dub, ~70 BPM, 8% volume)
        heartbeat_path = os.path.join(sfx_dir, "heartbeat.mp3")
        if os.path.exists(heartbeat_path):
            try:
                heartbeat_clip = AudioFileClip(heartbeat_path)
                heartbeat_dur = heartbeat_clip.duration
                t_hb = 0.0
                while t_hb < fact_start_time - 0.1:
                    hb_instance = heartbeat_clip.set_start(t_hb)
                    hb_instance = hb_instance.multiply_volume(0.08) if hasattr(hb_instance, "multiply_volume") else hb_instance.volumex(0.08)
                    audio_clips_to_mix.append(hb_instance)
                    t_hb += heartbeat_dur
                print(f"[VideoEngine] Mixed heartbeat.mp3 pulse loop up to {fact_start_time:.2f}s")
            except Exception as e:
                print(f"[VideoEngine] WARNING: Failed to mix heartbeat SFX: {e}")

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

        # Mix background low-frequency hum layer (hum.mp3)
        hum_path = os.path.join(self.assets_dir, "sfx", "hum.mp3")
        if os.path.exists(hum_path):
            try:
                hum_clip = AudioFileClip(hum_path)
                if hasattr(hum_clip, "subclipped"):
                    hum_sub = hum_clip.subclipped(0, min(hum_clip.duration, video_clip.duration))
                else:
                    hum_sub = hum_clip.subclip(0, min(hum_clip.duration, video_clip.duration))
                hum_sub = hum_sub.multiply_volume(0.12) if hasattr(hum_sub, "multiply_volume") else hum_sub.volumex(0.12)
                audio_clips_to_mix.append(hum_sub)
                print("[VideoEngine] Mixed low-frequency hum background layer successfully")
            except Exception as hum_err:
                print(f"[VideoEngine] WARNING: Failed to mix low-frequency hum: {hum_err}")

        mixed_audio = CompositeAudioClip(audio_clips_to_mix)
        video_clip, tmp_files = self._normalize_and_attach_audio(video_clip, mixed_audio, output_name)

        codec = "h264_nvenc" if self.has_cuda else "libx264"
        threads = os.cpu_count() or 4
        print(f"[VideoEngine] Starting rendering process (codec={codec}, threads={threads})...")
        video_clip.write_videofile(
            output_video_path,
            fps=25,
            codec=codec,
            audio_codec="aac",
            threads=threads
        )
        
        video_clip.close()
        # Clean up temp files
        for f_path in tmp_files:
            if os.path.exists(f_path):
                try:
                    os.remove(f_path)
                except:
                    pass
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
        if isinstance(audio_path, list):
            hook = (script_payload.get("s1_ssml") or script_payload.get("hook_ssml") or script_payload.get("hook") or "").strip()
            why_bizarre = (script_payload.get("s2_ssml") or script_payload.get("why_bizarre_ssml") or script_payload.get("why_bizarre") or "").strip()
            closing = (script_payload.get("s3_ssml") or script_payload.get("closing_statement_ssml") or script_payload.get("closing_statement") or "").strip()
            
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

            # Build mid_roll word indices from scene 2 text
            mid_roll_hook = (script_payload.get("mid_roll_hook") or "").strip().lower()
            mid_roll_word_indices = None
            if mid_roll_hook and len(scene_texts) > 1:
                hook_words = mid_roll_hook.split()
                s2_words = scene_texts[1].split()
                mid_roll_word_indices = set()
                for hw in hook_words:
                    for i, w in enumerate(s2_words):
                        if w.lower() == hw:
                            mid_roll_word_indices.add(i)
                if not mid_roll_word_indices:
                    mid_roll_word_indices = None

            starting_text = script_payload.get("starting_text")
            ending_text = script_payload.get("ending_text")

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
                mid_roll_word_indices=mid_roll_word_indices,
                starting_text=starting_text,
                ending_text=ending_text,
                topic=script_payload.get("topic"),
                episode_num=script_payload.get("episode_num")
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
        hook = (script_payload.get("hook") or "").strip()
        story_brief = (script_payload.get("story_brief") or "").strip()
        why_bizarre = (script_payload.get("why_bizarre") or "").strip()
        closing = (script_payload.get("closing_statement") or "").strip()
        cta = (script_payload.get("cta") or "").strip()
        sign_off = (script_payload.get("sign_off") or "Class dismissed.").strip()

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
            frame_pil = Image.blend(frame_pil, dark_overlay, 0.20)
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
        video_clip.write_videofile(output_video_path, fps=25, codec=codec, audio_codec="aac", threads=threads)

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
            hook = (payload.get("hook") or "").strip()
            context = (payload.get("context") or "").strip()
            fact = (payload.get("fact") or "").strip()
            
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

    def _normalize_and_attach_audio(self, video_clip, mixed_audio, output_name: str) -> Tuple[Any, List[str]]:
        """
        Exports the composite mixed_audio to a temporary wav, performs -14 LUFS/dBFS loudness
        normalization (with a peak ceiling of -1.0 dBFS to prevent clipping) using pydub,
        and returns the updated video_clip along with a list of temporary file paths to clean up.
        """
        temp_wav = os.path.join(self.assets_dir, f"temp_{output_name}_audio_raw.wav")
        norm_wav = os.path.join(self.assets_dir, f"temp_{output_name}_audio_norm.wav")
        tmp_files = []
        
        try:
            from pydub import AudioSegment
            # Export raw mix
            mixed_audio.write_audiofile(temp_wav, fps=44100, nbytes=2, codec="pcm_s16le", logger=None)
            tmp_files.append(temp_wav)
            
            # Load and normalize
            sound = AudioSegment.from_file(temp_wav)
            change_in_dB = -14.0 - sound.dBFS
            normalized = sound.apply_gain(change_in_dB)
            if normalized.max_dBFS > -1.0:
                reduction = normalized.max_dBFS - (-1.0)
                normalized = normalized.apply_gain(-reduction)
                
            normalized.export(norm_wav, format="wav")
            tmp_files.append(norm_wav)
            
            # Load normalized back to moviepy
            norm_audio_clip = AudioFileClip(norm_wav)
            video_clip = video_clip.with_audio(norm_audio_clip)
            print(f"[VideoEngine] Loudness normalized successfully to -14 dBFS target (max peak: {normalized.max_dBFS:.2f} dBFS)")
        except Exception as err:
            print(f"[VideoEngine] WARNING: pydub loudness normalization failed ({err}). Falling back to original mixed audio.")
            video_clip = video_clip.with_audio(mixed_audio)
            
        return video_clip, tmp_files

    def _create_scanline_overlay(self, width: int, height: int, opacity: float) -> np.ndarray:
        """Generates a static horizontal CRT scanline mesh overlay matrix."""
        # 1-pixel dark line every 4 pixels
        overlay = np.zeros((height, width, 3), dtype=np.float32)
        for y in range(0, height, 4):
            overlay[y, :, :] = opacity
        return overlay

    @staticmethod
    def _render_static(size: int = 90, expression: str = "neutral") -> Image.Image:
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
        # Create a larger noise canvas, then blur and mask into a cloud shape
        noise_canvas = Image.new("L", (size, size), 0)
        noise_draw = ImageDraw.Draw(noise_canvas)

        # Scatter static points in a roughly circular area
        num_points = int(size * 5)
        for _ in range(num_points):
            # Random position within the body circle, biased toward center
            angle = rng.uniform(0, 2 * 3.14159)
            radius = rng.uniform(0, body_r * 1.1)
            # Density falloff near edges for a soft cloud shape
            if radius > body_r * 0.8:
                if rng.random() < 0.5:
                    continue
            px = cx + int(radius * math.cos(angle))
            py = cy + int(radius * math.sin(angle))
            if 0 <= px < size and 0 <= py < size:
                brightness = rng.randint(60, 255)
                noise_draw.point((px, py), fill=brightness)

        # Blur the noise into a fuzzy cloud
        from PIL import ImageFilter
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
            # Larger glowing eyes, O mouth
            draw_glow_eye(cx - eye_spacing, eye_y, int(eye_r * 1.4))
            draw_glow_eye(cx + eye_spacing, eye_y, int(eye_r * 1.4))
            # O mouth
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
            # Closed happy eyes (arcs)
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
            # Big wide smile
            draw_mouth_glow(0, 180, int(size * 0.10), int(size * 0.06))

        elif expression == "wink":
            # Left eye open with glow, right eye winking
            draw_glow_eye(cx - eye_spacing, eye_y, eye_r)
            draw_eye_line(cx + eye_spacing, eye_y, int(size * 0.08))
            # Smirk
            draw_mouth_glow(0, 160, int(size * 0.07), int(size * 0.05))

        else:  # neutral (default)
            # Small glowing dot eyes
            draw_glow_eye(cx - eye_spacing, eye_y, eye_r)
            draw_glow_eye(cx + eye_spacing, eye_y, eye_r)
            # Small smile arc
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
        
        # Build lines of words that fit within max width (800px)
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
                
                # Draw highlighter box or text with Kinetic scale & rotate animations
                if is_active:
                    is_mid_roll = w.get("is_mid_roll", False)
                    is_emp = w.get("is_emphasized", False)
                    box_padding_x = 10
                    box_padding_y = int(font_px_height * 0.12)
                    canvas_w = int(word_width) + 2 * box_padding_x
                    canvas_h = font_px_height + 2 * box_padding_y

                    # Mid_roll active word: use highlight_bg as fill, pulse to 1.1x
                    if is_mid_roll:
                        pulse_scale = 1.0 + 0.10 * math.sin((t - w["start_time"]) * 8.0)
                        canvas_w = int(canvas_w * pulse_scale)
                        canvas_h = int(canvas_h * pulse_scale)
                    else:
                        pulse_scale = 1.0
                    
                    # Create temporary RGBA canvas for the active word highlight
                    word_canvas = Image.new("RGBA", (canvas_w, canvas_h), (0, 0, 0, 0))
                    word_draw = ImageDraw.Draw(word_canvas)
                    
                    # Draw highlight background pill: if emphasized, use outline color with white text
                    pill_fill = style.get("card_myth_outline", (255, 75, 75)) + (255,) if is_emp else style["highlight_bg"] + (255,)
                    text_fill = (255, 255, 255, 255) if is_emp else style["highlight_text"] + (255,)
                    
                    word_draw.rounded_rectangle(
                        [0, 0, canvas_w, canvas_h],
                        radius=10,
                        fill=pill_fill
                    )
                    # Draw word text
                    word_draw.text((box_padding_x, box_padding_y), word_str, fill=text_fill, font=font)
                    
                    # Calculate progress of word active duration
                    word_dur = max(0.01, w["end_time"] - w["start_time"])
                    progress = min(1.0, max(0.0, (t - w["start_time"]) / word_dur))
                    
                    # Apply elastic bounce scale and slight rotation angle sweep
                    pulse_scale = 1.0 + 0.12 * math.sin(progress * math.pi)
                    if is_emp:
                        pulse_scale *= 1.2
                    angle = -2.0 + 4.0 * progress
                    
                    new_w = int(canvas_w * pulse_scale)
                    new_h = int(canvas_h * pulse_scale)
                    
                    if new_w > 5 and new_h > 5:
                        word_canvas = word_canvas.resize((new_w, new_h), Image.Resampling.BILINEAR)
                        word_canvas = word_canvas.rotate(angle, expand=True, resample=Image.Resampling.BICUBIC)
                        
                        orig_center_x = current_x + word_width / 2
                        orig_center_y = y_pos + font_px_height / 2
                        rot_w, rot_h = word_canvas.size
                        paste_x = int(orig_center_x - rot_w / 2)
                        paste_y = int(orig_center_y - rot_h / 2)
                        
                        # Paste onto main PIL Image
                        if hasattr(draw, "_image"):
                            draw._image.paste(word_canvas, (paste_x, paste_y), word_canvas)
                        else:
                            draw.text((current_x, y_pos), word_str, fill=text_fill, font=font)
                    else:
                        draw.text((current_x, y_pos), word_str, fill=text_fill, font=font)
                else:
                    is_mid_roll = w.get("is_mid_roll", False)
                    is_emp = w.get("is_emphasized", False)
                    shadow_color = (0, 0, 0)
                    shadow_offset = 3

                    # Inactive mid_roll word: red tint foreshadowing
                    if is_mid_roll and not is_active:
                        mid_tint = style["watermark_color"] + (77,)  # 30% opacity
                        draw.text((current_x + shadow_offset, y_pos + shadow_offset), word_str, fill=shadow_color, font=font)
                        draw.text((current_x, y_pos), word_str, fill=mid_tint, font=font)
                        # Underline for mid_roll words
                        draw.line([(current_x, y_pos + font_px_height + 2),
                                   (current_x + word_width, y_pos + font_px_height + 2)],
                                  fill=style["watermark_color"] + (180,), width=2)
                    elif is_emp:
                        # Inactive emphasized words: render in style["highlight_bg"] instead of standard white style["subtitle_color"]
                        draw.text((current_x + shadow_offset, y_pos + shadow_offset), word_str, fill=shadow_color, font=font)
                        draw.text((current_x, y_pos), word_str, fill=style["highlight_bg"] + (255,), font=font)
                    else:
                        draw.text((current_x + shadow_offset, y_pos + shadow_offset), word_str, fill=shadow_color, font=font)
                        draw.text((current_x, y_pos), word_str, fill=style["subtitle_color"] + (255,), font=font)

                # Active mid_roll word: extra emphasis (handled in active block)
                if is_active and w.get("is_mid_roll", False):
                    # Draw underline beneath the active word
                    draw.line([(current_x, y_pos + font_px_height + 4),
                               (current_x + word_width, y_pos + font_px_height + 4)],
                              fill=style["watermark_color"] + (220,), width=3)
                
                # Advance pointer
                current_x += word_width + space_width
                
            # Move to next line's y coordinate
            y_pos += line_height

    def generate_thumbnail(self, topic: str, hook: str, output_name: str, style: str = "blueprint", img_myth_path: str = None, img_truth_path: str = None, bizarre_mode: bool = False, episode_num: Optional[int] = None) -> str:
        """Generates a thumbnail using actual video images. Supports myth/truth diagonal, bizarre anomaly, and fallback blueprint."""
        from thumbnail_generator import ThumbnailDesigner
        title = hook if hook else topic

        if bizarre_mode:
            img_path = img_myth_path or img_truth_path
            hd = ThumbnailDesigner(width=1280, height=720)
            thumb = hd.generate_bizarre_thumbnail(bg_image_path=img_path, title_text=title, topic_label=topic, episode_num=episode_num)
            out_path = os.path.join(self.assets_dir, f"{output_name}_thumb.png")
            thumb.save(out_path, "PNG", optimize=True)
            print(f"[VideoEngine] Bizarre thumbnail (16:9) saved: {out_path}")
            short = ThumbnailDesigner(width=1080, height=1920)
            thumb_short = short.generate_bizarre_thumbnail(bg_image_path=img_path, title_text=title, topic_label=topic, episode_num=episode_num)
            short_out = os.path.join(self.assets_dir, f"{output_name}_thumb_shorts.png")
            thumb_short.save(short_out, "PNG", optimize=True)
            print(f"[VideoEngine] Bizarre thumbnail (9:16) saved: {short_out}")
            return out_path

        if img_myth_path and img_truth_path and os.path.exists(img_myth_path) and os.path.exists(img_truth_path):
            hd = ThumbnailDesigner(width=1280, height=720)
            thumb = hd.generate_from_images(img_myth_path, img_truth_path, title_text=title, topic_label=topic, episode_num=episode_num)
            out_path = os.path.join(self.assets_dir, f"{output_name}_thumb.png")
            thumb.save(out_path, "PNG", optimize=True)
            print(f"[VideoEngine] Diagonal myth/truth thumbnail (16:9) saved: {out_path}")
            short = ThumbnailDesigner(width=1080, height=1920)
            thumb_short = short.generate_from_images(img_myth_path, img_truth_path, title_text=title, topic_label=topic, episode_num=episode_num)
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
    def _generate_card(self, image_path: str, label_text: str, status_text: str, is_truth: bool, style_dict: dict, topic: str = "", add_redactions: bool = False, card_text: str = "") -> Optional[Image.Image]:
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
            try:
                header_font = ImageFont.truetype(self.font_path, 28)
            except Exception:
                header_font = ImageFont.load_default()
                
            draw_card.text((34, 30), label_text.upper(), fill=outline_color + (255,), font=header_font)
            # Subtle header underline (thinner, faded)
            header_underline_y = 64
            header_text_w = draw_card.textlength(label_text.upper(), font=header_font) if hasattr(draw_card, 'textlength') else 300
            draw_card.line([(34, header_underline_y), (34 + int(header_text_w) + 10, header_underline_y)], fill=outline_color + (60,), width=1)
            
            # ── Fixed image dimensions ──
            img_w, img_h = 762, 550
            inner_img = square_img.resize((img_w, img_h), Image.Resampling.LANCZOS)
            
            # Create rounded corner mask for the inner image
            mask = Image.new("L", (img_w, img_h), 0)
            draw_mask = ImageDraw.Draw(mask)
            draw_mask.rounded_rectangle([0, 0, img_w, img_h], radius=12, fill=255)
            
            # ═══════════════════════════════════════════════════════════════
            # Card text area — shows extended script content below the image
            # ───────────────────────────────────────────────────────────────
            text_area_lines = []
            text_font_size = 18
            text_max_w = 730
            text_line_h = 26
            text_pad_top = 10   # gap after image border
            text_pad_bot = 8    # gap before topic separator
            if card_text:
                try:
                    ct_font = ImageFont.truetype(self.font_path, text_font_size)
                except Exception:
                    ct_font = ImageFont.load_default()
                # Wrap card_text into lines
                raw_words = card_text.split()
                curr_line_words = []
                for w in raw_words:
                    test_line = " ".join(curr_line_words + [w])
                    tw = draw_card.textlength(test_line, font=ct_font) if hasattr(draw_card, 'textlength') else len(test_line) * text_font_size * 0.6
                    if tw <= text_max_w:
                        curr_line_words.append(w)
                    else:
                        if curr_line_words:
                            text_area_lines.append(" ".join(curr_line_words))
                        curr_line_words = [w]
                if curr_line_words:
                    text_area_lines.append(" ".join(curr_line_words))
                # Allow up to 8 lines — no "...", let text flow naturally
                if len(text_area_lines) > 8:
                    text_area_lines = text_area_lines[:8]
            text_area_h = len(text_area_lines) * text_line_h
            extra_h = text_area_h + text_pad_top + text_pad_bot

            # Move existing bottom elements down by extra_h
            topic_sep_y = 648 + extra_h
            topic_y = 658 + extra_h
            status_y = 708 + extra_h
            sep_y = 750 + extra_h
            footer_y = 770 + extra_h

            # Extend card canvas and redraw card outline / shadow with new height
            new_canvas_h = 890 + extra_h
            # Recreate card canvas at new height
            card_canvas = Image.new("RGBA", (canvas_w, new_canvas_h), (0, 0, 0, 0))
            draw_card = ImageDraw.Draw(card_canvas)

            # Redraw card background / shadow at new height
            draw_card.rounded_rectangle([18, 18, 822, new_canvas_h - 18], radius=16, fill=(5, 10, 20, 200))
            draw_card.rounded_rectangle([22, 22, 818, new_canvas_h - 22], radius=14, fill=(10, 12, 25, 100))
            draw_card.rounded_rectangle([10, 10, 810, new_canvas_h - 10], radius=16, fill=style_dict["card_bg"] + (255,), outline=outline_color + (255,), width=4)
            draw_card.rectangle([14, 25, 20, new_canvas_h - 25], fill=outline_color + (255,))

            # Re-render header, image, and image border
            draw_card.text((34, 30), label_text.upper(), fill=outline_color + (255,), font=header_font)
            header_text_w = draw_card.textlength(label_text.upper(), font=header_font) if hasattr(draw_card, 'textlength') else 300
            draw_card.line([(34, header_underline_y), (34 + int(header_text_w) + 10, header_underline_y)], fill=outline_color + (60,), width=1)
            card_canvas.paste(inner_img, (34, 78), mask=mask)
            draw_card.rounded_rectangle([34, 78, 34 + img_w, 78 + img_h], radius=12, outline=outline_color + (50,), width=1)
            draw_card.rounded_rectangle([36, 80, 34 + img_w - 2, 78 + img_h - 2], radius=10, outline=(255, 255, 255, 25), width=1)

            # Render card text lines
            if text_area_lines and ct_font:
                text_start_y = 78 + img_h + text_pad_top  # below image
                for li, line in enumerate(text_area_lines):
                    ly = text_start_y + li * text_line_h
                    draw_card.text((34, ly), line, fill=(200, 210, 230, 230), font=ct_font)

            # Topic text with separator line above
            try:
                topic_font = ImageFont.truetype(self.font_path, 32)
                display_topic = (topic or label_text).upper()
                if len(display_topic) > 34:
                    display_topic = display_topic[:31] + "..."
                draw_card.line([(34, topic_sep_y), (796, topic_sep_y)], fill=(255, 255, 255, 25), width=1)
                draw_card.text((34, topic_y), display_topic, fill=(255, 255, 255, 240), font=topic_font)
            except Exception:
                pass

            # Status dot & label
            is_debunked = ("DEBUNKED" in status_text.upper() or "ANOMALOUS" in status_text.upper())
            dot_color = (255, 60, 60) if is_debunked else (0, 242, 254)
            glow_radius = 12
            dot_cx, dot_cy = 40, status_y + 12
            draw_card.ellipse([dot_cx - glow_radius, dot_cy - glow_radius, dot_cx + glow_radius, dot_cy + glow_radius], fill=dot_color + (40,))
            draw_card.ellipse([34, status_y + 6, 46, status_y + 18], fill=dot_color + (255,))
            try:
                status_font = ImageFont.truetype(self.font_path, 20)
                draw_card.text((56, status_y), status_text.upper(), fill=outline_color + (255,), font=status_font)
            except Exception:
                pass

            # Dashed/Subtle separator
            for dash_x in range(34, 796, 20):
                draw_card.line([(dash_x, sep_y), (min(dash_x + 10, 796), sep_y)], fill=(255, 255, 255, 30), width=1)

            # Footer metadata with subtle background pill
            case_num = f"CASE #{abs(hash(topic or label_text)) % 9999:04d}"
            try:
                footer_font = ImageFont.truetype(self.font_path, 18)
                footer_text = f"{case_num}  |  THE DAILY AUDIT"
                fw = int(draw_card.textlength(footer_text, font=footer_font)) if hasattr(draw_card, 'textlength') else 0
                pill_pad = 12
                pill_x1 = 34 - 4
                pill_y1 = footer_y - 4
                pill_x2 = 34 + fw + pill_pad + 4
                pill_y2 = footer_y + 24 + 4
                draw_card.rounded_rectangle([pill_x1, pill_y1, pill_x2, pill_y2], radius=6, fill=(255, 255, 255, 12))
                draw_card.text((34, footer_y), footer_text, fill=(255, 255, 255, 100), font=footer_font)
            except Exception:
                pass

            # ── Old duplicate block below has been removed ──
            # Card outline/shadow/header/image/card-text/topic/status/separator/footer
            # are all rendered in the dynamic-height section above.
            
            # Redaction bars for Scene 1 — curiosity gap (black bars with [REDACTED] stamps over the image)
            if add_redactions:
                import hashlib
                seed_str = (topic or label_text or str(style_dict.get("myth_label", "")))
                rng_seed = int(hashlib.md5(seed_str.encode()).hexdigest(), 16) % 999999
                rng = random.Random(rng_seed)
                
                # Cover ~30% of the image area with 2-3 bars in random positions
                num_bars = rng.randint(2, 3)
                redaction_draw = ImageDraw.Draw(card_canvas)
                
                # Bar spans horizontally across the image inset: x range 34 to 796 (w=762)
                bar_left = 34
                bar_right = 796
                bar_width = bar_right - bar_left
                
                # Image area runs from y=85 to y=625 (540px height)
                img_top = 85
                img_bottom = 85 + 540
                img_height = 540
                
                used_regions = []  # track y ranges to avoid overlaps
                
                for b in range(num_bars):
                    bar_height = rng.randint(35, 75)
                    # Find a gap that doesn't overlap previous bars
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
                    try:
                        red_font = ImageFont.truetype(self.font_path, max(14, bar_height // 3))
                        rt_w = int(draw_card.textlength(redacted_text, font=red_font)) if hasattr(draw_card, 'textlength') else 0
                        red_x = (bar_left + bar_right - rt_w) // 2 if rt_w else bar_left + 30
                        red_y = bar_y + (bar_height - max(14, bar_height // 3)) // 2
                        redaction_draw.text((red_x, red_y), redacted_text, fill=(180, 40, 40, 200), font=red_font)
                    except Exception:
                        pass
                
                print(f"[VideoEngine] Applied {num_bars} redaction bar(s) to card (seed={rng_seed})")

            return card_canvas
        except Exception as e:
            print(f"[VideoEngine] WARNING: Failed to generate forensic card for {image_path}: {e}")
            return None

    def _parse_srt_file(self, srt_path: str) -> list:
        if not os.path.exists(srt_path):
            return []
        import re
        try:
            with open(srt_path, "r", encoding="utf-8") as f:
                content = f.read()
            blocks = []
            entries = re.split(r'\n\s*\n', content.strip())
            for entry in entries:
                lines = [l.strip() for l in entry.strip().split('\n') if l.strip()]
                if len(lines) >= 3:
                    times = lines[1]
                    text = "\n".join(lines[2:])
                    match = re.match(r'(\d+):(\d+):(\d+),(\d+)\s*-->\s*(\d+):(\d+):(\d+),(\d+)', times)
                    if match:
                        h1, m1, s1, ms1, h2, m2, s2, ms2 = map(int, match.groups())
                        start_ms = ((h1 * 3600 + m1 * 60 + s1) * 1000) + ms1
                        end_ms = ((h2 * 3600 + m2 * 60 + s2) * 1000) + ms2
                        blocks.append({
                            "start_ms": start_ms,
                            "end_ms": end_ms,
                            "text": text
                        })
            return blocks
        except Exception as e:
            print(f"[VideoEngine] Error parsing SRT file {srt_path}: {e}")
            return []

    def _render_srt_subtitle_block(self, draw: ImageDraw.Draw, font: ImageFont.FreeTypeFont, text: str, y_pos: int = 1310):
        # Wrap words to fit within max width (960px)
        max_width = 960
        wrapped_lines = []
        
        # Split by existing newlines first
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
            # 3px offset drop shadow (darker for readability)
            draw.text((x + 3, y + 3), line, fill=(0, 0, 0, 120), font=font)
            # 2px black stroke, white text
            draw.text((x, y), line, fill=(255, 255, 255), font=font, stroke_width=2, stroke_fill=(0, 0, 0))

    def _render_kinetic_srt_block(self, draw: ImageDraw.Draw, font: ImageFont.FreeTypeFont,
                                  block_text: str, t_audio_ms: float,
                                  word_boundaries: list, y_pos: int = 1540,
                                  style: dict = None, block_start_ms: Optional[float] = None):
        """
        Renders an SRT subtitle block with word-level kinetic highlighting.
        Uses real word-level timestamps (from .words.json) to highlight the
        currently spoken word with a yellow background pill.
        Emphasis words are rendered at 130% font size with accent color bg.
        """
        if style is None:
            style = STYLE_PRESETS["blueprint"]
        highlight_bg = style.get("highlight_bg", (255, 242, 0))
        accent_color = style.get("card_myth_outline", (255, 75, 75))
        
        # Split block text into individual words
        block_words = block_text.split()
        
        # Find which word in the block is currently spoken, based on word boundary timestamps
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
        
        # Wrap words to fit within max width (800px)
        max_width = 800
        wrapped_line_words = []  # list of lists, each sublist is (word_text, is_active, is_emphasis_pos)
        current_line = []
        current_width = 0.0
        space_width = draw.textlength(" ", font=font)
        
        # For emphasis detection: mark words that should be emphasized
        # Emphasis words are typically short (3-8 chars) key words — we mark every Nth word
        # as a potential emphasis word based on position in the block
        emphasis_indices = set()
        if len(block_words) >= 4:
            # Mark roughly every 5th word as emphasis (matches SSML emphasis patterns)
            for ei in range(3, len(block_words), 5):
                emphasis_indices.add(ei)
            # Always emphasize the last word (strong reveal position)
            emphasis_indices.add(len(block_words) - 1)
        
        # Use large font for emphasis words
        try:
            emphasis_font = ImageFont.truetype(self.font_path, 68)
        except Exception:
            emphasis_font = font
        
        for word_idx, word in enumerate(block_words):
            # Determine if this word matches the active boundary
            is_active = (word_idx == active_word_index_in_block)
            is_emphasis = (word_idx in emphasis_indices)
            
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
        
        # SAFETY: cap at max 3 lines to prevent overflow past frame bottom (1920px)
        if len(wrapped_line_words) > 3:
            wrapped_line_words = wrapped_line_words[:3]
        
        line_height = 80  # taller to accommodate 68px emphasis font
        y_cursor = y_pos
        
        for line_idx, line_words in enumerate(wrapped_line_words):
            # Safety check: skip rendering if this line would go past frame bottom
            if y_cursor + line_height + 10 > 1920:
                break
            # Calculate total line width
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
                        radius=6, fill=highlight_bg + (255,)
                    )
                    # Active word text color: dark text on yellow bg
                    draw.text((x_cursor, y_cursor), w_text, fill=(10, 15, 30), font=w_font)
                elif w_emphasis:
                    # Emphasis word: accent color with subtle glow
                    draw.text((x_cursor + 3, y_cursor + 3), w_text, fill=(0, 0, 0, 80), font=w_font)
                    draw.text((x_cursor, y_cursor), w_text, fill=accent_color + (255,), font=w_font)
                else:
                    # Normal word: white with 2px black stroke + drop shadow for readability
                    draw.text((x_cursor + 3, y_cursor + 3), w_text, fill=(0, 0, 0, 100), font=w_font)
                    draw.text((x_cursor, y_cursor), w_text, fill=(255, 255, 255), font=w_font, stroke_width=2, stroke_fill=(0, 0, 0))
                
                x_cursor += int(w_width) + int(space_width)
            
            y_cursor += line_height

    # ── Sprint B: Emotion Beat Generator ─────────────────────────────────

    def _generate_emotion_beats(self, text: str, scene_idx: int, audio_duration: float, delay_offset: float) -> list:
        """Scan scene script text for emotion keywords and return list of (timestamp, expression, duration).
        These drive Static's reactive expressions at precise moments."""
        if not text:
            return []
        lower = text.lower()
        beats = []
        if scene_idx == 0:
            beats.append((delay_offset + audio_duration * 0.15, "neutral", 0.8))
            shock_words = ["shocking", "you won't believe", "crazy", "insane", "wrong", "lie",
                           "fake", "myth", "never happened", "debunked"]
            if any(w in lower for w in shock_words):
                beats.append((delay_offset + audio_duration * 0.45, "shocked", 1.0))
        elif scene_idx == 1:
            tension_words = ["but", "here's the thing", "actually", "surprising",
                             "get this", "the kicker", "it gets", "wait"]
            if any(w in lower for w in tension_words):
                beats.append((delay_offset + audio_duration * 0.3, "shocked", 0.9))
            beats.append((delay_offset + audio_duration * 0.7, "neutral", 0.6))
        elif scene_idx >= 2:
            beats.append((delay_offset + audio_duration * 0.1, "wink", 0.7))
            happy_words = ["truth", "revealed", "fact", "actually", "proven",
                           "real", "evidence", "case closed", "debunked"]
            if any(w in lower for w in happy_words):
                beats.append((delay_offset + audio_duration * 0.4, "happy", 1.2))
        return beats

    def _redact_text(self, text: str, redact_ratio: float = 0.4) -> str:
        """Redact key words from text to build mystery. Replaces ~40% of words with black bars.
        Preserves first 2-3 words for context, redacts from the middle, keeps last word.
        Skip redaction if text is too short."""
        import random, re
        words = text.split()
        if len(words) < 6:
            return text  # too short to redact meaningfully
        rng = random.Random(hash(text) % 10000)  # deterministic per text
        # Always keep first 2 and last 1 words visible
        keep_first = min(3, len(words) // 3)
        keep_last = 1
        middle_start = keep_first
        middle_end = len(words) - keep_last
        middle_words = list(range(middle_start, middle_end))
        num_to_redact = max(1, int(len(middle_words) * redact_ratio))
        redact_indices = set(rng.sample(middle_words, min(num_to_redact, len(middle_words))))
        result_words = []
        for i, w in enumerate(words):
            if i in redact_indices:
                bar_len = max(3, len(w))
                result_words.append("\u2588" * bar_len)  # █ full block
            else:
                result_words.append(w)
        return " ".join(result_words)

    # ── Sprint B: File Stamp Renderer ────────────────────────────────────

    def _render_stamp(self, stamp_text: str, scene_idx: int, t: float, delay_offset: float) -> Optional[Image.Image]:
        """Render a 'File Stamp' overlay. Returns RGBA PIL Image or None if outside stamp window."""
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

        slam_progress = min(1.0, stamp_t / 0.15)
        if slam_progress < 1.0:
            scale = 1.0 + 2.0 * (1.0 - slam_progress) * math.cos(slam_progress * math.pi * 2)
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
        sd.rounded_rectangle([4, 4, scaled_w - 4, scaled_h - 4], radius=16,
                             fill=stamp_color + (220,), outline=(255, 255, 255, 200), width=4)
        sd.rounded_rectangle([10, 10, scaled_w - 10, scaled_h - 10], radius=12,
                             fill=None, outline=(255, 255, 255, 80), width=1)
        try:
            stamp_font = ImageFont.truetype(self.font_path, int(min(scaled_w, scaled_h) * 0.22))
        except Exception:
            stamp_font = ImageFont.load_default()
        tw = sd.textlength(stamp_text, font=stamp_font)
        tx = (scaled_w - int(tw)) // 2
        ty = (scaled_h - int(min(scaled_w, scaled_h) * 0.25)) // 2
        sd.text((tx, ty), stamp_text, fill=(255, 255, 255, 240), font=stamp_font)
        canvas.paste(stamp_frame, (sx, sy), stamp_frame)
        return canvas

    # ── Sprint B: Category Themed Backgrounds ────────────────────────────

    CATEGORY_THEMES = {
        "biology": {"tint": (20, 100, 30), "strength": 0.08, "pattern": "cells"},
        "history": {"tint": (80, 60, 20), "strength": 0.12, "pattern": "paper"},
        "astronomy": {"tint": (20, 10, 80), "strength": 0.10, "pattern": "stars"},
        "physics": {"tint": (10, 30, 80), "strength": 0.10, "pattern": "grid"},
        "neuroscience": {"tint": (60, 20, 60), "strength": 0.08, "pattern": "waves"},
        "psychology": {"tint": (60, 30, 50), "strength": 0.08, "pattern": "waves"},
        "technology": {"tint": (10, 60, 70), "strength": 0.10, "pattern": "grid"},
        "geology": {"tint": (50, 40, 10), "strength": 0.10, "pattern": "dots"},
        "chemistry": {"tint": (30, 50, 20), "strength": 0.08, "pattern": "dots"},
        "economics": {"tint": (40, 40, 60), "strength": 0.06, "pattern": "lines"},
        "linguistics": {"tint": (40, 20, 50), "strength": 0.06, "pattern": "lines"},
        "anthropology": {"tint": (60, 40, 20), "strength": 0.08, "pattern": "dots"},
    }

    def _apply_category_overlay(self, frame: np.ndarray, category: str, t: float) -> np.ndarray:
        """Apply a subtle category-themed tint and pattern overlay to the frame."""
        if not category:
            return frame
        cat_lower = category.lower().strip()
        theme = None
        for key, val in self.CATEGORY_THEMES.items():
            if key in cat_lower or cat_lower in key:
                theme = val
                break
        if theme is None:
            return frame

        # Apply subtle tint
        tint_arr = np.array(theme["tint"], dtype=np.float32).reshape(1, 1, 3)
        frame_f = frame.astype(np.float32)
        frame_f = frame_f * (1.0 - theme["strength"]) + tint_arr * theme["strength"]
        result = np.clip(frame_f, 0, 255).astype(np.uint8)
        return result

    # ── Color Temperature Tint ─────────────────────────────────────────────

    def _create_color_tint(self, size: tuple, duration: float, warm: bool = True):
        """
        Creates a semi-transparent color temperature overlay.
        warm=True: amber/orange tint (~2800K) for explanation/mechanism scenes
        warm=False: cool blue tint (~7000K) for truth/reveal scenes
        Returns a MoviePy ImageClip that can be composited over a scene.
        """
        import tempfile, os
        from PIL import Image, ImageDraw
        try:
            from moviepy.editor import ImageClip
        except ImportError:
            from moviepy import ImageClip

        w, h = size
        if warm:
            # Amber/orange glow — warmth, trust, "let me explain"
            color = (255, 160, 40, 30)  # RGBA: warm amber, ~12% opacity
        else:
            # Cool blue cast — cold, clinical, "here's the harsh truth"
            color = (40, 120, 255, 35)  # RGBA: icy blue, ~14% opacity

        img = Image.new("RGBA", (w, h), color)
        # MoviePy v2 ImageClip requires a file path, not a PIL Image
        tint_tmp = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
        img.save(tint_tmp.name)
        tint_tmp.close()
        clip = ImageClip(tint_tmp.name).with_duration(duration)
        # Schedule cleanup after clip is no longer needed
        try:
            clip._cleanup_tint_path = tint_tmp.name
        except Exception:
            pass
        return clip

    def _create_color_tint_animated(self, size: tuple, duration: float, warm: bool = False, fade_duration: float = 1.5):
        """
        Creates a color temperature overlay that FADES IN over fade_duration seconds.
        warm=True: amber/orange tint (~2800K) for explanation/mechanism scenes
        warm=False: cool blue tint (~7000K) for truth/reveal scenes — fades in for dramatic effect
        The alpha starts at 0 and linearly increases to max over fade_duration.
        Returns a MoviePy VideoClip that can be composited over a scene.
        """
        import numpy as np
        try:
            from moviepy import VideoClip
        except ImportError:
            from moviepy.editor import VideoClip

        w, h = size
        if warm:
            r, g, b, max_alpha = 255, 160, 40, 30  # warm amber ~12%
        else:
            r, g, b, max_alpha = 40, 120, 255, 35  # cold blue ~14%

        def make_frame(t):
            if t < fade_duration:
                alpha = int(max_alpha * (t / fade_duration))
            else:
                alpha = max_alpha
            return np.full((h, w, 4), [r, g, b, alpha], dtype=np.uint8)

        clip = VideoClip(make_frame, duration=duration)
        return clip

    def _create_scene_clip(self, bg_source: Any, card_images: List[Image.Image], audio_duration: float, text: str, delay_offset: float, y_pos: int, scene_idx: int, scene_label: str, scene_title: str, style_dict: dict, audio_clip: Optional[Any] = None, mid_roll_word_indices: Optional[set] = None, is_last_scene: bool = False, audio_path: Optional[str] = None,
                            emotion_beats: Optional[list] = None, stamp_text: Optional[str] = None,
                            category: str = "") -> 'VideoClip':
        """
        Creates a single scene clip with CRT effects, cards, subtitles, and mascot.
        card_images: list of pre-rendered card PIL images. If >1, they rotate every 5-7s with crossfade.
        emotion_beats: list of (timestamp, expression_str, duration_s) for Static reactions (Sprint B)
        stamp_text: if set, renders a File Stamp at truth reveal with this text
        category: topic category for themed background overlays (Sprint B)
        """
        try:
            from moviepy.editor import VideoClip, VideoFileClip
        except ImportError:
            from moviepy import VideoClip, VideoFileClip

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
        font_size = 52
        try:
            sub_font = ImageFont.truetype(self.font_path, font_size)
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
                wm_font = ImageFont.truetype(self.font_path, 36)
            except Exception:
                wm_font = ImageFont.load_default()
            stamp_txt = "CLASSIFIED"
            sw = draw_wm.textlength(stamp_txt, font=wm_font)
            sh = 56
            stamp_canvas = Image.new("RGBA", (int(sw) + 24, sh), (0, 0, 0, 0))
            draw_stamp = ImageDraw.Draw(stamp_canvas)
            draw_stamp.rectangle([3, 3, sw + 21, sh - 3], outline=style_dict["watermark_color"] + (80,), width=2)
            draw_stamp.text((12, 10), stamp_txt, fill=style_dict["watermark_color"] + (80,), font=wm_font)
            rotated_stamp = stamp_canvas.rotate(15, expand=True, resample=Image.Resampling.BICUBIC)

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

        # Load SRT blocks
        srt_blocks = []
        word_boundaries = []
        if audio_path and os.path.exists(audio_path):
            srt_path = os.path.splitext(audio_path)[0] + ".srt"
            if os.path.exists(srt_path):
                srt_blocks = self._parse_srt_file(srt_path)
                # Load word-level timestamps for kinetic highlighting
                words_json_path = os.path.splitext(audio_path)[0] + ".words.json"
                if os.path.exists(words_json_path):
                    try:
                        import json
                        with open(words_json_path, "r", encoding="utf-8") as wf:
                            word_boundaries = json.load(wf)
                    except Exception as e:
                        print(f"[VideoEngine] WARNING: Failed to load word boundaries: {e}")
                
        # Fallback if no SRT file exists
        if not srt_blocks:
            words_info = self._parse_ssml_words_emphasis(text)
            if words_info and audio_duration > 0:
                total_chars = sum(len(w_info["word"]) for w_info in words_info)
                sec_per_char = audio_duration / total_chars if total_chars > 0 else 0.1
                current_time = 0.0
                scene_word_timings = []
                for w_idx, w_info in enumerate(words_info):
                    w_str = w_info["word"]
                    w_dur = len(w_str) * sec_per_char
                    scene_word_timings.append({
                        "word": w_str,
                        "offset_ms": current_time * 1000.0,
                        "duration_ms": w_dur * 1000.0
                    })
                    current_time += w_dur
                
                try:
                    from tts.subtitle_builder import SubtitleBuilder
                    srt_blocks = SubtitleBuilder.group_words_into_subtitles(scene_word_timings)
                except Exception as e:
                    print(f"[VideoEngine] SubtitleBuilder import failed: {e}")

        # ── PERFORMANCE: Background+parallax composite cache ──
        # The parallax zoom, blur, and layer blend only change gradually over time.
        # Cache at 0.3s intervals for ~90% reduction in per-frame background work.
        _bg_cache = {}
        _BG_CACHE_STEP = 0.3  # seconds between cache points
        _bg_is_static = (raw_img_pil is not None) or (base_arr is not None)

        def _compute_parallax_bg(t_val, is_last_scene, total_dur, delay_off, scene_idx, category):
            cache_key = round(t_val / _BG_CACHE_STEP) * _BG_CACHE_STEP
            if cache_key in _bg_cache:
                return _bg_cache[cache_key].copy()

            # Scene-specific background parameters
            if scene_idx == 0:
                base_blur, darken_f = 6.0, 0.30
            elif scene_idx == 1:
                base_blur, darken_f = 8.0, 0.35
            else:
                base_blur, darken_f = 4.0, 0.25

            if total_dur > 6.0 and cache_key > 5.0:
                blur_r = max(0.0, base_blur - base_blur * (cache_key - 5.0))
            else:
                blur_r = base_blur

            if raw_img_pil is not None:
                img_to_process = np.array(raw_img_pil)
                processed_bg = self._process_bg_frame(img_to_process, blur_radius=blur_r, darken_factor=darken_f)
            elif base_arr is not None:
                processed_bg = base_arr.copy()
            else:
                processed_bg = np.zeros((1920, 1080, 3), dtype=np.uint8)

            if scene_idx == 1:
                processed_bg = processed_bg.astype(np.int16)
                processed_bg[:, :, 2] = np.clip(processed_bg[:, :, 2] + 15, 0, 255)
                processed_bg = processed_bg.astype(np.uint8)
            elif scene_idx >= 2:
                processed_bg = processed_bg.astype(np.int16)
                processed_bg[:, :, 0] = np.clip(processed_bg[:, :, 0] + 20, 0, 255)
                processed_bg[:, :, 1] = np.clip(processed_bg[:, :, 1] + 10, 0, 255)
                processed_bg = processed_bg.astype(np.uint8)

            mid_zoom = 1.0 + 0.12 * (cache_key / total_dur)
            deep_zoom = 1.0 + 0.05 * (cache_key / total_dur)
            if is_last_scene and cache_key >= delay_off:
                t_audio = cache_key - delay_off
                if t_audio < 0.5:
                    extra_zoom = 0.15 * math.sin((t_audio / 0.5) * math.pi)
                    mid_zoom += extra_zoom
                    deep_zoom += extra_zoom * 0.4

            h, w, c = processed_bg.shape
            mid_new_h, mid_new_w = int(h / mid_zoom), int(w / mid_zoom)
            mid_top = (h - mid_new_h) // 2
            mid_left = (w - mid_new_w) // 2
            mid_crop = processed_bg[mid_top:mid_top+mid_new_h, mid_left:mid_left+mid_new_w]
            mid_layer = np.array(Image.fromarray(mid_crop).resize((w, h), Image.Resampling.BILINEAR))

            deep_new_h, deep_new_w = int(h / deep_zoom), int(w / deep_zoom)
            deep_top = (h - deep_new_h) // 2
            deep_left = (w - deep_new_w) // 2
            deep_crop = processed_bg[deep_top:deep_top+deep_new_h, deep_left:deep_left+deep_new_w]
            deep_layer_arr = np.array(Image.fromarray(deep_crop).resize((w, h), Image.Resampling.BILINEAR))
            deep_pil = Image.fromarray(deep_layer_arr).filter(ImageFilter.GaussianBlur(radius=3))
            deep_layer = np.clip(np.array(deep_pil).astype(np.float32) * 0.7, 0, 255).astype(np.uint8)

            bg_frame_arr = np.clip(
                deep_layer.astype(np.float32) * 0.25 + mid_layer.astype(np.float32) * 0.75,
                0, 255
            ).astype(np.uint8)

            bg_frame_arr = self._apply_category_overlay(bg_frame_arr, category, cache_key)
            _bg_cache[cache_key] = bg_frame_arr
            result = bg_frame_arr.copy()
            return result

        # ── PERFORMANCE: Vignette mask cache (computed once per scene) ──
        _vignette_mask = None
        _vignette_card_pos = None

        def _get_vignette_mask(card_center_x, card_center_y):
            nonlocal _vignette_mask, _vignette_card_pos
            ck = (card_center_x, card_center_y)
            if _vignette_mask is not None and _vignette_card_pos == ck:
                return _vignette_mask
            h_f, w_f = 1920, 1080
            yy, xx = np.meshgrid(np.arange(h_f, dtype=np.float32), np.arange(w_f, dtype=np.float32), indexing='ij')
            dist = np.sqrt((xx - card_center_x) ** 2 + (yy - card_center_y) ** 2)
            max_dist = np.sqrt(card_center_x ** 2 + card_center_y ** 2)
            vignette_factor = np.clip(dist / max_dist * 1.8, 0, 1) ** 1.8 * 0.35
            _vignette_mask = vignette_factor[:, :, np.newaxis]
            _vignette_card_pos = ck
            return _vignette_mask

        def make_frame(t):
            # Background: use cache for static images, compute live for video
            if bg_video is not None:
                # Video background — cannot cache, compute live (simplified: skip parallax for video)
                bg_dur = bg_video.duration
                raw_frame = bg_video.get_frame(t % bg_dur)
                if scene_idx == 0: base_blur, darken_f = 6.0, 0.50
                elif scene_idx == 1: base_blur, darken_f = 10.0, 0.60
                else: base_blur, darken_f = 4.0, 0.40
                if total_duration > 6.0 and t > 5.0:
                    blur_r = max(0.0, base_blur - base_blur * (t - 5.0))
                else:
                    blur_r = base_blur
                processed_bg = self._process_bg_frame(raw_frame, blur_radius=blur_r, darken_factor=darken_f)
                bg_frame_img = Image.fromarray(processed_bg)
            elif _bg_is_static:
                if self.evidence_mode:
                    # Evidence board: cork / case file texture instead of blurred image
                    from evidence_board import generate_casefile_background
                    bg_frame_img = generate_casefile_background(1080, 1920)
                else:
                    # Static image — use pre-computed cache
                    bg_frame_arr = _compute_parallax_bg(t, is_last_scene, total_duration, delay_offset, scene_idx, category)
                    if bg_frame_arr is None:
                        bg_frame_arr = np.zeros((1920, 1080, 3), dtype=np.uint8)
                    bg_frame_img = Image.fromarray(bg_frame_arr)
            else:
                bg_frame_img = Image.new("RGB", (1080, 1920), (10, 15, 30))

            draw_bg = ImageDraw.Draw(bg_frame_img)
            
            # Minimal case identifier (replaces removed HUD clutter: radar, oscilloscope, telemetry, redactions)
            try:
                case_font = ImageFont.truetype(self.font_path, 16)
                case_id = f"CASE #{abs(hash(text)) % 9999:04d}"
                draw_bg.text((900, 30), case_id, fill=(255, 255, 255, 40), font=case_font)
            except Exception:
                pass

            # Watermark stamp — subtle corner mark for Scene 1
            if scene_idx == 0 and rotated_stamp is not None and 0.4 <= t <= 3.5:
                t_stamp = t - 0.4
                if t_stamp < 0.15:
                    scale = 2.0 - 1.0 * (t_stamp / 0.15)
                    opacity = int(100 * (t_stamp / 0.15))
                else:
                    scale = 1.0
                    opacity = 100
                rw_s, rh_s = rotated_stamp.size
                new_w = int(rw_s * scale)
                new_h = int(rh_s * scale)
                if new_w > 10 and new_h > 10:
                    scaled_stamp = rotated_stamp.resize((new_w, new_h), Image.Resampling.BILINEAR)
                    # Bottom-left corner position
                    wpx = 30
                    wpy = 1750
                    r_arr = np.array(scaled_stamp)
                    r_arr[:, :, 3] = (r_arr[:, :, 3] * (opacity / 255.0)).astype(np.uint8)
                    scaled_stamp = Image.fromarray(r_arr)
                    bg_frame_img.paste(scaled_stamp, (wpx, wpy), scaled_stamp)

            # Scene labels at the top — typewriter effect (characters appear one at a time)
            if scene_label:
                # Typewriter reveal: 33 chars/sec (~30ms per character), full text by 0.8s
                typewriter_count = min(len(scene_label), int(t * 33))
                typewriter_label = scene_label[:typewriter_count]
                if typewriter_count > 0:
                    lw = draw_bg.textlength(typewriter_label, font=label_font)
                    draw_bg.text((60, 60), typewriter_label, fill=(180, 60, 60), font=label_font)
                    if typewriter_count == len(scene_label):
                        # Full text: show underline
                        draw_bg.line([(60, 90), (60 + int(lw), 90)], fill=(180, 60, 60, 150), width=2)
            if scene_title:
                typewriter_count = min(len(scene_title), int(t * 33))
                typewriter_title = scene_title[:typewriter_count]
                if typewriter_count > 0:
                    stw = draw_bg.textlength(typewriter_title, font=scene_title_font)
                    draw_bg.text(((1080 - stw) // 2, 120), typewriter_title, fill=(255, 255, 255, 200), font=scene_title_font)

            # --- Per-scene countdown timer bar (top edge, subtle) ---
            bar_y = 8
            bar_h = 4
            bar_w = 960
            bar_x = (1080 - bar_w) // 2
            if t >= delay_offset:
                local_t = t - delay_offset
                progress = min(1.0, local_t / max(audio_duration, 0.01))
            else:
                progress = 0.0
            # Background track
            draw_bg.rounded_rectangle([bar_x, bar_y, bar_x + bar_w, bar_y + bar_h], radius=2, fill=(255, 255, 255, 20))
            # Progress fill
            timer_color = style_dict.get("timer_bar_color", style_dict["highlight_bg"])
            fill_end = int(bar_x + bar_w * progress)
            if fill_end > bar_x:
                draw_bg.rounded_rectangle([bar_x, bar_y, fill_end, bar_y + bar_h], radius=2, fill=timer_color + (100,))

            fused_arr = np.array(bg_frame_img)
            
            # Scanlines
            drift_offset = int(t * 120) % 4
            drift_scanlines = np.roll(scanline_overlay, drift_offset, axis=0)
            fused_arr = (fused_arr * (1 - drift_scanlines) + (drift_scanlines * 0)).astype(np.uint8)
            
            # Grit
            grit_idx = int(t * 15) % 10
            fused_arr = np.clip(fused_arr.astype(np.int16) + grit_frames[grit_idx].astype(np.int16), 0, 255).astype(np.uint8)

            # Mascot compositing — emotion beats (Sprint B: Static reacts to content)
            if hasattr(self, 'mascot_img') and emotion_beats:
                for beat_ts, beat_expr, beat_dur in emotion_beats:
                    if beat_ts <= t <= beat_ts + beat_dur:
                        # Render Static with specific expression in prominent position
                        beat_mascot = VideoEngine._render_static(size=90, expression=beat_expr)
                        # Right side, near card area (visible, not hidden)
                        beat_mx = 920
                        beat_my = 400 + scene_idx * 200  # varies per scene
                        # Subtle jitter
                        beat_jx = int(3 * math.sin(t * 8))
                        beat_jy = int(2 * math.cos(t * 7))
                        fused_img = Image.fromarray(fused_arr).convert("RGBA")
                        fused_img.paste(beat_mascot, (beat_mx + beat_jx, beat_my + beat_jy), beat_mascot)
                        fused_arr = np.array(fused_img.convert("RGB"))
                        break  # only one beat at a time

            # Mascot compositing (subtle easter egg — The Lens peeks into scenes) — only when no emotion beat active
            if hasattr(self, 'mascot_img'):
                # Deterministic appearance per scene based on video_seed + scene_idx
                egg_seed = (self.video_seed or 0) + scene_idx * 7
                egg_rng = random.Random(egg_seed)
                egg_present = egg_rng.random() < 0.75  # 75% chance per scene
                
                if egg_present:
                    # Each scene has different timing windows and positions
                    egg_start = {0: 0.6, 1: 1.0, 2: 0.8}.get(scene_idx, 0.8)
                    egg_end = egg_start + egg_rng.uniform(0.8, 1.5)
                    egg_positions = [
                        (60, 80),      # top-left peeking
                        (920, 60),     # top-right corner
                        (60, 900),     # left mid, behind card
                        (920, 800),    # right mid
                        (500, 60),     # top center
                        (920, 1200),   # right lower
                    ]
                    egg_pos = egg_positions[scene_idx % len(egg_positions)]
                    
                    if egg_start <= t <= egg_end:
                        local_t = t - egg_start
                        bounce_y = int(3 * math.sin(local_t * 2.5))
                        mx = egg_pos[0]
                        my = egg_pos[1] + bounce_y
                        
                        # Subtle drift — Lens slowly moves horizontally
                        drift_x = int(10 * math.sin(local_t * 0.8))
                        mx += drift_x
                        
                        fused_img = Image.fromarray(fused_arr)
                        mascot_paste = self.mascot_img.copy()
                        # Gentle pulsing opacity
                        pulse = 0.6 + 0.15 * math.sin(local_t * 2.0)
                        m_arr = np.array(mascot_paste)
                        m_arr[:, :, 3] = (m_arr[:, :, 3] * pulse).astype(np.uint8)
                        mascot_paste = Image.fromarray(m_arr)
                        fused_img.paste(mascot_paste, (mx, my), mascot_paste)
                        fused_arr = np.array(fused_img)

            # Elastic Card (pop animation) or Static Card (last/verdict scene)
            # Multi-card rotation: if >1 card, each gets equal time with crossfade
            active_card_image = None
            next_card_image = None
            fade_progress = 0.0
            if card_images:
                num_cards = len(card_images)
                if num_cards > 1:
                    card_duration = audio_duration / num_cards
                    current_card_idx = min(int(t / card_duration), num_cards - 1)
                    active_card_image = card_images[current_card_idx]
                    # Crossfade during last 0.3s of each card's slot
                    card_local_t = t - current_card_idx * card_duration
                    fade_dur = 0.3
                    if current_card_idx < num_cards - 1 and card_local_t > card_duration - fade_dur:
                        fade_progress = (card_local_t - (card_duration - fade_dur)) / fade_dur
                        next_card_image = card_images[current_card_idx + 1]
                else:
                    active_card_image = card_images[0]

            if self.evidence_mode and card_images:
                # ── Evidence Board: polaroid photos on cork board ──
                from evidence_board import EvidenceBoardCompositor
                evidence = EvidenceBoardCompositor(1080, 1920)
                cap = self.evidence_captions or []
                total_scenes = 3  # default — caller could provide this
                fused_arr = evidence.apply(
                    fused_arr, card_images, scene_idx, total_scenes, t, audio_duration,
                    captions=cap
                )
            elif active_card_image is not None:
                if is_last_scene:
                    # Static card for last scene — always fully visible, no elastic pop
                    scaled_card = active_card_image.resize((840, 890), Image.Resampling.BILINEAR)
                    px = 540 - 840 // 2
                    py = 900 - 890 // 2
                    fused_img = Image.fromarray(fused_arr)
                    # Crossfade to next card if applicable
                    if next_card_image is not None and fade_progress > 0:
                        scaled_next = next_card_image.resize((840, 890), Image.Resampling.BILINEAR)
                        blend_arr = np.array(scaled_card).astype(np.float32) * (1 - fade_progress) + \
                                    np.array(scaled_next).astype(np.float32) * fade_progress
                        scaled_card = Image.fromarray(blend_arr.astype(np.uint8))
                    fused_img.paste(scaled_card, (px, py), scaled_card)
                    fused_arr = np.array(fused_img)
                elif t >= 0.2:
                    t_elapsed = t - 0.2
                    if t_elapsed < 1.0:
                        s_factor = 1.0 - math.exp(-6 * t_elapsed) * math.cos(12 * t_elapsed)
                    else:
                        s_factor = 1.0
                    new_w = int(840 * s_factor)
                    new_h = int(890 * s_factor)
                    if new_w > 10 and new_h > 10:
                        scaled_card = active_card_image.resize((new_w, new_h), Image.Resampling.BILINEAR)
                        # Crossfade to next card
                        if next_card_image is not None and fade_progress > 0:
                            scaled_next = next_card_image.resize((new_w, new_h), Image.Resampling.BILINEAR)
                            blend_arr = np.array(scaled_card).astype(np.float32) * (1 - fade_progress) + \
                                        np.array(scaled_next).astype(np.float32) * fade_progress
                            scaled_card = Image.fromarray(blend_arr.astype(np.uint8))
                        px = 540 - new_w // 2
                        py = 900 - new_h // 2
                        fused_img = Image.fromarray(fused_arr)
                        fused_img.paste(scaled_card, (px, py), scaled_card)
                        fused_arr = np.array(fused_img)

            # ── Sprint 6: Focal Point Vignette — radial gradient follows card position ──
            if active_card_image is not None:
                vx, vy = 540, 900
                vignette_factor = _get_vignette_mask(vx, vy)
                fused_arr = np.clip(fused_arr.astype(np.float32) * (1.0 - vignette_factor), 0, 255).astype(np.uint8)

            # ── Sprint 6: Forensic Scan Line Animation — horizontal sweep on card reveal ──
            SCAN_DURATION = 0.35
            scan_active = False
            scan_progress = 0.0
            if active_card_image is not None and not is_last_scene:
                if 0.2 <= t < 0.2 + SCAN_DURATION:
                    scan_active = True
                    scan_progress = (t - 0.2) / SCAN_DURATION
            if scan_active and scan_progress > 0.0:
                # Card bottom edge position in frame coordinates
                card_top_y = 900 - 890 // 2  # = 455
                card_bottom_y = card_top_y + 890  # = 1345
                scan_y = card_top_y + int(scan_progress * 890)
                scan_y = min(scan_y, card_bottom_y)
                # Draw a bright horizontal scan line
                line_h = 3
                scan_top = max(card_top_y, scan_y - line_h)
                scan_bottom = min(card_bottom_y, scan_y + line_h)
                if scan_bottom > scan_top:
                    scan_brightness = int(180 + 75 * math.sin(scan_progress * math.pi * 6))
                    fused_arr[scan_top:scan_bottom, :, :] = np.clip(
                        fused_arr[scan_top:scan_bottom, :, :].astype(np.int16) + scan_brightness,
                        0, 255
                    ).astype(np.uint8)

            # Pre-transition cue visual glitch: cued at last 0.15s of the scene
            if not is_last_scene and total_duration - 0.15 <= t <= total_duration:
                y_start = random.randint(0, 1919)
                y_end = min(1920, y_start + random.randint(15, 60))
                shift = random.randint(-15, 15)
                fused_arr[y_start:y_end, :, :] = np.roll(fused_arr[y_start:y_end, :, :], shift, axis=1)
                
                shift_r = random.randint(-3, 3)
                if shift_r != 0:
                    fused_arr[:, :, 0] = np.roll(fused_arr[:, :, 0], shift_r, axis=1)

            # Render Subtitles
            if t >= delay_offset and srt_blocks:
                t_audio_ms = (t - delay_offset) * 1000.0 + self.subtitle_lookahead_ms
                active_block = None
                for b in srt_blocks:
                    if b["start_ms"] <= t_audio_ms < b["end_ms"]:
                        active_block = b
                        break
                if active_block:
                    fused_img = Image.fromarray(fused_arr)
                    draw_subs = ImageDraw.Draw(fused_img)
                    # Word-level kinetic subtitle rendering using real timestamps
                    self._render_kinetic_srt_block(
                        draw_subs, sub_font, active_block["text"],
                        t_audio_ms, word_boundaries, y_pos=1580, style=style_dict,
                        block_start_ms=active_block["start_ms"]
                    )
                    fused_arr = np.array(fused_img)

                # ── Sprint 7: Animated Data Counters ──
                # Detect numbers in the spoken word and render counting-up animation
                if t >= delay_offset and word_boundaries:
                    tc_audio_ms = (t - delay_offset) * 1000.0 + self.subtitle_lookahead_ms
                    # Find the currently spoken word in word_boundaries
                    active_wb = None
                    for wb in word_boundaries:
                        wb_off = wb.get("offset_ms", 0)
                        wb_dur = wb.get("duration_ms", 0)
                        if wb_off <= tc_audio_ms < wb_off + wb_dur:
                            active_wb = wb
                            break
                    if active_wb:
                        import re as _re
                        w_clean = active_wb.get("word", "").strip(".,!?;: ")
                        num_match = _re.search(r'(\d+(?:\.\d+)?)', w_clean)
                        if num_match:
                            target_str = num_match.group(1)
                            is_float = '.' in target_str
                            target = float(target_str)
                            elapsed_ms = tc_audio_ms - active_wb["offset_ms"]
                            progress = min(1.0, elapsed_ms / 1500.0)
                            eased = 1.0 - (1.0 - progress) ** 3
                            if is_float:
                                animated_val = target * eased
                                counter_text = f"{animated_val:.1f}"
                            else:
                                animated_val = int(target * eased)
                                counter_text = str(animated_val)

                            # Render the counter as a large glowing number
                            try:
                                ctr_font = ImageFont.truetype(self.font_path, 72)
                            except Exception:
                                ctr_font = ImageFont.load_default()

                            fused_img_local = Image.fromarray(fused_arr).convert("RGBA")
                            ctr_layer = Image.new("RGBA", (1080, 1920), (0, 0, 0, 0))
                            draw_ctr = ImageDraw.Draw(ctr_layer)
                            ctw = int(draw_ctr.textlength(counter_text, font=ctr_font))
                            ctx = (1080 - ctw) // 2
                            cty = 1480

                            # Glow rings around the counter number
                            glow_col = (255, 242, 0)  # highlight yellow
                            for g_o in range(3, 0, -1):
                                gx = g_o * 4
                                ga = 25 // g_o
                                draw_ctr.text((ctx - gx, cty), counter_text, fill=glow_col + (ga,), font=ctr_font)
                                draw_ctr.text((ctx + gx, cty), counter_text, fill=glow_col + (ga,), font=ctr_font)
                                draw_ctr.text((ctx, cty - gx), counter_text, fill=glow_col + (ga,), font=ctr_font)
                                draw_ctr.text((ctx, cty + gx), counter_text, fill=glow_col + (ga,), font=ctr_font)

                            # Main text with stroke
                            draw_ctr.text((ctx + 2, cty + 2), counter_text, fill=(0, 0, 0, 180), font=ctr_font)
                            draw_ctr.text((ctx, cty), counter_text, fill=(255, 255, 255, 255), font=ctr_font)
                            fused_img_local = Image.alpha_composite(fused_img_local, ctr_layer).convert("RGB")
                            fused_arr = np.array(fused_img_local)

                # ── Sprint B: File Stamp at truth reveal ──
                if is_last_scene and stamp_text and t >= delay_offset:
                    stamp_img = self._render_stamp(stamp_text, scene_idx, t, delay_offset)
                    if stamp_img is not None:
                        # Position: centered at bottom-third, above card area
                        stamp_cx = (1080 - stamp_img.width) // 2
                        stamp_cy = 1200 - stamp_img.height // 2
                        fused_stamp = Image.fromarray(fused_arr).convert("RGBA")
                        fused_stamp.paste(stamp_img, (stamp_cx, stamp_cy), stamp_img)
                        fused_arr = np.array(fused_stamp.convert("RGB"))

            # Subscribe button overlay — subtle pill at 80% through the last scene's audio
            if is_last_scene and total_duration > 1.0:
                sub_progress = t / total_duration
                if sub_progress >= 0.80:
                    sub_alpha_factor = min(1.0, (sub_progress - 0.80) / 0.08)  # fade in over 8%
                    btn_w, btn_h = 280, 52
                    btn_x = (1080 - btn_w) // 2
                    btn_y = 1840  # below the 3-line kinetic subtitle area (1580-1820)
                    btn_bg = (255, 60, 60)  # YouTube red
                    btn_text = "SUBSCRIBE"
                    if sub_alpha_factor > 0.05:
                        fused_img = Image.fromarray(fused_arr).convert("RGBA")
                        overlay = Image.new("RGBA", (1080, 1920), (0, 0, 0, 0))
                        draw_btn = ImageDraw.Draw(overlay)
                        draw_btn.rounded_rectangle(
                            [btn_x, btn_y, btn_x + btn_w, btn_y + btn_h],
                            radius=26,
                            fill=btn_bg + (int(220 * sub_alpha_factor),)
                        )
                        try:
                            btn_font = ImageFont.truetype(self.font_path, 26)
                        except:
                            btn_font = ImageFont.load_default()
                        tw = draw_btn.textlength(btn_text, font=btn_font)
                        tx = btn_x + (btn_w - int(tw)) // 2
                        ty = btn_y + (btn_h - 32) // 2
                        draw_btn.text((tx, ty), btn_text, fill=(255, 255, 255, int(255 * sub_alpha_factor)), font=btn_font)
                        # Bell icon (simple circle)
                        bell_x = btn_x + 24
                        bell_y = btn_y + btn_h // 2
                        draw_btn.ellipse(
                            [bell_x - 10, bell_y - 10, bell_x + 10, bell_y + 10],
                            fill=(255, 255, 255, int(180 * sub_alpha_factor))
                        )
                        draw_btn.text((bell_x - 4, bell_y - 7), "\uD83D\uDD14", fill=(255, 255, 255, int(220 * sub_alpha_factor)), font=btn_font)
                        fused_img = Image.alpha_composite(fused_img, overlay).convert("RGB")
                        fused_arr = np.array(fused_img)
            
            return fused_arr
            
        clip = VideoClip(make_frame, duration=total_duration)
        clip.size = (1080, 1920)
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

    @staticmethod
    def _value_noise_2d(x: float, y: float, seed: int = 0) -> float:
        """Simple hash-based value noise returning [0,1]."""
        n = int(x * 157) ^ int(y * 311) ^ seed
        n = (n << 13) ^ n
        return ((n * (n * n * 60493 + 19990303) + 1376312589) & 0x7fffffff) / 0x7fffffff

    @staticmethod
    def _generate_burn_mask(w: int, h: int, progress: float, seed: int = 0) -> np.ndarray:
        """
        Returns a 2D float32 numpy array of shape (h, w) in range [0, 1].
        0 = fully burnt (transparent), 1 = intact.
        Progress 0.0 = no burn, 1.0 = fully burnt.
        """
        xx, yy = np.meshgrid(np.arange(w, dtype=np.float32), np.arange(h, dtype=np.float32))
        x_scaled = (xx * 0.02 * 157).astype(np.int32)
        y_scaled = (yy * 0.02 * 311).astype(np.int32)
        
        n = x_scaled ^ y_scaled ^ seed
        n = (n << 13) ^ n
        term = n * (n * n * 60493 + 19990303) + 1376312589
        noise_val = (term & 0x7fffffff).astype(np.float32) / 0x7fffffff
        
        nx = xx / w
        displaced = nx + (noise_val - 0.5) * 0.3
        burn_edge = 1.0 - pow(progress, 0.7)
        
        mask = np.clip((displaced - burn_edge) * 5.0, 0.0, 1.0)
        return mask

    def _add_global_progress_bar(self, clip, style_dict, height=6):
        duration = clip.duration
        color = style_dict.get("timer_bar_color", style_dict.get("highlight_bg", (0, 242, 254)))
        
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
                writeable_frame[h - height:h, 0:fill_width, :] = color
            return writeable_frame
            
        return clip.fl(filter_frame)

    def _parse_ssml_words_emphasis(self, ssml_text: str) -> list:
        """
        Parses an SSML string (potentially containing <emphasis> tags) and returns a list of dictionaries:
        [{"word": clean_word_string, "is_emphasized": bool}]
        Uses xml.etree.ElementTree with a fallback to regex.
        """
        import xml.etree.ElementTree as ET
        import re
        
        # Strip bracket cues like [sigh], [whispering], [/whispering] so they are not treated as words in subtitles
        ssml_text = re.sub(r'\[[\w\s_/-]+\]', '', ssml_text)
        
        # Clean text of basic break tags before wrapping
        cleaned_ssml = ssml_text.replace("&", "&amp;")
        wrapped = f"<root>{cleaned_ssml}</root>"
        
        try:
            root = ET.fromstring(wrapped)
            words_info = []
            
            def recurse(node, in_emphasis=False):
                is_emp = in_emphasis or (node.tag == 'emphasis')
                
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
        except Exception as e:
            pass
            
        # Fallback to regex
        emphasis_pattern = re.compile(r'<emphasis[^>]*>(.*?)</emphasis>', re.IGNORECASE)
        emphasized_words = set()
        for match in emphasis_pattern.finditer(ssml_text):
            for w in match.group(1).split():
                clean = re.sub(r'[^\w]', '', w).lower()
                if clean:
                    emphasized_words.add(clean)
                    
        # Clean of all XML tags
        clean_text = re.sub(r'<[^>]+>', '', ssml_text)
        words_info = []
        for w in clean_text.split():
            clean = re.sub(r'[^\w]', '', w).lower()
            is_emp = clean in emphasized_words
            words_info.append({"word": w, "is_emphasized": is_emp})
        return words_info

    def _create_burn_transition_clip(self, bg_source: Any, duration: float = 0.8, flash_image: Optional[Image.Image] = None) -> 'VideoClip':
        """Returns a VideoClip that applies a procedural burning-paper transition effect.
        flash_image: optional previous scene card to flash (desaturated, 40% opacity)
                     during the first 0.1s (Sprint 6 — Transition Memory Flash)."""
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

            # Get base bg frame
            if bg_video is not None:
                bg_dur = bg_video.duration
                raw_frame = bg_video.get_frame(t % bg_dur)
                bg_arr = self._process_bg_frame(raw_frame, blur_radius=15.0, darken_factor=0.45)
            elif raw_img_pil is not None:
                glow = raw_img_pil.filter(ImageFilter.GaussianBlur(radius=15))
                dark = Image.new("RGB", (1080, 1920), (10, 15, 30))
                glow = Image.blend(glow, dark, 0.45)
                bg_arr = np.array(glow)
            else:
                bg_arr = base_arr.copy()

            # Generate burn mask and flame glow
            burn_mask = self._generate_burn_mask(1080, 1920, progress, seed)
            bg_arr_float = bg_arr.astype(np.float32)

            # Flame glow gradient at burn edge
            xx, yy = np.meshgrid(np.arange(1080, dtype=np.float32), np.arange(1920, dtype=np.float32))
            x_scaled = (xx * 0.02 * 157).astype(np.int32)
            y_scaled = (yy * 0.02 * 311).astype(np.int32)
            
            n = x_scaled ^ y_scaled ^ seed
            n = (n << 13) ^ n
            term = n * (n * n * 60493 + 19990303) + 1376312589
            noise_v = (term & 0x7fffffff).astype(np.float32) / 0x7fffffff
            
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

            # Composite
            mask_3ch = np.stack([burn_mask] * 3, axis=-1)
            result = bg_arr_float * mask_3ch + flame * (1.0 - mask_3ch)

            # Ember particles
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
                                        result[py, px] = np.clip(result[py, px] * 0.6 + np.array(color, dtype=np.float32) * 0.4, 0, 255)

            # Add darken for burnt areas
            result = np.clip(result, 0, 255).astype(np.uint8)

            # Scanlines on top
            drift = int(t * 240) % 4
            scanlines = np.roll(scanline_overlay, drift, axis=0)
            result = (result * (1 - scanlines)).astype(np.uint8)

            # ── Sprint 6: Transition Memory Flash ──
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

    def _create_transition_clip(self, bg_source: Any, duration: float = 0.5, flash_image: Optional[Image.Image] = None) -> 'VideoClip':
        """
        Returns a VideoClip that applies a glitchy VHS-style transition effect.
        flash_image: optional previous scene card to flash (desaturated, 40% opacity)
                     during the first 0.1s (Sprint 6 — Transition Memory Flash).
        """
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

            # ── Sprint 6: Transition Memory Flash ──
            if flash_image is not None and t < 0.1:
                # Desaturated, 40% opacity flash of the previous card
                flash_card = flash_image.copy()
                # Convert to grayscale via desaturation
                flash_arr = np.array(flash_card.convert("RGBA"), dtype=np.float32)
                gray = flash_arr[:, :, :3].mean(axis=2, keepdims=True)
                flash_arr[:, :, :3] = gray * 0.5 + flash_arr[:, :, :3] * 0.5  # partial desaturate
                flash_arr[:, :, 3] = flash_arr[:, :, 3] * 0.4  # 40% opacity
                # Center in frame (840x890 card centered at x=540, y=900)
                fx = 540 - 840 // 2
                fy = 900 - 890 // 2
                flash_pil = Image.fromarray(flash_arr.astype(np.uint8))
                fused_pil = Image.fromarray(fused_arr).convert("RGBA")
                fused_pil.paste(flash_pil, (fx, fy), flash_pil)
                fused_arr = np.array(fused_pil.convert("RGB"))

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

    def _apply_crt_effects(self, frame_arr: np.ndarray, t: float, total_duration: float) -> np.ndarray:
        """Apply CRT monitor VFX for the signature channel look:
        - Enhanced drifting scanlines (wider, more visible)
        - Radial vignette (dark edges, subtle barrel shadow)
        - Chromatic aberration (RGB channel shift at edges)
        - Random static jitter (micro-displacement)
        - Phosphor glow (horizontal light bleed)
        Returns modified numpy array (H, W, 3) uint8.
        """
        h, w, c = frame_arr.shape
        arr = frame_arr.astype(np.float32)

        # 1. Enhanced scanlines (25% opacity, 4px wide, 8px pitch, drifting vertically)
        scan_drift = int(t * 90) % 8
        scanline_mask = np.zeros((h, w), dtype=np.float32)
        for sy in range(scan_drift % 8, h, 8):
            sy_end = min(sy + 3, h)
            scanline_mask[sy:sy_end, :] = 0.25  # 25% darkening
        arr = arr * (1.0 - scanline_mask[:, :, None])

        # 2. Radial vignette (darkens corners with smooth falloff)
        cx, cy = w / 2, h / 2
        max_r = np.sqrt(cx**2 + cy**2)
        yy, xx = np.ogrid[:h, :w]
        dist = np.sqrt((xx - cx)**2 + (yy - cy)**2) / max_r
        vignette = np.clip(1.0 - dist**2 * 0.6, 0.35, 1.0)  # 65% dark max at corners
        arr = arr * vignette[:, :, None]

        # 3. Subtle chromatic aberration (RGB channel shift toward edges)
        shift_px = max(0, 3 - int(dist.max() * 2))  # more shift at edges
        if shift_px > 0:
            arr_shifted = arr.copy()
            # Red shifts left
            arr_shifted[:-shift_px, shift_px:, 0] = arr[shift_px:, :-shift_px, 0]
            # Blue shifts right
            arr_shifted[shift_px:, :-shift_px, 2] = arr[:-shift_px, shift_px:, 2]
            blend = np.clip(dist * 0.5, 0, 0.1)[:, :, None]  # stronger at edges
            arr = arr * (1.0 - blend) + arr_shifted * blend

        # 4. Random static interference (sparkle dots)
        import random as rnd
        if rnd.random() < 0.15:  # 15% chance per frame
            sparkle = np.random.randint(0, 256, (h, w, 3), dtype=np.int32).astype(np.float32)
            sparkle_mask = np.random.random((h, w, 1)) < 0.003  # 0.3% of pixels
            arr = np.where(sparkle_mask, sparkle * 0.3 + arr * 0.7, arr)

        # 5. Phosphor glow — horizontal light bleed on bright areas
        gray = np.mean(arr, axis=2)
        bright_mask = gray > 180
        if bright_mask.any():
            # Horizontal blur (very subtle bloom on bright pixels)
            blur_kernel = np.ones((1, 5), dtype=np.float32) / 5
            glow = np.zeros_like(arr)
            for ch in range(3):
                channel = arr[:, :, ch]
                # Simple horizontal blur using convolution
                blurred = np.zeros_like(channel)
                for row in range(h):
                    blurred[row, :] = np.convolve(channel[row, :], blur_kernel[0], mode='same')
                glow[:, :, ch] = blurred * 0.08  # 8% glow intensity
            arr = arr + glow

        return np.clip(arr, 0, 255).astype(np.uint8)

    def _create_starting_bumper(self, audio_duration: float, video_type: str, style_dict: dict = None, text: str = None, audio_path: Optional[str] = None, episode_num: Optional[int] = None) -> 'VideoClip':
        """
        Creates the starting bumper video clip.
        Uses a blueprint video from assets/video_blueprints/starting/ (or static fallback),
        renders large bold text with subtitles synced to the narrator.
        """
        if style_dict is None:
            style_dict = STYLE_PRESETS["blueprint"]
        try:
            from moviepy.editor import VideoClip, VideoFileClip
        except ImportError:
            from moviepy import VideoClip, VideoFileClip

        # Determine text based on video_type if not explicitly provided
        if text is None:
            if video_type == "myth":
                text = "Now, bringing you the strangest MYTH that will shock you."
            elif video_type == "bizarre":
                text = "Now, bringing you the most BIZARRE TRUTH that will shock you."
            elif video_type == "dynamic":
                text = "Now, bringing you the declassified truth."
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
            bumper_font = ImageFont.truetype(self.font_path, 78)
        except Exception:
            bumper_font = ImageFont.load_default()

        scanline_overlay = self._create_scanline_overlay(1080, 1920, opacity=0.10)

        # Load SRT blocks
        srt_blocks = []
        if audio_path and os.path.exists(audio_path):
            srt_path = os.path.splitext(audio_path)[0] + ".srt"
            if os.path.exists(srt_path):
                srt_blocks = self._parse_srt_file(srt_path)

        # Fallback if no SRT file exists
        if not srt_blocks and text:
            words = text.split()
            if words and audio_duration > 0:
                total_chars = sum(len(w) for w in words)
                sec_per_char = audio_duration / total_chars if total_chars > 0 else 0.1
                current_time = 0.0
                scene_word_timings = []
                for w in words:
                    w_dur = len(w) * sec_per_char
                    scene_word_timings.append({
                        "word": w,
                        "offset_ms": current_time * 1000.0,
                        "duration_ms": w_dur * 1000.0
                    })
                    current_time += w_dur
                try:
                    from tts.subtitle_builder import SubtitleBuilder
                    srt_blocks = SubtitleBuilder.group_words_into_subtitles(scene_word_timings)
                except Exception as e:
                    print(f"[VideoEngine] SubtitleBuilder import failed in starting bumper: {e}")

        def make_frame(t):
            # Get background frame
            if bg_video is not None:
                bg_dur = bg_video.duration
                raw_frame = bg_video.get_frame(t % bg_dur)
                bg_arr = self._process_bg_frame(raw_frame, blur_radius=6.0, darken_factor=0.55)
            else:
                bg_arr = base_arr.copy()

            # Slow zoom
            zoom_factor = 1.0 + 0.08 * (t / max(total_duration, 0.1))
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
            # CRT signature VFX (scanlines, vignette, chromatic aberration, static, glow)
            fused_arr = self._apply_crt_effects(fused_arr, t, total_duration)

            # Render subtitles and episode badge
            fused_img = Image.fromarray(fused_arr)
            draw = ImageDraw.Draw(fused_img)
            
            if srt_blocks:
                t_ms = t * 1000.0 + self.subtitle_lookahead_ms
                active_block = None
                for b in srt_blocks:
                    if b["start_ms"] <= t_ms < b["end_ms"]:
                        active_block = b
                        break
                if active_block:
                    self._render_srt_subtitle_block(draw, bumper_font, active_block["text"], y_pos=1310)

        # Draw episode badge on starting bumper — REMOVED (users swipe away)
                    
            fused_arr = np.array(fused_img)
            return fused_arr

        clip = VideoClip(make_frame, duration=total_duration)
        clip.size = (1080, 1920)
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

    def _create_ending_scene(self, audio_duration: float, style_dict: dict = None, text: str = None, audio_path: Optional[str] = None) -> 'VideoClip':
        """
        Creates the ending bumper (Class Dismissed) video clip.
        Uses a blueprint video from assets/video_blueprints/ending/ (or static fallback),
        renders large bold text: "Subscribe — we expose a new lie EVERY. SINGLE. DAY. CLASS DISMISSED."
        with subtitles.
        """
        if style_dict is None:
            style_dict = STYLE_PRESETS["blueprint"]
        try:
            from moviepy.editor import VideoClip, VideoFileClip
        except ImportError:
            from moviepy import VideoClip, VideoFileClip

        if text is None:
            text = "Subscribe — we expose a new lie EVERY. SINGLE. DAY. CLASS DISMISSED."
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
            bumper_font = ImageFont.truetype(self.font_path, 72)
        except Exception:
            bumper_font = ImageFont.load_default()

        scanline_overlay = self._create_scanline_overlay(1080, 1920, opacity=0.10)

        # Load SRT blocks
        srt_blocks = []
        if audio_path and os.path.exists(audio_path):
            srt_path = os.path.splitext(audio_path)[0] + ".srt"
            if os.path.exists(srt_path):
                srt_blocks = self._parse_srt_file(srt_path)

        # Fallback if no SRT file exists
        if not srt_blocks and text:
            words = text.split()
            if words and audio_duration > 0:
                total_chars = sum(len(w) for w in words)
                sec_per_char = audio_duration / total_chars if total_chars > 0 else 0.1
                current_time = 0.0
                scene_word_timings = []
                for w in words:
                    w_dur = len(w) * sec_per_char
                    scene_word_timings.append({
                        "word": w,
                        "offset_ms": current_time * 1000.0,
                        "duration_ms": w_dur * 1000.0
                    })
                    current_time += w_dur
                try:
                    from tts.subtitle_builder import SubtitleBuilder
                    srt_blocks = SubtitleBuilder.group_words_into_subtitles(scene_word_timings)
                except Exception as e:
                    print(f"[VideoEngine] SubtitleBuilder import failed in ending bumper: {e}")

        def make_frame(t):
            if bg_video is not None:
                bg_dur = bg_video.duration
                raw_frame = bg_video.get_frame(t % bg_dur)
                bg_arr = self._process_bg_frame(raw_frame, blur_radius=6.0, darken_factor=0.55)
            else:
                bg_arr = base_arr.copy()

            zoom_factor = 1.0 + 0.08 * (t / max(total_duration, 0.1))
            h, w, c = bg_arr.shape
            new_h, new_w = int(h / zoom_factor), int(w / zoom_factor)
            top = (h - new_h) // 2
            left = (w - new_w) // 2
            cropped = bg_arr[top:top+new_h, left:left+new_w]
            frame = Image.fromarray(cropped).resize((w, h), Image.Resampling.BILINEAR)

            fused_arr = np.array(frame)
            # CRT signature VFX (scanlines, vignette, chromatic aberration, static, glow)
            fused_arr = self._apply_crt_effects(fused_arr, t, total_duration)

            # Render subtitles
            if srt_blocks:
                t_ms = t * 1000.0 + self.subtitle_lookahead_ms
                active_block = None
                for b in srt_blocks:
                    if b["start_ms"] <= t_ms < b["end_ms"]:
                        active_block = b
                        break
                if active_block:
                    fused_img = Image.fromarray(fused_arr)
                    draw = ImageDraw.Draw(fused_img)
                    self._render_srt_subtitle_block(draw, bumper_font, active_block["text"], y_pos=1310)
                    fused_arr = np.array(fused_img)

            # CRT Power-Off collapse transition in the last 0.15 seconds of the video
            if t >= total_duration - 0.15:
                dt = t - (total_duration - 0.15)
                norm = min(1.0, dt / 0.15)
                
                # Canvas for rendering black background and collapse highlights
                black_frame = Image.new("RGB", (w, h), (10, 15, 30)) # matching blueprint background tint
                draw_collapse = ImageDraw.Draw(black_frame)
                
                if norm < 0.70:
                    # Stage 1: Vertical collapse
                    y_scale = max(0.005, 1.0 - (norm / 0.70))
                    collapsed_h = int(h * y_scale)
                    if collapsed_h > 1:
                        temp_img = Image.fromarray(fused_arr).resize((w, collapsed_h), Image.Resampling.BILINEAR)
                        py_paste = (h - collapsed_h) // 2
                        black_frame.paste(temp_img, (0, py_paste))
                        # Phosphor glow line
                        draw_collapse.line([(0, h // 2), (w, h // 2)], fill=(230, 255, 255), width=max(1, int(15 * y_scale)))
                else:
                    # Stage 2: Horizontal collapse into dot
                    x_scale = max(0.001, 1.0 - ((norm - 0.70) / 0.30))
                    collapsed_w = int(w * x_scale)
                    if collapsed_w > 1:
                        px1 = (w - collapsed_w) // 2
                        px2 = px1 + collapsed_w
                        draw_collapse.line([(px1, h // 2), (px2, h // 2)], fill=(230, 255, 255), width=3)
                    
                    # Center dot glow
                    dot_radius = max(1, int(12 * (1.0 - (norm - 0.70) / 0.30)))
                    draw_collapse.ellipse(
                        [w // 2 - dot_radius, h // 2 - dot_radius, w // 2 + dot_radius, h // 2 + dot_radius],
                        fill=(255, 255, 255)
                    )
                    
                # Overlay dynamic NumPy random static noise array scaling with norm
                noise_amp = int(norm * 220)  # High intensity visual grit/analog static
                if noise_amp > 2:
                    # Gray/monochromatic static noise is more authentic for CRT
                    noise = np.random.randint(-noise_amp, noise_amp + 1, (h, w, 1), dtype=np.int16)
                    # Broadcast to 3 channels for RGB
                    noise = np.repeat(noise, 3, axis=2)
                    arr_temp = np.array(black_frame).astype(np.int16)
                    # Apply noise to the whole frame
                    arr_temp = np.clip(arr_temp + noise, 0, 255).astype(np.uint8)
                    black_frame = Image.fromarray(arr_temp)
                    
                fused_arr = np.array(black_frame)

            return fused_arr

        clip = VideoClip(make_frame, duration=total_duration)
        clip.size = (1080, 1920)
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
        video_type: str = "dynamic",
        starting_text: str = None,
        ending_text: str = None
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

        try:
            from moviepy.editor import AudioFileClip, VideoClip, CompositeAudioClip, concatenate_videoclips, VideoFileClip
        except ImportError:
            from moviepy import AudioFileClip, VideoClip, CompositeAudioClip, concatenate_videoclips, VideoFileClip

        import random

        output_video_path = os.path.join(self.assets_dir, f"{output_name}.mp4")
        print(f"[VideoEngine] Compiling dynamic N-scene video ({scene_count} scenes): {output_video_path}")

        self._ensure_sfx_exist()

        # Resource tracking
        tmp_files = []
        audio_clips = []
        bg_videos = []
        bg_music_clip = None
        bg_music_sub = None
        mixed_audio = None
        video_clip = None
        scene_clips = []
        transition_clips = []
        burn_transition_times = []
        starting_clip = None
        ending_clip = None

        try:
            # Load N+2 audio tracks [starting, s1..sN, ending]
            audio_clips = []
            for i, p in enumerate(audio_paths):
                if not os.path.exists(p):
                    print(f"[VideoEngine] CRITICAL: Audio file missing: {p}")
                audio_clips.append(AudioFileClip(p))
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

            SCENE_DELAY = 0.0
            TRANSITION_DURATION = 0.3

            # ---- Clip 1: Starting Bumper ----
            starting_clip = self._create_starting_bumper(
                audio_duration=audio_durations[0],
                video_type=video_type,
                style_dict=st,
                text=starting_text,
                audio_path=audio_paths[0]
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

                delay_offset = SCENE_DELAY if i < scene_count - 1 else 0.0
                y_pos = 330 if i < scene_count - 1 else 1400

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
                    audio_clip=audio_clips[audio_idx],
                    mid_roll_word_indices=None,
                    is_last_scene=(i == scene_count - 1),
                    audio_path=audio_paths[audio_idx],
                    # Sprint B: Emotion beats + File Stamp + Category theme
                    emotion_beats=self._generate_emotion_beats(scene_texts[i], i, audio_durations[audio_idx], delay_offset),
                    stamp_text=(lambda lbl: "DEBUNKED" if "MYTH" in (lbl or "").upper() else "ANOMALOUS" if "ANOMAL" in (lbl or "").upper() else "VERIFIED")(scene_labels[i] if i == scene_count - 1 else None),
                    category=category,
                )
                # We do not set the audio on individual content video clips to prevent MoviePy from dropping offsets.
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
                    use_burn = random.random() < 0.5
                    flash_mem = cards[i] if i < len(cards) else None  # previous scene card
                    if use_burn:
                        t_clip = self._create_burn_transition_clip(bg_source=next_bg, duration=TRANSITION_DURATION * 1.5, flash_image=flash_mem)
                        burn_transition_times.append(current_start)
                    else:
                        t_clip = self._create_transition_clip(bg_source=next_bg, duration=TRANSITION_DURATION, flash_image=flash_mem)
                    transition_clips.append(t_clip)
                    clip_sequence.append(t_clip)
                    current_start += TRANSITION_DURATION

            # ---- Last Clip: Ending Bumper ----
            ending_clip = self._create_ending_scene(
                audio_duration=audio_durations[-1],
                style_dict=st,
                text=ending_text,
                audio_path=audio_paths[-1]
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
                s_delay = SCENE_DELAY if i < scene_count - 1 else 0.0
                speaking_blocks.append((sc_start + s_delay, sc_start + s_delay + scene_audio_durations[i]))
            # Ending bumper
            speaking_blocks.append((ending_start, ending_start + ending_dur))

            audio_clips_to_mix = [video_clip.audio]
            # Mix content scene narration manually to align perfectly with subtitle frames
            for i in range(scene_count):
                audio_idx = i + 1
                s_delay = SCENE_DELAY if i < scene_count - 1 else 0.0
                audio_clips_to_mix.append(audio_clips[audio_idx].copy().set_start(scene_audio_starts[i] + s_delay))

            # ---- SFX Setup ----
            sfx_dir = os.path.join(self.assets_dir, "sfx")
            zap_path = os.path.join(sfx_dir, "zap.mp3")
            pop_path = os.path.join(sfx_dir, "pop.mp3")
            stamp_path = os.path.join(sfx_dir, "stamp.mp3")
            tick_path = os.path.join(sfx_dir, "tick.mp3")
            impact_path = os.path.join(sfx_dir, "impact.mp3")
            riser_path = os.path.join(sfx_dir, "riser.mp3")
            crackle_path = os.path.join(sfx_dir, "crackle.mp3")

            # A. Watermark Stamp SFX at 0.4s and at each scene start + 0.4s
            if os.path.exists(stamp_path):
                try:
                    stamp_clip = AudioFileClip(stamp_path)
                    vol = 0.25
                    stamp_clip = stamp_clip.multiply_volume(vol) if hasattr(stamp_clip, "multiply_volume") else stamp_clip.volumex(vol)
                    audio_clips_to_mix.append(stamp_clip.set_start(0.4))
                    for i in range(scene_count):
                        sc_start = scene_audio_starts[i]
                        audio_clips_to_mix.append(stamp_clip.copy().set_start(sc_start + 0.4))
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
                            while t_tick < sc_start + SCENE_DELAY - 0.2:
                                audio_clips_to_mix.append(tick_clip.set_start(t_tick))
                                t_tick += 0.6
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
                        audio_clips_to_mix.append(riser_clip.subclip(10.0 - SCENE_DELAY, 10.0).set_start(sc_start))
                    print(f"[VideoEngine] Mixed sub-bass riser build-up SFX across {scene_count} scenes")
                except Exception as e:
                    print(f"[VideoEngine] WARNING: Failed to mix riser SFX: {e}")

            # D. Card Pop SFX at card start times
            if os.path.exists(pop_path):
                try:
                    pop_clip = AudioFileClip(pop_path)
                    pop_clip = pop_clip.multiply_volume(0.15) if hasattr(pop_clip, "multiply_volume") else pop_clip.volumex(0.15)
                    for i in range(scene_count):
                        sc_start = scene_audio_starts[i]
                        audio_clips_to_mix.append(pop_clip.set_start(sc_start + 0.2))
                    print(f"[VideoEngine] Mixed pop.mp3 card pop SFX across {scene_count} scenes")
                except Exception as e:
                    print(f"[VideoEngine] WARNING: Failed to mix pop SFX: {e}")

            # E. Glitch Zap SFX during transitions
            if os.path.exists(zap_path):
                try:
                    zap_clip = AudioFileClip(zap_path)
                    zap_clip = zap_clip.multiply_volume(0.08) if hasattr(zap_clip, "multiply_volume") else zap_clip.volumex(0.08)
                    for i, t_clip in enumerate(transition_clips):
                        t_start = scene_audio_starts[i] + (SCENE_DELAY + scene_audio_durations[i])
                        audio_clips_to_mix.append(zap_clip.set_start(t_start))
                    print(f"[VideoEngine] Mixed zap.mp3 glitch transition SFX across {len(transition_clips)} transitions")
                except Exception as e:
                    print(f"[VideoEngine] WARNING: Failed to mix zap SFX: {e}")

            # F. Cinematic Impact Boom SFX at the start of each scene's narration
            if os.path.exists(impact_path):
                try:
                    impact_clip = AudioFileClip(impact_path)
                    impact_clip = impact_clip.multiply_volume(0.25) if hasattr(impact_clip, "multiply_volume") else impact_clip.volumex(0.25)
                    for i in range(scene_count):
                        sc_start = scene_audio_starts[i]
                        audio_clips_to_mix.append(impact_clip.set_start(sc_start + SCENE_DELAY))
                    print(f"[VideoEngine] Mixed impact.mp3 boom SFX across {scene_count} scenes")
                except Exception as e:
                    print(f"[VideoEngine] WARNING: Failed to mix impact SFX: {e}")

            # G. Crackle SFX for burn transitions
            if os.path.exists(crackle_path) and burn_transition_times:
                try:
                    crackle_clip = AudioFileClip(crackle_path)
                    crackle_clip = crackle_clip.multiply_volume(0.15) if hasattr(crackle_clip, "multiply_volume") else crackle_clip.volumex(0.15)
                    for bt_start in burn_transition_times:
                        audio_clips_to_mix.append(crackle_clip.copy().set_start(bt_start))
                    print(f"[VideoEngine] Mixed crackle.mp3 burn SFX at {len(burn_transition_times)} positions")
                except Exception as e:
                    print(f"[VideoEngine] WARNING: Failed to mix crackle SFX: {e}")

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

            # Mix background low-frequency hum layer (hum.mp3)
            hum_path = os.path.join(self.assets_dir, "sfx", "hum.mp3")
            if os.path.exists(hum_path):
                try:
                    hum_clip = AudioFileClip(hum_path)
                    if hasattr(hum_clip, "subclipped"):
                        hum_sub = hum_clip.subclipped(0, min(hum_clip.duration, video_clip.duration))
                    else:
                        hum_sub = hum_clip.subclip(0, min(hum_clip.duration, video_clip.duration))
                    hum_sub = hum_sub.multiply_volume(0.12) if hasattr(hum_sub, "multiply_volume") else hum_sub.volumex(0.12)
                    audio_clips_to_mix.append(hum_sub)
                    print("[VideoEngine] Mixed low-frequency hum background layer successfully")
                except Exception as hum_err:
                    print(f"[VideoEngine] WARNING: Failed to mix low-frequency hum: {hum_err}")

            mixed_audio = CompositeAudioClip(audio_clips_to_mix)
            video_clip, tmp_files = self._normalize_and_attach_audio(video_clip, mixed_audio, output_name)
            video_clip = self._add_global_progress_bar(video_clip, st)

            codec = "h264_nvenc" if self.has_cuda else "libx264"
            threads = os.cpu_count() or 4

            print(f"[VideoEngine] Starting rendering process (codec={codec}, threads={threads})...")
            video_clip.write_videofile(
                output_video_path,
                fps=25,
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
            # Clean up temp files
            for f_path in tmp_files:
                if os.path.exists(f_path):
                    try:
                        os.remove(f_path)
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

    def _compile_scene_based_video(self, image_paths: List[str], audio_paths: List[str], scene_texts: List[str], scene_labels: List[str], scene_titles: List[str], output_name: str, category: str, style: str, is_bizarre: bool, video_type: str = "myth", mid_roll_word_indices: Optional[set] = None, starting_text: Optional[str] = None, ending_text: Optional[str] = None, topic: Optional[str] = None, episode_num: Optional[int] = None) -> str:
        """
        Compiles a video from 5 audio tracks and 7 video clips:
          [starting bumper] → [scene 1] → [transition 1] → [scene 2] → [transition 2] → [scene 3] → [ending bumper]
        audio_paths: 5-element list [starting_tts, s1_tts, s2_tts, s3_tts, ending_tts]
        scene_texts: 3-element list [s1_text, s2_text, s3_text]  (content scenes only)
        """
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
        tmp_files = []
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
        content_video_clips = []
        transition_clips = []
        burn_transition_times = []
        bg_video_clips = []
        ending_clip = None
        
        try:
            # Load audio tracks
            audio_clips = []
            for i, p in enumerate(audio_paths):
                if not os.path.exists(p):
                    print(f"[VideoEngine] CRITICAL: Audio file missing: {p}")
                audio_clips.append(AudioFileClip(p))
            
            n = len(scene_texts)
            
            # Ensure we have enough labels and titles
            while len(scene_labels) < n:
                scene_labels.append(f"[ SCENE {len(scene_labels)+1} ]")
            while len(scene_titles) < n:
                scene_titles.append(f"SCENE {len(scene_titles)+1}")
            
            if len(audio_paths) == n:
                # Pre-rendered bumpers mode: bumpers are pre-rendered video clips with baked-in audio
                content_audio_clips = audio_clips
                content_durations = [clip.duration for clip in content_audio_clips]
                
                # Load pre-rendered starting bumper directly
                starting_bg = self._select_starting_blueprint(video_type)
                print(f"[VideoEngine] Loading pre-rendered starting bumper: {starting_bg}")
                starting_clip = VideoFileClip(starting_bg)
                starting_dur = starting_clip.duration
                
                # Load pre-rendered ending bumper directly
                ending_bg = self._select_ending_blueprint()
                print(f"[VideoEngine] Loading pre-rendered ending bumper: {ending_bg}")
                ending_clip = VideoFileClip(ending_bg)
                ending_dur = ending_clip.duration
                
                # Setup audio durations representation for timeline alignment
                audio_durations = [0.0] + content_durations + [0.0]
            else:
                # Dynamic bumpers mode: bumpers are generated dynamically from TTS
                content_audio_clips = audio_clips[1:-1]
                content_durations = [clip.duration for clip in content_audio_clips]
                audio_durations = [clip.duration for clip in audio_clips]
                
                starting_clip = self._create_starting_bumper(
                    audio_duration=audio_durations[0],
                    video_type=video_type,
                    style_dict=st,
                    text=starting_text,
                    audio_path=audio_paths[0],
                    episode_num=episode_num
                )
                starting_audio = audio_clips[0]
                starting_clip = starting_clip.with_audio(starting_audio)
                starting_dur = audio_durations[0]
                
                ending_clip = self._create_ending_scene(
                    audio_duration=audio_durations[-1],
                    style_dict=st,
                    text=ending_text,
                    audio_path=audio_paths[-1]
                )
                ending_audio = audio_clips[-1]
                ending_clip = ending_clip.with_audio(ending_audio)
                ending_dur = audio_durations[-1]
            
            print(f"[VideoEngine] Audio durations: starting={starting_dur:.2f}s, n={n} content scenes, ending={ending_dur:.2f}s")
            
            # Resolve background sources for n content scenes
            for i in range(n):
                bg_path = self._select_blueprint_video(scene_texts[i])
                bg_video = None
                if bg_path and os.path.exists(bg_path):
                    try:
                        bg_video = VideoFileClip(bg_path)
                    except Exception as e:
                        print(f"[VideoEngine] Failed to load blueprint video {i+1}: {e}")
                
                if bg_video is None:
                    fallback_img_path = image_paths[i] if i < len(image_paths) else image_paths[-1]
                    bg_video = fallback_img_path
                bg_video_clips.append(bg_video)
            
            # Generate forensic tech cards from ALL available images (grouped per scene for rotation)
            all_cards = []
            for i, img_path in enumerate(image_paths):
                is_truth = (i >= len(image_paths) // 2)  # latter half is truth-side
                label_letter = chr(65 + i)  # A, B, C, D, E...
                label = f"EXHIBIT {label_letter}"
                status = "STATUS: VERIFIED FACT" if is_truth else "STATUS: DEBUNKED MYTH"
                # Assign scene text as caption: cards 0-1→scene0, 2-3→scene1, 4-5→scene2
                scene_for_card = min(i * len(scene_texts) // len(image_paths), len(scene_texts) - 1) if image_paths and scene_texts else 0
                card_caption = scene_texts[scene_for_card] if scene_for_card < len(scene_texts) else ""
                # Redact key words from caption to build mystery (skip last scene — truth reveal)
                if scene_for_card < len(scene_texts) - 1 and card_caption:
                    card_caption = self._redact_text(card_caption, redact_ratio=0.4)
                card = self._generate_card(
                    image_path=img_path,
                    label_text=label,
                    status_text=status,
                    is_truth=is_truth,
                    style_dict=st,
                    topic=topic or "",
                    add_redactions=(i == 0),
                    card_text=card_caption
                )
                all_cards.append(card)
            
            # Group cards per scene: distribute images evenly across n scenes
            cards_per_scene = [[] for _ in range(n)]
            for ci, card in enumerate(all_cards):
                scene_for_card = min(ci * n // len(all_cards), n - 1) if all_cards else 0
                if card is not None:
                    cards_per_scene[scene_for_card].append(card)
            # Ensure each scene has at least 1 card
            for si in range(n):
                if not cards_per_scene[si] and all_cards:
                    if all_cards[-1] is not None:
                        cards_per_scene[si].append(all_cards[-1])
            
            print(f"[VideoEngine] Cards per scene: {[len(c) for c in cards_per_scene]}, all_cards total: {len(all_cards)}, st keys: {list(st.keys())[:5]}...")
            
            # Calculate scene timelines
            scene_timelines = []
            current_time = starting_dur
            
            for i in range(n):
                scene_start = current_time
                # All scenes: narration starts immediately, card pops in during first words
                scene_dur = content_durations[i]
                    
                scene_timelines.append({
                    "start": scene_start,
                    "duration": scene_dur,
                    "has_card": (i < n - 1)
                })
                
                # Advance current time by scene duration
                current_time += scene_dur
                
                # Transition delay between content scenes (shortened for pacing)
                if i < n - 1:
                    current_time += 0.2
                    
            ending_start = current_time
            ending_dur = ending_clip.duration
            
            # ---- Create content scene and transition clips ----
            for i in range(n):
                timeline = scene_timelines[i]
                if timeline["has_card"]:
                    scene_card_images = cards_per_scene[i] if cards_per_scene[i] else None
                    delay_offset = 0.0
                    y_pos = 330
                else:
                    # Last scene: use its cards as a static overlay (no pop delay)
                    scene_card_images = cards_per_scene[-1] if cards_per_scene else None
                    delay_offset = 0.0
                    y_pos = 1400
                    
                scene_clip = self._create_scene_clip(
                    bg_source=bg_video_clips[i],
                    card_images=scene_card_images,
                    audio_duration=content_durations[i],
                    text=scene_texts[i],
                    delay_offset=delay_offset,
                    y_pos=y_pos,
                    scene_idx=i,
                    scene_label=scene_labels[i],
                    scene_title=scene_titles[i],
                    style_dict=st,
                    audio_clip=content_audio_clips[i],
                    mid_roll_word_indices=mid_roll_word_indices,
                    is_last_scene=(i == n - 1),
                    audio_path=audio_paths[i+1] if len(audio_paths) == n + 2 else audio_paths[i],
                    # Sprint B: Emotion beats + File Stamp + Category theme
                    emotion_beats=self._generate_emotion_beats(scene_texts[i], i, content_durations[i], delay_offset),
                    stamp_text=(lambda lbl: "DEBUNKED" if "MYTH" in (lbl or "").upper() else "ANOMALOUS" if "ANOMAL" in (lbl or "").upper() else "VERIFIED")(scene_labels[i] if i == n - 1 else None),
                    category=category,
                )
                
                # We do not set the audio on individual content video clips to prevent MoviePy from dropping offsets.
                
                # ── Color Temperature Tint (v2.1) ──────────────────────────
                # Scene 2 (explanation/mechanism): warm amber — builds trust
                # Scene 3 (truth/reveal): cold blue — clinical, harsh truth
                if i == 1 and not is_bizarre:
                    try:
                        from moviepy.editor import CompositeVideoClip
                    except ImportError:
                        from moviepy import CompositeVideoClip
                    tint = self._create_color_tint((1080, 1920), content_durations[i], warm=True)
                    scene_clip = CompositeVideoClip([scene_clip, tint])
                elif i == 2 and not is_bizarre:
                    try:
                        from moviepy.editor import CompositeVideoClip
                    except ImportError:
                        from moviepy import CompositeVideoClip
                    # Fade in the cold blue tint over 1.5s for dramatic truth reveal
                    tint = self._create_color_tint_animated((1080, 1920), content_durations[i], warm=False, fade_duration=1.5)
                    scene_clip = CompositeVideoClip([scene_clip, tint])
                
                content_video_clips.append(scene_clip)
                
                # If not the last scene, create transition clip
                if i < n - 1:
                    use_burn = random.random() < 0.5
                    flash_mem = all_cards[i] if i < len(all_cards) else None  # previous scene card
                    if use_burn:
                        t_clip = self._create_burn_transition_clip(bg_source=bg_video_clips[i+1], duration=0.75, flash_image=flash_mem)
                        burn_transition_times.append(scene_timelines[i]["start"] + scene_timelines[i]["duration"])
                    else:
                        t_clip = self._create_transition_clip(bg_source=bg_video_clips[i+1], duration=0.5, flash_image=flash_mem)
                    transition_clips.append(t_clip)
                    
            # ---- Concatenate all clips ----
            clips_to_concatenate = [starting_clip]
            for i in range(n):
                clips_to_concatenate.append(content_video_clips[i])
                if i < n - 1:
                    clips_to_concatenate.append(transition_clips[i])
            clips_to_concatenate.append(ending_clip)
            
            video_clip = concatenate_videoclips(clips_to_concatenate)
            
            # Speaking blocks for ducking (starting, content scenes, ending)
            speaking_blocks = [(0.0, starting_dur)]
            for i in range(n):
                timeline = scene_timelines[i]
                speech_start = timeline["start"]
                speech_end = timeline["start"] + timeline["duration"]
                speaking_blocks.append((speech_start, speech_end))
            speaking_blocks.append((ending_start, ending_start + ending_dur))
            
            audio_clips_to_mix = [video_clip.audio]
            
            # Mix content scene narration manually to align perfectly with subtitle frames
            for i in range(n):
                timeline = scene_timelines[i]
                audio_clips_to_mix.append(content_audio_clips[i].copy().set_start(timeline["start"]))
            
            # Load SFX files
            sfx_dir = os.path.join(self.assets_dir, "sfx")
            zap_path = os.path.join(sfx_dir, "zap.mp3")
            pop_path = os.path.join(sfx_dir, "pop.mp3")
            stamp_path = os.path.join(sfx_dir, "stamp.mp3")
            tick_path = os.path.join(sfx_dir, "tick.mp3")
            impact_path = os.path.join(sfx_dir, "impact.mp3")
            riser_path = os.path.join(sfx_dir, "riser.mp3")
            crackle_path = os.path.join(sfx_dir, "crackle.mp3")

            # A. Stamp SFX at 0.4s (in starting bumper) and card reveal scenes
            if os.path.exists(stamp_path):
                try:
                    stamp_clip = AudioFileClip(stamp_path)
                    stamp_clip = stamp_clip.multiply_volume(0.25) if hasattr(stamp_clip, "multiply_volume") else stamp_clip.volumex(0.25)
                    audio_clips_to_mix.append(stamp_clip.set_start(0.4))
                    for i in range(1, n - 1):
                        timeline = scene_timelines[i]
                        audio_clips_to_mix.append(stamp_clip.copy().set_start(timeline["start"] + 0.4))
                    print("[VideoEngine] Mixed stamp.mp3 slam SFX")
                except Exception as e:
                    print(f"[VideoEngine] WARNING: Failed to mix stamp SFX: {e}")
                    
            # B. Quick Card Pop SFX at the start of each card scene
            if os.path.exists(pop_path):
                try:
                    pop_clip = AudioFileClip(pop_path)
                    pop_clip = pop_clip.multiply_volume(0.15) if hasattr(pop_clip, "multiply_volume") else pop_clip.volumex(0.15)
                    for i in range(n):
                        timeline = scene_timelines[i]
                        if timeline["has_card"]:
                            audio_clips_to_mix.append(pop_clip.copy().set_start(timeline["start"] + 0.2))
                    print("[VideoEngine] Mixed pop.mp3 card pop SFX")
                except Exception as e:
                    print(f"[VideoEngine] WARNING: Failed to mix pop SFX: {e}")
                    
            # E. Glitch Zap SFX during transitions
            if os.path.exists(zap_path):
                try:
                    zap_clip = AudioFileClip(zap_path)
                    zap_clip = zap_clip.multiply_volume(0.08) if hasattr(zap_clip, "multiply_volume") else zap_clip.volumex(0.08)
                    for i in range(n - 1):
                        timeline = scene_timelines[i]
                        transition_start = timeline["start"] + timeline["duration"]
                        audio_clips_to_mix.append(zap_clip.copy().set_start(transition_start))
                    print("[VideoEngine] Mixed zap.mp3 glitch transition SFX")
                except Exception as e:
                    print(f"[VideoEngine] WARNING: Failed to mix zap SFX: {e}")
                    
            # F. Cinematic Impact Boom SFX at the start of Scene 3 truth reveal
            if os.path.exists(impact_path):
                try:
                    impact_clip = AudioFileClip(impact_path)
                    impact_clip = impact_clip.multiply_volume(0.25) if hasattr(impact_clip, "multiply_volume") else impact_clip.volumex(0.25)
                    if n > 1:
                        # Final content scene (index n-1) is the reveal/verdict
                        timeline_reveal = scene_timelines[n-1]
                        audio_clips_to_mix.append(impact_clip.set_start(timeline_reveal["start"]))
                        print(f"[VideoEngine] Mixed impact.mp3 boom SFX at reveal start: {timeline_reveal['start']:.2f}s")
                except Exception as e:
                    print(f"[VideoEngine] WARNING: Failed to mix impact SFX: {e}")

            # G. Crackle SFX for burn transitions
            if os.path.exists(crackle_path) and burn_transition_times:
                try:
                    crackle_clip = AudioFileClip(crackle_path)
                    crackle_clip = crackle_clip.multiply_volume(0.15) if hasattr(crackle_clip, "multiply_volume") else crackle_clip.volumex(0.15)
                    for bt_start in burn_transition_times:
                        audio_clips_to_mix.append(crackle_clip.copy().set_start(bt_start))
                    print(f"[VideoEngine] Mixed crackle.mp3 burn SFX at {len(burn_transition_times)} positions")
                except Exception as e:
                    print(f"[VideoEngine] WARNING: Failed to mix crackle SFX: {e}")

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
                        
                        # Silence Beat (pre-reveal tension before scene 3)
                        if len(scene_timelines) > 2:
                            s2_end = scene_timelines[1]["start"] + scene_timelines[1]["duration"]
                            silence_start = s2_end - 0.3
                            silence_end = s2_end + 0.4
                            if silence_start <= t_val <= silence_end:
                                if t_val < s2_end:
                                    # Ramp down from vol_min to 0.0
                                    factor = (s2_end - t_val) / 0.3
                                    return vol_min * factor
                                else:
                                    return 0.0
                            elif silence_end < t_val < silence_end + 0.3:
                                # Ramp up from 0.0 to vol_min
                                factor = (t_val - silence_end) / 0.3
                                return vol_min * factor
                                
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
                    
            # Mix category-specific ambient sound layer (replaces general hum.mp3)
            category_lower = category.lower()
            if "biology" in category_lower or "science" in category_lower or "medicine" in category_lower:
                ambient_name = "ambient_science.mp3"
                ambient_vol = 0.04
            elif "history" in category_lower or "archeology" in category_lower or "social" in category_lower:
                ambient_name = "ambient_history.mp3"
                ambient_vol = 0.04
            elif "space" in category_lower or "astronomy" in category_lower or "physics" in category_lower:
                ambient_name = "ambient_space.mp3"
                ambient_vol = 0.04
            elif "tech" in category_lower or "comput" in category_lower:
                ambient_name = "ambient_tech.mp3"
                ambient_vol = 0.04
            else:
                ambient_name = "hum.mp3"
                ambient_vol = 0.03
                
            ambient_path = os.path.join(self.assets_dir, "sfx", ambient_name)
            if os.path.exists(ambient_path):
                try:
                    ambient_clip = AudioFileClip(ambient_path)
                    if hasattr(ambient_clip, "subclipped"):
                        ambient_sub = ambient_clip.subclipped(0, min(ambient_clip.duration, video_clip.duration))
                    else:
                        ambient_sub = ambient_clip.subclip(0, min(ambient_clip.duration, video_clip.duration))
                    ambient_sub = ambient_sub.multiply_volume(ambient_vol) if hasattr(ambient_sub, "multiply_volume") else ambient_sub.volumex(ambient_vol)
                    audio_clips_to_mix.append(ambient_sub)
                    print(f"[VideoEngine] Mixed category-specific ambient loop: {ambient_name} (volume={ambient_vol:.2f})")
                except Exception as ambient_err:
                    print(f"[VideoEngine] WARNING: Failed to mix ambient hum: {ambient_err}")

            mixed_audio = CompositeAudioClip(audio_clips_to_mix)
            video_clip, tmp_files = self._normalize_and_attach_audio(video_clip, mixed_audio, output_name)
            video_clip = self._add_global_progress_bar(video_clip, st)
            
            codec = "h264_nvenc" if self.has_cuda else "libx264"
            threads = os.cpu_count() or 4
            
            print(f"[VideoEngine] Starting rendering process (codec={codec}, threads={threads})...")
            video_clip.write_videofile(
                output_video_path,
                fps=25,
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
            # Clean up temp files
            for f_path in tmp_files:
                if os.path.exists(f_path):
                    try:
                        os.remove(f_path)
                    except:
                        pass
            for c in audio_clips:
                if c:
                    try:
                        c.close()
                    except:
                        pass
            if starting_clip:
                try:
                    starting_clip.close()
                except:
                    pass
            if ending_clip:
                try:
                    ending_clip.close()
                except:
                    pass
            for clip_ref in content_video_clips:
                if clip_ref:
                    try:
                        clip_ref.close()
                    except:
                        pass
            for clip_ref in transition_clips:
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
            for bg_v in bg_video_clips:
                if bg_v and hasattr(bg_v, "close"):
                    try:
                        bg_v.close()
                    except:
                        pass
            import gc
            gc.collect()

    # ═══════════════════════════════════════════════════════════════════
    # FAST GPU-ACCELERATED RENDERING (FFmpeg + h264_nvenc)
    # ═══════════════════════════════════════════════════════════════════
    # 30-50x faster than MoviePy frame-by-frame.
    # Trade-off: subtitles are SRT-based (no yellow highlight pill on active word).
    # Original _compile_scene_based_video() stays untouched.
    # ═══════════════════════════════════════════════════════════════════

    def compile_short_fast(self, image_myth_path: str, image_truth_path: str,
                           audio_path: Any, script_payload: Dict[str, Any],
                           output_name: str, category: str = "history",
                           style: str = "blueprint", video_type: str = "myth",
                           image_paths_override: Optional[List[str]] = None) -> str:
        """
        GPU-accelerated version of compile_short().
        Same API, same output format, 30-50x faster.
        Uses FFmpeg + h264_nvenc instead of MoviePy frame-by-frame rendering.
        Word-level subtitles are SRT-based (no highlight pill).
        Original compile_short() stays unchanged.
        """
        if not isinstance(audio_path, list):
            raise TypeError("compile_short_fast requires audio_path to be a 5-element list")

        hook = (script_payload.get("s1_ssml") or script_payload.get("hook_ssml")
                or script_payload.get("hook") or "").strip()
        context = (script_payload.get("s2_ssml") or script_payload.get("context_ssml")
                   or script_payload.get("context") or "").strip()
        fact = (script_payload.get("s3_ssml") or script_payload.get("fact_ssml")
                or script_payload.get("fact") or "").strip()

        scene_texts = [hook, context, fact]
        scene_labels = ["[ DECLASSIFIED MYTH ]", "[ VERIFIED FACT ]", "[ FINAL LESSON ]"]
        scene_titles = ["THE MYTH", "THE TRUTH", "THE VERDICT"]

        if image_paths_override and len(image_paths_override) >= 3:
            image_paths = image_paths_override[:3]
        else:
            image_paths = [
                image_myth_path,
                image_truth_path or image_myth_path,
                image_truth_path or image_myth_path
            ]

        starting_text = script_payload.get("starting_text")
        ending_text = script_payload.get("ending_text")

        return self._compile_scene_based_video_fast(
            image_paths=image_paths, audio_paths=audio_path,
            scene_texts=scene_texts, scene_labels=scene_labels,
            scene_titles=scene_titles, output_name=output_name,
            category=category, style=style, is_bizarre=False,
            video_type=video_type, starting_text=starting_text,
            ending_text=ending_text, topic=script_payload.get("topic"),
            episode_num=script_payload.get("episode_num"),
            script_payload=script_payload
        )

    def compile_bizarre_fast(self, image_paths: List[str], audio_path: Any,
                              script_payload: Dict[str, Any], output_name: str,
                              category: str = "history", style: str = "blueprint",
                              video_type: str = "bizarre") -> str:
        """
        GPU-accelerated version of compile_bizarre().
        Same API, same output, 30-50x faster via FFmpeg + h264_nvenc.
        """
        if not isinstance(audio_path, list):
            raise TypeError("compile_bizarre_fast requires audio_path to be a 5-element list")

        hook = (script_payload.get("s1_ssml") or script_payload.get("hook_ssml")
                or script_payload.get("hook") or "").strip()
        why_bizarre = (script_payload.get("s2_ssml") or script_payload.get("why_bizarre_ssml")
                       or script_payload.get("why_bizarre") or "").strip()
        closing = (script_payload.get("s3_ssml") or script_payload.get("closing_statement_ssml")
                   or script_payload.get("closing_statement") or "").strip()

        scene_texts = [hook, why_bizarre, closing]
        scene_labels = ["[ THE STORY ]", "[ WHY IT IS BIZARRE ]", "[ FINAL VERDICT ]"]
        scene_titles = ["THE STORY", "WHY IT'S BIZARRE", "THE VERDICT"]

        imgs = list(image_paths)
        while len(imgs) < 3:
            imgs.append(imgs[-1] if imgs else "")

        starting_text = script_payload.get("starting_text")
        ending_text = script_payload.get("ending_text")

        return self._compile_scene_based_video_fast(
            image_paths=imgs, audio_paths=audio_path,
            scene_texts=scene_texts, scene_labels=scene_labels,
            scene_titles=scene_titles, output_name=output_name,
            category=category, style=style, is_bizarre=True,
            video_type=video_type, starting_text=starting_text,
            ending_text=ending_text, topic=script_payload.get("topic"),
            episode_num=script_payload.get("episode_num"),
            script_payload=script_payload
        )

    def _compile_scene_based_video_fast(self, image_paths: List[str],
            audio_paths: List[str], scene_texts: List[str],
            scene_labels: List[str], scene_titles: List[str],
            output_name: str, category: str, style: str, is_bizarre: bool,
            video_type: str = "myth", starting_text: Optional[str] = None,
            ending_text: Optional[str] = None, topic: Optional[str] = None,
            episode_num: Optional[int] = None,
            script_payload: Optional[Dict[str, Any]] = None) -> str:
        """
        FFmpeg-accelerated alternative to _compile_scene_based_video().
        Same inputs, same output format. 30-50x faster using GPU encoding.

        Pipeline:
          1. Pre-composite scene backgrounds + cards into static images
          2. Generate word-timed SRT subtitles
          3. Mix all audio (TTS + SFX + background music) via FFmpeg amix
          4. Encode video with h264_nvenc (or libx264 fallback)
          5. Concatenate all segments

        Trade-off: word-level highlighting (yellow pill + 68px scale) is replaced
        by clean SRT word-timed captions. All other CRT effects preserved in the
        pre-composited image.
        """
        st = STYLE_PRESETS.get(style, STYLE_PRESETS["blueprint"])
        import random, subprocess, time, json, re as _re

        # Sanitize output_name: replace unicode dashes and special chars with ASCII
        output_name = _re.sub(r'[\u2013\u2014\u2015]', '-', output_name)  # em/en dash → hyphen
        output_name = _re.sub(r'[^\w\.\-\(\)\[\]]', '_', output_name)  # any other special chars → underscore
        output_name = _re.sub(r'_+', '_', output_name)  # collapse multiple underscores

        self._ensure_sfx_exist()
        output_video_path = os.path.join(self.assets_dir, f"{output_name}.mp4")
        print(f"[VideoEngine][FAST] GPU-accelerated render: {output_video_path}")
        _tstart = time.time()

        # ── Resolve FFmpeg ─────────────────────────────────────────────
        try:
            import imageio_ffmpeg
            ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
            ffprobe = ffmpeg.replace("ffmpeg.exe", "ffprobe.exe") if os.name == 'nt' else ffmpeg.replace("ffmpeg", "ffprobe")
        except Exception:
            ffmpeg = "ffmpeg"
            ffprobe = "ffprobe"

        startupinfo = None
        if os.name == 'nt':
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW

        # Detect NVENC
        try:
            enc_check = subprocess.run([ffmpeg, "-encoders"], capture_output=True, text=True,
                                       timeout=5, startupinfo=startupinfo)
            has_nvenc = "h264_nvenc" in enc_check.stdout
        except Exception:
            has_nvenc = False
        codec = "h264_nvenc" if has_nvenc else "libx264"
        vcodec_args = ["-preset", "p4", "-cq", "21", "-b:v", "10M", "-bufsize", "20M", "-rc", "vbr"] if has_nvenc else ["-preset", "medium", "-crf", "23"]

        n = len(scene_texts)
        while len(scene_labels) < n:
            scene_labels.append(f"[ SCENE {len(scene_labels)+1} ]")
        while len(scene_titles) < n:
            scene_titles.append(f"SCENE {len(scene_titles)+1}")

        # ── Get audio durations ──────────────────────────────────────────
        def _adur(p):
            try:
                r = subprocess.run([ffprobe, "-v", "quiet", "-print_format", "json",
                                    "-show_entries", "format=duration", p],
                                   capture_output=True, text=True, timeout=10, startupinfo=startupinfo)
                return float(json.loads(r.stdout)["format"]["duration"])
            except Exception:
                return 3.0

        audio_durs = [_adur(p) for p in audio_paths]
        s0, s1, s2, s3, s4 = audio_durs  # start, scene1, scene2, scene3, end
        t0 = 0.0
        t1 = s0
        t2 = s0 + s1 + 0.2  # + transition
        t3 = s0 + s1 + 0.2 + s2 + 0.2  # + two transitions
        t4 = s0 + s1 + 0.2 + s2 + 0.2 + s3
        total_dur = s0 + s1 + 0.2 + s2 + 0.2 + s3 + s4

        print(f"[VideoEngine][FAST] Durations: start={s0:.1f}s s1={s1:.1f}s s2={s2:.1f}s s3={s3:.1f}s end={s4:.1f}s total={total_dur:.1f}s")

        # ── STEP A: Pre-composite scene images ─────────────────────────
        print(f"[VideoEngine][FAST] Pre-compositing {n+2} scene frames...")
        from PIL import Image, ImageDraw, ImageFont, ImageFilter

        # Pre-render backgrounds and cards for all scenes
        scene_frames = []
        img_paths = image_paths[:n]
        while len(img_paths) < n:
            img_paths.append(img_paths[-1] if img_paths else None)

        # Generate cards for all images
        all_cards = []
        for ci, ip in enumerate(image_paths):
            if ip and os.path.exists(ip):
                is_truth = (ci >= len(image_paths) // 2)
                card = self._generate_card(
                    image_path=ip,
                    label_text=f"EXHIBIT {chr(65+ci)}",
                    status_text="STATUS: VERIFIED FACT" if is_truth else "STATUS: DEBUNKED MYTH",
                    is_truth=is_truth, style_dict=st, topic=topic or "",
                    add_redactions=(ci == 0)
                )
                all_cards.append(card)
            else:
                all_cards.append(None)

        # Distribute cards per scene
        cards_per_scene = [[] for _ in range(n)]
        for ci, card in enumerate(all_cards):
            si = min(ci * n // len(all_cards), n - 1) if all_cards else 0
            if card is not None:
                cards_per_scene[si].append(card)
        for si in range(n):
            if not cards_per_scene[si] and all_cards:
                cards_per_scene[si].append(all_cards[-1])

        for i in range(n):
            bg_path = img_paths[i]
            canvas = Image.new("RGB", (1080, 1920), (10, 15, 30))
            if bg_path and os.path.exists(bg_path):
                try:
                    bg_img = Image.open(bg_path).convert("RGB")
                    bg_img = bg_img.resize((1080, 1920), Image.Resampling.LANCZOS)
                    bg_img = bg_img.filter(ImageFilter.GaussianBlur(radius=6 if i < 2 else 8))
                    dark_over = Image.new("RGB", (1080, 1920), (10, 15, 30))
                    bg_img = Image.blend(bg_img, dark_over, 0.45)
                    canvas.paste(bg_img, (0, 0))
                except Exception:
                    pass

            # Composite cards on canvas
            if cards_per_scene[i]:
                y_off = 330 if i < n - 1 else 1400
                for card_img in cards_per_scene[i]:
                    if card_img is not None:
                        cw, ch = card_img.size
                        cx = (1080 - cw) // 2
                        cy = y_off
                        if card_img.mode == 'RGBA':
                            canvas.paste(card_img, (cx, cy), card_img)
                        else:
                            canvas.paste(card_img, (cx, cy))

            # Scene label overlay
            try:
                lbl_font = ImageFont.truetype(self.font_path, 28)
            except Exception:
                lbl_font = ImageFont.load_default()
            lbl_draw = ImageDraw.Draw(canvas)
            lbl_draw.text((30, 1850), scene_labels[i], fill=(255, 255, 255, 180), font=lbl_font)

            # Static easter egg (70% of scenes)
            if random.random() < 0.70:
                positions = [(50, 1600), (900, 100), (500, 500), (800, 1400), (100, 300), (950, 1000)]
                pos = random.choice(positions)
                static_small = self._render_static(size=60, expression=random.choice(["neutral", "wink"]))
                if static_small.mode == 'RGBA':
                    canvas.paste(static_small, pos, static_small)
                else:
                    canvas.paste(static_small, pos)

            frame_path = os.path.join(self.assets_dir, f"fast_scene{i}_{output_name}.png")
            canvas.save(frame_path)
            scene_frames.append(frame_path)

        # Create starting bumper image
        start_path = os.path.join(self.assets_dir, f"fast_start_{output_name}.png")
        start_canvas = Image.new("RGB", (1080, 1920), (10, 15, 30))
        if image_paths[0] and os.path.exists(image_paths[0]):
            try:
                si = Image.open(image_paths[0]).convert("RGB").resize((1080, 1920), Image.Resampling.LANCZOS)
                si = si.filter(ImageFilter.GaussianBlur(radius=3))
                si = Image.blend(si, Image.new("RGB", (1080, 1920), (10, 15, 30)), 0.5)
                start_canvas.paste(si, (0, 0))
            except Exception:
                pass
        try:
            sfont = ImageFont.truetype(self.font_path, 36)
            sfont_s = ImageFont.truetype(self.font_path, 28)
        except Exception:
            sfont = sfont_s = ImageFont.load_default()
        sd = ImageDraw.Draw(start_canvas)
        if starting_text:
            sd.text((540, 1600), f"\"{starting_text}\"", fill=(255, 60, 60), font=sfont, anchor="mt")
        start_canvas.save(start_path)

        # Create ending bumper image
        end_path = os.path.join(self.assets_dir, f"fast_end_{output_name}.png")
        end_canvas = Image.new("RGB", (1080, 1920), (10, 15, 30))
        ed = ImageDraw.Draw(end_canvas)
        if ending_text:
            ed.text((540, 900), f"\"{ending_text}\"", fill=(255, 242, 0), font=sfont, anchor="mt")
        ed.text((540, 1200), "#TheDailyAudit", fill=(0, 242, 254), font=sfont_s, anchor="mt")
        end_canvas.save(end_path)

        print(f"[VideoEngine][FAST] Scene frames: {(time.time()-_tstart):.1f}s")

        # ── STEP B: Generate word-timed SRT subtitles ───────────────────
        print(f"[VideoEngine][FAST] Generating SRT subtitles...")
        srt_path = os.path.join(self.assets_dir, f"fast_{output_name}.srt")

        # Build word timing from scene texts and audio durations
        srt_entries = []
        entry_num = 1

        scene_durs = [s0, s1, s2, s3, s4]
        scene_starts = [t0, t1, t2, t3, t4]
        scene_texts_all = [starting_text or ""] + scene_texts + [ending_text or ""]

        for si in range(5):  # 5 segments
            txt = scene_texts_all[si]
            if not txt:
                continue
            words = txt.split()
            if not words:
                continue
            dur = scene_durs[si]
            start = scene_starts[si]
            char_total = sum(len(w) for w in words)
            sec_per_char = dur / char_total if char_total > 0 else 0.05

            # First entry: show the scene label for 1.5s
            label_text = {
                0: "▶ STARTING BUMPER",
                1: f"▶ {scene_labels[0]}" if len(scene_labels) > 0 else "▶ SCENE 1",
                2: f"▶ {scene_labels[1]}" if len(scene_labels) > 1 else "▶ SCENE 2",
                3: f"▶ {scene_labels[2]}" if len(scene_labels) > 2 else "▶ SCENE 3",
                4: "▶ ENDING",
            }.get(si, f"▶ SCENE {si}")

            def _srt_time(sec):
                h = int(sec // 3600)
                m = int((sec % 3600) // 60)
                s = int(sec % 60)
                ms = int((sec - int(sec)) * 1000)
                return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"

            srt_entries.append(f"{entry_num}")
            lbl_end = start + min(1.5, dur * 0.2)
            srt_entries.append(f"{_srt_time(start)} --> {_srt_time(lbl_end)}")
            srt_entries.append(label_text)
            srt_entries.append("")
            entry_num += 1

            # Word-by-word subtitles
            current_time = lbl_end
            chunk_size = 4
            word_groups = [words[j:j+chunk_size] for j in range(0, len(words), chunk_size)]
            for wg in word_groups:
                wg_chars = sum(len(w) for w in wg)
                wg_dur = max(0.5, wg_chars * sec_per_char)
                wg_end = current_time + wg_dur
                if wg_end > start + dur:
                    wg_end = start + dur
                if wg_end <= current_time:
                    break
                srt_entries.append(f"{entry_num}")
                srt_entries.append(f"{_srt_time(current_time)} --> {_srt_time(wg_end)}")
                srt_entries.append(" ".join(wg))
                srt_entries.append("")
                entry_num += 1
                current_time = wg_end

        with open(srt_path, "w", encoding="utf-8") as f:
            f.write("\n".join(srt_entries))

        # ── STEP C: Mix audio (concatenate TTS, add SFX + music with MoviePy) ──
        print(f"[VideoEngine][FAST] Mixing audio...")
        mixed_audio_path = os.path.join(self.assets_dir, f"fast_mixed_{output_name}.wav")
        sfx_dir = os.path.join(self.assets_dir, "sfx")

        # Quick check: simple audio concat with MoviePy (fast - no frame rendering)
        try:
            from moviepy.editor import AudioFileClip, CompositeAudioClip, concatenate_audioclips
        except ImportError:
            from moviepy import AudioFileClip, CompositeAudioClip, concatenate_audioclips

        # Concatenate TTS files sequentially + mix SFX
        tts_clips = [AudioFileClip(p) for p in audio_paths]
        full_tts = concatenate_audioclips(tts_clips)
        full_dur = full_tts.duration

        audio_to_mix = [full_tts]

        # Stamp at 0.4s
        stamp_p = os.path.join(sfx_dir, "stamp.mp3")
        if os.path.exists(stamp_p):
            s = AudioFileClip(stamp_p).multiply_volume(0.25).with_start(0.4)
            audio_to_mix.append(s)

        # Pop at scene card reveals
        pop_p = os.path.join(sfx_dir, "pop.mp3")
        if os.path.exists(pop_p):
            for t_pos in [s0 + 0.2, s0 + s1 + 0.2 + 0.2]:
                p = AudioFileClip(pop_p).multiply_volume(0.15).with_start(t_pos)
                audio_to_mix.append(p)

        # Zap at transitions
        zap_p = os.path.join(sfx_dir, "zap.mp3")
        if os.path.exists(zap_p):
            for t_pos in [s0 + s1, s0 + s1 + 0.2 + s2]:
                z = AudioFileClip(zap_p).multiply_volume(0.08).with_start(t_pos)
                audio_to_mix.append(z)

        # Background music
        bg_music_path = self._resolve_theme_music(category)
        if bg_music_path:
            bg = AudioFileClip(bg_music_path)
            if bg.duration < full_dur:
                bg = bg.loop(duration=full_dur)
            else:
                bg = bg.subclip(0, full_dur)
            bg = bg.multiply_volume(0.08)
            audio_to_mix.append(bg)

        # Mix everything
        mixed = CompositeAudioClip(audio_to_mix)
        mixed.write_audiofile(mixed_audio_path, fps=44100)

        # Clean up
        for c in tts_clips:
            try: c.close()
            except: pass
        for c in audio_to_mix[1:]:
            try: c.close()
            except: pass
        mixed.close()
        full_tts.close()

        print(f"[VideoEngine][FAST] Audio mixed: {(time.time()-_tstart):.1f}s")

        # ── STEP D: Encode video with FFmpeg ─────────────────────────────
        print(f"[VideoEngine][FAST] Encoding video with {codec}...")

        # Images + durations for each scene
        img_durations = [
            (start_path, s0, "start"),
            (scene_frames[0], s1, "scene1"),
            (scene_frames[0], 0.2, "trans1"),
            (scene_frames[1], s2, "scene2"),
            (scene_frames[1], 0.2, "trans2"),
            (scene_frames[2], s3, "scene3"),
            (end_path, s4, "end"),
        ]

        # Encode each image as a video loop (FFmpeg concat demuxer only gives
        # 1 frame per image — we need -loop 1 -t DURATION to duplicate frames)
        temp_videos = []
        for idx, (img_path, dur, _label) in enumerate(img_durations):
            temp_path = os.path.join(self.assets_dir,
                                     f"fast_seg{idx}_{output_name}.mp4")
            seg_cmd = [
                ffmpeg, "-y",
                "-stream_loop", "-1", "-i", img_path,
                "-t", str(dur),
                "-r", "30",
                "-c:v", codec,
            ] + vcodec_args + [
                "-pix_fmt", "yuv420p",
                "-an",  # no audio in segments
                temp_path
            ]
            r = subprocess.run(seg_cmd, startupinfo=startupinfo,
                               capture_output=True, text=True, timeout=120)
            if r.returncode != 0:
                print(f"[VideoEngine][FAST] Segment {idx} encode FAILED: {r.stderr[-300:]}")
                raise RuntimeError(f"Segment {idx} ({_label}) encoding failed")
            temp_videos.append(temp_path)

        # Write concat file for video segments
        import shutil
        vconcat_path = os.path.join(self.assets_dir, f"fast_vconcat_{output_name}.txt")
        with open(vconcat_path, "w") as f:
            for vp in temp_videos:
                f.write(f"file '{vp.replace(os.sep, '/')}'\n")

        # SRT subtitle setup (copy to relative path — FFmpeg subtitles filter
        # chokes on Windows C:\\... colons)
        local_srt_name = f"local_subtitles_{output_name}.srt"
        local_srt_abs = os.path.join(self.assets_dir, local_srt_name)
        shutil.copy2(srt_path, local_srt_abs)
        rel_assets = os.path.basename(self.assets_dir)  # "assets"
        rel_srt = os.path.join(rel_assets, local_srt_name).replace(os.sep, '/')
        vf_filter = f"subtitles={rel_srt}"

        # Final: concat video segments + audio + burn subtitles
        encode_cmd = [
            ffmpeg, "-y",
            "-f", "concat", "-safe", "0", "-i", vconcat_path,
            "-i", mixed_audio_path,
            "-vf", vf_filter,
            "-c:v", codec,
        ] + vcodec_args + [
            "-c:a", "aac", "-b:a", "128k",
            "-pix_fmt", "yuv420p",
            "-movflags", "+faststart",
            "-shortest",
            output_video_path
        ]
        result = subprocess.run(encode_cmd, startupinfo=startupinfo,
                                capture_output=True, text=True,
                                timeout=600)
        if result.returncode != 0:
            print(f"[VideoEngine][FAST] FFmpeg final encode FAILED (exit {result.returncode})")
            print(f"[VideoEngine][FAST] STDERR: {result.stderr[-1000:]}")
            raise RuntimeError(f"FFmpeg encoding failed: {result.stderr[-500:]}")
        print(f"[VideoEngine][FAST] FFmpeg encode OK")
        if result.stderr.strip():
            stderr_lines = result.stderr.strip().splitlines()
            for line in stderr_lines[-3:]:
                print(f"[VideoEngine][FAST] FFmpeg: {line.strip()}")

        # Clean up temp segment files
        for vp in temp_videos:
            try:
                os.remove(vp)
            except Exception:
                pass
        try:
            os.remove(vconcat_path)
        except Exception:
            pass

        total_time = time.time() - _tstart
        print(f"[VideoEngine][FAST] Render complete: {output_video_path} ({total_time:.1f}s total)")
        return output_video_path


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

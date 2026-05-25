# =============================================================================
# "The Daily Audit" - Long-Form Video Pipeline (10-Minute Educational)
# =============================================================================
# Completely standalone from main.py. Builds a 16:9 landscape long-form video
# with deep research, chapter-by-chapter teaching, and private draft uploads.
#
# Pipeline:
#   1. Select a topic (myth or deep-dive suitable for 10 min)
#   2. Gemini 2.5 Pro researches deeply + writes 8-12 chapter script
#   3. Edge TTS generates narration per chapter
#   4. Wikipedia scraping + Imagen fallback per chapter
#   5. VideoEngine card generation for each chapter
#   6. FFmpeg composes: intro → chapters with Ken Burns → outro
#   7. Private draft upload to YouTube + draft to Facebook
#   8. Output: video file, SRT subtitles, chapter timestamps text
# =============================================================================

import os
import sys
import json
import time
import random
import datetime
import subprocess
import re
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# ── Imports from the existing app_build modules ──────────────────────────
from data_ingestion import DataIngestion
from llm_orchestrator import LLMOrchestrator
from asset_generator import AssetGenerator
from video_engine import VideoEngine, STYLE_PRESETS
from data_scraper import DataScraper
from youtube_uploader import YouTubeUploader
from facebook_uploader import FacebookUploader
from analytics_logger import AnalyticsLogger

# ── Constants ────────────────────────────────────────────────────────────
WIDTH, HEIGHT = 1920, 1080  # 16:9 landscape
FPS = 30
TARGET_DURATION_SEC = 600  # ~10 minutes

# The Daily Audit intro bumper text rotation
INTRO_TEXTS = [
    "The Daily Audit",
    "Classified File Opened",
    "Case File: Declassified",
]

OUTRO_TEXTS = [
    "Thanks for watching.",
    "Subscribe for the next declassified file.",
    "The truth never sleeps. Neither do we.",
]

# Style preset (blueprint is the default)
DEFAULT_STYLE = "blueprint"


# ── Helper: Resolve FFmpeg executable ───────────────────────────────────
def _get_ffmpeg():
    """Resolve ffmpeg path, preferring imageio_ffmpeg bundled copy."""
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        return "ffmpeg"


def _get_ffprobe():
    """Resolve ffprobe path."""
    ffmpeg = _get_ffmpeg()
    if os.name == 'nt':
        return ffmpeg.replace("ffmpeg.exe", "ffprobe.exe").replace("ffmpeg", "ffprobe.exe")
    return ffmpeg.replace("ffmpeg", "ffprobe")


# ── Helper: Duration from ffprobe ───────────────────────────────────────
def _get_audio_duration(path):
    """Get audio file duration in seconds via ffprobe."""
    ffprobe = _get_ffprobe()
    startupinfo = None
    if os.name == 'nt':
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    try:
        r = subprocess.run(
            [ffprobe, "-v", "quiet", "-print_format", "json",
             "-show_entries", "format=duration", path],
            capture_output=True, text=True, timeout=10, startupinfo=startupinfo
        )
        if r.returncode == 0:
            return float(json.loads(r.stdout)["format"]["duration"])
    except Exception:
        pass
    return 3.0  # fallback


# ── Helper: Build chapter timestamps description ────────────────────────
def _build_chapter_timestamps(chapters: list, chapter_durations: list[float]):
    """Build YouTube chapter timestamp lines."""
    lines = ["\n\n--- CHAPTERS ---"]
    elapsed = 0.0
    for i, (ch, dur) in enumerate(zip(chapters, chapter_durations)):
        mins = int(elapsed // 60)
        secs = int(elapsed % 60)
        lines.append(f"{mins}:{secs:02d} - {ch.title}")
        elapsed += dur
    return "\n".join(lines)


# ── Helper: Generate SRT subtitles for a chapter ────────────────────────
def _generate_chapter_srt(chapter_idx: int, text: str, start_ms: float, duration_ms: float) -> str:
    """Generate a single SRT subtitle entry for the chapter's full text."""
    words = text.split()
    if not words:
        return ""

    total_chars = sum(len(w) for w in words)
    sec_per_char = (duration_ms / 1000.0) / total_chars if total_chars > 0 else 0.05

    lines = []
    entry_num = chapter_idx + 1
    # Show the chapter title for 2 seconds at the start
    title_entry_start = start_ms
    title_entry_end = title_entry_start + min(2000, duration_ms * 0.15)

    lines.append(f"{entry_num}")
    lines.append(f"{_ms_to_srt_time(title_entry_start)} --> {_ms_to_srt_time(title_entry_end)}")
    lines.append(f"[ {chapter_idx + 1}. {text[:80].strip()}... ]")
    lines.append("")

    # Split remaining text into subtitle chunks (max 5 words per subtitle)
    chunk_size = 5
    word_groups = [words[i:i + chunk_size] for i in range(0, len(words), chunk_size)]
    char_offset = 0
    current_ms = title_entry_end
    for gi, group in enumerate(word_groups):
        group_chars = sum(len(w) for w in group)
        group_duration_ms = max(500, group_chars * sec_per_char * 1000)
        entry_num_2 = entry_num + gi + 1
        group_text = " ".join(group)
        end_ms = current_ms + group_duration_ms
        lines.append(f"{entry_num_2}")
        lines.append(f"{_ms_to_srt_time(current_ms)} --> {_ms_to_srt_time(end_ms)}")
        lines.append(group_text)
        lines.append("")
        current_ms = end_ms

    return "\n".join(lines)


def _ms_to_srt_time(ms: float) -> str:
    """Convert milliseconds to SRT time format HH:MM:SS,mmm."""
    total_sec = ms / 1000.0
    hours = int(total_sec // 3600)
    minutes = int((total_sec % 3600) // 60)
    seconds = int(total_sec % 60)
    millis = int((total_sec - int(total_sec)) * 1000)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d},{millis:03d}"


# ── Main Pipeline ─────────────────────────────────────────────────────────
def run_long_pipeline():
    """Executes the complete 10-minute long-form video pipeline."""
    print("=" * 80)
    print("   THE DAILY AUDIT — LONG-FORM VIDEO PIPELINE (10 MIN)")
    print("=" * 80)

    # 0. Initialize systems
    timestamp = str(int(time.time()))
    ingestion = DataIngestion()
    gemini_key = (
        os.getenv("FREE_GEMINI_API_KEY")
        or os.getenv("GEMINI_API_KEY")
        or os.getenv("PAID_GEMINI_API_KEY")
    )
    if not gemini_key:
        print("[main_long] CRITICAL: No Gemini API key found.")
        sys.exit(1)

    orchestrator = LLMOrchestrator(api_key=gemini_key)
    client_ref = orchestrator.client if hasattr(orchestrator, "client") else None
    style = DEFAULT_STYLE
    st = STYLE_PRESETS.get(style, STYLE_PRESETS["blueprint"])

    # ── STEP 1: Select Topic ─────────────────────────────────────────────
    # Try to fetch a myth topic first (deep enough for 10 min)
    topic = None
    category = None
    try:
        topic, category, description = ingestion.fetch_unused_misconception(
            gemini_client=client_ref, category_filter=None,
        )
        print(f"[main_long] Selected Myth Topic: '{topic}' | Category: {category}")
    except Exception as e:
        print(f"[main_long] No myth topic available ({e}). Trying bizarre topic...")
        try:
            topic, category, description = ingestion.fetch_unused_bizarre_topic(
                gemini_client=client_ref, category_filter=None,
            )
            print(f"[main_long] Selected Bizarre Topic: '{topic}' | Category: {category}")
        except Exception as e2:
            print(f"[main_long] CRITICAL: No topics available: {e2}")
            sys.exit(1)

    # Reserve topic so it's not picked by Shorts pipeline
    ingestion.log_uploaded_topic(topic, "")

    # ── STEP 2: Gemini 2.5 Pro Deep Research + Script Generation ─────────
    print(f"\n{'=' * 80}")
    print(f"   STEP 2: GENERATING LONG-FORM SCRIPT — '{topic}'")
    print(f"{'=' * 80}")

    try:
        script = orchestrator.generate_long_script(topic, category)
    except Exception as e:
        print(f"[main_long] CRITICAL: Long-form script generation failed: {e}")
        sys.exit(1)

    chapters = script.chapters
    num_chapters = len(chapters)
    print(f"[main_long] Script generated: {num_chapters} chapters, climax ready.")

    # ── STEP 3: Generate TTS Audio Per Chapter ───────────────────────────
    print(f"\n{'=' * 80}")
    print(f"   STEP 3: GENERATING TTS AUDIO ({num_chapters} CHAPTERS)")
    print(f"{'=' * 80}")

    try:
        gcp_cred = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
        asset_gen = AssetGenerator(gemini_client=client_ref, gcp_credentials_path=gcp_cred)
    except Exception as e:
        print(f"[main_long] CRITICAL: Asset generator init failed: {e}")
        sys.exit(1)

    # Intro TTS
    intro_text = random.choice(INTRO_TEXTS)
    try:
        intro_audio = asset_gen.generate_tts_audio(
            f"<prosody pitch='0st' rate='0.95'>{intro_text}. Today, we audit: {topic}.</prosody>",
            f"long_intro_{timestamp}", is_ssml=True
        )
        print(f"[main_long] Intro TTS: '{intro_text}'")
    except Exception as e:
        print(f"[main_long] WARNING: Intro TTS failed: {e}")
        intro_audio = None

    # Chapter TTS
    chapter_audios = []
    for i, ch in enumerate(chapters):
        try:
            # Use per-scene prosody similar to main.py (subtle variation)
            rate = 0.97 if i < num_chapters // 3 else (0.95 if i < num_chapters * 2 // 3 else 0.93)
            pitch = "0st" if i < num_chapters * 2 // 3 else "-0.5st"
            ssml = f"<prosody pitch='{pitch}' rate='{rate}'>{ch.content}</prosody>"
            path = asset_gen.generate_tts_audio(
                ssml, f"long_ch{i}_{timestamp}", is_ssml=True
            )
            chapter_audios.append(path)
            print(f"[main_long] Ch.{i+1} '{ch.title}': TTS generated ({len(ch.content.split())} words)")
        except Exception as e:
            print(f"[main_long] WARNING: Ch.{i+1} TTS failed: {e}. Generating silent placeholder...")
            silent = asset_gen._generate_silent_placeholder(
                os.path.join(asset_gen.assets_dir, f"long_ch{i}_{timestamp}.mp3"),
                duration_ms=max(3000, len(ch.content) * 60)
            )
            chapter_audios.append(silent)

    # Outro TTS
    outro_text = random.choice(OUTRO_TEXTS)
    climax = script.climax
    try:
        outro_audio = asset_gen.generate_tts_audio(
            f"<prosody pitch='0st' rate='0.95'>{climax} {outro_text} "
            f"This has been The Daily Audit. The truth doesn't change. Subscribe so you never miss it.</prosody>",
            f"long_outro_{timestamp}", is_ssml=True
        )
        print(f"[main_long] Outro TTS generated (climax included)")
    except Exception as e:
        print(f"[main_long] WARNING: Outro TTS failed: {e}")
        outro_audio = None

    # ── STEP 4: Fetch Images Per Chapter ─────────────────────────────────
    print(f"\n{'=' * 80}")
    print(f"   STEP 4: FETCHING IMAGES ({num_chapters} CHAPTERS)")
    print(f"{'=' * 80}")

    scraper = DataScraper()
    chapter_images = []

    for i, ch in enumerate(chapters):
        img_path = None
        queries = [ch.visual_query, topic]

        for query in queries:
            if not query:
                continue
            try:
                # Try Wikipedia first
                img_path = scraper.fetch_image_multi_source(
                    query, f"long_ch{i}_img_{timestamp}"
                )
                if img_path and os.path.exists(img_path):
                    print(f"[main_long] Ch.{i+1}: Wikipedia image found: '{query}'")
                    break
            except Exception:
                img_path = None

        # Fallback: generate with Imagen
        if not img_path or not os.path.exists(img_path):
            try:
                safe_suffix = " No human faces, no political content, no violence, no text, safe for all ages."
                img_path = asset_gen.generate_background_image(
                    f"Educational illustration of {ch.title}, {topic}. {safe_suffix}",
                    f"long_ch{i}_fallback_{timestamp}",
                    aspect_ratio="16:9",
                    is_blueprint=True,
                    style_suffix=st["bg_prompt_suffix"]
                )
                print(f"[main_long] Ch.{i+1}: Imagen fallback generated")
            except Exception as img_err:
                print(f"[main_long] WARNING: Ch.{i+1} image failed: {img_err}")
                img_path = None

        chapter_images.append(img_path)

    # ── STEP 5: Generate Visual Cards (using VideoEngine) ────────────────
    print(f"\n{'=' * 80}")
    print(f"   STEP 5: GENERATING CHAPTER CARDS")
    print(f"{'=' * 80}")

    video_engine = VideoEngine()
    chapter_cards = []

    for i, ch in enumerate(chapters):
        img_path = chapter_images[i]
        if not img_path or not os.path.exists(img_path):
            # Use the first available image
            fallback = next((p for p in chapter_images if p and os.path.exists(p)), None)
            if fallback:
                img_path = fallback
            else:
                img_path = chapter_images[i]  # keep None

        try:
            label_letter = chr(65 + i)  # A, B, C...
            card = video_engine._generate_card(
                image_path=img_path,
                label_text=f"CHAPTER {i+1}: {ch.title.upper()}",
                status_text=f"EXHIBIT {label_letter}",
                is_truth=(i >= num_chapters // 2),
                style_dict=st,
                topic=topic,
                add_redactions=(i == 0),
                card_text=ch.key_takeaway,
            )
            chapter_cards.append(card)
            print(f"[main_long] Ch.{i+1} card generated: {ch.title}")
        except Exception as e:
            print(f"[main_long] WARNING: Ch.{i+1} card failed: {e}")
            chapter_cards.append(None)

    # Generate Static mascot for intro/outro
    static_mascot = video_engine._render_static(size=200, expression="neutral")
    static_path = os.path.join(video_engine.assets_dir, f"static_mascot_long_{timestamp}.png")
    static_mascot.save(static_path)

    # ── STEP 6: Compose Video with FFmpeg ────────────────────────────────
    print(f"\n{'=' * 80}")
    print(f"   STEP 6: COMPOSING VIDEO ({num_chapters} CHAPTERS, 16:9)")
    print(f"{'=' * 80}")

    ffmpeg = _get_ffmpeg()
    assets_dir = video_engine.assets_dir
    output_dir = os.path.join(assets_dir, "long_form")
    os.makedirs(output_dir, exist_ok=True)

    startupinfo = None
    if os.name == 'nt':
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW

    # ── 6a. Build per-chapter video segments ────────────────────────────
    chapter_video_paths = []
    chapter_real_durations = []

    # Get intro audio duration
    intro_dur = _get_audio_duration(intro_audio) if intro_audio else 4.0
    intro_segment = os.path.join(output_dir, f"segment_intro_{timestamp}.mp4")
    chapter_real_durations.append(intro_dur)

    # Create a simple intro: dark background + text overlay + static mascot
    # We'll use a card-style intro with the channel name
    intro_card_path = os.path.join(assets_dir, f"long_intro_card_{timestamp}.png")
    from PIL import Image, ImageDraw, ImageFont, ImageFilter
    intro_card = Image.new("RGB", (WIDTH, HEIGHT), (10, 15, 30))
    draw = ImageDraw.Draw(intro_card)
    try:
        font_large = ImageFont.truetype(video_engine.font_path, 72)
        font_med = ImageFont.truetype(video_engine.font_path, 48)
        font_small = ImageFont.truetype(video_engine.font_path, 36)
    except Exception:
        font_large = ImageFont.load_default()
        font_med = font_large
        font_small = font_large

    # Draw intro card
    title_text = "THE DAILY AUDIT"
    subtitle_text = f"DEEP DIVE: {topic.upper()}"
    t_w = draw.textlength(title_text, font=font_large)
    draw.text(((WIDTH - t_w) // 2, HEIGHT // 3), title_text, fill=(255, 242, 0), font=font_large)
    t_w2 = draw.textlength(subtitle_text, font=font_med)
    draw.text(((WIDTH - t_w2) // 2, HEIGHT // 3 + 100), subtitle_text, fill=(0, 242, 254), font=font_med)
    draw.text((WIDTH // 2 - 200, HEIGHT // 2 + 50), "═══════════════════", fill=(100, 100, 160), font=font_small)
    draw.text((WIDTH // 2 - 200, HEIGHT // 2 + 100), "A Daily Audit Production", fill=(150, 150, 200), font=font_small)

    # Paste Static mascot on the right side
    mascot_resized = static_mascot.resize((300, 300), Image.Resampling.LANCZOS)
    intro_card.paste(mascot_resized, (WIDTH - 380, 50), mascot_resized if mascot_resized.mode == 'RGBA' else None)
    intro_card.save(intro_card_path)

    # Encode intro segment
    intro_filter = (
        f"[0:v]zoompan=z=1.005:d={int(intro_dur * FPS)}:s={WIDTH}x{HEIGHT},fps={FPS}[v]"
    )
    subprocess.run(
        [ffmpeg, "-y", "-loop", "1", "-i", intro_card_path,
         "-i", intro_audio,
         "-filter_complex", intro_filter,
         "-map", "[v]", "-map", "1:a",
         "-c:v", "libx264", "-preset", "medium", "-crf", "23",
         "-c:a", "aac", "-b:a", "128k",
         "-t", str(intro_dur),
         "-pix_fmt", "yuv420p",
         intro_segment],
        startupinfo=startupinfo,
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        timeout=120
    )
    chapter_video_paths.append(intro_segment)
    print(f"[main_long] Intro segment rendered ({intro_dur:.1f}s)")

    # ── 6b. Render each chapter as a separate segment ───────────────────
    for i, ch in enumerate(chapters):
        card_img = chapter_cards[i]
        if card_img is None:
            # Fallback: create a simple text-based card
            fallback_card = Image.new("RGB", (WIDTH, HEIGHT), (10, 15, 30))
            fb_draw = ImageDraw.Draw(fallback_card)
            fb_draw.text((100, HEIGHT // 2 - 50), f"CHAPTER {i+1}: {ch.title}", fill=(255, 255, 255), font=font_large)
            fcard_path = os.path.join(assets_dir, f"long_ch{i}_fallback_card_{timestamp}.png")
            fallback_card.save(fcard_path)
            card_path = fcard_path
        else:
            # Card is RGBA PIL image — paste on dark background
            canvas = Image.new("RGB", (WIDTH, HEIGHT), (10, 15, 30))
            # Scale card to fit — cards are portrait (840x890), center in landscape
            card_resized = card_img.resize((540, 620), Image.Resampling.LANCZOS)
            cx = (WIDTH - 540) // 2
            cy = (HEIGHT - 620) // 2
            if card_resized.mode == 'RGBA':
                canvas.paste(card_resized, (cx, cy), card_resized)
            else:
                canvas.paste(card_resized, (cx, cy))

            # Add chapter title overlay at top
            try:
                ch_font = ImageFont.truetype(video_engine.font_path, 42)
            except Exception:
                ch_font = ImageFont.load_default()
            ch_draw = ImageDraw.Draw(canvas)
            ch_label = f"CHAPTER {i+1}: {ch.title}"
            ct_w = ch_draw.textlength(ch_label, font=ch_font)
            ch_draw.text(((WIDTH - ct_w) // 2, 30), ch_label, fill=(0, 242, 254), font=ch_font)

            # Add takeaway at the bottom
            try:
                tk_font = ImageFont.truetype(video_engine.font_path, 28)
            except Exception:
                tk_font = ImageFont.load_default()
            tk_label = f"▸ {ch.key_takeaway}"
            ch_draw.text((60, HEIGHT - 100), tk_label, fill=(200, 200, 200), font=tk_font)

            card_path = os.path.join(assets_dir, f"long_ch{i}_canvas_{timestamp}.png")
            canvas.save(card_path)

        # Get audio duration
        audio_dur = _get_audio_duration(chapter_audios[i])
        chapter_real_durations.append(audio_dur)

        # Ken Burns slow zoom effect
        ch_segment = os.path.join(output_dir, f"segment_ch{i}_{timestamp}.mp4")
        ch_filter = (
            f"[0:v]zoompan=z='if(lte(zoom,1.0),1.0,zoom+0.002)':"
            f"d={int(audio_dur * FPS)}:s={WIDTH}x{HEIGHT}:fps={FPS}[v]"
        )
        subprocess.run(
            [ffmpeg, "-y", "-loop", "1", "-i", card_path,
             "-i", chapter_audios[i],
             "-filter_complex", ch_filter,
             "-map", "[v]", "-map", "1:a",
             "-c:v", "libx264", "-preset", "medium", "-crf", "23",
             "-c:a", "aac", "-b:a", "128k",
             "-t", str(audio_dur),
             "-pix_fmt", "yuv420p",
             ch_segment],
            startupinfo=startupinfo,
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            timeout=300
        )
        chapter_video_paths.append(ch_segment)
        print(f"[main_long] Ch.{i+1} '{ch.title}' rendered ({audio_dur:.1f}s)")

    # ── 6c. Render outro segment ────────────────────────────────────────
    outro_dur = _get_audio_duration(outro_audio) if outro_audio else 8.0
    chapter_real_durations.append(outro_dur)

    outro_card_path = os.path.join(assets_dir, f"long_outro_card_{timestamp}.png")
    outro_card = Image.new("RGB", (WIDTH, HEIGHT), (10, 15, 30))
    outro_draw = ImageDraw.Draw(outro_card)
    outro_draw.text(((WIDTH - draw.textlength("THANK YOU", font=font_large)) // 2, HEIGHT // 3),
                    "THANK YOU", fill=(255, 242, 0), font=font_large)
    outro_draw.text(((WIDTH - draw.textlength("Subscribe for the next deep dive.", font=font_med)) // 2, HEIGHT // 3 + 100),
                    "Subscribe for the next deep dive.", fill=(0, 242, 254), font=font_med)
    try:
        small_font = ImageFont.truetype(video_engine.font_path, 28)
    except Exception:
        small_font = ImageFont.load_default()
    outro_draw.text((60, HEIGHT - 80), "#TheDailyAudit", fill=(150, 150, 200), font=small_font)
    # Static mascot in outro (winking)
    static_wink = video_engine._render_static(size=180, expression="wink")
    outro_card.paste(static_wink, (WIDTH - 250, HEIGHT // 3 - 50), static_wink if static_wink.mode == 'RGBA' else None)
    outro_card.save(outro_card_path)

    outro_segment = os.path.join(output_dir, f"segment_outro_{timestamp}.mp4")
    outro_filter = (
        f"[0:v]zoompan=z=1.003:d={int(outro_dur * FPS)}:s={WIDTH}x{HEIGHT},fps={FPS}[v]"
    )
    subprocess.run(
        [ffmpeg, "-y", "-loop", "1", "-i", outro_card_path,
         "-i", outro_audio,
         "-filter_complex", outro_filter,
         "-map", "[v]", "-map", "1:a",
         "-c:v", "libx264", "-preset", "medium", "-crf", "23",
         "-c:a", "aac", "-b:a", "128k",
         "-t", str(outro_dur),
         "-pix_fmt", "yuv420p",
         outro_segment],
        startupinfo=startupinfo,
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        timeout=120
    )
    chapter_video_paths.append(outro_segment)
    print(f"[main_long] Outro segment rendered ({outro_dur:.1f}s)")

    # ── 6d. Concatenate all segments ────────────────────────────────────
    concat_list_path = os.path.join(output_dir, f"concat_list_{timestamp}.txt")
    with open(concat_list_path, "w") as f:
        for seg_path in chapter_video_paths:
            # Use forward slashes for FFmpeg concat
            f.write(f"file '{seg_path.replace(os.sep, '/')}'\n")

    output_name = f"daily_audit_long_{timestamp}"
    output_video_path = os.path.join(output_dir, f"{output_name}.mp4")

    print(f"[main_long] Concatenating {len(chapter_video_paths)} segments...")
    subprocess.run(
        [ffmpeg, "-y", "-f", "concat", "-safe", "0",
         "-i", concat_list_path,
         "-c", "copy",
         "-movflags", "+faststart",
         output_video_path],
        startupinfo=startupinfo,
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        timeout=300
    )
    print(f"[main_long] Video composition complete: {output_video_path}")

    # ── STEP 7: Generate SRT Subtitles ──────────────────────────────────
    print(f"\n{'=' * 80}")
    print(f"   STEP 7: GENERATING SRT SUBTITLES")
    print(f"{'=' * 80}")

    srt_lines = []
    current_ms = intro_dur * 1000  # Start after intro

    for i, ch in enumerate(chapters):
        dur_ms = chapter_real_durations[i + 1] * 1000  # +1 because i=0 is intro
        chapter_srt = _generate_chapter_srt(i, ch.content, current_ms, dur_ms)
        srt_lines.append(chapter_srt)
        current_ms += dur_ms

    srt_path = os.path.join(output_dir, f"{output_name}.srt")
    with open(srt_path, "w", encoding="utf-8") as f:
        f.write("\n".join(srt_lines))
    print(f"[main_long] SRT subtitles saved: {srt_path}")

    # ── STEP 8: Generate Thumbnail ──────────────────────────────────────
    print(f"\n{'=' * 80}")
    print(f"   STEP 8: GENERATING THUMBNAIL")
    print(f"{'=' * 80}")

    thumb_path = os.path.join(output_dir, f"{output_name}_thumb.png")
    try:
        # First chapter image as background
        thumb_bg = Image.new("RGB", (1920, 1080), (10, 15, 30))
        if chapter_images[0] and os.path.exists(chapter_images[0]):
            bg_img = Image.open(chapter_images[0]).convert("RGB")
            bg_img = bg_img.resize((1920, 1080), Image.Resampling.LANCZOS)
            bg_img = bg_img.filter(ImageFilter.GaussianBlur(radius=8))
            dark_overlay = Image.new("RGB", (1920, 1080), (10, 15, 30))
            bg_img = Image.blend(bg_img, dark_overlay, 0.5)
            thumb_bg.paste(bg_img, (0, 0))
        thumb_draw = ImageDraw.Draw(thumb_bg)
        try:
            title_font = ImageFont.truetype(video_engine.font_path, 64)
            sub_font = ImageFont.truetype(video_engine.font_path, 40)
        except Exception:
            title_font = ImageFont.load_default()
            sub_font = title_font
        thumb_draw.text((100, 100), "THE DAILY AUDIT", fill=(255, 242, 0), font=title_font)
        thumb_draw.text((100, 200), topic.upper(), fill=(255, 255, 255), font=sub_font)
        thumb_draw.text((100, 270), "A 10-Minute Deep Dive", fill=(0, 242, 254), font=sub_font)
        # Static mascot
        static_thumb = video_engine._render_static(size=350, expression="shocked")
        thumb_bg.paste(static_thumb, (1500, 350), static_thumb if static_thumb.mode == 'RGBA' else None)
        thumb_bg.save(thumb_path)
        print(f"[main_long] Thumbnail saved: {thumb_path}")
    except Exception as e:
        print(f"[main_long] WARNING: Thumbnail generation failed: {e}")
        thumb_path = None

    # ── STEP 9: Build YouTube Description with Chapters ─────────────────
    print(f"\n{'=' * 80}")
    print(f"   STEP 9: PREPARING METADATA")
    print(f"{'=' * 80}")

    # Calculate real chapter durations (excluding intro/outro)
    chapter_times = chapter_real_durations[1:-1]  # skip intro & outro
    chapter_timestamps = _build_chapter_timestamps(chapters, chapter_times)

    tags_str = " ".join([f"#{t.strip().replace(' ', '')}" for t in script.tags if t.strip()])
    yt_title = script.youtube_title
    yt_desc = (
        f"{script.youtube_description}\n\n"
        f"───\n"
        f"{chapter_timestamps}\n\n"
        f"#TheDailyAudit {tags_str}"
    )

    print(f"[main_long] YouTube Title: {yt_title}")
    print(f"[main_long] YouTube Description: {yt_desc[:200]}...")

    # ── STEP 10: Upload as Private Draft ─────────────────────────────────
    print(f"\n{'=' * 80}")
    print(f"   STEP 10: UPLOADING TO YOUTUBE (PRIVATE DRAFT)")
    print(f"{'=' * 80}")

    yt_success = False
    yt_video_id = None
    try:
        uploader = YouTubeUploader()
        yt_success, yt_video_id = uploader.upload_short(
            video_path=output_video_path,
            title=yt_title,
            description=yt_desc,
            tags=script.tags,
            thumbnail_path=thumb_path,
        )
        if yt_success and yt_video_id:
            print(f"[main_long] YouTube upload successful! Private draft: https://studio.youtube.com/video/{yt_video_id}/edit")
    except Exception as e:
        print(f"[main_long] YouTube upload failed (non-fatal): {e}")

    # ── STEP 11: Upload to Facebook as Draft ────────────────────────────
    print(f"\n{'=' * 80}")
    print(f"   STEP 11: UPLOADING TO FACEBOOK (DRAFT)")
    print(f"{'=' * 80}")

    fb_success = False
    fb_video_id = None
    try:
        fb_uploader = FacebookUploader()
        fb_success, fb_video_id = fb_uploader.upload_reel(
            video_path=output_video_path,
            description=f"{script.youtube_description[:200]}\n\n#TheDailyAudit #Education {tags_str}",
        )
        if fb_success and fb_video_id:
            print(f"[main_long] Facebook upload successful! Draft video ID: {fb_video_id}")
    except Exception as e:
        print(f"[main_long] Facebook upload failed (non-fatal): {e}")

    # ── FINAL SUMMARY ────────────────────────────────────────────────────
    total_duration = sum(chapter_real_durations)
    total_words = sum(len(ch.content.split()) for ch in chapters)

    print(f"\n{'=' * 80}")
    print(f"   LONG-FORM PIPELINE COMPLETE")
    print(f"{'=' * 80}")
    print(f"   Topic:              {topic}")
    print(f"   Chapters:           {num_chapters}")
    print(f"   Total Words:        {total_words}")
    print(f"   Total Duration:     {int(total_duration//60)}:{int(total_duration%60):02d}")
    print(f"   Video File:         {output_video_path}")
    print(f"   Thumbnail:          {thumb_path or 'N/A'}")
    print(f"   SRT Subtitles:      {srt_path}")
    print(f"   YouTube Draft:      {'https://studio.youtube.com/video/' + yt_video_id + '/edit' if yt_video_id else 'N/A'}")
    print(f"   Facebook Draft:     {'Video ID: ' + fb_video_id if fb_video_id else 'N/A'}")
    print(f"   Style:              {style}")
    separator = "=" * 80
    print(separator)
    print("   IMPORTANT: Review the private draft on YouTube Studio before publishing!")
    print("   YouTube Studio:     https://studio.youtube.com/")
    print(separator)

    return {
        "topic": topic,
        "category": category,
        "video_path": output_video_path,
        "thumbnail_path": thumb_path,
        "srt_path": srt_path,
        "yt_video_id": yt_video_id,
        "fb_video_id": fb_video_id,
        "total_duration": total_duration,
        "chapters": num_chapters,
        "title": yt_title,
    }


# ── Entry Point ───────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("[main_long] Starting The Daily Audit Long-Form Pipeline...")
    try:
        result = run_long_pipeline()
        print(f"\n[main_long] Pipeline completed successfully.")
        print(f"[main_long] Video: {result.get('video_path', 'N/A')}")
    except KeyboardInterrupt:
        print("\n[main_long] Pipeline interrupted by user.")
        sys.exit(1)
    except Exception as e:
        print(f"\n[main_long] Pipeline failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

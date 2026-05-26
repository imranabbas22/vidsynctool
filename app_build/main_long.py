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
#   6. FFmpeg composes: intro → chapters → outro (PARALLEL, GPU-ACCELERATED)
#   7. Private draft upload to YouTube + draft to Facebook
#   8. Output: video file, SRT subtitles, chapter timestamps text
#
# RENDER SPEED (target): 10-min video in under 10 minutes total pipeline time
#   - TTS generation: 2-3 min
#   - Image scraping: 1-2 min
#   - Card rendering: ~10s (PIL, fast)
#   - FFmpeg encoding: ~30-60s (h264_nvenc GPU, parallel chapters)
#   - Concat: ~2s
#   - Upload: ~2-3 min
# =============================================================================

import os
import sys
import json
import time
import random
import datetime
import subprocess
import re
import concurrent.futures
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

# ── Constants ────────────────────────────────────────────────────────────
WIDTH, HEIGHT = 1920, 1080  # 16:9 landscape
FPS = 30

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

DEFAULT_STYLE = "blueprint"


# ── FFmpeg helpers ───────────────────────────────────────────────────────
def _get_ffmpeg():
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        return "ffmpeg"


def _get_ffprobe():
    ffmpeg = _get_ffmpeg()
    if os.name == 'nt':
        return ffmpeg.replace("ffmpeg.exe", "ffprobe.exe").replace("ffmpeg", "ffprobe.exe")
    return ffmpeg.replace("ffmpeg", "ffprobe")


def _get_audio_duration(path):
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
    return 3.0


def _detect_nvenc(ffmpeg):
    """Check if CUDA NVENC is available."""
    try:
        startupinfo = None
        if os.name == 'nt':
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        r = subprocess.run([ffmpeg, "-encoders"], capture_output=True, text=True,
                          timeout=5, startupinfo=startupinfo)
        return "h264_nvenc" in r.stdout
    except Exception:
        return False


def _get_nvenc_preset(ffmpeg):
    """Check available NVENC presets and return the fastest one (p1)."""
    try:
        startupinfo = None
        if os.name == 'nt':
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        r = subprocess.run([ffmpeg, "-hide_banner", "-f", "lavfi", "-i",
                           "nullsrc=s=1280x720", "-c:v", "h264_nvenc", "-preset", "p1",
                           "-f", "null", "-"], capture_output=True, text=True,
                          timeout=5, startupinfo=startupinfo)
        if r.returncode == 0:
            return "p1"
    except Exception:
        pass
    # Fallback presets supported by all NVENC versions
    return "fast"


def _build_chapter_timestamps(chapters, chapter_durations):
    lines = ["\n\n--- CHAPTERS ---"]
    elapsed = 0.0
    for i, (ch, dur) in enumerate(zip(chapters, chapter_durations)):
        mins = int(elapsed // 60)
        secs = int(elapsed % 60)
        lines.append(f"{mins}:{secs:02d} - {ch.title}")
        elapsed += dur
    return "\n".join(lines)


def _generate_chapter_srt(chapter_idx, text, start_ms, duration_ms):
    words = text.split()
    if not words:
        return ""
    total_chars = sum(len(w) for w in words)
    sec_per_char = (duration_ms / 1000.0) / total_chars if total_chars > 0 else 0.05
    lines = []
    entry_num = chapter_idx + 1
    title_entry_start = start_ms
    title_entry_end = title_entry_start + min(2000, duration_ms * 0.15)
    lines.append(f"{entry_num}")
    lines.append(f"{_ms_to_srt_time(title_entry_start)} --> {_ms_to_srt_time(title_entry_end)}")
    lines.append(f"[ {chapter_idx + 1}. {text[:80].strip()}... ]")
    lines.append("")
    chunk_size = 5
    word_groups = [words[i:i + chunk_size] for i in range(0, len(words), chunk_size)]
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


def _ms_to_srt_time(ms):
    total_sec = ms / 1000.0
    hours = int(total_sec // 3600)
    minutes = int((total_sec % 3600) // 60)
    seconds = int(total_sec % 60)
    millis = int((total_sec - int(total_sec)) * 1000)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d},{millis:03d}"


def _render_segment(ffmpeg, codec, nvenc_preset, card_path, audio_path,
                    output_path, duration, startupinfo, timeout=180):
    """
    Render a single video segment: static image + audio.
    Uses simple -loop 1 (no zoompan filters) for max speed.
    """
    cmd = [
        ffmpeg, "-y",
        "-loop", "1", "-i", card_path,
        "-i", audio_path,
        "-c:v", codec,
    ]
    if codec == "h264_nvenc":
        cmd += ["-preset", nvenc_preset, "-cq", "23", "-b:v", "5M",
                "-bufsize", "10M", "-rc", "vbr"]
    else:
        cmd += ["-preset", "veryfast", "-crf", "26"]
    cmd += [
        "-c:a", "aac", "-b:a", "128k",
        "-t", str(duration),
        "-pix_fmt", "yuv420p",
        "-movflags", "+faststart",
        output_path
    ]
    subprocess.run(cmd, startupinfo=startupinfo,
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                   timeout=timeout)
    return output_path


# ── Main Pipeline ─────────────────────────────────────────────────────────
def run_long_pipeline():
    print("=" * 80)
    print("   THE DAILY AUDIT — LONG-FORM VIDEO PIPELINE (10 MIN)")
    print("=" * 80)

    pipeline_start = time.time()

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
    topic = None
    category = None
    try:
        topic, category, description = ingestion.fetch_unused_misconception(
            gemini_client=client_ref, category_filter=None,
        )
        print(f"[main_long] Selected Myth Topic: '{topic}' | Category: {category}")
    except Exception as e:
        print(f"[main_long] No myth topic ({e}). Trying bizarre topic...")
        try:
            topic, category, description = ingestion.fetch_unused_bizarre_topic(
                gemini_client=client_ref, category_filter=None,
            )
            print(f"[main_long] Selected Bizarre Topic: '{topic}' | Category: {category}")
        except Exception as e2:
            print(f"[main_long] CRITICAL: No topics available: {e2}")
            sys.exit(1)

    ingestion.log_uploaded_topic(topic, "")

    # ── STEP 2: Gemini 2.5 Pro Deep Research + Script Generation ─────────
    t2_start = time.time()
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
    print(f"[main_long] Script generated: {num_chapters} chapters ({(time.time()-t2_start):.1f}s)")

    # ── STEP 3: Generate TTS Audio Per Chapter (parallel) ────────────────
    t3_start = time.time()
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
            f"<prosody pitch='+0st' rate='0.95'>{intro_text}. Today, we audit: {topic}.</prosody>",
            f"long_intro_{timestamp}", is_ssml=True
        )
        print(f"[main_long] Intro TTS: '{intro_text}'")
    except Exception as e:
        print(f"[main_long] WARNING: Intro TTS failed: {e}")
        intro_audio = None

    # Chapter TTS — parallel
    def _gen_chapter_tts(i, ch):
        rate = 0.97 if i < num_chapters // 3 else (0.95 if i < num_chapters * 2 // 3 else 0.93)
        pitch = "+0st" if i < num_chapters * 2 // 3 else "-0.5st"
        ssml = f"<prosody pitch='{pitch}' rate='{rate}'>{ch.content}</prosody>"
        path = asset_gen.generate_tts_audio(ssml, f"long_ch{i}_{timestamp}", is_ssml=True)
        return (i, path)

    chapter_audios = [None] * num_chapters
    with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:
        futures = [pool.submit(_gen_chapter_tts, i, ch) for i, ch in enumerate(chapters)]
        for f in concurrent.futures.as_completed(futures):
            idx, path = f.result()
            chapter_audios[idx] = path
            print(f"[main_long] Ch.{idx+1} '{chapters[idx].title}': TTS ready ({len(chapters[idx].content.split())} words)")

    # Outro TTS
    outro_text = random.choice(OUTRO_TEXTS)
    climax = script.climax
    try:
        outro_audio = asset_gen.generate_tts_audio(
            f"<prosody pitch='+0st' rate='0.95'>{climax} {outro_text} "
            f"This has been The Daily Audit. The truth doesn't change. Subscribe so you never miss it.</prosody>",
            f"long_outro_{timestamp}", is_ssml=True
        )
        print(f"[main_long] Outro TTS generated (climax included)")
    except Exception as e:
        print(f"[main_long] WARNING: Outro TTS failed: {e}")
        outro_audio = None

    print(f"[main_long] TTS phase: {(time.time()-t3_start):.1f}s")

    # ── STEP 4: Fetch Images Per Chapter (parallel) ──────────────────────
    t4_start = time.time()
    print(f"\n{'=' * 80}")
    print(f"   STEP 4: FETCHING IMAGES ({num_chapters} CHAPTERS)")
    print(f"{'=' * 80}")

    scraper = DataScraper()
    chapter_images = [None] * num_chapters

    def _fetch_chapter_image(i, ch):
        for query in [ch.visual_query, topic]:
            if not query:
                continue
            try:
                img_path = scraper.fetch_image_multi_source(query, f"long_ch{i}_img_{timestamp}")
                if img_path and os.path.exists(img_path):
                    print(f"[main_long] Ch.{i+1}: Wikipedia image: '{query}'")
                    return (i, img_path)
            except Exception:
                pass
        return (i, None)

    with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:
        futures = [pool.submit(_fetch_chapter_image, i, ch) for i, ch in enumerate(chapters)]
        for f in concurrent.futures.as_completed(futures):
            idx, path = f.result()
            chapter_images[idx] = path

    # Imagen fallback for any missing images
    for i, img_path in enumerate(chapter_images):
        if not img_path or not os.path.exists(img_path):
            try:
                safe = " No human faces, no political content, no violence, no text, safe for all ages."
                chapter_images[i] = asset_gen.generate_background_image(
                    f"Educational illustration of {chapters[i].title}, {topic}. {safe}",
                    f"long_ch{i}_fallback_{timestamp}",
                    aspect_ratio="16:9", is_blueprint=True,
                    style_suffix=st["bg_prompt_suffix"]
                )
                print(f"[main_long] Ch.{i+1}: Imagen fallback generated")
            except Exception:
                chapter_images[i] = None

    print(f"[main_long] Images phase: {(time.time()-t4_start):.1f}s")

    # ── STEP 5: Generate Visual Cards ────────────────────────────────────
    t5_start = time.time()
    print(f"\n{'=' * 80}")
    print(f"   STEP 5: GENERATING CHAPTER CARDS")
    print(f"{'=' * 80}")

    video_engine = VideoEngine()
    from PIL import Image, ImageDraw, ImageFont, ImageFilter

    # Pre-load fonts
    try:
        font_large = ImageFont.truetype(video_engine.font_path, 72)
        font_med = ImageFont.truetype(video_engine.font_path, 48)
        font_small = ImageFont.truetype(video_engine.font_path, 28)
        font_ch = ImageFont.truetype(video_engine.font_path, 42)
        font_tk = ImageFont.truetype(video_engine.font_path, 28)
    except Exception:
        default_font = ImageFont.load_default()
        font_large = font_med = font_small = font_ch = font_tk = default_font

    # Generate chapter cards (sequential — fast PIL operations)
    chapter_cards = [None] * num_chapters
    for i, ch in enumerate(chapters):
        img_path = chapter_images[i]
        if img_path and os.path.exists(img_path):
            try:
                label = f"CHAPTER {i+1}: {ch.title.upper()}"
                card = video_engine._generate_card(
                    image_path=img_path, label_text=label,
                    status_text=f"EXHIBIT {chr(65+i)}",
                    is_truth=(i >= num_chapters // 2),
                    style_dict=st, topic=topic,
                    add_redactions=(i == 0), card_text=ch.key_takeaway,
                )
                chapter_cards[i] = card
            except Exception:
                chapter_cards[i] = None

        # Render card to 16:9 canvas regardless
        card_img = chapter_cards[i]
        canvas = Image.new("RGB", (WIDTH, HEIGHT), (10, 15, 30))
        if card_img is not None:
            card_resized = card_img.resize((540, 620), Image.Resampling.LANCZOS)
            cx, cy = (WIDTH - 540) // 2, (HEIGHT - 620) // 2
            if card_resized.mode == 'RGBA':
                canvas.paste(card_resized, (cx, cy), card_resized)
            else:
                canvas.paste(card_resized, (cx, cy))
            # Chapter title at top
            ch_label = f"CHAPTER {i+1}: {ch.title}"
            ch_draw = ImageDraw.Draw(canvas)
            ct_w = ch_draw.textlength(ch_label, font=font_ch)
            ch_draw.text(((WIDTH - ct_w) // 2, 30), ch_label, fill=(0, 242, 254), font=font_ch)
            # Takeaway at bottom
            tk_label = f"▸ {ch.key_takeaway}"
            ch_draw.text((60, HEIGHT - 100), tk_label, fill=(200, 200, 200), font=font_tk)
        else:
            fb_draw = ImageDraw.Draw(canvas)
            ch_label = f"CHAPTER {i+1}: {ch.title}"
            fb_draw.text((100, HEIGHT // 2 - 50), ch_label, fill=(255, 255, 255), font=font_large)
        chapter_cards[i] = canvas

    print(f"[main_long] Cards phase: {(time.time()-t5_start):.1f}s")

    # Generate Static mascot for intro/outro
    static_mascot = video_engine._render_static(size=200, expression="neutral")

    # ── STEP 6: Compose Video (PARALLEL, GPU-ACCELERATED) ────────────────
    t6_start = time.time()
    print(f"\n{'=' * 80}")
    print(f"   STEP 6: COMPOSING VIDEO (parallel GPU encoding)")
    print(f"{'=' * 80}")

    ffmpeg = _get_ffmpeg()
    has_nvenc = _detect_nvenc(ffmpeg)
    codec = "h264_nvenc" if has_nvenc else "libx264"
    nvenc_preset = _get_nvenc_preset(ffmpeg) if has_nvenc else "veryfast"
    print(f"[main_long] Encoder: {codec}" + (f" (NVENC preset={nvenc_preset})" if has_nvenc else ""))

    assets_dir = video_engine.assets_dir
    output_dir = os.path.join(assets_dir, "long_form")
    os.makedirs(output_dir, exist_ok=True)

    startupinfo = None
    if os.name == 'nt':
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW

    card_paths = []
    for i, canvas in enumerate(chapter_cards):
        path = os.path.join(assets_dir, f"long_ch{i}_canvas_{timestamp}.png")
        canvas.save(path)
        card_paths.append(path)

    # Intro card
    intro_card_path = os.path.join(assets_dir, f"long_intro_card_{timestamp}.png")
    intro_card = Image.new("RGB", (WIDTH, HEIGHT), (10, 15, 30))
    draw = ImageDraw.Draw(intro_card)
    t_w = draw.textlength("THE DAILY AUDIT", font=font_large)
    draw.text(((WIDTH - t_w) // 2, HEIGHT // 3), "THE DAILY AUDIT", fill=(255, 242, 0), font=font_large)
    subtitle = f"DEEP DIVE: {topic.upper()}"
    t_w2 = draw.textlength(subtitle, font=font_med)
    draw.text(((WIDTH - t_w2) // 2, HEIGHT // 3 + 100), subtitle, fill=(0, 242, 254), font=font_med)
    draw.text((WIDTH // 2 - 200, HEIGHT // 2 + 50), "═══════════════════", fill=(100, 100, 160), font=font_small)
    draw.text((WIDTH // 2 - 200, HEIGHT // 2 + 100), "A Daily Audit Production", fill=(150, 150, 200), font=font_small)
    mascot_resized = static_mascot.resize((300, 300), Image.Resampling.LANCZOS)
    intro_card.paste(mascot_resized, (WIDTH - 380, 50),
                     mascot_resized if mascot_resized.mode == 'RGBA' else None)
    intro_card.save(intro_card_path)

    # Outro card
    outro_card_path = os.path.join(assets_dir, f"long_outro_card_{timestamp}.png")
    outro_card = Image.new("RGB", (WIDTH, HEIGHT), (10, 15, 30))
    outro_draw = ImageDraw.Draw(outro_card)
    outro_draw.text(((WIDTH - draw.textlength("THANK YOU", font=font_large)) // 2, HEIGHT // 3),
                    "THANK YOU", fill=(255, 242, 0), font=font_large)
    outro_draw.text(((WIDTH - draw.textlength("Subscribe for the next deep dive.", font=font_med)) // 2, HEIGHT // 3 + 100),
                    "Subscribe for the next deep dive.", fill=(0, 242, 254), font=font_med)
    outro_draw.text((60, HEIGHT - 80), "#TheDailyAudit", fill=(150, 150, 200), font=font_small)
    static_wink = video_engine._render_static(size=180, expression="wink")
    outro_card.paste(static_wink, (WIDTH - 250, HEIGHT // 3 - 50),
                     static_wink if static_wink.mode == 'RGBA' else None)
    outro_card.save(outro_card_path)

    # Get durations for all segments
    intro_dur = _get_audio_duration(intro_audio) if intro_audio else 4.0
    audio_durs = [_get_audio_duration(a) for a in chapter_audios]
    outro_dur = _get_audio_duration(outro_audio) if outro_audio else 8.0

    # RENDER ALL SEGMENTS IN PARALLEL
    segment_tasks = []

    # Intro
    seg_intro = os.path.join(output_dir, f"seg_intro_{timestamp}.mp4")
    segment_tasks.append((ffmpeg, codec, nvenc_preset, intro_card_path,
                          intro_audio, seg_intro, intro_dur, startupinfo))

    # Chapters
    for i in range(num_chapters):
        seg = os.path.join(output_dir, f"seg_ch{i}_{timestamp}.mp4")
        segment_tasks.append((ffmpeg, codec, nvenc_preset, card_paths[i],
                              chapter_audios[i], seg, audio_durs[i], startupinfo))

    # Outro
    seg_outro = os.path.join(output_dir, f"seg_outro_{timestamp}.mp4")
    segment_tasks.append((ffmpeg, codec, nvenc_preset, outro_card_path,
                          outro_audio, seg_outro, outro_dur, startupinfo))

    seg_paths = [None] * len(segment_tasks)
    print(f"[main_long] Rendering {len(segment_tasks)} segments in parallel (GPU)...")
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        future_map = {}
        for idx, task in enumerate(segment_tasks):
            f = pool.submit(_render_segment, *task)
            future_map[f] = idx
        for f in concurrent.futures.as_completed(future_map):
            idx = future_map[f]
            seg_paths[idx] = f.result()
            name = "intro" if idx == 0 else ("outro" if idx == len(segment_tasks) - 1 else f"ch.{idx}")
            print(f"[main_long]   {name} rendered ✓")

    # CONCATENATE
    print(f"[main_long] Concatenating {len(seg_paths)} segments...")
    concat_list = os.path.join(output_dir, f"concat_{timestamp}.txt")
    with open(concat_list, "w") as f:
        for sp in seg_paths:
            f.write(f"file '{sp.replace(os.sep, '/')}'\n")

    output_name = f"daily_audit_long_{timestamp}"
    output_video_path = os.path.join(output_dir, f"{output_name}.mp4")

    subprocess.run(
        [ffmpeg, "-y", "-f", "concat", "-safe", "0", "-i", concat_list,
         "-c", "copy", "-movflags", "+faststart", output_video_path],
        startupinfo=startupinfo, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=300
    )
    print(f"[main_long] Composition: {(time.time()-t6_start):.1f}s total")

    # ── STEP 7: SRT Subtitles ────────────────────────────────────────────
    srt_lines = []
    current_ms = intro_dur * 1000
    for i, ch in enumerate(chapters):
        dur_ms = audio_durs[i] * 1000
        srt_lines.append(_generate_chapter_srt(i, ch.content, current_ms, dur_ms))
        current_ms += dur_ms

    srt_path = os.path.join(output_dir, f"{output_name}.srt")
    with open(srt_path, "w", encoding="utf-8") as f:
        f.write("\n".join(srt_lines))
    print(f"[main_long] SRT: {srt_path}")

    # ── STEP 8: Thumbnail ────────────────────────────────────────────────
    thumb_path = os.path.join(output_dir, f"{output_name}_thumb.png")
    try:
        thumb_bg = Image.new("RGB", (1920, 1080), (10, 15, 30))
        if chapter_images[0] and os.path.exists(chapter_images[0]):
            bg = Image.open(chapter_images[0]).convert("RGB").resize((1920, 1080), Image.Resampling.LANCZOS)
            bg = bg.filter(ImageFilter.GaussianBlur(radius=8))
            dark = Image.new("RGB", (1920, 1080), (10, 15, 30))
            bg = Image.blend(bg, dark, 0.5)
            thumb_bg.paste(bg, (0, 0))
        td = ImageDraw.Draw(thumb_bg)
        td.text((100, 100), "THE DAILY AUDIT", fill=(255, 242, 0), font=font_large)
        td.text((100, 200), topic.upper(), fill=(255, 255, 255), font=font_med)
        td.text((100, 270), "A 10-Minute Deep Dive", fill=(0, 242, 254), font=font_med)
        st_thumb = video_engine._render_static(size=350, expression="shocked")
        thumb_bg.paste(st_thumb, (1500, 350), st_thumb if st_thumb.mode == 'RGBA' else None)
        thumb_bg.save(thumb_path)
    except Exception as e:
        print(f"[main_long] Thumbnail failed: {e}")
        thumb_path = None

    # ── STEP 9: Metadata ─────────────────────────────────────────────────
    chapter_times = audio_durs  # content chapters only, no intro/outro
    chapter_timestamps = _build_chapter_timestamps(chapters, chapter_times)
    tags_str = " ".join([f"#{t.strip().replace(' ', '')}" for t in script.tags if t.strip()])
    yt_title = script.youtube_title
    yt_desc = f"{script.youtube_description}\n\n───\n{chapter_timestamps}\n\n#TheDailyAudit {tags_str}"

    # ── STEP 10: Upload to YouTube (Private Draft) ───────────────────────
    print(f"\n{'=' * 80}")
    print(f"   STEP 10: UPLOADING TO YOUTUBE (PRIVATE DRAFT)")
    print(f"{'=' * 80}")
    yt_success, yt_video_id = False, None
    try:
        uploader = YouTubeUploader()
        yt_success, yt_video_id = uploader.upload_short(
            video_path=output_video_path, title=yt_title, description=yt_desc,
            tags=script.tags, thumbnail_path=thumb_path,
        )
    except Exception as e:
        print(f"[main_long] YouTube upload failed: {e}")

    # ── STEP 11: Upload to Facebook (Draft) ──────────────────────────────
    print(f"\n{'=' * 80}")
    print(f"   STEP 11: UPLOADING TO FACEBOOK (DRAFT)")
    print(f"{'=' * 80}")
    fb_success, fb_video_id = False, None
    try:
        fb_uploader = FacebookUploader()
        fb_success, fb_video_id = fb_uploader.upload_reel(
            video_path=output_video_path,
            description=f"{script.youtube_description[:200]}\n\n#TheDailyAudit #Education {tags_str}",
        )
    except Exception as e:
        print(f"[main_long] Facebook upload failed: {e}")

    # ── SUMMARY ──────────────────────────────────────────────────────────
    total_duration = sum([intro_dur] + audio_durs + [outro_dur])
    total_words = sum(len(c.content.split()) for c in chapters)
    pipeline_elapsed = time.time() - pipeline_start

    print(f"\n{'=' * 80}")
    print(f"   LONG-FORM PIPELINE COMPLETE")
    print(f"{'=' * 80}")
    print(f"   Topic:              {topic}")
    print(f"   Chapters:           {num_chapters}")
    print(f"   Total Words:        {total_words}")
    print(f"   Video Duration:     {int(total_duration//60)}:{int(total_duration%60):02d}")
    print(f"   Pipeline Time:      {int(pipeline_elapsed//60)}m {int(pipeline_elapsed%60)}s")
    print(f"   Encoder:            {codec}")
    print(f"   Video File:         {output_video_path}")
    print(f"   SRT Subtitles:      {srt_path}")
    print(f"   YouTube Draft:      {'https://studio.youtube.com/video/' + yt_video_id + '/edit' if yt_video_id else 'N/A'}")
    print(f"   Facebook Draft:     {'Video ID: ' + fb_video_id if fb_video_id else 'N/A'}")
    separator = "=" * 80
    print(separator)
    print("   IMPORTANT: Review the private draft on YouTube Studio before publishing!")
    print(separator)

    return {
        "topic": topic, "category": category, "video_path": output_video_path,
        "thumbnail_path": thumb_path, "srt_path": srt_path,
        "yt_video_id": yt_video_id, "fb_video_id": fb_video_id,
        "total_duration": total_duration, "chapters": num_chapters, "title": yt_title,
        "pipeline_time": pipeline_elapsed, "encoder": codec,
    }


if __name__ == "__main__":
    print("[main_long] Starting The Daily Audit Long-Form Pipeline...")
    try:
        result = run_long_pipeline()
        print(f"\n[main_long] Pipeline completed in {result.get('pipeline_time', 0):.0f}s.")
    except KeyboardInterrupt:
        print("\n[main_long] Interrupted.")
        sys.exit(1)
    except Exception as e:
        print(f"\n[main_long] Failed: {e}")
        import traceback; traceback.print_exc()
        sys.exit(1)

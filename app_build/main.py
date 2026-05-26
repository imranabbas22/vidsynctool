# =============================================================================
# "The Daily Audit" - Master Orchestration Pipeline
# =============================================================================
import os
import sys
import time
import argparse
import random
import re
import datetime
import functools
from dotenv import load_dotenv

# Load local environment parameters
load_dotenv()

from data_ingestion import DataIngestion
from llm_orchestrator import LLMOrchestrator
from asset_generator import AssetGenerator
from video_engine import VideoEngine, STYLE_PRESETS
from youtube_uploader import YouTubeUploader
from facebook_uploader import FacebookUploader
from data_scraper import DataScraper
from analytics_logger import AnalyticsLogger

CTA_ROTATION = [
    "That was today's audit. Subscribe — the next file is already open.",
    "Case closed. Follow for tomorrow's declassified truth.",
    "Audit complete. Subscribe — we expose one lie every single day.",
    "File sealed. Hit follow — tomorrow's case is worse.",
    "Subscribe now. The truth does not wait.",
]

STYLES = ["blueprint", "blueprint", "chalkboard", "classified", "cyberpunk", "retro_vhs", "terminal"]

TRANSITIONS = ["glitch", "burn"]

# ── Retry utility ────────────────────────────────────────────────────────────
def retry_with_backoff(max_retries=3, base_delay=2.0, backoff_factor=2.0,
                       retryable_exceptions=(Exception,)):
    """
    Decorator that retries a function on failure with exponential backoff.
    Only retries on the specified exception types (default: all Exceptions).
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            last_exc = None
            for attempt in range(1, max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except retryable_exceptions as e:
                    last_exc = e
                    if attempt < max_retries:
                        delay = base_delay * (backoff_factor ** (attempt - 1))
                        print(f"[Retry] {func.__name__} failed (attempt {attempt}/{max_retries}): "
                              f"{type(e).__name__}: {e}. Retrying in {delay:.1f}s...")
                        time.sleep(delay)
                    else:
                        print(f"[Retry] {func.__name__} failed after {max_retries} attempts. "
                              f"Giving up: {type(e).__name__}: {e}")
            raise last_exc
        return wrapper
    return decorator


def split_myth_ssml(ssml_script, hook_clean, context_clean, fact_clean):
    """
    Splits the unified SSML script into 3 clean content scenes for Myth format.
    No CTA or sign-off appended to scene 3 — handled by ending bumper.
    """
    clean_ssml = ssml_script.strip()
    for tag in ["<speak>", "</speak>"]:
        clean_ssml = clean_ssml.replace(tag, "")
    clean_ssml = re.sub(r'<voice[^>]*>', '', clean_ssml)
    clean_ssml = clean_ssml.replace('</voice>', '').strip()
    
    # Find all break tags
    break_pattern = r'<break\s+time=["\']([^"\']+)["\']\s*/>'
    matches = list(re.finditer(break_pattern, clean_ssml, flags=re.IGNORECASE))
    
    idx_1200 = -1
    idx_700 = -1
    for i, m in enumerate(matches):
        if "1200" in m.group(1):
            idx_1200 = i
        if "700" in m.group(1):
            idx_700 = i
    
    if idx_1200 != -1 and idx_700 != -1:
        m_700 = matches[idx_700]
        m_1200 = matches[idx_1200]
        if m_700.start() < m_1200.start():
            s1_ssml = clean_ssml[:m_700.start()].strip()
            s2_ssml = clean_ssml[m_700.end():m_1200.start()].strip()
            s3_ssml = clean_ssml[m_1200.end():].strip()
        else:
            s1_ssml = clean_ssml[:m_1200.start()].strip()
            s2_ssml = clean_ssml[m_1200.end():m_700.start()].strip()
            s3_ssml = clean_ssml[m_700.end():].strip()
    elif idx_1200 != -1:
        m_1200 = matches[idx_1200]
        s1_ssml = clean_ssml[:m_1200.start()].strip()
        remaining = clean_ssml[m_1200.end():].strip()
        if idx_700 != -1 and idx_700 > idx_1200:
            m_700 = matches[idx_700]
            s2_ssml = remaining[:m_700.start() - m_1200.end()].strip()
            s3_ssml = remaining[m_700.end() - m_1200.end():].strip()
        else:
            s2_ssml = ""
            s3_ssml = remaining
    elif idx_700 != -1:
        m_700 = matches[idx_700]
        s1_ssml = clean_ssml[:m_700.start()].strip()
        s2_ssml = clean_ssml[m_700.end():].strip()
        s3_ssml = ""
    else:
        s1_ssml = hook_clean
        s2_ssml = context_clean
        s3_ssml = fact_clean
    
    s1_ssml = re.sub(r'\s+', ' ', s1_ssml).strip()
    s2_ssml = re.sub(r'\s+', ' ', s2_ssml).strip()
    s3_ssml = re.sub(r'\s+', ' ', s3_ssml).strip()

    # Guard: redistribute if any scene is empty (e.g. script too short for 3 scenes)
    scenes = [s1_ssml, s2_ssml, s3_ssml]
    non_empty = [s for s in scenes if s]
    if len(non_empty) == 2:
        longer_idx = 0 if len(non_empty[0]) >= len(non_empty[1]) else 1
        orig_longer_idx = next(i for i, s in enumerate(scenes) if s == non_empty[longer_idx])
        empty_idx = next(i for i, s in enumerate(scenes) if not s)
        longer_text = scenes[orig_longer_idx]
        sentences = re.split(r'(?<=[.!?])\s+', longer_text)
        if len(sentences) >= 2:
            split_point = len(sentences) // 2
            first_half = ' '.join(sentences[:split_point])
            second_half = ' '.join(sentences[split_point:])
        else:
            mid = len(longer_text) // 2
            first_half = longer_text[:mid]
            second_half = longer_text[mid:]
        scenes[orig_longer_idx] = first_half.strip()
        scenes[empty_idx] = second_half.strip()
    elif len(non_empty) == 1:
        sentences = re.split(r'(?<=[.!?])\s+', non_empty[0])
        if len(sentences) >= 3:
            each = len(sentences) // 3
            parts = [' '.join(sentences[i*each:(i+1)*each]) for i in range(3)]
            for i in range(3):
                scenes[i] = parts[i].strip()
        elif len(sentences) >= 2:
            scenes[0] = ' '.join(sentences[:1])
            scenes[1] = ' '.join(sentences[1:])
            scenes[2] = scenes[1]
        else:
            scenes[0] = scenes[1] = scenes[2] = non_empty[0]
    elif len(non_empty) == 0:
        scenes[0] = hook_clean.strip()
        scenes[1] = context_clean.strip()
        scenes[2] = fact_clean.strip()

    s1_ssml, s2_ssml, s3_ssml = [s for s in scenes]
    return s1_ssml, s2_ssml, s3_ssml


def split_bizarre_ssml(ssml_script, hook_clean, why_bizarre, closing_statement):
    """
    Splits the unified SSML script into 3 clean content scenes for Bizarre format.
    No CTA or sign-off appended to scene 3 — handled by ending bumper.
    """
    clean_ssml = ssml_script.strip()
    for tag in ["<speak>", "</speak>"]:
        clean_ssml = clean_ssml.replace(tag, "")
    clean_ssml = re.sub(r'<voice[^>]*>', '', clean_ssml)
    clean_ssml = clean_ssml.replace('</voice>', '').strip()
    
    # Find all break tags
    break_pattern = r'<break\s+time=["\']([^"\']+)["\']\s*/>'
    matches = list(re.finditer(break_pattern, clean_ssml, flags=re.IGNORECASE))
    
    idx_1200 = -1
    idx_700 = -1
    for i, m in enumerate(matches):
        if "1200" in m.group(1):
            idx_1200 = i
        if "700" in m.group(1):
            idx_700 = i
    
    if idx_1200 != -1 and idx_700 != -1:
        m_700 = matches[idx_700]
        m_1200 = matches[idx_1200]
        if m_700.start() < m_1200.start():
            s1_ssml = clean_ssml[:m_700.start()].strip()
            s2_ssml = clean_ssml[m_700.end():m_1200.start()].strip()
            s3_ssml = clean_ssml[m_1200.end():].strip()
        else:
            s1_ssml = clean_ssml[:m_1200.start()].strip()
            s2_ssml = clean_ssml[m_1200.end():m_700.start()].strip()
            s3_ssml = clean_ssml[m_700.end():].strip()
    elif idx_1200 != -1:
        m_1200 = matches[idx_1200]
        s1_ssml = clean_ssml[:m_1200.start()].strip()
        remaining = clean_ssml[m_1200.end():].strip()
        if idx_700 != -1 and idx_700 > idx_1200:
            m_700 = matches[idx_700]
            s2_ssml = remaining[:m_700.start() - m_1200.end()].strip()
            s3_ssml = remaining[m_700.end() - m_1200.end():].strip()
        else:
            s2_ssml = ""
            s3_ssml = remaining
    elif idx_700 != -1:
        m_700 = matches[idx_700]
        s1_ssml = clean_ssml[:m_700.start()].strip()
        s2_ssml = clean_ssml[m_700.end():].strip()
        s3_ssml = ""
    else:
        s1_ssml = hook_clean
        s2_ssml = why_bizarre
        s3_ssml = closing_statement
    
    s1_ssml = re.sub(r'\s+', ' ', s1_ssml).strip()
    s2_ssml = re.sub(r'\s+', ' ', s2_ssml).strip()
    s3_ssml = re.sub(r'\s+', ' ', s3_ssml).strip()

    # Guard: redistribute if any scene is empty (e.g. script too short for 3 scenes)
    scenes = [s1_ssml, s2_ssml, s3_ssml]
    non_empty = [s for s in scenes if s]
    if len(non_empty) == 2:
        longer_idx = 0 if len(non_empty[0]) >= len(non_empty[1]) else 1
        orig_longer_idx = next(i for i, s in enumerate(scenes) if s == non_empty[longer_idx])
        empty_idx = next(i for i, s in enumerate(scenes) if not s)
        longer_text = scenes[orig_longer_idx]
        sentences = re.split(r'(?<=[.!?])\s+', longer_text)
        if len(sentences) >= 2:
            split_point = len(sentences) // 2
            first_half = ' '.join(sentences[:split_point])
            second_half = ' '.join(sentences[split_point:])
        else:
            mid = len(longer_text) // 2
            first_half = longer_text[:mid]
            second_half = longer_text[mid:]
        scenes[orig_longer_idx] = first_half.strip()
        scenes[empty_idx] = second_half.strip()
    elif len(non_empty) == 1:
        sentences = re.split(r'(?<=[.!?])\s+', non_empty[0])
        if len(sentences) >= 3:
            each = len(sentences) // 3
            parts = [' '.join(sentences[i*each:(i+1)*each]) for i in range(3)]
            for i in range(3):
                scenes[i] = parts[i].strip()
        elif len(sentences) >= 2:
            scenes[0] = ' '.join(sentences[:1])
            scenes[1] = ' '.join(sentences[1:])
            scenes[2] = scenes[1]
        else:
            scenes[0] = scenes[1] = scenes[2] = non_empty[0]
    elif len(non_empty) == 0:
        scenes[0] = hook_clean.strip()
        scenes[1] = context_clean.strip()
        scenes[2] = fact_clean.strip()

    s1_ssml, s2_ssml, s3_ssml = [s for s in scenes]
    return s1_ssml, s2_ssml, s3_ssml


def verify_video_audio(video_path: str) -> None:
    """Post-render check: ensure video has a non-silent audio stream.
    Raises RuntimeError if audio is missing or silent, preventing silent
    videos from being uploaded."""
    import subprocess, json, os
    # Find ffprobe
    ffprobe = "ffprobe"
    try:
        import imageio_ffmpeg
        ffmpeg_dir = os.path.dirname(imageio_ffmpeg.get_ffmpeg_exe())
        candidate = os.path.join(ffmpeg_dir, "ffprobe.exe" if os.name == 'nt' else "ffprobe")
        if os.path.exists(candidate):
            ffprobe = candidate
    except Exception:
        pass

    startupinfo = None
    if os.name == 'nt':
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW

    # Check audio stream exists
    probe = subprocess.run(
        [ffprobe, "-v", "quiet", "-print_format", "json", "-show_streams", video_path],
        capture_output=True, text=True, timeout=15, startupinfo=startupinfo
    )
    if probe.returncode != 0:
        raise RuntimeError(f"ffprobe failed on output video: {probe.stderr[-200:]}")

    streams = json.loads(probe.stdout).get("streams", [])
    audio_streams = [s for s in streams if s.get("codec_type") == "audio"]
    if not audio_streams:
        raise RuntimeError(
            f"OUTPUT VIDEO HAS NO AUDIO STREAM: {video_path}. "
            "Pipeline aborted to prevent publishing a silent video."
        )

    # Check audio isn't silent (max_volume > -60 dB = actual sound)
    vol = subprocess.run(
        [ffprobe, "-v", "quiet", "-f", "lavfi",
         "-i", f"amovie={video_path},volumedetect",
         "-show_entries", "frame_tags=lavfi.volume_mean,lavfi.volume_max",
         "-of", "json"],
        capture_output=True, text=True, timeout=15, startupinfo=startupinfo
    )
    try:
        frames = json.loads(vol.stdout).get("frames", [])
        max_db = -100.0
        for f in frames:
            tags = f.get("tags", {})
            v = float(tags.get("lavfi.volume_max", "-100"))
            if v > max_db:
                max_db = v
        if max_db < -50.0:
            raise RuntimeError(
                f"OUTPUT VIDEO AUDIO IS SILENT (max_volume={max_db:.0f}dB): {video_path}"
            )
        print(f"[Main] Audio verification PASSED: max_volume={max_db:.0f}dB, streams={len(audio_streams)}")
    except json.JSONDecodeError:
        print(f"[Main] Audio verification WARNING: couldn't parse volume data — passing on stream presence")
    except RuntimeError:
        raise
    except Exception as e:
        print(f"[Main] Audio volume check failed ({e}) — passing on stream presence")


def run_pipeline():
    """Executes the complete Shorts generation and uploading pipeline."""
    print("=" * 80)
    print("   STARTING AUTOMATED PRODUCTION CYCLE: THE DAILY AUDIT SHORTS NETWORK")
    print("=" * 80)

    # 0. Parse Command Line Arguments for Video Type
    parser = argparse.ArgumentParser(description="TDA Shorts Pipeline Master Script")
    parser.add_argument("--type", choices=["myth", "bizarre", "all", "dynamic"], default=None, help="Specify video format type, 'all' to build all, 'dynamic' for user-prompt-driven, or omit for random weighted selection")
    parser.add_argument("--prompt", type=str, default=None, help="User prompt for dynamic video generation (requires --type dynamic)")
    args = parser.parse_args()

    if args.type == "dynamic" and not args.prompt:
        print("[Main] ERROR: --prompt is required when --type is 'dynamic'")
        sys.exit(1)

    THEME_DAYS = {
        "Monday": {"type": "myth", "category": "Biology", "name": "Medical Myths Monday"},
        "Tuesday": {"type": "bizarre", "category": "History", "name": "Time Warp Tuesday"},
        "Wednesday": {"type": "bizarre", "category": "Biology", "name": "Weird Science Wednesday"},
        "Thursday": {"type": "myth", "category": "History", "name": "Textbook Lies Thursday"},
        "Friday": {"type": "myth", "category": "History", "name": "Friday Files"},
        "Saturday": {"type": "bizarre", "category": "Astronomy", "name": "Strange But True Saturday"},
        "Sunday": {"type": "myth", "category": "Physics", "name": "Sunday Audit"},
    }

    selected_types = []
    category_filter = None
    if args.type:
        if args.type == "all":
            selected_types = ["myth", "bizarre"]
        else:
            selected_types = [args.type]
    else:
        day_of_week = datetime.datetime.now().strftime("%A")
        day_info = THEME_DAYS.get(day_of_week, {"type": "myth", "category": None, "name": "General Audit"})
        selected_types = [day_info["type"]]
        category_filter = day_info.get("category")
        print(f"[Main] Theme Days Selection: Today is {day_of_week} ({day_info['name']}) -> Format: {day_info['type'].upper()}, Category Filter: {category_filter}")
    print(f"[Main] Production Target Formats Selected: {[t.upper() for t in selected_types]}")

    # Initialize analytics tracker for data-driven decisions (Sprint 5)
    try:
        analytics_tracker = AnalyticsLogger()
        print(f"[Main] Analytics tracker initialized: {analytics_tracker.log_path}")
    except Exception as e:
        print(f"[Main] WARNING: Analytics tracker init failed: {e}")
        analytics_tracker = None

    # Select a visual style using analytics rotation (A/B style tracking)
    if analytics_tracker is not None:
        try:
            video_style = analytics_tracker.select_rotation_style(STYLES)
            print(f"[Main] Analytics-rotated Visual Style Selected: {video_style.upper()}"
                  f" (A/B rotation tracking active)")
        except Exception:
            video_style = random.choice(STYLES)
            print(f"[Main] Visual Style Selected: {video_style.upper()} (fallback random)")
    else:
        video_style = random.choice(STYLES)
        print(f"[Main] Visual Style Selected: {video_style.upper()} (no analytics)")

    # Select a random transition type for A/B tracking
    transition_type = random.choice(TRANSITIONS)
    print(f"[Main] Transition Type: {transition_type}")

    # Select a random CTA for this run
    cta_text = random.choice(CTA_ROTATION)
    print(f"[Main] CTA Text: '{cta_text}'")
    
    # 1. Initialize Ingestion Module & SQLite Database
    try:
        ingestion = DataIngestion()
        print(f"[Main] Database initialized. Target path: {ingestion.db_path}")
    except Exception as e:
        print(f"[Main] CRITICAL: Failed to initialize SQLite database: {e}")
        sys.exit(1)

    # 2. Initialize Gemini API Client & Script Architect
    gemini_key = (
        os.getenv("FREE_GEMINI_API_KEY") 
        or os.getenv("GEMINI_API_KEY") 
        or os.getenv("PAID_GEMINI_API_KEY")
    )
    if not gemini_key:
        print("[Main] CRITICAL: Gemini API Key environment variable is missing.")
        print("[Main] Please define FREE_GEMINI_API_KEY or GEMINI_API_KEY in your .env file.")
        sys.exit(1)

    try:
        orchestrator = LLMOrchestrator(api_key=gemini_key)
    except Exception as e:
        print(f"[Main] CRITICAL: Failed to initialize Gemini Script Orchestrator: {e}")
        sys.exit(1)

    client_ref = orchestrator.client if hasattr(orchestrator, "client") else None

    # Loop through each selected format consecutively
    for video_type in selected_types:
        print("\n" + "=" * 80)
        print(f"   PROCESSING VIDEO FORMAT: {video_type.upper()}")
        print("=" * 80)

        timestamp = f"{int(time.time())}_{random.randint(1000, 9999)}"
        meta = {}
        title = ""
        topic = ""
        hook_text = ""
        video_path = ""
        style_suffix = STYLE_PRESETS.get(video_style, STYLE_PRESETS["blueprint"])["bg_prompt_suffix"]

        # =========================================================================
        # FORMAT 1: MYTH BUSTING
        # =========================================================================
        if video_type == "myth":
            # Retrieve next unused misconception
            try:
                topic, category, description = ingestion.fetch_unused_misconception(
                    gemini_client=client_ref, category_filter=category_filter,
                    analytics_logger=analytics_tracker,
                )
                print(f"[Main] Selected Myth Topic: '{topic}' | Discipline: {category}")
            except Exception as e:
                print(f"[Main] CRITICAL: Ingestion failed to retrieve misconception: {e}")
                sys.exit(1)

            # Immediately reserve topic to prevent re-selection if pipeline crashes
            ingestion.log_uploaded_topic(topic, "")

            # Generate structured 5-beat script payload from Gemini
            script_payload = None
            try:
                print("[Main] Calling Gemini to construct structured 5-beat script...")
                script_payload = orchestrator.generate_structured_script(topic, category, description)
                episode_num = ingestion.get_next_episode()
                script_payload["episode_num"] = episode_num
                word_count = LLMOrchestrator.calculate_word_count(script_payload)
                script_payload["word_count"] = word_count
                print(f"[Main] Script generated successfully. Word count: {word_count} | Episode: {episode_num}")
            except Exception as e:
                print(f"[Main] ERROR: Script generation failed: {e}")
                sys.exit(1)

            # Initialize Asset Generator
            try:
                gcp_cred = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
                asset_gen = AssetGenerator(gemini_client=client_ref, gcp_credentials_path=gcp_cred)
            except Exception as e:
                print(f"[Main] CRITICAL: Failed to initialize Asset Generator: {e}")
                sys.exit(1)

            # ── Extract 5-beat script ──────────────────────────────────────
            # Map beats to 3 scenes: 1+2→scene1, 3→scene2, 4→scene3, 5→bumper
            beat1 = getattr(script_payload, 'beat1_hook', '') or script_payload.get('beat1_hook', '')
            beat2 = getattr(script_payload, 'beat2_pivot', '') or script_payload.get('beat2_pivot', '')
            beat3 = getattr(script_payload, 'beat3_mechanism', '') or script_payload.get('beat3_mechanism', '')
            beat4 = getattr(script_payload, 'beat4_reframe', '') or script_payload.get('beat4_reframe', '')
            beat5 = getattr(script_payload, 'beat5_signoff', '') or script_payload.get('beat5_signoff', '')

            # Fallback: if no beats found, use old-style payload fields
            if not beat1:
                beat1 = script_payload.get('hook', '')
                beat2 = ''  # old format has no pivot
                beat3 = script_payload.get('context', '')
                beat4 = script_payload.get('fact', '')
                beat5 = script_payload.get('sign_off', 'Class dismissed.')
                print("[Main] Using legacy script format (no 5-beat structure)")

            content_type = getattr(script_payload, 'content_type', 'myth') if hasattr(script_payload, 'content_type') else 'myth'
            print(f"[Main] Content type: {content_type} | Word count: {script_payload.get('word_count', '?')}")

            # Generate 5 audio files: [starting, s1, s2, s3, ending]
            audio_paths = []
            try:
                # --- Starting bumper TTS (kept short for retention) ---
                starting_text = random.choice([
                    "Classified file just dropped.",
                    "New audit. Pay attention.",
                    "Another lie exposed today.",
                    "Declassified. Watch carefully.",
                ])
                starting_ssml_wrapped = f"<prosody pitch='0st' rate='0.95'>{starting_text}</prosody>"
                print(f"[Main] Myth Starting Bumper: '{starting_text}'")

                # --- Ending bumper TTS using beat5 sign-off ---
                ending_text = f"{cta_text} {beat5}" if beat5 else cta_text
                ending_ssml_wrapped = f"<prosody pitch='0st' rate='0.95'>{ending_text}</prosody>"
                print(f"[Main] Myth Ending Bumper: '{ending_text}'")

                # Build SSML for 3 content scenes from 5 beats
                s1_ssml = f"{beat1}<break time='500ms'/>{beat2}"
                s2_ssml = beat3
                s3_ssml = beat4

                # Per-scene prosody
                s1_ssml_wrapped = f"<prosody pitch='0st' rate='0.97'>{s1_ssml}</prosody>"
                s2_ssml_wrapped = f"<prosody pitch='0st' rate='0.95'>{s2_ssml}</prosody>"
                s3_ssml_wrapped = f"<prosody pitch='-0.5st' rate='0.93'>{s3_ssml}</prosody>"

                print(f"[Main] Scene 1 (beat1+2): {beat1[:60]}...")
                print(f"[Main] Scene 2 (beat3): {beat3[:60]}...")
                print(f"[Main] Scene 3 (beat4): {beat4[:60]}...")
                
                # Build 5-element audio paths for content scenes and bumpers
                audio_paths = [
                    asset_gen.generate_tts_audio(starting_ssml_wrapped, f"tts_{timestamp}_start", is_ssml=True),
                    asset_gen.generate_tts_audio(s1_ssml_wrapped, f"tts_{timestamp}_s1", is_ssml=True),
                    asset_gen.generate_tts_audio(s2_ssml_wrapped, f"tts_{timestamp}_s2", is_ssml=True),
                    asset_gen.generate_tts_audio(s3_ssml_wrapped, f"tts_{timestamp}_s3", is_ssml=True),
                    asset_gen.generate_tts_audio(ending_ssml_wrapped, f"tts_{timestamp}_end", is_ssml=True),
                ]
            except Exception as e:
                print(f"[Main] ERROR: Asset Generator failed to create scene TTS MP3s: {e}")
                sys.exit(1)

            # ── IMAGE ACQUISITION: Scrape-first, AI-fallback ──────────────────
            # Step 1: Scrape Wikipedia for ALL needed images first (cost-free)
            image_myth_path = None
            image_truth_path = None
            extra_images = []
            verdict_image_path = None

            try:
                scraper = DataScraper()
            except Exception:
                scraper = None

            # Try scraping for myth image
            if scraper:
                try:
                    myth_query = topic
                    scraped_myth = scraper.fetch_image_multi_source(
                        myth_query, f"myth_scraped_{timestamp}"
                    )
                    if scraped_myth and os.path.exists(scraped_myth):
                        image_myth_path = scraped_myth
                        print(f"[Main] Scraped myth image: {scraped_myth}")
                except Exception as e:
                    print(f"[Main] Myth image scrape failed: {e}")

            # Try scraping for truth image
            if scraper:
                try:
                    truth_keywords = ' '.join([w for w in topic.split() if len(w) > 3][:3]) or topic
                    scraped_truth = scraper.fetch_image_multi_source(
                        truth_keywords, f"truth_scraped_{timestamp}"
                    )
                    if scraped_truth and os.path.exists(scraped_truth):
                        image_truth_path = scraped_truth
                        print(f"[Main] Scraped truth image: {scraped_truth}")
                except Exception as e:
                    print(f"[Main] Truth image scrape failed: {e}")

            # Scrape Wikipedia for extra context images
            if scraper:
                try:
                    wiki_queries = [topic]
                    if hook_clean:
                        hook_words = [w for w in hook_clean.split() if len(w) > 4]
                        if hook_words:
                            wiki_queries.append(' '.join(hook_words[:3]))
                    if fact_clean:
                        fact_words = [w for w in fact_clean.split() if len(w) > 4]
                        if fact_words:
                            wiki_queries.append(' '.join(fact_words[:3]))
                    wiki_images = scraper.fetch_multiple_wikipedia_images(
                        wiki_queries, f"wiki_{timestamp}", max_images=3
                    )
                    extra_images.extend(wiki_images)
                    print(f"[Main] Wikipedia extra images: {len(wiki_images)}")
                except ImportError:
                    print("[Main] DataScraper not available — skipping Wikipedia")
                except Exception as e:
                    print(f"[Main] Wikipedia extra fetch failed: {e}")

            # Try scraping for verdict image
            if scraper:
                try:
                    verdict_keywords = topic
                    scraped_verdict = scraper.fetch_image_multi_source(
                        verdict_keywords, f"verdict_scraped_{timestamp}"
                    )
                    if scraped_verdict and os.path.exists(scraped_verdict):
                        verdict_image_path = scraped_verdict
                        print(f"[Main] Scraped verdict image: {scraped_verdict}")
                except Exception as e:
                    print(f"[Main] Verdict image scrape failed: {e}")

            # ── Step 2: AI generation as FALLBACK for missing images ─────────
            visual_prompt_myth = getattr(script_payload, 'visual_hook', None) or script_payload.get('visual_hook') or script_payload.get('myth_visual_prompt', "Technical blueprint representing the false myth")
            visual_prompt_truth = getattr(script_payload, 'visual_mechanism', None) or script_payload.get('visual_mechanism') or script_payload.get('fact_visual_prompt', "Realistic laboratory photography representing the scientific truth")
            safe_suffix = " No human faces, no political content, no violence, no text, safe for all ages."

            # Myth image — AI fallback if scraping failed
            if not image_myth_path:
                try:
                    image_myth_name = f"background_myth_{timestamp}"
                    print(f"[Main] Scraping failed for myth image. Generating with AI: '{visual_prompt_myth[:60]}...'")
                    image_myth_path = asset_gen.generate_background_image(
                        visual_prompt_myth + safe_suffix, image_myth_name,
                        aspect_ratio="9:16", is_blueprint=True, style_suffix=style_suffix
                    )
                except Exception as e:
                    print(f"[Main] ERROR: Myth background image generation failed: {e}")
                    sys.exit(1)

            # Truth image — AI fallback if scraping failed
            if not image_truth_path:
                try:
                    image_truth_name = f"foreground_fact_{timestamp}"
                    print(f"[Main] Scraping failed for truth image. Generating with AI: '{visual_prompt_truth[:60]}...'")
                    image_truth_path = asset_gen.generate_background_image(
                        visual_prompt_truth + safe_suffix, image_truth_name,
                        aspect_ratio="1:1", is_blueprint=False
                    )
                except Exception as e:
                    print(f"[Main] WARNING: Truth image generation failed: {e}. Falling back to myth image.")
                    image_truth_path = image_myth_path

            # Extra context image — AI fallback only if we have < 3 scraped extras
            if len(extra_images) < 3:
                try:
                    extra_img_name = f"context_extra_{timestamp}"
                    extra_prompt = getattr(script_payload, 'visual_mechanism', None) or script_payload.get('visual_mechanism') or script_payload.get('context_visual_prompt')
                    if not extra_prompt:
                        extra_prompt = f"Scientific illustration showing {topic}, detailed, realistic, high contrast"
                    extra_path = asset_gen.generate_background_image(
                        extra_prompt + " No politics, no violence, no human faces, safe for all ages.",
                        extra_img_name, aspect_ratio="1:1", is_blueprint=False
                    )
                    if extra_path:
                        extra_images.append(extra_path)
                        print(f"[Main] AI-generated extra context image: {extra_path}")
                except Exception as e:
                    print(f"[Main] Extra image generation failed (non-fatal): {e}")

            # Verdict image — AI fallback if scraping failed
            if not verdict_image_path:
                verdict_prompt = getattr(script_payload, 'visual_reframe', None) or script_payload.get('visual_reframe') or script_payload.get('verdict_visual_prompt',
                    f"Symbolic visual representing the final truth about {topic}, forensic evidence, case closed, official seal")
                try:
                    verdict_name = f"verdict_reveal_{timestamp}"
                    print(f"[Main] Scraping failed for verdict. Generating with AI: '{verdict_prompt[:60]}...'")
                    verdict_image_path = asset_gen.generate_background_image(
                        verdict_prompt + safe_suffix, verdict_name,
                        aspect_ratio="9:16", is_blueprint=True, style_suffix=style_suffix
                    )
                except Exception as e:
                    print(f"[Main] WARNING: Verdict image generation failed: {e}. Falling back to truth image.")
                    verdict_image_path = image_truth_path or image_myth_path

            # Build image override with Wikipedia + extra images for visual variety
            myth_image_paths = [image_myth_path] if image_myth_path else []
            # Insert extra (wiki + Imagen) images for scene 2 variety
            for ei in extra_images:
                myth_image_paths.append(ei)
            # Verdict images (scene 3) — fresh, never seen before
            if verdict_image_path:
                myth_image_paths.append(verdict_image_path)
            if image_truth_path:
                myth_image_paths.append(image_truth_path)
            # Deduplicate
            seen = set()
            deduped = []
            for p in myth_image_paths:
                if p and p not in seen:
                    seen.add(p)
                    deduped.append(p)
            myth_image_paths = deduped
            print(f"[Main] Total images for video: {len(myth_image_paths)}")

            meta = script_payload.get("youtube_metadata", {})
            raw_title = meta.get("title", f"The Daily Audit: {topic} #Shorts")
            if episode_num is not None:
                title = f"EP.{episode_num} — {raw_title}"
            else:
                title = raw_title
            if "youtube_metadata" in script_payload:
                script_payload["youtube_metadata"]["title"] = title
            clean_title = re.sub(r'[<>:"/\\|?*#]', '', title).strip().replace(' ', '_')[:100]
            clean_title = re.sub(r'[\u2013\u2014\u2015]', '-', clean_title)
            clean_title = re.sub(r'[^\w\.\-\(\)\[\]]', '_', clean_title)
            clean_title = re.sub(r'_+', '_', clean_title)

            try:
                video_eng = VideoEngine()
                video_name = f"{clean_title}_{timestamp}"
                script_payload["cta"] = cta_text
                script_payload["starting_text"] = starting_text
                script_payload["ending_text"] = ending_text
                video_path = video_eng.compile_short(image_myth_path, image_truth_path, audio_paths, script_payload, video_name, category, style=video_style, video_type="myth", image_paths_override=myth_image_paths)
                print(f"[Main] Video assembled and saved successfully: {video_path}")
                verify_video_audio(video_path)  # Hard-stop if audio is missing/silent
                # Generate thumbnail using actual video images
                video_eng.generate_thumbnail(topic, hook_clean, video_name, style=video_style, img_myth_path=image_myth_path, img_truth_path=image_truth_path, episode_num=episode_num)
            except Exception as e:
                print(f"[Main] ERROR: Video engine compilation failed: {e}")
                sys.exit(1)

            hook_text = hook_clean

        # =========================================================================
        # FORMAT 2: DECLASSIFIED ANOMALIES (BIZARRE FACTS)
        # =========================================================================
        elif video_type == "bizarre":
            # 1. Retrieve bizarre topic
            try:
                topic, category, description = ingestion.fetch_unused_bizarre_topic(
                    gemini_client=client_ref, category_filter=category_filter,
                    analytics_logger=analytics_tracker,
                )
                print(f"[Main] Selected Anomaly Topic: '{topic}' | Discipline: {category}")
            except Exception as e:
                print(f"[Main] CRITICAL: Ingestion failed to retrieve bizarre topic: {e}")
                sys.exit(1)

            # Immediately reserve topic to prevent re-selection
            ingestion.log_uploaded_topic(topic, "")

            # 2. Generate structured 5-beat script payload from Gemini
            try:
                print("[Main] Calling Gemini to construct structured 5-beat bizarre script...")
                bizarre_payload = orchestrator.generate_structured_script(topic, category)
                episode_num = ingestion.get_next_episode()
                bizarre_payload.episode_num = episode_num
                content_type = bizarre_payload.content_type
                print(f"[Main] Script generated: {bizarre_payload.word_count} words, type={content_type} | Episode: {episode_num}")
            except Exception as e:
                print(f"[Main] ERROR: Script generation failed: {e}")
                sys.exit(1)

            # 3. Initialize Asset Generator and Data Scraper
            try:
                gcp_cred = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
                asset_gen = AssetGenerator(gemini_client=client_ref, gcp_credentials_path=gcp_cred)
                scraper = DataScraper()
            except Exception as e:
                print(f"[Main] CRITICAL: Failed to initialize asset systems: {e}")
                sys.exit(1)

            # 4. Scrape images using visual prompts from 5-beat script
            scene_queries = [
                getattr(bizarre_payload, 'visual_hook', '') or bizarre_payload.get('visual_hook', topic),
                getattr(bizarre_payload, 'visual_mechanism', '') or bizarre_payload.get('visual_mechanism', topic),
                getattr(bizarre_payload, 'visual_reframe', '') or bizarre_payload.get('visual_reframe', topic),
            ]

            scraped_bizarre_images = []
            try:
                scraped_bizarre_images = scraper.fetch_scene_images(
                    scene_queries, f"bizarre_{timestamp}", max_images=3
                )
            except Exception as e:
                print(f"[Main] Scraper failed for bizarre scenes: {e}")

            # If any scene is missing an image, use Imagen 4 to generate one
            if len(scraped_bizarre_images) < 3:
                print(f"[Main] Only got {len(scraped_bizarre_images)}/3 scraped images. Generating missing ones with Imagen 4...")
                for idx in range(3):
                    if idx >= len(scraped_bizarre_images):
                        query = scene_queries[idx] if idx < len(scene_queries) else topic
                        print(f"[Main] Generating Imagen 4 image for scene {idx+1} with query: '{query}'")
                        try:
                            gen_path = asset_gen.generate_background_image(
                                f"Schematic blueprint representation of {query}",
                                f"bizarre_imagen_{timestamp}_scene{idx}",
                                aspect_ratio="9:16",
                                is_blueprint=True,
                                style_suffix=style_suffix
                            )
                            if gen_path:
                                scraped_bizarre_images.append(gen_path)
                        except Exception as e:
                            print(f"[Main] Imagen 4 generation failed for scene {idx}: {e}")
                            # Last resort: fallback to reuse last available image
                            if scraped_bizarre_images:
                                scraped_bizarre_images.append(scraped_bizarre_images[-1])
                            else:
                                # Generate a blank blueprint fallback
                                fallback_path = os.path.join(asset_gen.assets_dir, f"bizarre_fallback_{timestamp}_scene{idx}.png")
                                try:
                                    path = asset_gen._render_programmatic_blueprint(query, fallback_path)
                                    scraped_bizarre_images.append(path)
                                except Exception:
                                    from PIL import Image
                                    os.makedirs(asset_gen.assets_dir, exist_ok=True)
                                    Image.new("RGB", (1080, 1920), (10, 24, 47)).save(fallback_path)
                                    scraped_bizarre_images.append(fallback_path)

            if not scraped_bizarre_images:
                fallback_query = scene_queries[0] if scene_queries else topic
                print(f"[Main] Falling back to programmatic image for bizarre query '{fallback_query}'")
                try:
                    fallback_path = asset_gen.generate_background_image(
                        f"Schematic blueprint of {fallback_query}",
                        f"bizarre_fallback_{timestamp}",
                        aspect_ratio="9:16",
                        is_blueprint=True,
                        style_suffix=style_suffix
                    )
                    scraped_bizarre_images = [fallback_path, fallback_path, fallback_path]
                except Exception as e:
                    print(f"[Main] Failed to generate fallback image: {e}")
                    sys.exit(1)

            image_myth_path = scraped_bizarre_images[0]
            image_truth_path = scraped_bizarre_images[-1]

            # 5. Generate TTS Audio with 5-part structure (starting, s1, s2, s3, ending)
            # Extract 5-beat script for bizarre path
            beat1 = getattr(bizarre_payload, 'beat1_hook', '') or bizarre_payload.get('beat1_hook', '')
            beat2 = getattr(bizarre_payload, 'beat2_pivot', '') or bizarre_payload.get('beat2_pivot', '')
            beat3 = getattr(bizarre_payload, 'beat3_mechanism', '') or bizarre_payload.get('beat3_mechanism', '')
            beat4 = getattr(bizarre_payload, 'beat4_reframe', '') or bizarre_payload.get('beat4_reframe', '')
            beat5 = getattr(bizarre_payload, 'beat5_signoff', '') or bizarre_payload.get('beat5_signoff', '')

            # Fallback to old-style payload
            if not beat1:
                beat1 = bizarre_payload.get('hook', '')
                beat2 = ''
                beat3 = bizarre_payload.get('why_bizarre', '')
                beat4 = bizarre_payload.get('closing_statement', '')
                beat5 = 'Class dismissed.'

            hook_clean = beat1
            why_bizarre = beat3
            closing_statement = beat4

            # TTS for 5 audio slots: [starting, s1(hook+pivot), s2(mechanism), s3(reframe), ending]
            starting_text = random.choice([

                "Classified file just dropped.",
                "New audit. Pay attention.",
                "Another lie exposed today.",
                "Declassified. Watch carefully.",
            ])
            starting_ssml_wrapped = f"<prosody pitch='0st' rate='0.95'>{starting_text}</prosody>"
            print(f"[Main] Bizarre Starting Bumper: '{starting_text}'")

            ending_text = f"{cta_text} {beat5}" if beat5 else cta_text
            ending_ssml_wrapped = f"<prosody pitch='0st' rate='0.95'>{ending_text}</prosody>"
            print(f"[Main] Bizarre Ending Bumper: '{ending_text}'")

            s1_ssml = f"{beat1}<break time='500ms'/>{beat2}"
            s2_ssml = beat3
            s3_ssml = beat4

            s1_ssml_wrapped = f"<prosody pitch='0st' rate='0.97'>{s1_ssml}</prosody>"
            s2_ssml_wrapped = f"<prosody pitch='0st' rate='0.95'>{s2_ssml}</prosody>"
            s3_ssml_wrapped = f"<prosody pitch='-0.5st' rate='0.93'>{s3_ssml}</prosody>"
            
            audio_paths = []
            try:
                # --- Starting bumper TTS (kept short for retention) ---
                starting_text = random.choice([
                    "Classified file just dropped.",
                    "New audit. Pay attention.",
                    "Something bizarre just surfaced.",
                    "Declassified. Watch carefully.",
                ])
                starting_ssml_wrapped = f"<prosody pitch='0st' rate='0.95'>{starting_text}</prosody>"
                print(f"[Main] Bizarre Starting Bumper: '{starting_text}'")

                # --- Ending bumper using signature sign-off ---
                sign_off = bizarre_payload.get("sign_off", "Class dismissed.")
                ending_text = f"{cta_text} {sign_off}"
                ending_ssml_wrapped = f"<prosody pitch='0st' rate='0.95'>{ending_text}</prosody>"
                print(f"[Main] Bizarre Ending Bumper: '{ending_text}' (sign-off: '{sign_off}')")

                # Determine raw ssml script
                if "ssml_script" in bizarre_payload:
                    ssml_raw = bizarre_payload["ssml_script"]
                else:
                    ssml_raw = (
                        f"{hook_clean}"
                        f"<break time='700ms'/>"
                        f"{why_bizarre}"
                        f"<break time='1200ms'/>"
                        f"{closing_statement}"
                    )
                
                # Split SSML into 3 content scenes (no CTA/sign-off)
                s1_ssml, s2_ssml, s3_ssml = split_bizarre_ssml(
                    ssml_raw, hook_clean, why_bizarre, closing_statement
                )
                
                # Per-scene prosody: subtle variation, no voice degradation
                # All scenes use near-normal rate; the dramatic shift comes from SFX/music
                s1_ssml_wrapped = f"<prosody pitch='0st' rate='0.97'>{s1_ssml}</prosody>"
                s2_ssml_wrapped = f"<prosody pitch='0st' rate='0.95'>{s2_ssml}</prosody>"
                s3_ssml_wrapped = f"<prosody pitch='-0.5st' rate='0.93'>{s3_ssml}</prosody>"
                
                print(f"[Main] Bizarre Scene 1 SSML: {s1_ssml_wrapped}")
                print(f"[Main] Bizarre Scene 2 SSML: {s2_ssml_wrapped}")
                print(f"[Main] Bizarre Scene 3 SSML: {s3_ssml_wrapped}")
                
                audio_paths = [
                    asset_gen.generate_tts_audio(starting_ssml_wrapped, f"bizarre_tts_{timestamp}_start", is_ssml=True),
                    asset_gen.generate_tts_audio(s1_ssml_wrapped, f"bizarre_tts_{timestamp}_s1", is_ssml=True),
                    asset_gen.generate_tts_audio(s2_ssml_wrapped, f"bizarre_tts_{timestamp}_s2", is_ssml=True),
                    asset_gen.generate_tts_audio(s3_ssml_wrapped, f"bizarre_tts_{timestamp}_s3", is_ssml=True),
                    asset_gen.generate_tts_audio(ending_ssml_wrapped, f"bizarre_tts_{timestamp}_end", is_ssml=True),
                ]
            except Exception as e:
                print(f"[Main] ERROR: Asset Generator failed to create bizarre scene TTS MP3s: {e}")
                sys.exit(1)

            # 6. Build script payload for compile_bizarre 3-scene format (no sign_off)
            script_payload = {
                "hook": hook_clean,
                "why_bizarre": why_bizarre,
                "closing_statement": closing_statement,
                "cta": cta_text,
                "starting_text": starting_text,
                "ending_text": ending_text,
                "episode_num": episode_num,
            }

            # 7. Compile Anomaly Video with multiple scene images
            meta = bizarre_payload.get("youtube_metadata", {})
            raw_title = meta.get("title", f"Declassified Anomaly: {topic} #Shorts")
            if episode_num is not None:
                title = f"EP.{episode_num} — {raw_title}"
            else:
                title = raw_title
            if "youtube_metadata" in bizarre_payload:
                bizarre_payload["youtube_metadata"]["title"] = title
            clean_title = re.sub(r'[<>:"/\\|?*#]', '', title).strip().replace(' ', '_')[:100]
            clean_title = re.sub(r'[\u2013\u2014\u2015]', '-', clean_title)
            clean_title = re.sub(r'[^\w\.\-\(\)\[\]]', '_', clean_title)
            clean_title = re.sub(r'_+', '_', clean_title)
            
            try:
                video_eng = VideoEngine()
                video_name = f"{clean_title}_{timestamp}"
                video_path = video_eng.compile_bizarre(
                    scraped_bizarre_images, audio_paths, script_payload,
                    video_name, category, style=video_style, video_type="bizarre"
                )
                print(f"[Main] Anomaly Video assembled successfully: {video_path}")
                verify_video_audio(video_path)  # Hard-stop if audio is missing/silent
                video_eng.generate_thumbnail(
                    topic, hook_clean, video_name, style=video_style,
                    img_myth_path=scraped_bizarre_images[0], img_truth_path=scraped_bizarre_images[-1],
                    bizarre_mode=True, episode_num=episode_num
                )
            except Exception as e:
                print(f"[Main] ERROR: Video engine compilation failed: {e}")
                sys.exit(1)

            hook_text = hook_clean

        # =========================================================================
        # FORMAT 3: DYNAMIC USER-PROMPT VIDEO
        # =========================================================================
        elif video_type == "dynamic":
            user_prompt = args.prompt
            print(f"[Main] DYNAMIC MODE: Processing user prompt: '{user_prompt}'")

            # 1. Research phase (Wikipedia scrape)
            try:
                scraper = DataScraper()
                print(f"[Main] Scraping research data for prompt: '{user_prompt}'")
                scraped_data = scraper.scrape_wikipedia_summary(user_prompt)
                print(f"[Main] Scraped {len(scraped_data)} chars of research data.")
            except Exception as e:
                print(f"[Main] ERROR: Scraper failed: {e}")
                scraped_data = f"No direct search results found for topic: {user_prompt}"

            # 2. Run the two-pass research agent prompt chain & reviewer loop
            try:
                from pipeline.orchestrator import PipelineOrchestrator
                pipe_orchestrator = PipelineOrchestrator(client_ref)
                
                pipeline_results = pipe_orchestrator.run_research_pipeline(user_prompt, scraped_data)
                pass1_output = pipeline_results["pass1_output"]
                scene_sequence = pipeline_results["scene_sequence"]
                review_res = pipeline_results["review"]
                
                topic = pass1_output.get("topic_core_mystery", user_prompt)
                category = "bizarre"
                print(f"[Main] Pipeline completed: topic='{topic}', scenes={len(scene_sequence)}")
            except Exception as e:
                print(f"[Main] CRITICAL: Pipeline orchestrator failed: {e}")
                sys.exit(1)

            # 3. Initialize Asset Generator
            try:
                gcp_cred = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
                asset_gen = AssetGenerator(gemini_client=client_ref, gcp_credentials_path=gcp_cred)
            except Exception as e:
                print(f"[Main] CRITICAL: Failed to initialize Asset Generator: {e}")
                sys.exit(1)

            # 4. Fetch materials (images per content scene)
            image_paths = []
            timestamp = str(int(time.time()))
            
            content_scenes = scene_sequence[1:-1]
            for i, scene in enumerate(content_scenes):
                query = scene.get("visual_query", "").strip()
                if not query:
                    query = topic
                
                try:
                    print(f"[Main] Fetching image for content scene {i+1} using query: '{query}'")
                    path = scraper.fetch_image_multi_source(query, f"dynamic_{timestamp}_scene{i}")
                    if path:
                        image_paths.append(path)
                    else:
                        print(f"[Main] No image found for scene {i} query '{query}', generating fallback blueprint...")
                        fallback_path = os.path.join(asset_gen.assets_dir, f"dynamic_fallback_{timestamp}_scene{i}.png")
                        path = asset_gen._render_programmatic_blueprint(query, fallback_path)
                        image_paths.append(path)
                except Exception as e:
                    print(f"[Main] Image fetch failed for scene {i}: {e}, generating fallback blueprint...")
                    fallback_path = os.path.join(asset_gen.assets_dir, f"dynamic_fallback_{timestamp}_scene{i}.png")
                    try:
                        path = asset_gen._render_programmatic_blueprint(query, fallback_path)
                        image_paths.append(path)
                    except Exception:
                        from PIL import Image
                        os.makedirs(asset_gen.assets_dir, exist_ok=True)
                        Image.new("RGB", (1080, 1920), (10, 24, 47)).save(fallback_path)
                        image_paths.append(fallback_path)

            print(f"[Main] Fetched {len(image_paths)} scene images")

            # 5. Generate TTS audio (N+2 files: starting + N scenes + ending)
            audio_paths = []
            try:
                from tts.ssml_builder import SSMLBuilder
                
                for i, scene in enumerate(scene_sequence):
                    text = scene["narration_text"]
                    emotion = scene.get("ssml_emotion", "calm")
                    scene_type = scene["scene_type"]
                    
                    scene_ssml = SSMLBuilder.build_scene_ssml(
                        text=text,
                        emotion=emotion,
                        scene_type=scene_type,
                        voice_name=asset_gen.voice_name
                    )
                    
                    label = f"dynamic_tts_{timestamp}_{scene_type}_{i}"
                    print(f"[Main] Dynamic Scene {i+1} ({scene_type.upper()}): emotion='{emotion}' -> Generating TTS...")
                    
                    audio_path = asset_gen.generate_tts_audio(scene_ssml, label, is_ssml=True)
                    audio_paths.append(audio_path)
                    
                scene_count = len(scene_sequence) - 2
                print(f"[Main] Generated {len(audio_paths)} TTS audio files for {scene_count} content scenes")
            except Exception as e:
                print(f"[Main] ERROR: TTS generation failed: {e}")
                sys.exit(1)

            # 6. Build metadata and compile dynamic N-scene video
            title = f"The Surprising Truth About {topic} #Shorts"
            title = title[:90] + " #Shorts"
            tags = ["education", "science", "shorts", "mystery", "declassified"]
            base_desc = (
                f"Declassifying the truth about {topic}.\n\n"
                f"Narrative Payoff: {pass1_output.get('narrative_payoff', '')}\n\n"
                f"Next: {pass1_output.get('teaser_next', '')}"
            )
            meta = {
                "title": title,
                "tags": tags,
                "description": base_desc
            }
            clean_title = re.sub(r'[<>:"/\\|?*#]', '', title).strip().replace(' ', '_')[:100]
            clean_title = re.sub(r'[\u2013\u2014\u2015]', '-', clean_title)
            clean_title = re.sub(r'[^\w\.\-\(\)\[\]]', '_', clean_title)
            clean_title = re.sub(r'_+', '_', clean_title)

            try:
                video_eng = VideoEngine()
                video_name = f"{clean_title}_{timestamp}"
                
                scene_titles = []
                for i, s in enumerate(scene_sequence[1:-1]):
                    t = "THE PARADOX" if s["scene_type"] == "body" and s.get("emotion_register") == "tension" else "THE REVELATION"
                    if s["scene_type"] == "verdict":
                        t = "THE DECLASSIFIED TRUTH"
                    scene_titles.append(t)
                    
                scene_labels = [f"[ SCENE {i+1} ]" for i in range(len(scene_sequence[1:-1]))]

                video_path = video_eng.compile_dynamic_video(
                    image_paths=image_paths,
                    audio_paths=audio_paths,
                    scene_texts=[s["narration_text"] for s in scene_sequence[1:-1]],
                    scene_titles=scene_titles,
                    scene_labels=scene_labels,
                    output_name=video_name,
                    category=category,
                    style=video_style,
                    video_type="dynamic",
                    starting_text=scene_sequence[0]["narration_text"],
                    ending_text=scene_sequence[-1]["narration_text"]
                )
                print(f"[Main] Dynamic video assembled successfully: {video_path}")
                verify_video_audio(video_path)  # Hard-stop if audio is missing/silent
                
                video_eng.generate_thumbnail(
                    topic, scene_sequence[1]["narration_text"] if len(scene_sequence) > 1 else topic,
                    video_name, style=video_style,
                    img_myth_path=image_paths[0] if image_paths else None,
                    img_truth_path=image_paths[-1] if len(image_paths) > 1 else None,
                    bizarre_mode=True,
                )
            except Exception as e:
                print(f"[Main] ERROR: Video engine compilation failed: {e}")
                sys.exit(1)

            hook_text = scene_sequence[0]["narration_text"] if scene_sequence else ""

        # =========================================================================
        # UPLOAD AND FINALIZATION SUBSYSTEM
        # =========================================================================

        # Build common upload fields
        tags = meta.get("tags", ["education", "shorts"])
        hashtags_str = " ".join([f"#{t.strip().replace(' ', '')}" for t in tags if t.strip()])
        base_desc = meta.get("description", f"Educating about {topic}.")
        yt_desc = f"{base_desc}\n\n#TheDailyAudit #Shorts {hashtags_str}"
        fb_desc = f"{base_desc}\n\n#TheDailyAudit #Reels {hashtags_str}"

        # Upload to YouTube via API with retry
        yt_upload_success = False
        yt_video_id = None
        try:
            uploader = YouTubeUploader()
            print(f"[Main] Connecting to YouTube Data API for Short deployment with tags: {tags}")
            @retry_with_backoff(max_retries=3, base_delay=2.0)
            def _yt_upload():
                thumb_path = os.path.splitext(video_path)[0] + "_thumb.png"
                return uploader.upload_short(video_path, title, yt_desc, tags, thumbnail_path=thumb_path)
            yt_upload_success, yt_video_id = _yt_upload()
            if yt_upload_success and yt_video_id:
                comment_hook = script_payload.get("comment_hook", "")
                if comment_hook:
                    print(f"[Main] Posting and pinning comment hook: '{comment_hook}'")
                    uploader.post_and_pin_comment(yt_video_id, comment_hook)
        except Exception as e:
            print(f"[Main] ERROR: YouTube upload subsystem failed: {e}")

        # Upload to Facebook Reels via API with retry
        fb_upload_success = False
        fb_video_id = None
        try:
            fb_uploader = FacebookUploader()
            print("[Main] Connecting to Meta Graph API for Facebook Reels deployment...")
            @retry_with_backoff(max_retries=3, base_delay=2.0)
            def _fb_upload():
                return fb_uploader.upload_reel(video_path, fb_desc)
            fb_upload_success, fb_video_id = _fb_upload()
        except Exception as e:
            print(f"[Main] ERROR: Facebook upload subsystem failed: {e}")

        # Complete transaction: Log history with A/B metadata if successfully uploaded
        if yt_upload_success or fb_upload_success:
            try:
                ingestion.log_uploaded_topic(
                    topic, hook_text,
                    style_preset=video_style,
                    video_type=video_type,
                    transition_type=transition_type,
                )
                print(f"[Main] SUCCESS: Topic '{topic}' permanently retired and logged in database.")
                print(f"[Main] A/B Data: style={video_style}, type={video_type}, transition={transition_type}")
                
                # Log to analytics for cross-session tracking
                try:
                    analytics = AnalyticsLogger()
                    analytics.log_video({
                        "episode": episode_num,
                        "topic": topic,
                        "category": category,
                        "format": video_type,
                        "style_preset": video_style,
                        "transition_type": transition_type,
                        "word_count": script_payload.get("word_count", 0) if isinstance(script_payload, dict) else 0,
                        "duration_seconds": None,
                        "uploaded_at": datetime.datetime.now(datetime.timezone.utc).isoformat().replace("+00:00", "Z"),
                        "youtube_video_id": yt_video_id,
                    })
                    print(f"[Main] Analytics entry logged.")
                except Exception as e:
                    print(f"[Main] WARNING: Failed to log analytics: {e}")
            except Exception as e:
                print(f"[Main] WARNING: Failed to record upload event in database: {e}")
        else:
            print(f"[Main] WARNING: Upload transaction was not marked successful on any platform. Local video remains in: {video_path}")

        print("\n" + "=" * 80)
        print(f"   CYCLE COMPLETED SUCCESSFULLY FOR FORMAT: {video_type.upper()}")
        print("=" * 80 + "\n")

if __name__ == "__main__":
    run_pipeline()

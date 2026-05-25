# =============================================================================
# "The Daily Audit" - Local Testing Pipeline (no uploads, no topic retirement)
# =============================================================================
import os
import sys
import time
import argparse
import random
import re
import datetime
from dotenv import load_dotenv

# Load local environment parameters
load_dotenv()

from data_ingestion import DataIngestion
from llm_orchestrator import LLMOrchestrator
from asset_generator import AssetGenerator
from video_engine import VideoEngine, STYLE_PRESETS
from data_scraper import DataScraper

CTA_ROTATION = [
    "That was today's audit. Subscribe — the next file is already open.",
    "Case closed. Follow for tomorrow's declassified truth.",
    "Audit complete. Subscribe — we expose one lie every single day.",
    "File sealed. Hit follow — tomorrow's case is worse.",
    "Subscribe now. The truth does not wait.",
]

STYLES = ["blueprint", "blueprint", "chalkboard", "classified", "cyberpunk", "retro_vhs", "terminal"]


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


def run_pipeline():
    """Executes the Shorts generation pipeline for local testing (no uploads, no topic retirement)."""
    print("=" * 80)
    print("   STARTING LOCAL TEST PIPELINE: THE DAILY AUDIT SHORTS NETWORK")
    print("   (Uploads disabled — topics ARE retired to prevent duplicate picks)")
    print("=" * 80)

    # 0. Parse Command Line Arguments for Video Type
    parser = argparse.ArgumentParser(description="TDA Shorts Pipeline — Local Test Mode")
    parser.add_argument("--type", choices=["myth", "bizarre", "all", "dynamic"], default=None, help="Specify video format type, 'all' to build all, 'dynamic' for user-prompt-driven, or omit for random weighted selection")
    parser.add_argument("--prompt", type=str, default=None, help="User prompt for dynamic video generation (requires --type dynamic)")
    args = parser.parse_args()

    if args.type == "dynamic" and not args.prompt:
        print("[Local] ERROR: --prompt is required when --type is 'dynamic'")
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
        print(f"[Local] Theme Days Selection: Today is {day_of_week} ({day_info['name']}) -> Format: {day_info['type'].upper()}, Category Filter: {category_filter}")
    print(f"[Local] Production Target Formats Selected: {[t.upper() for t in selected_types]}")

    # Select a random visual style for variety (weighted: blueprint 50%, chalkboard 25%, classified 25%)
    video_style = random.choice(STYLES)
    print(f"[Local] Visual Style Selected: {video_style.upper()}")

    # Select a random CTA for this run
    cta_text = random.choice(CTA_ROTATION)
    print(f"[Local] CTA Text: '{cta_text}'")
    
    # 1. Initialize Ingestion Module & SQLite Database
    try:
        ingestion = DataIngestion()
        print(f"[Local] Database initialized. Target path: {ingestion.db_path}")
    except Exception as e:
        print(f"[Local] CRITICAL: Failed to initialize SQLite database: {e}")
        sys.exit(1)

    # 2. Initialize Gemini API Client & Script Architect
    gemini_key = (
        os.getenv("FREE_GEMINI_API_KEY") 
        or os.getenv("GEMINI_API_KEY") 
        or os.getenv("PAID_GEMINI_API_KEY")
    )
    if not gemini_key:
        print("[Local] CRITICAL: Gemini API Key environment variable is missing.")
        print("[Local] Please define FREE_GEMINI_API_KEY or GEMINI_API_KEY in your .env file.")
        sys.exit(1)

    try:
        orchestrator = LLMOrchestrator(api_key=gemini_key)
    except Exception as e:
        print(f"[Local] CRITICAL: Failed to initialize Gemini Script Orchestrator: {e}")
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
                topic, category, description = ingestion.fetch_unused_misconception(gemini_client=client_ref, category_filter=category_filter)
                print(f"[Local] Selected Myth Topic: '{topic}' | Discipline: {category}")
            except Exception as e:
                print(f"[Local] CRITICAL: Ingestion failed to retrieve misconception: {e}")
                sys.exit(1)

            # Immediately reserve topic to prevent re-selection if pipeline crashes
            ingestion.log_uploaded_topic(topic, "")

            # Generate structured script payload from Gemini
            script_payload = None
            try:
                print("[Local] Calling Gemini to construct structured short script...")
                script_payload = orchestrator.generate_script(topic, category, description)
                episode_num = ingestion.get_next_episode()
                script_payload["episode_num"] = episode_num
                word_count = LLMOrchestrator.calculate_word_count(script_payload)
                print(f"[Local] Script generated successfully. Word count: {word_count} | Episode: {episode_num}")
            except Exception as e:
                print(f"[Local] ERROR: Script generation failed: {e}")
                sys.exit(1)

            # Initialize Asset Generator
            try:
                gcp_cred = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
                asset_gen = AssetGenerator(gemini_client=client_ref, gcp_credentials_path=gcp_cred)
            except Exception as e:
                print(f"[Local] CRITICAL: Failed to initialize Asset Generator: {e}")
                sys.exit(1)

            # Compile speech text in rich SSML format
            hook_clean = script_payload.get('hook', '').strip()
            context_clean = script_payload.get('context', '').strip()
            fact_clean = script_payload.get('fact', '').strip()

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
                print(f"[Local] Myth Starting Bumper: '{starting_text}'")

                # --- Ending bumper TTS ---
                ending_text = f"{cta_text} CLASS DISMISSED."
                ending_ssml_wrapped = f"<prosody pitch='0st' rate='0.95'>{ending_text}</prosody>"
                print(f"[Local] Myth Ending Bumper: '{ending_text}'")

                # Determine raw ssml script
                if "ssml_script" in script_payload:
                    ssml_raw = script_payload["ssml_script"]
                else:
                    ssml_raw = (
                        f"{hook_clean}"
                        f"<break time='700ms'/>"
                        f"{context_clean}"
                        f"<break time='1200ms'/>"
                        f"{fact_clean}"
                    )
                
                # Split SSML into 3 content scenes (no CTA/sign-off)
                s1_ssml, s2_ssml, s3_ssml = split_myth_ssml(
                    ssml_raw, hook_clean, context_clean, fact_clean
                )
                
                # Per-scene prosody: subtle variation, no voice degradation
                # All scenes use near-normal rate; the dramatic shift comes from SFX/music
                s1_ssml_wrapped = f"<prosody pitch='0st' rate='0.97'>{s1_ssml}</prosody>"
                s2_ssml_wrapped = f"<prosody pitch='0st' rate='0.95'>{s2_ssml}</prosody>"
                s3_ssml_wrapped = f"<prosody pitch='-0.5st' rate='0.93'>{s3_ssml}</prosody>"
                
                print(f"[Local] Myth Scene 1 SSML: {s1_ssml_wrapped}")
                print(f"[Local] Myth Scene 2 SSML: {s2_ssml_wrapped}")
                print(f"[Local] Myth Scene 3 SSML: {s3_ssml_wrapped}")
                
                # Build 5-element audio paths for content scenes and bumpers
                audio_paths = [
                    asset_gen.generate_tts_audio(starting_ssml_wrapped, f"tts_{timestamp}_start", is_ssml=True),
                    asset_gen.generate_tts_audio(s1_ssml_wrapped, f"tts_{timestamp}_s1", is_ssml=True),
                    asset_gen.generate_tts_audio(s2_ssml_wrapped, f"tts_{timestamp}_s2", is_ssml=True),
                    asset_gen.generate_tts_audio(s3_ssml_wrapped, f"tts_{timestamp}_s3", is_ssml=True),
                    asset_gen.generate_tts_audio(ending_ssml_wrapped, f"tts_{timestamp}_end", is_ssml=True),
                ]
            except Exception as e:
                print(f"[Local] ERROR: Asset Generator failed to create scene TTS MP3s: {e}")
                sys.exit(1)

            image_myth_path = None
            try:
                image_myth_name = f"background_myth_{timestamp}"
                visual_prompt_myth = script_payload.get("myth_visual_prompt", "Technical blueprint representing the false myth")
                print(f"[Local] Requesting visual representing the FALSE MYTH: '{visual_prompt_myth}'")
                # Append content safety instruction: no politics, no gore, no people, safe for teen+
                safe_suffix = " No human faces, no political content, no violence, no text, safe for all ages."
                image_myth_path = asset_gen.generate_background_image(visual_prompt_myth + safe_suffix, image_myth_name, aspect_ratio="9:16", is_blueprint=True, style_suffix=style_suffix)
            except Exception as e:
                print(f"[Local] ERROR: Myth background image generation failed: {e}")
                sys.exit(1)

            image_truth_path = None
            try:
                image_truth_name = f"foreground_fact_{timestamp}"
                visual_prompt_truth = script_payload.get("fact_visual_prompt", "Realistic laboratory or historical archive photography representing the scientific truth")
                print(f"[Local] Requesting visual representing the TRUTH/REALITY: '{visual_prompt_truth}'")
                safe_suffix = " No human faces, no political content, no violence, no text, safe for all ages."
                image_truth_path = asset_gen.generate_background_image(visual_prompt_truth + safe_suffix, image_truth_name, aspect_ratio="1:1", is_blueprint=False)
            except Exception as e:
                print(f"[Local] WARNING: Truth foreground image generation failed: {e}. Gracefully falling back to background-only rendering.")
                image_truth_path = None

            # ── Sprint 7: Visual Variety — Wikipedia scraping + extra Imagen images ──
            extra_images = []
            try:
                from data_scraper import DataScraper
                scraper = DataScraper()
                # Build search queries for Wikipedia: topic + related concepts
                wiki_queries = [topic]
                if hook_clean:
                    # Extract key nouns from hook for additional searches
                    hook_words = [w for w in hook_clean.split() if len(w) > 4]
                    if hook_words:
                        wiki_queries.append(' '.join(hook_words[:3]))
                if fact_clean:
                    fact_words = [w for w in fact_clean.split() if len(w) > 4]
                    if fact_words:
                        wiki_queries.append(' '.join(fact_words[:3]))
                wiki_images = scraper.fetch_multiple_wikipedia_images(
                    wiki_queries,
                    f"wiki_{timestamp}",
                    max_images=3
                )
                extra_images.extend(wiki_images)
                print(f"[Local] Wikipedia images fetched: {len(wiki_images)}")
            except ImportError:
                print("[Local] DataScraper not available — skipping Wikipedia image fetch")
            except Exception as e:
                print(f"[Local] Wikipedia image fetch failed: {e}")

            # Generate 1 extra Imagen image for scene 2 context variety
            extra_imagen_path = None
            try:
                extra_img_name = f"context_extra_{timestamp}"
                extra_prompt = script_payload.get("context_visual_prompt")
                if not extra_prompt:
                    extra_prompt = f"Scientific illustration showing {topic}, detailed, realistic, high contrast"
                extra_imagen_path = asset_gen.generate_background_image(
                    extra_prompt + " No politics, no violence, no human faces, safe for all ages.", extra_img_name,
                    aspect_ratio="1:1", is_blueprint=False
                )
                if extra_imagen_path:
                    extra_images.append(extra_imagen_path)
                    print(f"[Local] Extra context image generated: {extra_imagen_path}")
            except Exception as e:
                print(f"[Local] Extra image generation failed (non-fatal): {e}")

            # Build image_paths_override: [wiki1, myth_bg, wiki2, extra_imagen, wiki3, truth_fg, ...]
            image_paths_override = []
            # Scene 1 (Hook): myth bg + first wiki image
            if image_myth_path:
                image_paths_override.append(image_myth_path)
            # Scene 2 (Context): wiki images + extra imagen
            for ei in extra_images:
                image_paths_override.append(ei)
            # Scene 3 (Verdict): truth foreground — fresh image never seen before
            if image_truth_path:
                image_paths_override.append(image_truth_path)
            # Deduplicate
            seen = set()
            image_paths_override_deduped = []
            for p in image_paths_override:
                if p and p not in seen:
                    seen.add(p)
                    image_paths_override_deduped.append(p)
            image_paths_override = image_paths_override_deduped
            print(f"[Local] Total images for video: {len(image_paths_override)} ({image_paths_override})")

            meta = script_payload.get("youtube_metadata", {})
            raw_title = meta.get("title", f"The Daily Audit: {topic} #Shorts")
            if episode_num is not None:
                title = f"EP.{episode_num} — {raw_title}"
            else:
                title = raw_title
            if "youtube_metadata" in script_payload:
                script_payload["youtube_metadata"]["title"] = title
            clean_title = re.sub(r'[<>:"/\\|?*#]', '', title).strip().replace(' ', '_')[:100]

            try:
                video_eng = VideoEngine()
                video_name = f"{clean_title}_{timestamp}"
                script_payload["cta"] = cta_text
                script_payload["starting_text"] = starting_text
                script_payload["ending_text"] = ending_text
                video_path = video_eng.compile_short(image_myth_path, image_truth_path, audio_paths, script_payload, video_name, category, style=video_style, video_type="myth", image_paths_override=image_paths_override if image_paths_override else None)
                print(f"[Local] Video assembled and saved successfully: {video_path}")
                # Generate thumbnail using actual video images
                video_eng.generate_thumbnail(topic, hook_clean, video_name, style=video_style, img_myth_path=image_myth_path, img_truth_path=image_truth_path, episode_num=episode_num)
            except Exception as e:
                print(f"[Local] ERROR: Video engine compilation failed: {e}")
                sys.exit(1)

            hook_text = hook_clean

        # =========================================================================
        # FORMAT 2: DECLASSIFIED ANOMALIES (BIZARRE FACTS)
        # =========================================================================
        elif video_type == "bizarre":
            # 1. Retrieve bizarre topic
            try:
                topic, category, description = ingestion.fetch_unused_bizarre_topic(gemini_client=client_ref, category_filter=category_filter)
                print(f"[Local] Selected Anomaly Topic: '{topic}' | Discipline: {category}")
            except Exception as e:
                print(f"[Local] CRITICAL: Ingestion failed to retrieve bizarre topic: {e}")
                sys.exit(1)

            # Immediately reserve topic to prevent re-selection if pipeline crashes
            ingestion.log_uploaded_topic(topic, "")

            # 2. Generate structured script payload from Gemini
            try:
                print("[Local] Calling Gemini to construct bizarre fact script payload...")
                bizarre_payload = orchestrator.generate_bizarre_fact(topic, category)
                episode_num = ingestion.get_next_episode()
                bizarre_payload["episode_num"] = episode_num
                print(f"[Local] Anomaly script generated: '{bizarre_payload.get('hook')}' | Episode: {episode_num}")
            except Exception as e:
                print(f"[Local] ERROR: Anomaly script generation failed: {e}")
                sys.exit(1)

            # 3. Initialize Asset Generator and Data Scraper
            try:
                gcp_cred = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
                asset_gen = AssetGenerator(gemini_client=client_ref, gcp_credentials_path=gcp_cred)
                scraper = DataScraper()
            except Exception as e:
                print(f"[Local] CRITICAL: Failed to initialize asset systems: {e}")
                sys.exit(1)

            # 4. Scrape 3 images from multiple sources for immersive scenes
            scene_queries = [
                bizarre_payload.get("illustration_query", topic),
                bizarre_payload.get("scene_query_2", "") or bizarre_payload.get("illustration_query", topic),
                bizarre_payload.get("scene_query_3", "") or bizarre_payload.get("illustration_query", topic),
            ]

            scraped_bizarre_images = []
            try:
                scraped_bizarre_images = scraper.fetch_scene_images(
                    scene_queries, f"bizarre_{timestamp}", max_images=3
                )
            except Exception as e:
                print(f"[Local] Scraper failed for bizarre scenes: {e}")

            if not scraped_bizarre_images:
                fallback_query = scene_queries[0] if scene_queries else topic
                print(f"[Local] Falling back to programmatic image for bizarre query '{fallback_query}'")
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
                    print(f"[Local] Failed to generate fallback image: {e}")
                    sys.exit(1)

            image_myth_path = scraped_bizarre_images[0]
            image_truth_path = scraped_bizarre_images[-1]

            # 5. Generate TTS Audio with 5-part structure (starting, s1, s2, s3, ending)
            hook_clean = bizarre_payload.get('hook', '').strip()
            why_bizarre = bizarre_payload.get('why_bizarre', '').strip()
            closing_statement = bizarre_payload.get('closing_statement', '').strip()
            
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
                print(f"[Local] Bizarre Starting Bumper: '{starting_text}'")

                # --- Ending bumper TTS ---
                ending_text = f"{cta_text} CLASS DISMISSED."
                ending_ssml_wrapped = f"<prosody pitch='0st' rate='0.95'>{ending_text}</prosody>"
                print(f"[Local] Bizarre Ending Bumper: '{ending_text}'")

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
                
                print(f"[Local] Bizarre Scene 1 SSML: {s1_ssml_wrapped}")
                print(f"[Local] Bizarre Scene 2 SSML: {s2_ssml_wrapped}")
                print(f"[Local] Bizarre Scene 3 SSML: {s3_ssml_wrapped}")
                
                audio_paths = [
                    asset_gen.generate_tts_audio(starting_ssml_wrapped, f"bizarre_tts_{timestamp}_start", is_ssml=True),
                    asset_gen.generate_tts_audio(s1_ssml_wrapped, f"bizarre_tts_{timestamp}_s1", is_ssml=True),
                    asset_gen.generate_tts_audio(s2_ssml_wrapped, f"bizarre_tts_{timestamp}_s2", is_ssml=True),
                    asset_gen.generate_tts_audio(s3_ssml_wrapped, f"bizarre_tts_{timestamp}_s3", is_ssml=True),
                    asset_gen.generate_tts_audio(ending_ssml_wrapped, f"bizarre_tts_{timestamp}_end", is_ssml=True),
                ]
            except Exception as e:
                print(f"[Local] ERROR: Asset Generator failed to create bizarre scene TTS MP3s: {e}")
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
            
            try:
                video_eng = VideoEngine()
                video_name = f"{clean_title}_{timestamp}"
                video_path = video_eng.compile_bizarre(
                    scraped_bizarre_images, audio_paths, script_payload,
                    video_name, category, style=video_style, video_type="bizarre"
                )
                print(f"[Local] Anomaly Video assembled successfully: {video_path}")
                video_eng.generate_thumbnail(
                    topic, hook_clean, video_name, style=video_style,
                    img_myth_path=scraped_bizarre_images[0], img_truth_path=scraped_bizarre_images[-1],
                    bizarre_mode=True, episode_num=episode_num
                )
            except Exception as e:
                print(f"[Local] ERROR: Video engine compilation failed: {e}")
                sys.exit(1)

            hook_text = hook_clean

        # =========================================================================
        # FORMAT 3: DYNAMIC USER-PROMPT VIDEO
        # =========================================================================
        elif video_type == "dynamic":
            user_prompt = args.prompt
            print(f"[Local] DYNAMIC MODE: Processing user prompt: '{user_prompt}'")

            # 1. Research phase (Wikipedia scrape)
            try:
                scraper = DataScraper()
                print(f"[Local] Scraping research data for prompt: '{user_prompt}'")
                scraped_data = scraper.scrape_wikipedia_summary(user_prompt)
                print(f"[Local] Scraped {len(scraped_data)} chars of research data.")
            except Exception as e:
                print(f"[Local] ERROR: Scraper failed: {e}")
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
                print(f"[Local] Pipeline completed: topic='{topic}', scenes={len(scene_sequence)}")
            except Exception as e:
                print(f"[Local] CRITICAL: Pipeline orchestrator failed: {e}")
                sys.exit(1)

            # 3. Initialize Asset Generator
            try:
                gcp_cred = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
                asset_gen = AssetGenerator(gemini_client=client_ref, gcp_credentials_path=gcp_cred)
            except Exception as e:
                print(f"[Local] CRITICAL: Failed to initialize Asset Generator: {e}")
                sys.exit(1)

            # 4. Fetch materials (images per content scene)
            image_paths = []
            timestamp = f"{int(time.time())}_{random.randint(1000, 9999)}"
            
            content_scenes = scene_sequence[1:-1]
            for i, scene in enumerate(content_scenes):
                query = scene.get("visual_query", "").strip()
                if not query:
                    query = topic
                
                try:
                    print(f"[Local] Fetching image for content scene {i+1} using query: '{query}'")
                    path = scraper.fetch_image_multi_source(query, f"dynamic_{timestamp}_scene{i}")
                    if path:
                        image_paths.append(path)
                    else:
                        print(f"[Local] No image found for scene {i} query '{query}', generating fallback blueprint...")
                        fallback_path = os.path.join(asset_gen.assets_dir, f"dynamic_fallback_{timestamp}_scene{i}.png")
                        path = asset_gen._render_programmatic_blueprint(query, fallback_path)
                        image_paths.append(path)
                except Exception as e:
                    print(f"[Local] Image fetch failed for scene {i}: {e}, generating fallback blueprint...")
                    fallback_path = os.path.join(asset_gen.assets_dir, f"dynamic_fallback_{timestamp}_scene{i}.png")
                    try:
                        path = asset_gen._render_programmatic_blueprint(query, fallback_path)
                        image_paths.append(path)
                    except Exception:
                        from PIL import Image
                        os.makedirs(asset_gen.assets_dir, exist_ok=True)
                        Image.new("RGB", (1080, 1920), (10, 24, 47)).save(fallback_path)
                        image_paths.append(fallback_path)

            print(f"[Local] Fetched {len(image_paths)} scene images")

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
                    print(f"[Local] Dynamic Scene {i+1} ({scene_type.upper()}): emotion='{emotion}' -> Generating TTS...")
                    
                    audio_path = asset_gen.generate_tts_audio(scene_ssml, label, is_ssml=True)
                    audio_paths.append(audio_path)
                    
                scene_count = len(scene_sequence) - 2
                print(f"[Local] Generated {len(audio_paths)} TTS audio files for {scene_count} content scenes")
            except Exception as e:
                print(f"[Local] ERROR: TTS generation failed: {e}")
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
                print(f"[Local] Dynamic video assembled successfully: {video_path}")
                
                video_eng.generate_thumbnail(
                    topic, scene_sequence[1]["narration_text"] if len(scene_sequence) > 1 else topic,
                    video_name, style=video_style,
                    img_myth_path=image_paths[0] if image_paths else None,
                    img_truth_path=image_paths[-1] if len(image_paths) > 1 else None,
                    bizarre_mode=True,
                )
            except Exception as e:
                print(f"[Local] ERROR: Video engine compilation failed: {e}")
                sys.exit(1)

            hook_text = scene_sequence[0]["narration_text"] if scene_sequence else ""

        # =========================================================================
        # LOCAL TEST MODE: No uploads, no topic retirement
        # =========================================================================
        print(f"[Local] Local test video saved at: {video_path}")
        print(f"[Local] Topic '{topic}' has been reserved and will not be reused by main.py.")

        print("\n" + "=" * 80)
        print(f"   LOCAL TEST CYCLE COMPLETED SUCCESSFULLY FOR FORMAT: {video_type.upper()}")
        print("=" * 80 + "\n")


if __name__ == "__main__":
    run_pipeline()

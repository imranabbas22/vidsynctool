# =============================================================================
# "The Daily Audit" - Local Testing Pipeline (no uploads, no topic retirement)
# =============================================================================
import os
import sys
import time
import argparse
import random
import re
from dotenv import load_dotenv

# Load local environment parameters
load_dotenv()

from data_ingestion import DataIngestion
from llm_orchestrator import LLMOrchestrator
from asset_generator import AssetGenerator
from video_engine import VideoEngine, STYLE_PRESETS
from data_scraper import DataScraper

CTA_ROTATION = [
    "Subscribe. Tomorrow, I expose another lie.",
    "Subscribe — we expose a new lie EVERY. SINGLE. DAY.",
    "Join the truth-seekers. New declassified files daily.",
    "Hit subscribe — or keep believing the lies.",
    "The truth does not declassify itself. Neither does your sub button.",
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
    return s1_ssml, s2_ssml, s3_ssml


def run_pipeline():
    """Executes the Shorts generation pipeline for local testing (no uploads, no topic retirement)."""
    print("=" * 80)
    print("   STARTING LOCAL TEST PIPELINE: THE DAILY AUDIT SHORTS NETWORK")
    print("   (Uploads disabled — topics are NOT retired from the database)")
    print("=" * 80)

    # 0. Parse Command Line Arguments for Video Type
    parser = argparse.ArgumentParser(description="TDA Shorts Pipeline — Local Test Mode")
    parser.add_argument("--type", choices=["myth", "bizarre", "all", "dynamic"], default=None, help="Specify video format type, 'all' to build all, 'dynamic' for user-prompt-driven, or omit for random weighted selection")
    parser.add_argument("--prompt", type=str, default=None, help="User prompt for dynamic video generation (requires --type dynamic)")
    args = parser.parse_args()

    if args.type == "dynamic" and not args.prompt:
        print("[Local] ERROR: --prompt is required when --type is 'dynamic'")
        sys.exit(1)

    selected_types = []
    if args.type:
        if args.type == "all":
            selected_types = ["myth", "bizarre"]
        else:
            selected_types = [args.type]
    else:
        # Default: pick one randomly with weighted probabilities
        selected_types = [random.choices(["myth", "bizarre"], weights=[0.60, 0.40], k=1)[0]]
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
                topic, category, description = ingestion.fetch_unused_misconception(gemini_client=client_ref)
                print(f"[Local] Selected Myth Topic: '{topic}' | Discipline: {category}")
            except Exception as e:
                print(f"[Local] CRITICAL: Ingestion failed to retrieve misconception: {e}")
                sys.exit(1)

            # NOTE: Topic is NOT reserved in the database — local testing only

            # Generate structured script payload from Gemini
            script_payload = None
            try:
                print("[Local] Calling Gemini to construct structured short script...")
                script_payload = orchestrator.generate_script(topic, category, description)
                word_count = LLMOrchestrator.calculate_word_count(script_payload)
                print(f"[Local] Script generated successfully. Word count: {word_count}")
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
                # --- Starting bumper TTS ---
                starting_text = "Now, bringing you the strangest MYTH that will shock you."
                starting_ssml_wrapped = f"<prosody pitch='-1.0st' rate='0.93'>{starting_text}</prosody>"
                print(f"[Local] Myth Starting Bumper: '{starting_text}'")

                # --- Ending bumper TTS ---
                ending_text = f"{cta_text} CLASS DISMISSED."
                ending_ssml_wrapped = f"<prosody pitch='-1.0st' rate='0.93'>{ending_text}</prosody>"
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
                
                s1_ssml_wrapped = f"<prosody pitch='-1.0st' rate='0.93'>{s1_ssml}</prosody>"
                s2_ssml_wrapped = f"<prosody pitch='-1.0st' rate='0.93'>{s2_ssml}</prosody>"
                s3_ssml_wrapped = f"<prosody pitch='-1.0st' rate='0.93'>{s3_ssml}</prosody>"
                
                print(f"[Local] Myth Scene 1 SSML: {s1_ssml_wrapped}")
                print(f"[Local] Myth Scene 2 SSML: {s2_ssml_wrapped}")
                print(f"[Local] Myth Scene 3 SSML: {s3_ssml_wrapped}")
                
                # Build 3-element audio paths for content scenes (bumpers are pre-rendered)
                audio_paths = [
                    asset_gen.generate_tts_audio(s1_ssml_wrapped, f"tts_{timestamp}_s1", is_ssml=True),
                    asset_gen.generate_tts_audio(s2_ssml_wrapped, f"tts_{timestamp}_s2", is_ssml=True),
                    asset_gen.generate_tts_audio(s3_ssml_wrapped, f"tts_{timestamp}_s3", is_ssml=True),
                ]
            except Exception as e:
                print(f"[Local] ERROR: Asset Generator failed to create scene TTS MP3s: {e}")
                sys.exit(1)

            image_myth_path = None
            try:
                image_myth_name = f"background_myth_{timestamp}"
                visual_prompt_myth = script_payload.get("myth_visual_prompt", "Technical blueprint representing the false myth")
                print(f"[Local] Requesting visual representing the FALSE MYTH: '{visual_prompt_myth}'")
                image_myth_path = asset_gen.generate_background_image(visual_prompt_myth, image_myth_name, aspect_ratio="9:16", is_blueprint=True, style_suffix=style_suffix)
            except Exception as e:
                print(f"[Local] ERROR: Myth background image generation failed: {e}")
                sys.exit(1)

            image_truth_path = None
            try:
                image_truth_name = f"foreground_fact_{timestamp}"
                visual_prompt_truth = script_payload.get("fact_visual_prompt", "Realistic laboratory or historical archive photography representing the scientific truth")
                print(f"[Local] Requesting visual representing the TRUTH/REALITY: '{visual_prompt_truth}'")
                image_truth_path = asset_gen.generate_background_image(visual_prompt_truth, image_truth_name, aspect_ratio="1:1", is_blueprint=False)
            except Exception as e:
                print(f"[Local] WARNING: Truth foreground image generation failed: {e}. Gracefully falling back to background-only rendering.")
                image_truth_path = None

            meta = script_payload.get("youtube_metadata", {})
            title = meta.get("title", f"The Daily Audit: {topic} #Shorts")
            clean_title = re.sub(r'[<>:"/\\|?*#]', '', title).strip().replace(' ', '_')[:100]

            try:
                video_eng = VideoEngine()
                video_name = f"{clean_title}_{timestamp}"
                script_payload["cta"] = cta_text
                script_payload["starting_text"] = starting_text
                script_payload["ending_text"] = ending_text
                video_path = video_eng.compile_short(image_myth_path, image_truth_path, audio_paths, script_payload, video_name, category, style=video_style, video_type="myth")
                print(f"[Local] Video assembled and saved successfully: {video_path}")
                # Generate thumbnail using actual video images
                video_eng.generate_thumbnail(topic, hook_clean, video_name, style=video_style, img_myth_path=image_myth_path, img_truth_path=image_truth_path)
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
                topic, category, description = ingestion.fetch_unused_bizarre_topic(gemini_client=client_ref)
                print(f"[Local] Selected Anomaly Topic: '{topic}' | Discipline: {category}")
            except Exception as e:
                print(f"[Local] CRITICAL: Ingestion failed to retrieve bizarre topic: {e}")
                sys.exit(1)

            # NOTE: Topic is NOT reserved in the database — local testing only

            # 2. Generate structured script payload from Gemini
            try:
                print("[Local] Calling Gemini to construct bizarre fact script payload...")
                bizarre_payload = orchestrator.generate_bizarre_fact(topic, category)
                print(f"[Local] Anomaly script generated: '{bizarre_payload.get('hook')}'")
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
                # --- Starting bumper TTS ---
                starting_text = "Now, bringing you the most BIZARRE TRUTH that will shock you."
                starting_ssml_wrapped = f"<prosody pitch='-1.0st' rate='0.93'>{starting_text}</prosody>"
                print(f"[Local] Bizarre Starting Bumper: '{starting_text}'")

                # --- Ending bumper TTS ---
                ending_text = f"{cta_text} CLASS DISMISSED."
                ending_ssml_wrapped = f"<prosody pitch='-1.0st' rate='0.93'>{ending_text}</prosody>"
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
                
                s1_ssml_wrapped = f"<prosody pitch='-1.0st' rate='0.93'>{s1_ssml}</prosody>"
                s2_ssml_wrapped = f"<prosody pitch='-1.0st' rate='0.93'>{s2_ssml}</prosody>"
                s3_ssml_wrapped = f"<prosody pitch='-1.0st' rate='0.93'>{s3_ssml}</prosody>"
                
                print(f"[Local] Bizarre Scene 1 SSML: {s1_ssml_wrapped}")
                print(f"[Local] Bizarre Scene 2 SSML: {s2_ssml_wrapped}")
                print(f"[Local] Bizarre Scene 3 SSML: {s3_ssml_wrapped}")
                
                audio_paths = [
                    asset_gen.generate_tts_audio(s1_ssml_wrapped, f"bizarre_tts_{timestamp}_s1", is_ssml=True),
                    asset_gen.generate_tts_audio(s2_ssml_wrapped, f"bizarre_tts_{timestamp}_s2", is_ssml=True),
                    asset_gen.generate_tts_audio(s3_ssml_wrapped, f"bizarre_tts_{timestamp}_s3", is_ssml=True),
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
            }

            # 7. Compile Anomaly Video with multiple scene images
            meta = bizarre_payload.get("youtube_metadata", {})
            title = meta.get("title", f"Declassified Anomaly: {topic} #Shorts")
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
                    bizarre_mode=True,
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
        print(f"[Local] Topic '{topic}' was NOT retired — it remains available for future runs.")

        print("\n" + "=" * 80)
        print(f"   LOCAL TEST CYCLE COMPLETED SUCCESSFULLY FOR FORMAT: {video_type.upper()}")
        print("=" * 80 + "\n")


if __name__ == "__main__":
    run_pipeline()

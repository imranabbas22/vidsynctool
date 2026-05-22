# =============================================================================
# "The Daily Audit" - Master Orchestration Pipeline
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
from youtube_uploader import YouTubeUploader
from facebook_uploader import FacebookUploader
from tiktok_uploader import TikTokUploader
from data_scraper import DataScraper

CTA_ROTATION = [
    "Subscribe for more declassified truths.",
    "Follow The Daily Audit. The truth does not declassify itself.",
    "Hit subscribe. The next audit file is already open.",
    "Join the audit. New declassified files every day.",
]

STYLES = ["blueprint", "blueprint", "chalkboard", "classified"]


def split_myth_ssml(ssml_script, hook_clean, context_clean, fact_clean, sign_off_clean, cta_text):
    """
    Splits the unified SSML script into 3 scenes for Myth format.
    """
    clean_ssml = ssml_script.strip()
    for tag in ["<speak>", "</speak>"]:
        clean_ssml = clean_ssml.replace(tag, "")
    clean_ssml = re.sub(r'<voice[^>]*>', '', clean_ssml)
    clean_ssml = clean_ssml.replace('</voice>', '').strip()
    
    # Strip "Class dismissed" at the end if it exists
    ssml_temp = re.sub(r'<break\s+time=["\']1000ms["\']\s*/>\s*Class\s+dismissed\.?', '', clean_ssml, flags=re.IGNORECASE).strip()
    ssml_temp = re.sub(r'Class\s+dismissed\.?', '', ssml_temp, flags=re.IGNORECASE).strip()
    
    # Find all break tags in ssml_temp
    break_pattern = r'<break\s+time=["\']([^"\']+)["\']\s*/>'
    matches = list(re.finditer(break_pattern, ssml_temp, flags=re.IGNORECASE))
    
    idx_1200 = -1
    for i, m in enumerate(matches):
        if "1200" in m.group(1):
            idx_1200 = i
            break
            
    if idx_1200 != -1:
        # Split at the 1200ms break
        m_1200 = matches[idx_1200]
        s1_ssml = ssml_temp[:m_1200.start()].strip()
        s2_ssml = ssml_temp[m_1200.end():].strip()
        s3_ssml = f"{cta_text} <break time='550ms'/> Class dismissed."
        
        # Clean double spaces
        s1_ssml = re.sub(r'\s+', ' ', s1_ssml).strip()
        s2_ssml = re.sub(r'\s+', ' ', s2_ssml).strip()
        s3_ssml = re.sub(r'\s+', ' ', s3_ssml).strip()
        return s1_ssml, s2_ssml, s3_ssml
        
    # Fallback to fields
    s1_ssml = f"{hook_clean} <break time='550ms'/> {context_clean}"
    s2_ssml = f"{fact_clean}"
    s3_ssml = f"{cta_text} <break time='550ms'/> {sign_off_clean}"
    
    s1_ssml = re.sub(r'\s+', ' ', s1_ssml).strip()
    s2_ssml = re.sub(r'\s+', ' ', s2_ssml).strip()
    s3_ssml = re.sub(r'\s+', ' ', s3_ssml).strip()
    return s1_ssml, s2_ssml, s3_ssml


def split_bizarre_ssml(ssml_script, hook_clean, story_brief, why_bizarre, closing_statement, sign_off_clean, cta_text):
    """
    Splits the unified SSML script into 3 scenes for Bizarre format.
    """
    clean_ssml = ssml_script.strip()
    for tag in ["<speak>", "</speak>"]:
        clean_ssml = clean_ssml.replace(tag, "")
    clean_ssml = re.sub(r'<voice[^>]*>', '', clean_ssml)
    clean_ssml = clean_ssml.replace('</voice>', '').strip()
    
    # Strip "Class dismissed" at the end if it exists
    ssml_temp = re.sub(r'<break\s+time=["\']1000ms["\']\s*/>\s*Class\s+dismissed\.?', '', clean_ssml, flags=re.IGNORECASE).strip()
    ssml_temp = re.sub(r'Class\s+dismissed\.?', '', ssml_temp, flags=re.IGNORECASE).strip()
    
    # Find all break tags in ssml_temp
    break_pattern = r'<break\s+time=["\']([^"\']+)["\']\s*/>'
    matches = list(re.finditer(break_pattern, ssml_temp, flags=re.IGNORECASE))
    
    idx_1200 = -1
    for i, m in enumerate(matches):
        if "1200" in m.group(1):
            idx_1200 = i
            break
            
    if idx_1200 != -1:
        # We split the ssml_temp into segments by breaks
        segments = []
        prev_end = 0
        for m in matches:
            segments.append(ssml_temp[prev_end:m.start()])
            prev_end = m.end()
        segments.append(ssml_temp[prev_end:])
        
        # Reconstruct Scene 1: Hook + Story Brief
        s1_parts = [segments[0]]
        for i in range(1, idx_1200 + 1):
            break_tag = matches[i-1].group(0)
            s1_parts.append(break_tag)
            s1_parts.append(segments[i])
        s1_ssml = " ".join(s1_parts).strip()
        
        # Reconstruct Scene 2: Why Bizarre (truth reveal)
        s2_ssml = segments[idx_1200 + 1].strip()
        
        # Reconstruct Scene 3: Closing Statement + CTA + Sign-off
        s3_parts = []
        for i in range(idx_1200 + 2, len(segments)):
            if i > idx_1200 + 2:
                break_tag = matches[i-1].group(0)
                s3_parts.append(break_tag)
            s3_parts.append(segments[i])
        closing_ssml = " ".join(s3_parts).strip()
        
        if closing_ssml:
            s3_ssml = f"{closing_ssml} <break time='500ms'/> {cta_text} <break time='400ms'/> Class dismissed."
        else:
            s3_ssml = f"{cta_text} <break time='400ms'/> Class dismissed."
            
        # Clean double spaces
        s1_ssml = re.sub(r'\s+', ' ', s1_ssml).strip()
        s2_ssml = re.sub(r'\s+', ' ', s2_ssml).strip()
        s3_ssml = re.sub(r'\s+', ' ', s3_ssml).strip()
        return s1_ssml, s2_ssml, s3_ssml

    # Fallback to fields
    s1_ssml = f"{hook_clean} <break time='600ms'/> {story_brief}"
    s2_ssml = f"{why_bizarre}"
    s3_ssml = f"{closing_statement} <break time='500ms'/> {cta_text} <break time='400ms'/> {sign_off_clean}"
    
    s1_ssml = re.sub(r'\s+', ' ', s1_ssml).strip()
    s2_ssml = re.sub(r'\s+', ' ', s2_ssml).strip()
    s3_ssml = re.sub(r'\s+', ' ', s3_ssml).strip()
    return s1_ssml, s2_ssml, s3_ssml


def run_pipeline():
    """Executes the complete Shorts generation and uploading pipeline."""
    print("=" * 80)
    print("   STARTING AUTOMATED PRODUCTION CYCLE: THE DAILY AUDIT SHORTS NETWORK")
    print("=" * 80)

    # 0. Parse Command Line Arguments for Video Type
    parser = argparse.ArgumentParser(description="TDA Shorts Pipeline Master Script")
    parser.add_argument("--type", choices=["myth", "bizarre", "all"], default=None, help="Specify video format type, 'all' to build all, or omit for random weighted selection")
    parser.add_argument("--skip-tiktok", action="store_true", help="Skip TikTok upload")
    args = parser.parse_args()

    selected_types = []
    if args.type:
        if args.type == "all":
            selected_types = ["myth", "bizarre"]
        else:
            selected_types = [args.type]
    else:
        # Default: pick one randomly with weighted probabilities
        selected_types = [random.choices(["myth", "bizarre"], weights=[0.60, 0.40], k=1)[0]]
    print(f"[Main] Production Target Formats Selected: {[t.upper() for t in selected_types]}")

    # Select a random visual style for variety (weighted: blueprint 50%, chalkboard 25%, classified 25%)
    video_style = random.choice(STYLES)
    print(f"[Main] Visual Style Selected: {video_style.upper()}")

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
                topic, category, description = ingestion.fetch_unused_misconception(gemini_client=client_ref)
                print(f"[Main] Selected Myth Topic: '{topic}' | Discipline: {category}")
            except Exception as e:
                print(f"[Main] CRITICAL: Ingestion failed to retrieve misconception: {e}")
                sys.exit(1)

            # Immediately reserve topic to prevent re-selection if pipeline crashes
            ingestion.log_uploaded_topic(topic, "")

            # Generate structured script payload from Gemini
            script_payload = None
            try:
                print("[Main] Calling Gemini to construct structured short script...")
                script_payload = orchestrator.generate_script(topic, category, description)
                word_count = LLMOrchestrator.calculate_word_count(script_payload)
                print(f"[Main] Script generated successfully. Word count: {word_count}")
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

            # Compile speech text in rich SSML format
            hook_clean = script_payload.get('hook', '').strip()
            context_clean = script_payload.get('context', '').strip()
            fact_clean = script_payload.get('fact', '').strip()
            sign_off_clean = script_payload.get('sign_off', '').strip()

            # Split and generate 3-scene audio files
            audio_paths = []
            try:
                # Determine raw ssml script
                if "ssml_script" in script_payload:
                    ssml_raw = script_payload["ssml_script"]
                else:
                    ssml_raw = (
                        f"{hook_clean}"
                        f"<break time='550ms'/>"
                        f"{context_clean}"
                        f"<break time='1200ms'/>"
                        f"{fact_clean}"
                    )
                
                # Split SSML into scenes
                s1_ssml, s2_ssml, s3_ssml = split_myth_ssml(
                    ssml_raw, hook_clean, context_clean, fact_clean, sign_off_clean, cta_text
                )
                
                s1_ssml_wrapped = f"<prosody pitch='-1.0st' rate='0.93'>{s1_ssml}</prosody>"
                s2_ssml_wrapped = f"<prosody pitch='-1.0st' rate='0.93'>{s2_ssml}</prosody>"
                s3_ssml_wrapped = f"<prosody pitch='-1.0st' rate='0.93'>{s3_ssml}</prosody>"
                
                print(f"[Main] Myth Scene 1 SSML: {s1_ssml_wrapped}")
                print(f"[Main] Myth Scene 2 SSML: {s2_ssml_wrapped}")
                print(f"[Main] Myth Scene 3 SSML: {s3_ssml_wrapped}")
                
                audio_paths = [
                    asset_gen.generate_tts_audio(s1_ssml_wrapped, f"tts_{timestamp}_s1", is_ssml=True),
                    asset_gen.generate_tts_audio(s2_ssml_wrapped, f"tts_{timestamp}_s2", is_ssml=True),
                    asset_gen.generate_tts_audio(s3_ssml_wrapped, f"tts_{timestamp}_s3", is_ssml=True)
                ]
            except Exception as e:
                print(f"[Main] ERROR: Asset Generator failed to create scene TTS MP3s: {e}")
                sys.exit(1)

            image_myth_path = None
            try:
                image_myth_name = f"background_myth_{timestamp}"
                visual_prompt_myth = script_payload.get("myth_visual_prompt", "Technical blueprint representing the false myth")
                print(f"[Main] Requesting visual representing the FALSE MYTH: '{visual_prompt_myth}'")
                image_myth_path = asset_gen.generate_background_image(visual_prompt_myth, image_myth_name, aspect_ratio="9:16", is_blueprint=True, style_suffix=style_suffix)
            except Exception as e:
                print(f"[Main] ERROR: Myth background image generation failed: {e}")
                sys.exit(1)

            image_truth_path = None
            try:
                image_truth_name = f"foreground_fact_{timestamp}"
                visual_prompt_truth = script_payload.get("fact_visual_prompt", "Realistic laboratory or historical archive photography representing the scientific truth")
                print(f"[Main] Requesting visual representing the TRUTH/REALITY: '{visual_prompt_truth}'")
                image_truth_path = asset_gen.generate_background_image(visual_prompt_truth, image_truth_name, aspect_ratio="1:1", is_blueprint=False)
            except Exception as e:
                print(f"[Main] WARNING: Truth foreground image generation failed: {e}. Gracefully falling back to background-only rendering.")
                image_truth_path = None

            meta = script_payload.get("youtube_metadata", {})
            title = meta.get("title", f"The Daily Audit: {topic} #Shorts")
            clean_title = re.sub(r'[<>:"/\\|?*#]', '', title).strip().replace(' ', '_')[:100]

            try:
                video_eng = VideoEngine()
                video_name = f"{clean_title}_{timestamp}"
                script_payload["cta"] = cta_text
                video_path = video_eng.compile_short(image_myth_path, image_truth_path, audio_paths, script_payload, video_name, category, style=video_style)
                print(f"[Main] Video assembled and saved successfully: {video_path}")
                # Generate thumbnail using actual video images
                video_eng.generate_thumbnail(topic, hook_clean, video_name, style=video_style, img_myth_path=image_myth_path, img_truth_path=image_truth_path)
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
                topic, category, description = ingestion.fetch_unused_bizarre_topic(gemini_client=client_ref)
                print(f"[Main] Selected Anomaly Topic: '{topic}' | Discipline: {category}")
            except Exception as e:
                print(f"[Main] CRITICAL: Ingestion failed to retrieve bizarre topic: {e}")
                sys.exit(1)

            # Immediately reserve topic to prevent re-selection
            ingestion.log_uploaded_topic(topic, "")

            # 2. Generate structured script payload from Gemini
            try:
                print("[Main] Calling Gemini to construct bizarre fact script payload...")
                bizarre_payload = orchestrator.generate_bizarre_fact(topic, category)
                print(f"[Main] Anomaly script generated: '{bizarre_payload.get('hook')}'")
            except Exception as e:
                print(f"[Main] ERROR: Anomaly script generation failed: {e}")
                sys.exit(1)

            # 3. Initialize Asset Generator and Data Scraper
            try:
                gcp_cred = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
                asset_gen = AssetGenerator(gemini_client=client_ref, gcp_credentials_path=gcp_cred)
                scraper = DataScraper()
            except Exception as e:
                print(f"[Main] CRITICAL: Failed to initialize asset systems: {e}")
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
                print(f"[Main] Scraper failed for bizarre scenes: {e}")

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

            # 5. Generate TTS Audio with 3-part structure
            hook_clean = bizarre_payload.get('hook', '').strip()
            story_brief = bizarre_payload.get('story_brief', '').strip()
            why_bizarre = bizarre_payload.get('why_bizarre', '').strip()
            closing_statement = bizarre_payload.get('closing_statement', '').strip()
            sign_off_clean = bizarre_payload.get('sign_off', 'Class dismissed.').strip()
            
            # Split and generate 3-scene audio files for bizarre
            audio_paths = []
            try:
                # Determine raw ssml script
                if "ssml_script" in bizarre_payload:
                    ssml_raw = bizarre_payload["ssml_script"]
                else:
                    ssml_raw = (
                        f"{hook_clean} {story_brief}"
                        f"<break time='1200ms'/>"
                        f"{why_bizarre}"
                        f"<break time='700ms'/>"
                        f"{closing_statement}"
                    )
                
                # Split SSML into scenes
                s1_ssml, s2_ssml, s3_ssml = split_bizarre_ssml(
                    ssml_raw, hook_clean, story_brief, why_bizarre, closing_statement, sign_off_clean, cta_text
                )
                
                s1_ssml_wrapped = f"<prosody pitch='-1.0st' rate='0.93'>{s1_ssml}</prosody>"
                s2_ssml_wrapped = f"<prosody pitch='-1.0st' rate='0.93'>{s2_ssml}</prosody>"
                s3_ssml_wrapped = f"<prosody pitch='-1.0st' rate='0.93'>{s3_ssml}</prosody>"
                
                print(f"[Main] Bizarre Scene 1 SSML: {s1_ssml_wrapped}")
                print(f"[Main] Bizarre Scene 2 SSML: {s2_ssml_wrapped}")
                print(f"[Main] Bizarre Scene 3 SSML: {s3_ssml_wrapped}")
                
                audio_paths = [
                    asset_gen.generate_tts_audio(s1_ssml_wrapped, f"bizarre_tts_{timestamp}_s1", is_ssml=True),
                    asset_gen.generate_tts_audio(s2_ssml_wrapped, f"bizarre_tts_{timestamp}_s2", is_ssml=True),
                    asset_gen.generate_tts_audio(s3_ssml_wrapped, f"bizarre_tts_{timestamp}_s3", is_ssml=True)
                ]
            except Exception as e:
                print(f"[Main] ERROR: Asset Generator failed to create bizarre scene TTS MP3s: {e}")
                sys.exit(1)

            # 6. Build script payload for compile_bizarre immersive 3-scene format
            script_payload = {
                "hook": hook_clean,
                "story_brief": story_brief,
                "why_bizarre": why_bizarre,
                "closing_statement": closing_statement,
                "cta": cta_text,
                "sign_off": sign_off_clean,
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
                    video_name, category, style=video_style
                )
                print(f"[Main] Anomaly Video assembled successfully: {video_path}")
                video_eng.generate_thumbnail(
                    topic, hook_clean, video_name, style=video_style,
                    img_myth_path=scraped_bizarre_images[0], img_truth_path=scraped_bizarre_images[-1],
                    bizarre_mode=True,
                )
            except Exception as e:
                print(f"[Main] ERROR: Video engine compilation failed: {e}")
                sys.exit(1)

            hook_text = hook_clean

        # =========================================================================
        # UPLOAD AND FINALIZATION SUBSYSTEM
        # =========================================================================
        # Upload to YouTube via API
        yt_upload_success = False
        yt_video_id = None
        try:
            uploader = YouTubeUploader()
            tags = meta.get("tags", ["education", "shorts"])
            
            # Format tags as hashtags and append to the description
            hashtags_str = " ".join([f"#{t.strip().replace(' ', '')}" for t in tags if t.strip()])
            base_desc = meta.get("description", f"Educating about {topic}.")
            desc = f"{base_desc}\n\n#TheDailyAudit #Shorts {hashtags_str}"
            
            print(f"[Main] Connecting to YouTube Data API for Short deployment with tags: {tags}")
            yt_upload_success, yt_video_id = uploader.upload_short(video_path, title, desc, tags)
        except Exception as e:
            print(f"[Main] ERROR: YouTube upload subsystem failed: {e}")

        # Upload to Facebook Reels via API
        fb_upload_success = False
        fb_video_id = None
        try:
            fb_uploader = FacebookUploader()
            fb_desc = f"{base_desc}\n\n#TheDailyAudit #Reels {hashtags_str}"
            print("[Main] Connecting to Meta Graph API for Facebook Reels deployment...")
            fb_upload_success, fb_video_id = fb_uploader.upload_reel(video_path, fb_desc)
        except Exception as e:
            print(f"[Main] ERROR: Facebook upload subsystem failed: {e}")

        # Upload to TikTok via Playwright browser (uses Opera GX profile cookies)
        tt_upload_success = False
        tt_video_id = None
        if not getattr(args, 'skip_tiktok', False):
            try:
                tt_uploader = TikTokUploader(headless=True)
                tt_caption = f"{base_desc}\n\n#TheDailyAudit #Shorts #fyp {hashtags_str}"
                print("[Main] Uploading to TikTok via Playwright (AIGC label enabled)...")
                tt_upload_success, tt_video_id = tt_uploader.upload(video_path, tt_caption)
            except Exception as e:
                print(f"[Main] ERROR: TikTok upload subsystem failed: {e}")
        else:
            print("[Main] TikTok upload skipped (--skip-tiktok flag)")

        # Complete transaction: Log history if successfully uploaded (or successfully mocked)
        if yt_upload_success or fb_upload_success or tt_upload_success:
            try:
                ingestion.log_uploaded_topic(topic, hook_text)
                print(f"[Main] SUCCESS: Topic '{topic}' permanently retired and logged in database.")
            except Exception as e:
                print(f"[Main] WARNING: Failed to record upload event in database: {e}")
        else:
            print(f"[Main] WARNING: Upload transaction was not marked successful on any platform. Local video remains in: {video_path}")

        print("\n" + "=" * 80)
        print(f"   CYCLE COMPLETED SUCCESSFULLY FOR FORMAT: {video_type.upper()}")
        print("=" * 80 + "\n")

if __name__ == "__main__":
    run_pipeline()

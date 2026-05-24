# =============================================================================
# "The Daily Audit" - Asset Generation Module (TTS & Imagen)
# =============================================================================
import os
import time
import random
import threading
from typing import Tuple, Optional
from PIL import Image, ImageDraw

_azure_tts_thread_lock = threading.Lock()

class AssetGenerator:
    """Generates the TTS audio (GCP TTS) and the vintage schematic background image (Gemini/Imagen)."""

    def __init__(self, gemini_client=None, gcp_credentials_path: Optional[str] = None,
                 azure_speech_key: Optional[str] = None, azure_speech_region: Optional[str] = None,
                 azure_voice_name: Optional[str] = None):
        self.gemini_client = gemini_client
        self.gcp_credentials_path = gcp_credentials_path or os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
        
        # Explicitly configure environment variable for GCP clients
        if self.gcp_credentials_path:
            os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = self.gcp_credentials_path

        # Load Azure Speech settings
        self.azure_speech_key = azure_speech_key or os.getenv("AZURE_SPEECH_KEY")
        self.azure_speech_region = azure_speech_region or os.getenv("AZURE_SPEECH_REGION", "southeastasia")
        self.voice_name = azure_voice_name or os.getenv("AZURE_VOICE_NAME", "en-US-AndrewMultilingualNeural")

        # Create assets storage path
        base_dir = os.path.dirname(os.path.abspath(__file__))
        self.assets_dir = os.path.join(base_dir, "assets")
        os.makedirs(self.assets_dir, exist_ok=True)

    def _process_brackets_to_ssml(self, text: str) -> str:
        """
        Converts human emotion style brackets (like [whisper]...[/whisper]) and paralinguistic cues
        (like [sigh], [breathing]) into Azure SSML mstts tags.
        """
        import re
        
        # 1. Handle self-closing paralinguistic tags
        paralinguistic_map = {
            r'\[sigh(?:ing)?\]': '<mstts:paralinguistic type="sighing"/>',
            r'\[breath(?:ing)?\]': '<mstts:paralinguistic type="breathing"/>',
            r'\[gasp(?:ing)?\]': '<mstts:paralinguistic type="breathing"/>',
            r'\[laugh(?:ter|ing)?\]': '<mstts:paralinguistic type="laughter"/>',
            r'\[giggle\]': '<mstts:paralinguistic type="laughter"/>',
            r'\[throat[-_]clearing\]': '<mstts:paralinguistic type="throat_clearing"/>',
            r'\[cough(?:ing)?\]': '<mstts:paralinguistic type="coughing"/>',
            r'\[yawn(?:ing)?\]': '<mstts:paralinguistic type="yawning"/>',
        }
        
        processed = text
        for pattern, tag in paralinguistic_map.items():
            processed = re.sub(pattern, tag, processed, flags=re.IGNORECASE)
            
        # 2. Handle block styles like [whisper]...[/whisper] or [whispering]...[/whispering]
        # Common styles: whispering, cheerful, sad, excited, angry, terrified, hopeful, friendly, unfriendly, shouting, empathetic, relieved
        styles = ["whispering", "whisper", "cheerful", "sad", "excited", "angry", "terrified", "hopeful", "friendly", "unfriendly", "shouting", "empathetic", "relieved"]
        for s in styles:
            # Map alias "whisper" to Azure style "whispering"
            azure_style = "whispering" if s == "whisper" else s
            # Match [style]...[/style]
            pattern_block = rf'\[{s}\](.*?)\[/{s}\]'
            replacement_block = f'<mstts:express-as style="{azure_style}">\\1</mstts:express-as>'
            processed = re.sub(pattern_block, replacement_block, processed, flags=re.DOTALL | re.IGNORECASE)
            
            # Match unclosed [style] and close it at the end of the text/prosody block if any remains
            pattern_start = rf'\[{s}\]'
            if re.search(pattern_start, processed, flags=re.IGNORECASE):
                processed = re.sub(pattern_start, f'<mstts:express-as style="{azure_style}">', processed, flags=re.IGNORECASE)
                processed = processed + '</mstts:express-as>'
                
        return processed

    def _write_srt_from_word_boundaries(self, word_boundaries: list, audio_path: str):
        try:
            from tts.subtitle_builder import SubtitleBuilder
            sub_items = SubtitleBuilder.group_words_into_subtitles(word_boundaries)
            srt_content = SubtitleBuilder.build_srt(sub_items)
            srt_path = os.path.splitext(audio_path)[0] + ".srt"
            with open(srt_path, "w", encoding="utf-8") as f:
                f.write(srt_content)
            print(f"[AssetGen] Subtitle SRT generated: {srt_path}")
        except Exception as e:
            print(f"[AssetGen] WARNING: Failed to generate subtitle SRT: {e}")

    def _estimate_word_boundaries(self, text: str, audio_path: str) -> list:
        duration = 5.0
        try:
            from moviepy.editor import AudioFileClip
            clip = AudioFileClip(audio_path)
            duration = clip.duration
            clip.close()
        except Exception:
            pass
            
        import re
        clean_text = re.sub(r'<[^>]*>', '', text)
        clean_text = re.sub(r'\[[\w\s_/-]+\]', '', clean_text).strip()
        words = clean_text.split()
        if not words:
            return []
            
        total_chars = sum(len(w) for w in words)
        sec_per_char = duration / total_chars if total_chars > 0 else 0.1
        
        word_boundaries = []
        current_time = 0.0
        for w in words:
            word_dur = len(w) * sec_per_char
            word_boundaries.append({
                "word": w,
                "offset_ms": current_time * 1000.0,
                "duration_ms": word_dur * 1000.0
            })
            current_time += word_dur
        return word_boundaries

    def generate_tts_audio(self, text: str, output_name: str, is_ssml: bool = False) -> str:
        """
        Synthesizes script text into an MP3 file using Microsoft Azure Cognitive Services Speech SDK.
        Uses voice specified by self.voice_name (defaults to en-US-AndrewMultilingualNeural).
        Supports SSML for dramatic phrasing, stern pausing, and rate modulation.
        Processes bracket tags like [sigh] or [whisper]...[/whisper] to enrich narration.
        """
        output_path = os.path.join(self.assets_dir, f"{output_name}.mp3")
        
        # Pre-process brackets into Azure SSML tags
        text_with_cues = self._process_brackets_to_ssml(text)
        
        # Format the text into standard Azure Speech SSML
        if is_ssml:
            inner_text = text_with_cues.strip()
            # If the text already has a root <speak> element, strip it to avoid duplicates
            if inner_text.startswith("<speak>"):
                inner_text = inner_text[7:]
            if inner_text.endswith("</speak>"):
                inner_text = inner_text[:-8]
            
            processed_text = (
                f'<speak version="1.0" xmlns="http://www.w3.org/2001/10/synthesis" '
                f'xmlns:mstts="https://www.w3.org/2001/mstts" '
                f'xml:lang="en-US">'
                f'<voice name="{self.voice_name}">'
                f'{inner_text}'
                f'</voice>'
                f'</speak>'
            )
        else:
            # Wrap plain text in SSML to apply the configured voice and default speaking rate
            processed_text = (
                f'<speak version="1.0" xmlns="http://www.w3.org/2001/10/synthesis" '
                f'xmlns:mstts="https://www.w3.org/2001/mstts" '
                f'xml:lang="en-US">'
                f'<voice name="{self.voice_name}">'
                f'<prosody rate="0.93">'
                f'{text_with_cues}'
                f'</prosody>'
                f'</voice>'
                f'</speak>'
            )

        # Concurrency Lock (Azure Free Tier allows max 1 concurrent request)
        lock_file = os.path.join(self.assets_dir, "azure_tts.lock")
        
        with _azure_tts_thread_lock:
            start_time = time.time()
            timeout = 300.0
            delay = 0.5
            fd = None
            try:
                while True:
                    try:
                        fd = os.open(lock_file, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
                        break
                    except FileExistsError:
                        try:
                            # Stale lock recovery (e.g. if previous process crashed hard)
                            mtime = os.path.getmtime(lock_file)
                            if (time.time() - mtime) > 60.0:
                                print(f"[AssetGen] Stale lock file detected (age: {time.time() - mtime:.1f}s). Removing: {lock_file}")
                                os.remove(lock_file)
                                fd = os.open(lock_file, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
                                break
                        except Exception:
                            pass
                    
                    if (time.time() - start_time) > timeout:
                        raise TimeoutError(f"Timeout waiting for Azure TTS lock on {lock_file}")
                    
                    time.sleep(delay + random.uniform(0.0, 0.2))
                
                # Cascade 1: Azure Cognitive Services Speech SDK
                try:
                    if not self.azure_speech_key or self.azure_speech_key == "YourAzureSpeechKeyHere":
                        raise ValueError("Azure Speech subscription key not configured.")
                        
                    import azure.cognitiveservices.speech as speechsdk
                    
                    speech_config = speechsdk.SpeechConfig(subscription=self.azure_speech_key, region=self.azure_speech_region)
                    audio_config = speechsdk.audio.AudioConfig(filename=output_path)
                    
                    # Use MP3 format (or PCM which MoviePy can read, but mp3 is standard here)
                    # Default mp3 format is 24khz 96kbps mono
                    speech_config.set_speech_synthesis_output_format(
                        speechsdk.SpeechSynthesisOutputFormat.Audio24Khz96KBitRateMonoMp3
                    )
                    
                    synthesizer = speechsdk.SpeechSynthesizer(speech_config=speech_config, audio_config=audio_config)
                    
                    word_boundaries = []
                    def on_word_boundary(evt):
                        word_boundaries.append({
                            "word": evt.text,
                            "offset_ms": evt.audio_offset / 10000.0,  # ticks to ms
                            "duration_ms": evt.duration / 10000.0
                        })
                    synthesizer.synthesis_word_boundary.connect(on_word_boundary)

                    print(f"[AssetGen] Requesting Azure SDK TTS (Voice={self.voice_name}, Region={self.azure_speech_region}) for: '{text[:50]}...'")
                    result = synthesizer.speak_ssml_async(processed_text).get()
                    
                    if result.reason == speechsdk.ResultReason.SynthesizingAudioCompleted:
                        print(f"[AssetGen] TTS Audio generated: {output_path}")
                        self._write_srt_from_word_boundaries(word_boundaries, output_path)
                        return output_path
                    else:
                        details = speechsdk.SpeechSynthesisCancellationDetails.from_result(result)
                        error_msg = f"Azure SDK Synthesis failed: {result.reason}"
                        if details.reason == speechsdk.CancellationReason.Error:
                            error_msg += f" (Error details: {details.error_details})"
                        raise RuntimeError(error_msg)
                        
                except Exception as sdk_err:
                    print(f"[AssetGen] Azure Speech SDK failed ({sdk_err}). Trying Azure REST API fallback...")
                    
                    # Cascade 2: Azure Speech REST API Fallback
                    try:
                        res_path = self._generate_azure_rest_tts(processed_text, output_path)
                        w_bounds = self._estimate_word_boundaries(text, output_path)
                        self._write_srt_from_word_boundaries(w_bounds, output_path)
                        return res_path
                    except Exception as rest_err:
                        print(f"[AssetGen] Azure REST API fallback failed ({rest_err}). Synthesizing offline mockup audio...")
                        
                        # Cascade 3: Offline Mockup Audio
                        import re
                        # Clean both XML and bracket emotion cues before sending to offline mockup
                        plain_text = re.sub(r'<[^>]*>', '', text)
                        plain_text = re.sub(r'\[[\w\s_/-]+\]', '', plain_text).strip()
                        res_path = self._generate_offline_mockup_audio(plain_text, output_path)
                        w_bounds = self._estimate_word_boundaries(plain_text, output_path)
                        self._write_srt_from_word_boundaries(w_bounds, output_path)
                        return res_path
            finally:
                if fd is not None:
                    try:
                        os.close(fd)
                    except Exception:
                        pass
                try:
                    if os.path.exists(lock_file):
                        os.remove(lock_file)
                except Exception:
                    pass

    def _generate_azure_rest_tts(self, ssml_text: str, output_path: str) -> str:
        """Fallback to generate TTS audio using Azure REST API directly (no SDK dependency)."""
        import requests
        
        if not self.azure_speech_key or self.azure_speech_key == "YourAzureSpeechKeyHere":
            raise ValueError("Azure Speech API Key is not configured for REST API.")
            
        url = f"https://{self.azure_speech_region}.tts.speech.microsoft.com/cognitiveservices/v1"
        headers = {
            "Ocp-Apim-Subscription-Key": self.azure_speech_key,
            "Content-Type": "application/ssml+xml",
            "X-Microsoft-OutputFormat": "audio-24khz-96kbitrate-mono-mp3",
            "User-Agent": "TheDailyAudit"
        }
        print(f"[AssetGen] Requesting Azure REST TTS (Voice={self.voice_name}) for: '{ssml_text[:50]}...'")
        response = requests.post(url, headers=headers, data=ssml_text.encode('utf-8'), timeout=15)
        if response.status_code == 200:
            with open(output_path, "wb") as f:
                f.write(response.content)
            print(f"[AssetGen] Azure REST TTS Audio generated: {output_path}")
            return output_path
        else:
            raise Exception(f"Azure REST TTS request failed with status {response.status_code}: {response.text}")

    def _generate_offline_mockup_audio(self, text: str, output_path: str) -> str:
        """Fallback to synthesize lightweight offline mockup MP3 using pyttsx3 or ffmpeg silent generation."""
        try:
            import pyttsx3
            engine = pyttsx3.init()
            engine.save_to_file(text, output_path)
            engine.runAndWait()
            print(f"[AssetGen] Offline mock audio synthesized: {output_path}")
            return output_path
        except Exception as e:
            print(f"[AssetGen] pyttsx3 offline synthesizer not available ({e}). Attempting dynamic FFmpeg silent generation...")
            
            # Estimate audio duration based on word count (approx 135 words per minute ~ 2.25 words per second) plus safety padding
            words = len(text.split())
            estimated_duration = max(5, int(words / 2.25) + 3)
            
            import subprocess
            try:
                import imageio_ffmpeg
                ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
            except ImportError:
                ffmpeg_exe = "ffmpeg"
                
            try:
                # Generate a valid, clean silent MP3 file matching the estimated script duration
                cmd = [
                    ffmpeg_exe, "-y",
                    "-f", "lavfi",
                    "-i", "anullsrc=r=44100:cl=mono",
                    "-t", str(estimated_duration),
                    "-acodec", "libmp3lame",
                    output_path
                ]
                
                startupinfo = None
                if os.name == 'nt':
                    startupinfo = subprocess.STARTUPINFO()
                    startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                
                subprocess.run(
                    cmd, 
                    check=True, 
                    startupinfo=startupinfo, 
                    stdout=subprocess.DEVNULL, 
                    stderr=subprocess.DEVNULL
                )
                print(f"[AssetGen] Silent placeholder MP3 of {estimated_duration}s generated using FFmpeg: {output_path}")
                return output_path
            except Exception as ffmpeg_err:
                print(f"[AssetGen] FFmpeg silent generation failed ({ffmpeg_err}). Writing tiny fallback MP3...")
                # Tiny valid 1-frame silent MP3 base64
                import base64
                silent_mp3_b64 = (
                    "SUQzBAAAAAAAAFRYWFgAAAASAAADbWFqb3JfYnJhbmQAbXA0MgBUWFhYAAAAEgAAA21pbm9yX3ZlcnNpb24AM"
                    "QBUWFhYAAAAHAAAA2NvbXBhdGlibGVfYnJhbmRzAG1wNDJpc29tAFRFTgAAAA4AAAMAd2RDcmVhdG9yAFAA//"
                    "MUxAAAAAAAAAAAAAAAIEAElgQD5nAPgAADA8A/gQD5gAD8AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
                    "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
                    "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
                )
                missing_padding = len(silent_mp3_b64) % 4
                if missing_padding:
                    silent_mp3_b64 += "=" * (4 - missing_padding)
                with open(output_path, "wb") as f:
                    f.write(base64.b64decode(silent_mp3_b64))
                print(f"[AssetGen] Fallback tiny silent placeholder MP3 written: {output_path}")
                return output_path

    def generate_background_image(self, visual_prompt: str, output_name: str, aspect_ratio: str = "9:16", is_blueprint: bool = True, style_suffix: str = None) -> str:
        """
        Generates the vintage CRT/declassified blueprint or realistic fact showcase image.
        Cascade-tests a list of verified working models (Imagen 4.0 and Gemini 2.5/3.0)
        with automatic failover, falling back to programmatic drawing as the final resort.
        """
        output_path = os.path.join(self.assets_dir, f"{output_name}.png")
        
        # Build the exact prompt requested by the mission rules
        if is_blueprint:
            suffix = style_suffix or "Style of a declassified government document, dark blue and white blueprint, highly detailed."
            styled_prompt = (
                f"{visual_prompt}. "
                f"{suffix} "
                "High contrast, realistic, highly detailed, no cartoons, no text."
            )
        else:
            styled_prompt = visual_prompt
        
        # Check if the modern Google GenAI Client is set up and supports image generation
        if self.gemini_client is not None and not isinstance(self.gemini_client, str):
            try:
                from google import genai
                from google.genai import types
                
                # Duck-type check: avoid importing SmartGeminiClient by name to prevent
                # a potential circular dependency if llm_orchestrator ever imports asset_generator.
                if hasattr(self.gemini_client, 'execute_with_failover') and hasattr(self.gemini_client, 'models'):
                    image_client = self.gemini_client
                else:
                    api_key_val = getattr(self.gemini_client, 'api_key', None) or os.getenv("FREE_GEMINI_API_KEY") or os.getenv("GEMINI_API_KEY")
                    image_client = genai.Client(
                        api_key=api_key_val,
                        http_options=types.HttpOptions(timeout=30000)
                    )
                
                # List of verified models in order of preferred usage (cheapest first)
                models_to_try = [
                    {"name": "imagen-4.0-fast-generate-001", "type": "imagen"},    # $0.02 / image
                    {"name": "gemini-2.5-flash-image", "type": "gemini"},          # ~$0.039 / image
                    {"name": "imagen-4.0-generate-001", "type": "imagen"},         # $0.04 / image
                    {"name": "imagen-4.0-ultra-generate-001", "type": "imagen"},   # $0.06 / image
                    {"name": "gemini-3-pro-image-preview", "type": "gemini"},      # Pro tier / most expensive
                ]
                
                for model_info in models_to_try:
                    model_name = model_info["name"]
                    model_type = model_info["type"]
                    print(f"[AssetGen] Attempting image generation with model '{model_name}' (type: {model_type})...")
                    
                    try:
                        image_bytes = None
                        if model_type == "imagen":
                            response = image_client.models.generate_images(
                                model=model_name,
                                prompt=styled_prompt,
                                config=types.GenerateImagesConfig(
                                    number_of_images=1,
                                    aspect_ratio=aspect_ratio
                               )
                            )
                            if response.generated_images:
                                image_bytes = response.generated_images[0].image.image_bytes
                                
                        elif model_type == "gemini":
                            response = image_client.models.generate_content(
                                model=model_name,
                                contents=styled_prompt,
                                config=types.GenerateContentConfig(
                                    response_modalities=["IMAGE"],
                                    image_config=types.ImageConfig(
                                        aspect_ratio=aspect_ratio
                                    )
                                )
                            )
                            if response.candidates and response.candidates[0].content.parts:
                                for part in response.candidates[0].content.parts:
                                    if part.inline_data:
                                        image_bytes = part.inline_data.data
                                        break
                                        
                        if image_bytes:
                            with open(output_path, "wb") as f:
                                f.write(image_bytes)
                            print(f"[AssetGen] SUCCESS: Image successfully generated using model '{model_name}'. Saved to: {output_path}")
                            return output_path
                        else:
                            print(f"[AssetGen] Model '{model_name}' returned empty or missing image payload. Trying fallback...")
                            
                    except Exception as model_err:
                        print(f"[AssetGen] Model '{model_name}' failed: {type(model_err).__name__} - {model_err}. Trying fallback...")
                
                print("[AssetGen] All modern image generation models failed or timed out. Rendering custom blueprint programmatically...")
                
            except Exception as e:
                print(f"[AssetGen] General error in image generation setup: {type(e).__name__} - {e}. Rendering custom blueprint programmatically...")
        else:
            print("[AssetGen] Gemini GenAI client not available or legacy mode. Generating local vector blueprint...")

        # Fallback: Draw a gorgeous monochromatic dark blue vintage document grid programmatically
        return self._render_programmatic_blueprint(styled_prompt, output_path)

    def _render_programmatic_blueprint(self, prompt_text: str, output_path: str) -> str:
        """
        Programmatically draws a high-contrast vintage technical blueprint vector image
        in 1080x1920 portrait format using Pillow (PIL), dynamically tailored to the prompt.
        """
        print(f"[AssetGen] Drawing technical blueprint programmatically at: {output_path}")
        import math
        
        # 1080x1920 (9:16 Portrait Ratio for Shorts)
        width, height = 1080, 1920
        # Dark Blue background
        bg_color = (10, 24, 47)
        # Technical blueprint white-cyan lines
        cyan_line_color = (0, 242, 254)
        dim_cyan_color = (0, 75, 110)
        
        # Create base image
        img = Image.new("RGB", (width, height), bg_color)
        draw = ImageDraw.Draw(img)
        
        # 1. Draw grid background (spacing every 60px)
        grid_spacing = 60
        for x in range(0, width, grid_spacing):
            draw.line([(x, 0), (x, height)], fill=dim_cyan_color, width=1)
        for y in range(0, height, grid_spacing):
            draw.line([(0, y), (width, y)], fill=dim_cyan_color, width=1)
            
        # 2. Draw border frame
        border_inset = 40
        draw.rectangle(
            [(border_inset, border_inset), (width - border_inset, height - border_inset)], 
            outline=cyan_line_color, 
            width=3
        )
        
        # Crosshair lines in the corners to give industrial look
        cross_len = 30
        corners = [
            (border_inset, border_inset),
            (width - border_inset, border_inset),
            (border_inset, height - border_inset),
            (width - border_inset, height - border_inset)
        ]
        for cx, cy in corners:
            draw.line([(cx - cross_len, cy), (cx + cross_len, cy)], fill=cyan_line_color, width=2)
            draw.line([(cx, cy - cross_len), (cx, cy + cross_len)], fill=cyan_line_color, width=2)

        # 3. Draw vintage technical blueprint header box
        box_top = 180
        box_bottom = 280
        box_left = 120
        box_right = width - 120
        draw.rectangle(
            [(box_left, box_top), (box_right, box_bottom)], 
            fill=(15, 34, 64), 
            outline=cyan_line_color, 
            width=2
        )
        
        # Add blueprint design labels inside the header box
        draw.line([(box_left + 150, box_top), (box_left + 150, box_bottom)], fill=cyan_line_color, width=1)
        draw.line([(box_left + 450, box_top), (box_left + 450, box_bottom)], fill=cyan_line_color, width=1)
        
        # 4. Draw dynamic central technical schematic based on prompt keywords
        center_x, center_y = width // 2, height // 2
        prompt_lower = prompt_text.lower()
        
        if "black hole" in prompt_lower or "vortex" in prompt_lower or "funnel" in prompt_lower or "spiral" in prompt_lower or "space" in prompt_lower or "spacetime" in prompt_lower:
            print("[AssetGen] Rendering dynamic Space/Vortex blueprint schema...")
            # Warp space grid funnel
            for r in range(10, 320, 15):
                factor = (r / 320.0) ** 1.3
                cy = center_y + int(120 * (1.0 - factor))
                rx = int(320 * factor)
                ry = int(120 * factor)
                draw.ellipse([(center_x - rx, cy - ry), (center_x + rx, cy + ry)], outline=cyan_line_color, width=1)
            # Perspective warping radial gridlines
            for angle in range(0, 360, 30):
                rad = math.radians(angle)
                x1 = center_x + int(320 * math.cos(rad))
                y1 = center_y + int(120 * math.sin(rad))
                # All converge to the bottom funnel center
                draw.line([(x1, y1), (center_x, center_y + 120)], fill=dim_cyan_color, width=1)
                
        elif "evolution" in prompt_lower or "monkey" in prompt_lower or "human" in prompt_lower or "ape" in prompt_lower or "dna" in prompt_lower or "ancestor" in prompt_lower or "tree" in prompt_lower or "gene" in prompt_lower or "darwin" in prompt_lower:
            print("[AssetGen] Rendering dynamic DNA/Evolutionary Tree blueprint schema...")
            # 1. Draw a branching tree node structure (evolutionary tree)
            # Main root at bottom-center
            root_x, root_y = center_x, center_y + 280
            # Level 1 split
            mid_left_x, mid_left_y = center_x - 180, center_y + 50
            mid_right_x, mid_right_y = center_x + 180, center_y + 50
            # Level 2 splits (left side)
            leaf_l1_x, leaf_l1_y = center_x - 280, center_y - 180
            leaf_l2_x, leaf_l2_y = center_x - 80, center_y - 180
            # Level 2 splits (right side)
            leaf_r1_x, leaf_r1_y = center_x + 80, center_y - 180
            leaf_r2_x, leaf_r2_y = center_x + 280, center_y - 180
            
            # Draw connection lines
            draw.line([(root_x, root_y), (mid_left_x, mid_left_y)], fill=cyan_line_color, width=2)
            draw.line([(root_x, root_y), (mid_right_x, mid_right_y)], fill=cyan_line_color, width=2)
            draw.line([(mid_left_x, mid_left_y), (leaf_l1_x, leaf_l1_y)], fill=cyan_line_color, width=2)
            draw.line([(mid_left_x, mid_left_y), (leaf_l2_x, leaf_l2_y)], fill=cyan_line_color, width=2)
            draw.line([(mid_right_x, mid_right_y), (leaf_r1_x, leaf_r1_y)], fill=cyan_line_color, width=2)
            draw.line([(mid_right_x, mid_right_y), (leaf_r2_x, leaf_r2_y)], fill=cyan_line_color, width=2)
            
            # Draw circles at the nodes representing species/phases
            nodes = [
                (root_x, root_y, "ROOT"),
                (mid_left_x, mid_left_y, "BRANCH_A"),
                (mid_right_x, mid_right_y, "BRANCH_B"),
                (leaf_l1_x, leaf_l1_y, "SPECIES_1"),
                (leaf_l2_x, leaf_l2_y, "SPECIES_2"),
                (leaf_r1_x, leaf_r1_y, "SPECIES_3"),
                (leaf_r2_x, leaf_r2_y, "SPECIES_4")
            ]
            for nx, ny, label in nodes:
                # Node outer ring
                draw.ellipse([(nx - 24, ny - 24), (nx + 24, ny + 24)], outline=cyan_line_color, fill=bg_color, width=2)
                # Inner dot
                draw.ellipse([(nx - 8, ny - 8), (nx + 8, ny + 8)], fill=cyan_line_color)
                
            # 2. Draw a DNA Double Helix strand on the side (center-left and center-right vertical bounds)
            helix_y_start = center_y - 350
            helix_y_end = center_y + 350
            helix_step = 25
            for hy in range(helix_y_start, helix_y_end, helix_step):
                # Calculate double helix sine wave offsets
                angle_offset = (hy - helix_y_start) / 100.0 * math.pi
                
                # Left side DNA helix
                x_left_1 = center_x - 360 + int(45 * math.sin(angle_offset))
                x_left_2 = center_x - 360 + int(45 * math.sin(angle_offset + math.pi))
                draw.line([(x_left_1, hy), (x_left_2, hy)], fill=dim_cyan_color, width=1)
                draw.ellipse([(x_left_1 - 6, hy - 6), (x_left_1 + 6, hy + 6)], fill=cyan_line_color)
                draw.ellipse([(x_left_2 - 6, hy - 6), (x_left_2 + 6, hy + 6)], fill=cyan_line_color)
                
                # Right side DNA helix
                x_right_1 = center_x + 360 + int(45 * math.sin(angle_offset))
                x_right_2 = center_x + 360 + int(45 * math.sin(angle_offset + math.pi))
                draw.line([(x_right_1, hy), (x_right_2, hy)], fill=dim_cyan_color, width=1)
                draw.ellipse([(x_right_1 - 6, hy - 6), (x_right_1 + 6, hy + 6)], fill=cyan_line_color)
                draw.ellipse([(x_right_2 - 6, hy - 6), (x_right_2 + 6, hy + 6)], fill=cyan_line_color)
                
        elif "virus" in prompt_lower or "bacteria" in prompt_lower or "cell" in prompt_lower or "antibiotic" in prompt_lower or "biology" in prompt_lower:
            print("[AssetGen] Rendering dynamic Cellular/Biology blueprint schema...")
            # Draw a primary mother cell with spiky crown receptors
            draw.ellipse([(center_x - 130, center_y - 130), (center_x + 130, center_y + 130)], outline=cyan_line_color, width=2)
            draw.ellipse([(center_x - 50, center_y - 50), (center_x + 50, center_y + 50)], outline=dim_cyan_color, width=1)
            for angle in range(0, 360, 30):
                rad = math.radians(angle)
                x1 = center_x + int(130 * math.cos(rad))
                y1 = center_y + int(130 * math.sin(rad))
                x2 = center_x + int(190 * math.cos(rad))
                y2 = center_y + int(190 * math.sin(rad))
                draw.line([(x1, y1), (x2, y2)], fill=cyan_line_color, width=2)
                draw.ellipse([(x2 - 12, y2 - 12), (x2 + 12, y2 + 12)], fill=bg_color, outline=cyan_line_color, width=2)
                
            # Draw auxiliary cells/structures orbiting around
            orbit_centers = [(center_x - 240, center_y - 200), (center_x + 240, center_y + 200), (center_x - 200, center_y + 240)]
            for ox, oy in orbit_centers:
                draw.ellipse([(ox - 40, oy - 40), (ox + 40, oy + 40)], outline=cyan_line_color, width=1)
                draw.line([(ox, oy - 60), (ox, oy + 60)], fill=dim_cyan_color, width=1)
                draw.line([(ox - 60, oy), (ox + 60, oy)], fill=dim_cyan_color, width=1)
                
        elif "velociraptor" in prompt_lower or "dinosaur" in prompt_lower or "skeleton" in prompt_lower or "bone" in prompt_lower or "fossil" in prompt_lower or "predator" in prompt_lower:
            print("[AssetGen] Rendering dynamic Skeletal/Fossil blueprint schema...")
            # Draw spine center column
            draw.line([(center_x, center_y - 300), (center_x, center_y + 300)], fill=cyan_line_color, width=2)
            # Draw arching skeletal rib bones
            for ry in range(center_y - 240, center_y + 240, 48):
                # Calculate narrowing rib width for anatomical shape
                rib_w = int(220 * math.sin(math.radians(90 * (ry - (center_y - 240)) / 480.0)))
                draw.arc([(center_x - rib_w, ry - 35), (center_x, ry + 35)], start=90, end=270, fill=cyan_line_color, width=2)
                draw.arc([(center_x, ry - 35), (center_x + rib_w, ry + 35)], start=270, end=90, fill=cyan_line_color, width=2)
            # Triangulation reference marks
            draw.line([(center_x - 250, center_y - 320), (center_x + 250, center_y - 320)], fill=dim_cyan_color, width=1)
            draw.line([(center_x - 250, center_y + 320), (center_x + 250, center_y + 320)], fill=dim_cyan_color, width=1)
            
        elif "gear" in prompt_lower or "machine" in prompt_lower or "mechanical" in prompt_lower or "engine" in prompt_lower or "clock" in prompt_lower:
            print("[AssetGen] Rendering dynamic Mechanical/Gear blueprint schema...")
            # Main gear center
            draw.ellipse([(center_x - 160, center_y - 160), (center_x + 160, center_y + 160)], outline=cyan_line_color, width=2)
            draw.ellipse([(center_x - 70, center_y - 70), (center_x + 70, center_y + 70)], outline=dim_cyan_color, width=1)
            # Gear teeth ticks
            for angle in range(0, 360, 15):
                rad = math.radians(angle)
                x1 = center_x + int(160 * math.cos(rad))
                y1 = center_y + int(160 * math.sin(rad))
                x2 = center_x + int(185 * math.cos(rad))
                y2 = center_y + int(185 * math.sin(rad))
                draw.line([(x1, y1), (x2, y2)], fill=cyan_line_color, width=3)
            # Secondary gear interlocking
            sec_x, sec_y = center_x - 220, center_y - 220
            draw.ellipse([(sec_x - 80, sec_y - 80), (sec_x + 80, sec_y + 80)], outline=cyan_line_color, width=1)
            for angle in range(0, 360, 30):
                rad = math.radians(angle)
                x1 = sec_x + int(80 * math.cos(rad))
                y1 = sec_y + int(80 * math.sin(rad))
                x2 = sec_x + int(95 * math.cos(rad))
                y2 = sec_y + int(95 * math.sin(rad))
                draw.line([(x1, y1), (x2, y2)], fill=cyan_line_color, width=2)
                
        elif "globe" in prompt_lower or "earth" in prompt_lower or "planet" in prompt_lower or "orbit" in prompt_lower or "gravity" in prompt_lower:
            print("[AssetGen] Rendering dynamic Globe/Orbit blueprint schema...")
            # Outer sphere profile
            draw.ellipse([(center_x - 220, center_y - 220), (center_x + 220, center_y + 220)], outline=cyan_line_color, width=2)
            # Latitude lines
            for lat in [-165, -110, -55, 0, 55, 110, 165]:
                r = 220
                if r*r > lat*lat:
                    dx = int(math.sqrt(r*r - lat*lat))
                    draw.line([(center_x - dx, center_y + lat), (center_x + dx, center_y + lat)], fill=cyan_line_color, width=1)
            # Longitude ellipses
            for rx_factor in [0.25, 0.50, 0.75]:
                rx = int(220 * rx_factor)
                draw.ellipse([(center_x - rx, center_y - 220), (center_x + rx, center_y + 220)], outline=dim_cyan_color, width=1)
            # Diagonal axis orbit rings
            draw.ellipse([(center_x - 280, center_y - 80), (center_x + 280, center_y + 80)], outline=cyan_line_color, width=1)
            
        elif "wire" in prompt_lower or "electric" in prompt_lower or "circuit" in prompt_lower or "lightning" in prompt_lower or "electron" in prompt_lower or "current" in prompt_lower:
            print("[AssetGen] Rendering dynamic Electrical/Circuit blueprint schema...")
            # Central integrated chip
            draw.rectangle([(center_x - 120, center_y - 180), (center_x + 120, center_y + 180)], outline=cyan_line_color, width=2)
            draw.rectangle([(center_x - 100, center_y - 160), (center_x + 100, center_y + 160)], fill=(15, 34, 64), outline=dim_cyan_color, width=1)
            # Chip pins
            for py in range(center_y - 140, center_y + 160, 40):
                draw.line([(center_x - 180, py), (center_x - 120, py)], fill=cyan_line_color, width=2)
                draw.line([(center_x + 120, py), (center_x + 180, py)], fill=cyan_line_color, width=2)
            # Circuit symbols nearby (resistor zigzag)
            rx = center_x - 260
            draw.line([(rx, center_y - 100), (rx, center_y - 60)], fill=cyan_line_color, width=1)
            draw.line([(rx, center_y - 60), (rx - 15, center_y - 50)], fill=cyan_line_color, width=1)
            draw.line([(rx - 15, center_y - 50), (rx + 15, center_y - 30)], fill=cyan_line_color, width=1)
            draw.line([(rx + 15, center_y - 30), (rx - 15, center_y - 10)], fill=cyan_line_color, width=1)
            draw.line([(rx - 15, center_y - 10), (rx, center_y)], fill=cyan_line_color, width=1)
            draw.line([(rx, center_y), (rx, center_y + 40)], fill=cyan_line_color, width=1)
            
        elif "atom" in prompt_lower or "chemistry" in prompt_lower or "particle" in prompt_lower or "molecule" in prompt_lower or "sphere" in prompt_lower:
            print("[AssetGen] Rendering dynamic Atomic/Molecular blueprint schema...")
            # Central nucleus
            nucleus_centers = [(0, 0), (-20, 10), (15, -15), (-10, -20), (20, 20), (5, 25), (-25, -5)]
            for nx, ny in nucleus_centers:
                draw.ellipse([(center_x + nx - 25, center_y + ny - 25), (center_x + nx + 25, center_y + ny + 25)], fill=bg_color, outline=cyan_line_color, width=2)
            # Orbit ellipses
            for rx, ry, rot_angle in [(260, 90, 0), (240, 80, 45), (240, 80, -45)]:
                orbit_points = []
                rad_rot = math.radians(rot_angle)
                for deg in range(0, 365, 5):
                    rad = math.radians(deg)
                    x_rel = rx * math.cos(rad)
                    y_rel = ry * math.sin(rad)
                    x_rot = center_x + int(x_rel * math.cos(rad_rot) - y_rel * math.sin(rad_rot))
                    y_rot = center_y + int(x_rel * math.sin(rad_rot) + y_rel * math.cos(rad_rot))
                    orbit_points.append((x_rot, y_rot))
                draw.polygon(orbit_points, outline=dim_cyan_color, fill=None)
                ex, ey = orbit_points[len(orbit_points) // 3]
                draw.ellipse([(ex - 12, ey - 12), (ex + 12, ey + 12)], fill=cyan_line_color, outline=cyan_line_color, width=1)
            
        else:
            print("[AssetGen] Rendering general schematic technical blueprint schema...")
            # Classic highly intricate target radar calibration overlay blueprint
            draw.ellipse([(center_x - 260, center_y - 260), (center_x + 260, center_y + 260)], outline=cyan_line_color, width=2)
            draw.ellipse([(center_x - 240, center_y - 240), (center_x + 240, center_y + 240)], outline=cyan_line_color, width=1)
            draw.ellipse([(center_x - 140, center_y - 140), (center_x + 140, center_y + 140)], outline=dim_cyan_color, width=1)
            draw.ellipse([(center_x - 60, center_y - 60), (center_x + 60, center_y + 60)], outline=cyan_line_color, width=1)
            
            # Draw concentric circular angle scale ticks
            for angle in range(0, 360, 10):
                rad = math.radians(angle)
                x1 = center_x + int(240 * math.cos(rad))
                y1 = center_y + int(240 * math.sin(rad))
                x2 = center_x + int(260 * math.cos(rad))
                y2 = center_y + int(260 * math.sin(rad))
                draw.line([(x1, y1), (x2, y2)], fill=cyan_line_color, width=1)
                
            # Angle guide markings
            for angle in [30, 45, 60, 120, 135, 150]:
                rad = math.radians(angle)
                x_dir = int(300 * math.cos(rad))
                y_dir = int(300 * math.sin(rad))
                draw.line([(center_x - x_dir, center_y - y_dir), (center_x + x_dir, center_y + y_dir)], fill=dim_cyan_color, width=1)

        # Draw default calibration crosshair crossing center
        draw.line([(center_x - 420, center_y), (center_x + 420, center_y)], fill=cyan_line_color, width=1)
        draw.line([(center_x, center_y - 420), (center_x, center_y + 420)], fill=cyan_line_color, width=1)
        
        # Save to disk
        img.save(output_path, "PNG")
        print(f"[AssetGen] Programmatic blueprint saved: {output_path}")
        return output_path

if __name__ == "__main__":
    # Test asset generator locally
    generator = AssetGenerator()
    audio = generator.generate_tts_audio("Welcome back students. Today we correct historical lies.", "test_speech")
    image = generator.generate_background_image("An archaic wooden model of the globe", "test_blueprint")
    print("Test Audio Output:", audio)
    print("Test Image Output:", image)

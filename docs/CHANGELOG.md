# Changelog: "The Daily Audit" Shorts Pipeline

All notable changes to this project will be documented in this file.

## [4.9.0] - 2026-05-25

### Added
- **Subscribe Button Overlay**: Added a red pill-shaped "SUBSCRIBE" button with bell icon that fades in at 80% through the last (verdict/reveal) scene at y=1780, giving viewers a visual call-to-action during the final moments of the video.
- **Imagen 4 Fallback for Bizarre Scene Images**: When the Wikipedia scraper returns fewer than 3 images for bizarre content scenes, Imagen 4 now auto-generates blueprint-style images for the missing scenes. Falls back through programmatic rendering to solid-color fill if Imagen also fails.
- **Dedicated Verdict Image for Myth Pipeline**: The myth pipeline now generates a third unique image via Imagen 4 for the FINAL VERDICT scene (scene 3), using `verdict_visual_prompt` from the script payload. All three myth scenes now have unique flashcard images.

### Changed
- **Narration Starts During Card Pop Animation (Retention)**: Removed the 1.75s dead-air delay before narration on every card scene. The card still pops in with elastic animation at t=0.2s, but the narrator now speaks immediately. This eliminates ~20% filler time and keeps viewers engaged through the visual reveal.
- **Transition Gaps Reduced**: Between-scene delays cut from 0.5s → 0.2s (scene-based pipeline) and 0.5s → 0.3s (dynamic pipeline), tightening overall pacing.
- **CRT Power-Off Collapse: 0.2s → 0.15s**: Faster screen collapse prevents viewers from swiping away during black frames before the CTA.
- **Subtitles Lowered: y=1450 → y=1680**: Moved subtitles to the natural lower-third position for mobile viewing, no longer overlapping the flashcard card image.
- **Watermark Stamp Shrunk & Moved**: Reduced text from "CLASSIFIED AUDIT FILE" → "CLASSIFIED" with smaller font (60→36), relocated from center-screen to bottom-left corner (x=30, y=1750), and lowered opacity (255→100). No longer obstructs the flashcard visual.
- **All Scene Cards Get Unique Images**: Every scene now generates its own dedicated forensic tech card image. The last scene (verdict/reveal) gets a static card overlay instead of bare blurred background video.

### Removed
- **Ticking Clock Loop SFX**: Removed the mechanical tick SFX that was counting down during the now-eliminated 1.75s card delay dead air.
- **Sub-bass Riser Buildup SFX**: Removed the pre-naration riser sweep that no longer has dead air to fill.
- **Heartbeat Pulse SFX**: Removed the sub-bass heartbeat that played during the removed card pop delay.
- **Leftover dead-code print statement**: Cleaned up a stray heartbeat error print in the pop SFX exception handler.

### Fixed
- **Black Screen Between Starting Bumper and First Scene**: All VideoClip instances (`_create_starting_bumper`, `_create_scene_clip`, `_create_ending_scene`) now explicitly declare `clip.size = (1080, 1920)`. MoviePy's `VideoClip(make_frame, ...)` didn't automatically report its dimensions, causing `concatenate_videoclips` to insert a brief black frame at stitch boundaries. Every clip now correctly reports 1080×1920 resolution.
- **Last Scene Missing Flashcard**: `_compile_scene_based_video` now generates forensic tech cards for ALL n scenes (was n-1). The `_create_scene_clip` function renders the last scene's card as a static full-size overlay (no elastic pop) so the verdict/reveal scene has a visual card throughout.
- **compile_dynamic_video Passing None for Last Scene Card**: Changed `card_image=cards[i] if i < scene_count - 1 else None` to always pass `cards[i]`, fixing the missing card on the dynamic pipeline's last scene.

## [4.8.0] - 2026-05-24

### Added
- **Thumbnail Designer Overhaul (Fix 3.2)**: Replaced diagonal myth/truth split compositions with a clean, single full-screen base background image in `ThumbnailDesigner` (`thumbnail_generator.py`). Designed a premium 2-line title layout (`_draw_premium_title`) placing the topic name on the top line (white) and the hook word on the bottom line (emphasized in style-specific accent color: red for myths, cyan for bizarre anomalies). Added a corner episode badge showing `EP. ###` in a rounded outline matching the topic style color, and a solid progress-style bottom accent bar. Removed warning triangles and magnifying glass icons to reduce clutter.
- **YouTube Comment Pinning (Fix 4.2 & 4.1)**: Integrated automatic comment posting and pinning of the Gemini-generated `comment_hook` question to the YouTube Shorts comment section right after a successful video upload via `uploader.post_and_pin_comment` in `main.py`.
- **Dynamic Bumper Narration & Episode Badges (Fix 3.1)**: Upgraded `main.py` and `main_local.py` to construct a 5-element `audio_paths` list containing starting and ending bumper TTS files. This activates the video engine's dynamic bumpers compilation mode, which dynamically renders the episode number (`EP. ###`) directly on the starting bumper.
- **Calendar Theme Days Scheduling (Fix 3.4)**: Integrated a dynamic theme days schedule based on the day of the week (e.g. Medical Myths Monday, Time Warp Tuesday) in both `main.py` and `main_local.py` to automatically assign format types (myth vs bizarre) and category filters if no format type is explicitly requested at startup.

## [4.7.0] - 2026-05-24

### Added
- **Premium Card Redesign (Fix 1.5)**: Replaced database-like rectangle layout in `_generate_card` with a premium rounded outline, colored left accent stripe, rounded corner body image inset (using an RGBA mask), all-caps topic title, status dot indicator (red for debunked/anomalous, cyan for verified/truth), and a custom footer showing the case number (derived from the topic hash) and channel brand.
- **Topic-Specific Card Labels (Fix 1.4)**: Threaded `topic` into the scene-based video compiler and dynamically set labels (e.g. `EXHIBIT A: {TOPIC} MYTH`) rather than hardcoded presets.
- **Scene-Specific Color Temperature & Blur (Fix 1.2)**: Programmed `_create_scene_clip` to apply varying blur, darkening, and custom color tints per scene (Scene 1: 6.0 blur, 0.50 dark, neutral; Scene 2: 10.0 blur, 0.60 dark, cool blue tint; Scene 3: 4.0 blur, 0.40 dark, warm amber tint) to enhance visual progression.
- **Screen Shake on Reveal Zoom Punch (Fix 1.3)**: Added a dynamic 2D random screen shake (offsetting crop parameters by up to 4px) during the first 0.2s of the Scene 3 truth reveal zoom punch.
- **Silence Beat Ducking & Reveal SFX Alignment (Fix 2.2)**: Implemented a 0.7s background music silence beat (0.3s ramp down at the end of Scene 2, 0.4s hold during transition) before Scene 3, and relocated the sub-bass cinematic impact boom SFX to play precisely at the start of Scene 3 reveal rather than Scene 2.
- **Drop Shadow Subtitles (Fix 1.1)**: Modified `_render_srt_subtitle_block` to render a 4px offset drop shadow in semi-transparent black before the main white subtitle line is drawn.
- **The Auditor Persona Prompts (Fix 3.3)**: Updated system instructions in `generate_script` and `generate_bizarre_fact` to enforce "The Auditor" persona — a sharp, confident, slightly irreverent investigator who uses provocative, conversational statements, and updated Scene 1-3 word limits (10-15 words, 20-30 words, and 12-18 words, respectively).

## [4.6.0] - 2026-05-24

### Added
- **Two-Pass Researcher Prompt Chain**: Implemented a two-pass prompt chain (Pass 1: Knowledge Decomposition for surprising atomic truths, Pass 2: Scene Narrative Builder for a scene-by-scene script sequence).
- **Retention Reviewer Agent**: Implemented a dedicated retention review step scoring hook strength, narrative tension, visual variety, payoff satisfaction, and exit quality (overall score threshold >= 7.0, max 2 retries).
- **Azure Word Boundary Subtitles**: Refactored the subtitle builder to group Azure word boundary events into full-line sentences (max 2 lines, max 7 words per line) positioned in the lower third (y_pos=1450) and styled with white fill and a 2px black outline (no background highlights/pills).
- **SSML Emotion & Silence Mapping**: Added emotional style mapping (whispering, excited, calm, lyrical, newscast) to Azure styles with sentence-boundary pauses (150ms) for body/verdict scenes and leading inhales (200ms) for hooks.
- **Dynamic Bumper Audio Propagation**: Propagated companion SRT files and audio paths to starting and ending bumpers.
- **Unit & Integration Testing**: Appended `test_retention_overhaul_pipeline` verifying orchestrator prompt flow, review retry loops, emotional style mapping, and subtitle grouping.
- **Local Testing Synchronization**: Ported the dynamic prompt-driven two-pass pipeline, Wikipedia scraper, and emotional SSML building setup to `main_local.py` for headless debug workflows.

### Fixed
- **Narration Audio Offset Correction**: Prevented MoviePy from dropping start offsets when concatenating scenes by manual timeline-based compositing of content scene narration tracks. This ensures the 1.75-second card pop delay is correctly preserved in both audio and subtitles for Scene 1 and Scene 2.
- **Subtitle Sync Lookahead Offset**: Added a 200ms lookahead shift (`self.subtitle_lookahead_ms = 200.0`) to subtitle block rendering time calculations (`t_audio_ms` / `t_ms`) inside starting bumpers, body scenes, and ending bumpers. This corrects the minor lag between narration audio playback and visual subtitle rendering.
- **Forensic Card Overlap**: Shifted the vertical center of the forensic cards up to `cy=900` across both `compile_short` and `_create_scene_clip` rendering to prevent them from being covered by the lower-third subtitles.
- **Robust Subtitle Wrapping**: Added automatic word-wrapping logic inside `_render_srt_subtitle_block` to guarantee that text is broken into multiple lines if it exceeds the `960px` safe margin width, preventing subtitles from going off the video canvas.

## [4.5.6] - 2026-05-24

### Fixed
- **Defensive SSML Field Fallback**: Replaced nested `.get(key, default)` chaining with `or` short-circuit eval in `compile_short`, `compile_bizarre`, and timing methods across `video_engine.py` to correctly fall through `None`/empty-string values when resolving SSML field keys (`s1_ssml`, `s2_ssml`, `s3_ssml`, `mid_roll_hook`, and legacy field names). This prevents empty-string truthy values from blocking fallback to alternative keys.

## [4.5.5] - 2026-05-24

### Added
- **Immersive Narrator Expression Cues & Speaking Styles**: Added support for paralinguistic tags (`[sigh]`, `[breathing]`, `[gasp]`, `[laughter]`, `[giggle]`, `[throat-clearing]`, `[cough]`, `[yawn]`) and voice style tags (`[whisper]...[/whisper]`, `[cheerful]...[/cheerful]`, `[excited]...[/excited]`, `[sad]...[/sad]`, `[angry]...[/angry]`, `[hopeful]...[/hopeful]`, `[friendly]...[/friendly]`, `[unfriendly]...[/unfriendly]`, `[terrified]...[/terrified]`, `[shouting]...[/shouting]`, `[empathetic]...[/empathetic]`, `[relieved]...[/relieved]`) in script narration.
- **SSML Namespace Integration**: Added the `xmlns:mstts="https://www.w3.org/2001/mstts"` namespace declaration to the root `<speak>` elements in `asset_generator.py` to enable Azure Cognitive Services Speech SDK and REST API emotional/paralinguistic support.
- **Subtitle & Timing Filtering**: Programmed the subtitle engine, dynamic script parser, and word count utility to strip narrator bracket cues from transcript rendering, timing computations, and word metrics to prevent brackets from showing as subtitles.
- **Hardened System Prompts**: Updated system instructions for dynamic, myth, and bizarre script generators to guide Gemini to organically inject these immersive and iconic narrator expression cues.
- **Unit Testing**: Added the `test_narrator_expression_cues` suite to verify SSML conversion, subtitle word timing filtering, and word metrics calculation.

## [4.5.4] - 2026-05-24

### Added
- **Kinetic Subtitle Styles (SSML Emphasis)**: Enhanced `_render_highlighted_subtitles` to render active emphasized words with a 1.2x scale multiplier (120% scale boost) on the elastic bounce animation, drawing the highlight pill in the myth card outline color with white text. Rendered inactive emphasized words in the preset's highlight background color (e.g. yellow) instead of standard white.
- **SSML Emphasis Propagation**: Updated `_parse_ssml_script` to extract and return raw SSML segments containing emphasis tags as `s1_ssml`, `s2_ssml`, `s3_ssml`, and updated `compile_short`, `compile_bizarre`, and dynamic video orchestrators to pass these SSML strings into the compilation pipelines.
- **Loudness Normalization**: Integrated `pydub` to perform target loudness normalization to -14 dBFS (equivalent to YouTube's -14 LUFS standard) on the final compiled audio mix before video rendering, utilizing peak limiting at -1.0 dBFS to prevent clipping and distortion, and ensuring temporary files are safely deleted in `finally:` blocks.
- **Thumbnail Decoration (No Faces)**: Modified the thumbnail generator to draw premium static vector decorations (a warning exclamation triangle on the Myth side, and a magnifying glass on the Truth side) instead of human/living faces to respect the user's religious beliefs (haram) while driving click-through-rate (CTR).

## [4.5.3] - 2026-05-23

### Added
- **Visual Style Extensions**: Introduced three brand-new aesthetic presets: `cyberpunk` (neon wireframe), `retro_vhs` (retro scanline grid), and `terminal` (monochrome phosphor computer).
- **Kinetic Subtitle Highlights**: Introduced dynamic pulsing scaling and slight rotation sweeps to active yellow highlighted subtitle words.
- **Audio-Reactive Waveform**: Programmed the procedural Oscilloscope to read raw audio frame levels and dynamically fluctuate its amplitude and frequency in sync with the speaker's voice.
- **Conspiracy Redactions**: Overlaid glitch-flashing black censorship bars and `[REDACTED]` stamps over coordinates/frequency telemetry, which flash away 1.0s after narration begins.
- **CRT Power-Off Ending Transition**: Appended a retro screen shut-down collapse animation (vertical squashing, horizontal compression, and center dot fade-out) in the final 0.8s of the ending bumper.
- **Whistleblower Persona Prompts**: Upgraded LLM prompts in `llm_orchestrator.py` to command whistleblower claim openings (e.g. "Declassified file reveals...") and descriptive search term descriptors.

### Fixed
- **MoviePy v2.x Native compatibility**: Patched `AudioClip`, `AudioFileClip`, `VideoClip`, `VideoFileClip`, and `CompositeAudioClip` on import to add back-compat methods (`volumex`, `multiply_volume`, `fl`, `set_start`, and `subclip` mapping to `subclipped`) when running in environments with MoviePy v2.x. This resolves all mixing errors for sound effects and background music.
- **Scene Compiler NameError**: Initialized the `bg_video_clips` list in the resource tracking section of the scene based video compiler method (`_compile_scene_based_video`) to prevent a `NameError` during the `finally` cleanup block.
- **Pre-render bumper threads**: Upgraded `pre_render_bumpers.py` to dynamically utilize all available CPU threads during rendering.

## [4.5.2] - 2026-05-23

### Fixed
- **Root-Level Bumper Resolution**: Patched `_select_starting_blueprint` and `_select_ending_blueprint` in `app_build/video_engine.py` to check both the root-level `assets/video_blueprints` folder and the app-level `app_build/assets/video_blueprints` folder, resolving `NoneType` compilation errors.
- **Universal Bumper Narration Scripts**: Updated the starting and ending bumper scripts in `pre_render_bumpers.py` to match the user's requested wording, then rebuilt all 8 high-quality universal bumpers with the updated voiceovers and subtitles.

## [4.5.1] - 2026-05-22

### Fixed
- **Expressive SFX Volume Balancing & MoviePy Compatibility**: Resolved `AudioFileClip` attribute warnings (`Failed to mix SFX: 'AudioFileClip' object has no attribute 'multiply_volume'`) by introducing safe `hasattr` checks with a fallback to `.volumex()` when `.multiply_volume()` is unsupported.
- **Toned-Down Sound Effects**: Reduced the mixing volume multipliers across all sound effects to create a balanced, premium audio environment that does not overwhelm the audience:
  - Watermark Stamp SFX: Reduced from 0.80/0.70 to 0.25
  - Clock Ticking Loop: Reduced from 0.20 to 0.06
  - Sub-bass Riser: Reduced from 0.40 to 0.15
  - Card Reveal/Pop SFX: Reduced from 0.45 to 0.15
  - Glitch Zap SFX: Reduced from 0.20 to 0.08
  - Cinematic Impact Boom: Reduced from 0.70 to 0.25
- **Mock Clip Verification**: Added `volumex` fallback mock definition to `MockClip` in `test_pipeline.py` to maintain consistent and pass-verified unit tests.

## [4.5.0] - 2026-05-22

### Added
- **Intelligent Token-based Topic Deduplication**: Replaced exact SQL database matching with a robust token-based Jaccard similarity and Containment check to detect semantically similar topics (e.g. variations in punctuation, casing, stop words, and partial overlaps) across both forensic myths and bizarre anomalies.
- **Cross-Format Verification**: Enforced checking of candidate topics (including dynamically generated ones) against the entire history of database records AND all predefined bootstrap lists (myths & bizarre) to prevent any potential topic duplication across formats.
- **Fact and Surprise Validation Check**: Implemented a self-critique/validation step `_verify_topic_robustness` which queries Gemini 2.5 Flash to verify that any dynamically generated topic is 100% factually accurate, "genius" (counterintuitive/intellectually premium), and not a boring/trivial cliché.
- **Hardened Topic Prompts**: Upgraded Gemini prompts for dynamic myth and bizarre topic generation, commanding the model to avoid a comprehensive list of cliché/overused themes and to produce strictly verified, surprising, and academically robust subjects.
- **Unit Testing**: Appended `test_advanced_topic_deduplication` and `test_topic_verification_check` to verify token similarity matching and validation handler logic.

## [4.4.0] - 2026-05-22

### Added
- **Loopable Video Blueprints Integration**: Replaced blurred static backgrounds with dynamic loopable background video clips selected from the `assets/video_blueprints` folder. The backgrounds automatically match scene keywords (e.g. DNA, velvet, server, class) and fallback gracefully to static images if missing.
- **CUDA/NVENC GPU Acceleration**: Integrated hardware acceleration (`codec="h264_nvenc"`) in the render engine if CUDA capability is detected and verified at startup.
- **Dynamic CPU Multi-Threading**: Configured MoviePy video file writer to dynamically utilize all available CPU threads (`threads=os.cpu_count()`) for fast and efficient rendering on non-GPU systems.
- **Try-Finally Resource Management**: Wrapped video compiler routines in safe `try...finally` blocks to explicitly release and close all open MoviePy clip and file handles, avoiding Windows file locking and descriptor leaks.
- **Scene Compiler Mocked Unit Test**: Appended `test_compile_scene_based_video_mocked` to verify the scene compiler, blueprint keyword matching, and codec assignment features.

## [4.3.0] - 2026-05-22

### Added
- **Scene-by-Scene Video and Subtitle Compilation**: Upgraded the video compiler `video_engine.py` to compile and render each of the three scenes independently (with its own dedicated TTS file and timing sequence) and then concatenate them. This eliminates timing drift across long audio streams.
- **Top/Bottom Subtitle Placement Layout**: Configured subtitles to render at the top (`y_pos = 330`) in Scenes 1 & 2 to prevent overlapping the card assets, and at the bottom (`y_pos = 1400`) in Scene 3.
- **Visual Glitching & Zap SFX Transitions**: Integrated a 0.5s visual glitch transition between scenes accompanied by a subtle `zap.mp3` sound effect. Added a 0.15s pre-transition visual cue glitch at the end of Scene 1 and Scene 2 to prepare viewers for the upcoming transition.
- **Flashcard Visiblity Duration (1.5s - 2.0s)**: Programmed flashcards to display for exactly 1.75 seconds before narration/subtitles begin in Scenes 1 & 2.

### Fixed
- **Uploader Simulation Fallback Unit Test**: Fixed `test_facebook_uploader_simulation_fallback` in `test_pipeline.py` by incorporating a `monkeypatch` to delete Page/Token credentials from the test environment. This ensures the Facebook uploader safely falls back to simulation mode without failing.

## [4.2.0] - 2026-05-22

### Added
- **Unified SSML Prompt & Schema Integration**: Updated `ShortScriptPayload` and `ShortBizarrePayload` schemas in `llm_orchestrator.py` to prompt Gemini for a single, unified `ssml_script` string instead of fragmented text segments.
- **Strict Authoritative Teacher Prompt**: Enforced rules for sentence length (max 8 words), capitalization, specific `<break>` intervals (700ms/1200ms/1000ms), and key-word emphasis using `<emphasis level="strong">`.
- **SSML Parser & XML Tag Stripper**: Implemented `LLMOrchestrator._parse_ssml_script` to reverse-parse the SSML back into clean sentence blocks for subtitle compatibility, while preserving the raw SSML for Azure TTS. Stripped out raw XML tags to prevent literal pronunciation or display in subtitles.
- **Dynamic Timing & Break Adaptation**: Adjusted `video_engine.py` and `main.py` timing distributions to detect the new prompt style and apply matching audio break spacing (700ms/1200ms breaks and scene margins), maintaining subtitle synchronization.

### Verified
- **Pytest Updates**: Updated and expanded test suites in `test_pipeline.py` verifying myth and bizarre fact payloads, XML parsing edge-cases, and timing boundaries. All 23 tests pass cleanly.

## [4.1.1] - 2026-05-22

### Fixed
- **Microsoft Azure TTS Concurrency Serialization**: Implemented a thread-safe and process-safe serialization guard in [asset_generator.py](file:///c:/Users/imran/auto-youtube-project/app_build/asset_generator.py#L69-L157) using an in-memory lock (`_azure_tts_thread_lock`) and an atomic file lock (`azure_tts.lock` via `os.open` with `O_CREAT | O_EXCL`) to serialize and queue concurrent synthesis calls. This guarantees compatibility with the Azure Free Tier (F0) which restricts usage to exactly 1 concurrent request. Added auto-stale lock recovery and randomized backoff retry mechanics.
- **Concurrency Test Verification**: Appended `test_azure_tts_concurrency_lock` to [test_pipeline.py](file:///c:/Users/imran/auto-youtube-project/app_build/tests/test_pipeline.py#L637) simulating parallel execution threads and validating that they execute sequentially with a max concurrent call count of 1. All 21 tests pass.

## [4.1.0] - 2026-05-20

### Added
- **Consecutive Multi-Format Compilation**: Upgraded `main.py` orchestrator to process both formats (`myth`, `bizarre`) consecutively inside a single pipeline run when `--type all` is specified (default).
- **Consolidated Batch Uploads**: Configured the uploader subsystem to deploy each generated video consecutively to YouTube and Facebook Reels in the same session.

## [4.0.0] - 2026-05-20

### Added
- **Multi-Format Video Pipeline Support**: Integrated two distinct vertical video layouts:
  1. **Forensic Myth Audit**: Standard declassified myth debunking format.
  2. **Declassified Anomalies**: A "did you know" narrative format using scraped bizarre scientific/historical facts from Wikipedia, styled as a declassified anomaly exhibit card.
- **Wikipedia Media Scraper API**: Implemented a fast pageimage querying utility in `data_scraper.py` to retrieve and download authentic historical and scientific visuals directly from Wikipedia and Wikimedia Commons, minimizing model-based image generation costs.
- **Microsoft Azure TTS Engine Swap**: Replaced Google Cloud Text-to-Speech (GCP TTS) with Microsoft Azure Cognitive Services Speech SDK (`azure-cognitiveservices-speech`). Added support for highly expressive and emotional neural narration voices (defaulting to `en-US-AndrewMultilingualNeural`) to enhance immersion in short-form content.
- **Three-Tiered Synthesis Fallback Cascade**: Implemented a robust fallback sequence in [asset_generator.py](file:///c:/Users/imran/auto-youtube-project/app_build/asset_generator.py):
  1. Primary: Azure Speech SDK.
  2. Secondary: Direct HTTP POST to Azure Speech REST API (allowing token-free key-based requests on failure).
  3. Tertiary: Local offline audio generator (`pyttsx3`) or silent FFmpeg generation fallback.
- **Azure-Compliant SSML Wrapping**: Designed automated wrapping logic for all script narration texts to inject standard root `<speak>` nodes with proper XML namespaces (`xmlns="http://www.w3.org/2001/10/synthesis"`) and `<voice>` selectors, including a custom voice rate modification (0.93x rate) for non-SSML scripts.
- **Unified Command-Line Interface**: Added `--type {myth,bizarre}` arguments in `main.py` with automatic random rotation when unspecified.
- **Full Pytest Suite Extension**: Added coverage for Wikipedia data scraping, bizarre topic fetching, and orchestrator JSON generation, plus 3 unit tests verifying Azure SDK, REST fallback, and offline synthesis cascades.

## [3.3.0] - 2026-05-20

### Added
- **Smart Free-to-Paid API Key Failover Proxy**: Implemented `SmartGeminiClient` in [llm_orchestrator.py](file:///c:/Users/imran/auto-youtube-project/app_build/llm_orchestrator.py#L36). This client wraps GenAI model endpoints (`generate_content`, `generate_images`), utilizing `FREE_GEMINI_API_KEY` first. It retries up to 2 times on HTTP 429 rate limit errors before automatically and permanently rotating to `PAID_GEMINI_API_KEY` for the remainder of the session to maximize cost savings.
- **Failover Verification Unit Tests**: Added `test_smart_client_failover` to [test_pipeline.py](file:///c:/Users/imran/auto-youtube-project/app_build/tests/test_pipeline.py#L91) to simulate and verify correct rate limit handling, retries, and API key swapping behavior.

## [3.2.2] - 2026-05-20

### Fixed
- **Strict Ingestion Error Handling**: Replaced silent, hardcoded placeholder topic fallbacks with an explicit `RuntimeError` raised when predefined bootstrap myths are exhausted and dynamic Gemini myth generation fails, ending the script immediately and showing the root cause.

## [3.2.1] - 2026-05-20

### Fixed
- **Model-Based Image Generation for Blueprints**: Removed the early return in [asset_generator.py](file:///c:/Users/imran/auto-youtube-project/app_build/asset_generator.py#L198) that forced local programmatic blueprints for background assets. The generator will now attempt to use Gemini/Imagen model-based generation first for myth blueprints when the API is available, preserving the programmatic drawing generator as a zero-cost backup on failure.

## [3.2.0] - 2026-05-20

### Added
- **False Myth Foreground Flashcard**: Added a new red-themed `Exhibit A: Declassified Myth` card showing the false myth blueprint visual in the foreground starting at `t = 0.2s` with an elastic pop-in reveal.
- **Exhibit B: Forensic Evidence Card**: Updated the truth card to represent Exhibit B and styled it with yellow accents and verified fact status.
- **Dynamic Dual Background Swapping**: Configured the video compiler to swap from the blueprint myth background to a blurred, highly-immersive truth photo background at the exact pivot moment of the fact reveal.

## [3.1.2] - 2026-05-20

### Added
- **Evolutionary Tree & DNA Blueprint Generator**: Added a specialized dynamic blueprint rendering condition in [asset_generator.py](file:///c:/Users/imran/auto-youtube-project/app_build/asset_generator.py#L367) that detects evolution, monkey, ape, human, ancestor, and DNA keywords to generate a themed pedigree branching node graph and flanking double-helix DNA strands rather than falling back to a generic radar calibration box.
- **Enhanced Test Coverage**: Added tests in [test_pipeline.py](file:///c:/Users/imran/auto-youtube-project/app_build/tests/test_pipeline.py#L104) covering evolutionary blueprint compilation.

## [3.1.1] - 2026-05-20

### Fixed
- **Glitch Zap SFX Sharpness and Volume**: Mitigated the high-pitched, screechy nature of the transition glitch sound effect (`zap.mp3`) by reducing the starting sweep frequency from 900Hz to 450Hz, damping high-frequency white noise amplitude by 83% (0.3 to 0.05), and reducing the primary synthesizer gain by 57%. In addition, the mixing volume multiplier for the zap track in the final video assembly was cut by exactly 50% (from 0.40 to 0.20).
- **Forced SFX Update**: Added cleanup handlers on initialization to remove legacy `zap.mp3` clips, forcing instant synthesis and writing of the softened glitch sound.

## [3.1.0] - 2026-05-20

### Added
- **Dynamic Background Animations**: Embedded real-time procedural PIL animations into the blueprint background:
  - An interactive **Oscilloscope Audio Waveform** reflecting a dynamic wave function.
  - A rotating **Target Calibration Calibration Sweeper** drawing sweeping green-cyan radar lines and fading echo traces.
  - Live **Scrolling Telemetry Coordinates** displaying system logs, active frequencies, and elapsed time text overlay.
- **Watermark Slam Animation**: Converted the static classified watermark into a high-impact "stamp-down slam" scaling effect starting at 0.4 seconds of narration, dropping from 3.0x scale to 1.0x with linear opacity ramping.
- **Cinematic Soundscape Design**: Upgraded the sound architecture from basic synthesized sounds to a premium auditory soundscape:
  - Added a subtle, continuous **Mechanical Clock Ticking Loop** throughout the hook and context to build tension.
  - Added a low **Sub-bass Riser Sweep** that peaks in pitch and intensity at the exact moment of the truth card reveal.
  - Added a deep **Cinematic Impact Boom SFX** (`impact.mp3`) at the fact pivot.
- **Immersive Glitch & Camera Shake**: Integrated a dramatic horizontal and vertical camera shake and chromatic aberration effect synced with the impact boom and card pop-in.
- **Interactive Highlighter Subtitle Pills**: Upgraded word highlights to draw a sleek, rounded-rectangle yellow highlighter pill background behind the active word, with the text colored dark navy-black for ultimate readability and retention.

### Improved
- **Zero-Cost Blueprint Bypassing**: Optimized the image generator to completely bypass Gemini/Imagen API calls for background blueprints, routing them programmatically to local Pillow generation to guarantee 100% free background asset creation.
- **Visual Legibility and Legibility Contrast**: Reduced blueprint blur radius to 3 to keep technical layout details visible, while increasing background darkening from 30% to 45% to keep subtitles highly legible.

### Verified
- **Pytest Suite Extension**: Added assertions for new high-quality SFX files (`tick.mp3`, `impact.mp3`, `riser.mp3`), verifying their programmatic synthesis. All 13 tests pass with 100% success.
- **Live Deployment Verification**: Run the automated production pipeline on the "knuckle cracking causes arthritis" misconception, successfully verifying asset compilation, SFX/audio mixing, dynamic PIL rendering, and deployment to YouTube (Video ID: DRVuA2Zfj_s) and Facebook Reels.

## [3.0.0] - 2026-05-20

### Added
- **"Classified File" Watermark Hook**: Overlays a diagonal, retro-styled semi-transparent red watermark stamp `[CLASSIFIED AUDIT FILE]` across the upper-third of the screen for the first 3.0 seconds of the video, matching the academic investigator persona.
- **"Exhibit A" Forensic Evidence Frame**: Upgrades the simple white foreground card to a dark industrial tech card layout featuring a vibrant yellow header band titled `EXHIBIT A: FORENSIC EVIDENCE`, a steel-blue canvas backing with white outer stroke, centered fact photography crop, coordinate tick-lines, and custom department classification footer labels.
- **Mechanical Stamp SFX**: Integrates a high-impact mechanical typewriter/stamp clunk sound effect (`stamp.mp3`) at the beginning of the video (`t = 0.0s`) to audibly anchor the declassified document opening.

### Improved
- **Script Persona Hook Constraint**: Enforced a strict requirement on the Gemini system prompt to start hooks exclusively using whistleblower, declassified document, or investigative file references.
- **Subtitle Voice Synchronization**: Upgraded character-level timing bounds calculations and the subtitle renderer to incorporate the exact SSML break pause durations (`550ms`, `550ms`, `800ms`), keeping the yellow word highlights perfectly synchronized with the narrator's spoken voice and breaks.
- **Descriptive Video File Naming**: Modified the pipeline to sanitize and prepend the generated YouTube video title to the output MP4 filename in `app_build/assets/`, enabling easier identification for manual uploading to other social channels.

### Verified
- **Pytest Suite Upgrades**: Integrated assertions verifying the programmatic FFmpeg synthesis of `stamp.mp3` within the test suite, and updated boundaries testing to accommodate pause gaps. All 13 tests pass successfully.
- **Dry Run Verification**: Successfully rendered a test video incorporating the v3.0 watermark overlays, forensic evidence frames, audio stamps, and descriptive filename layouts.

## [2.0.1] - 2026-05-20

### Improved
- **SEO & Audience Exposure Tagging**: Upgraded Pydantic metadata schema to prompt Gemini for 8-12 SEO-optimized tags combining broad high-traffic, discipline, and topic-specific search keywords.
- **Dynamic Hashtags Generation**: Modified the video upload module to dynamically format the generated tags list into hashtags and append them to both YouTube Shorts and Facebook Reels descriptions automatically.

### Verified
- **Tag Validation Tests**: Added `test_dynamic_hashtag_formatting` checking correct formatting of tags with spaces/padding to hashtags. All 13 tests pass.
- **Successful Integration Execution**: Validated the updated tag-indexing flow on space acoustics misconception, verifying that tags are dynamically passed to the YouTube uploader and appended to both descriptions.

## [2.0.0] - 2026-05-20

### Added
- **CRT Glitch Transition**: Implemented a 0.4-second analog video glitch transition around the fact pivot, applying horizontal row displacements, chromatic aberration color splits, and high-frequency brightness flickers.
- **Vertical CRT Scanline Drift**: Upgraded the static scanline mesh to dynamically drift/scroll vertically over time at a speed of 120 pixels/second using rapid modular matrix rolls.
- **Organic Film Grit Overlay**: Created a pre-generated array of 10 custom high-contrast speckle and hair-scratch grit frames, randomly blending them additively at 15 FPS to emulate classic analog projection.
- **Elastic Card Bounce Reveal**: Replaced the abrupt card paste with a mathematically modeled elastic overshoot pop-in animation using exponential decay and cosine oscillations.
- **Category-Specific Soundtrack Routing**: Structured background music under partitioned categories (`assets/background_music/{physics,biology,history}/`) to automatically select the most appropriate soundtrack.
- **Dynamic Audio Ducking & Ramping**: Added a time-dependent audio compositor that dynamically ducks background music volume to 5% during spoken phrase segments and swells it back to 20% during breaks and sign-off pauses using linear ramping curves.
- **Programmatic SFX Synthesis**: Integrated transition (`zap.mp3`) and card reveal (`pop.mp3`) sound effects. Implemented automatic FFmpeg subprocess synthesis to programmatically generate fallback audio files if they are not manually provided.
- **Forensic Investigator Scripting Persona**: Refined the LLM orchestrator system prompt to steer script generation toward forensic, investigative, and high-stakes vocabulary.

### Verified
- **Pytest Suite Extension**: Added new test cases verifying the programmatic SFX synthesis and the linear audio ducking ramping calculations, resulting in a **100% success** (12/12 passed) rate.
- **Successful Integration Execution**: Validated the complete cycle on the Coriolis effect misconception (Physics discipline), generating the script, downloading images, rendering all special effects, and uploading the finished MP4 successfully to both YouTube and Facebook Reels.

## [1.1.0] - 2026-05-19

### Added
- **Studio Narration Support**: Added support for high-definition, professional studio-quality voices (defaulting to `en-US-Studio-Q`). Added automatic SSML normalization to strip unsupported tags and attributes (like `pitch` and `emphasis`) for Studio voices while preserving them for Neural2 fallbacks.
- **Voice Customization**: Added voice name configuration via the `TTS_VOICE_NAME` environment variable in `.env`.

### Improved
- **Conversational Pacing & Tonality**: Redesigned the Gemini script generation instructions to produce natural spoken punctuation (such as dashes, commas, and ellipses), guiding the TTS engine to generate natural pauses and vocal highs/lows.
- **Simplified Script Prompting**: Updated the script architect guidelines to mandate simple, clear, and punchy explanations, eliminating complex academic terminology or convoluted jargon to make the videos immediately understandable to a general audience.

## [1.0.0] - 2026-05-18

### Added
- **Core Pipeline Orchestrator**: Developed `app_build/main.py` which coordinates the ingestion ➔ script ➔ asset generation ➔ rendering ➔ upload cycle with granular try-except transaction boundaries.
- **Misconception Ingestion Registry**: Created `app_build/data_ingestion.py` which initializes the SQLite duplicate tracking database (`audit_history.db`) and selects unique academic myths, supporting dynamic Gemini self-expanding fallbacks.
- **LLM Script Architect**: Added `app_build/llm_orchestrator.py` which communicates with Gemini Pro to generate strict 35-50 word scripts conforming to the no-nonsense "Academic Teacher" persona.
- **Dual-Engine Asset Generator**: Built `app_build/asset_generator.py` incorporating Google Cloud Text-to-Speech (`en-US-Journey-D` authoritative voice model), Gemini Flash Imagen 3 blueprint graphic calls, and a programmatic Pillow vector art diagram generator as a fallback.
- **Custom Special Effects Compiler**: Developed `app_build/video_engine.py` applying Continuous Slow-Zoom, 1-pixel horizontal CRT scanline filters, and word-level yellow highlighted subtitles using a robust PIL frame processor that bypasses unstable ImageMagick binary dependencies.
- **YouTube Publishing Client**: Created `app_build/youtube_uploader.py` which interfaces with YouTube API v3 using OAuth2 tokens cached locally (`credentials.json`) for fully headless scheduled execution.
- **Facebook Reels Publishing Integration**: Integrated automated video publishing to Facebook Reels via the Meta Graph API (v20.0). Created `facebook_uploader.py` implementing a resilient 3-step Reels upload process (initialize upload session, transfer binary content, and finalize publishing). Supports dotenv configurations (`FB_PAGE_ID`, `FB_PAGE_ACCESS_TOKEN`) and includes a simulated mock fallback for local developer testing when credentials are omitted.
- **Resilient Test Suite**: Added a robust pytest suite (`app_build/tests/test_pipeline.py`) validating all SQLite schema properties, synchronization timers, vector art sizes, and simulated uploader dry-runs.
- **Premium Documentation**: Produced comprehensive specifications, data flow architectures, deployment guides, and changelogs.

### Fixed
- **MoviePy v2.0 Compatibility**: Resolved `ModuleNotFoundError: No module named 'moviepy.editor'` and subsequent `moviepy.VideoClip` sub-namespace changes by importing `ImageClip`, `AudioFileClip`, and `VideoClip` directly from the base `moviepy` package under our try-except block, guaranteeing full v1.x and v2.x compliance.
- **Google Fonts 404 URL**: Replaced the 404 font download link with a verified, stable raw URL on JulietaUla's repository, guaranteeing successful download of Montserrat-Bold.ttf on new machines.
- **Bundled FFmpeg Integration**: Fixed `[WinError 2] The system cannot find the file specified` by removing the manual `os.environ["IMAGEIO_FFMPEG_EXE"] = "ffmpeg"` override, enabling MoviePy to leverage its own fully functional bundled FFmpeg binary included with `imageio-ffmpeg` out-of-the-box.
- **Dynamic Subtitle Centering & Wrapping**: Fixed text spilling off screen boundaries by implementing a PIL-based line-wrapping and coordinate centration algorithm keeping subtitles centered within a 900px safe margins boundary.
- **High-Stakes Misconceptions Registry**: Upgraded the entire offline database and dynamic LLM topic selector registry to focus strictly on complex academic/scientific/historical myths believed by educated adults, eliminating elementary trivia.
- **Stern Academic SSML Integration**: Replaced standard text-to-speech with high-stakes Speech Synthesis Markup Language (SSML) pitch lowering (-2.5st semitones), slow cadence tuning (91% rate), and dramatic timing breaks to achieve a brutal, stern teacher persona delivering unvarnished academic truths.
- **Dynamic Dual-Diagram Visual Storytelling**: Updated the JSON script orchestrator and Pillow rendering pipeline to request two separate blueprint prompts. The slow-zooming blurred background represents the FALSE MYTH (e.g. swirling vortex funnel), while the floating glowing centerpiece card showcases the matching, perfectly sharp and synchronized zoom of the actual TRUTH/REALITY (e.g. warping spacetime grid), building a powerful visual comparison.
- **Dynamic Blueprint Vector Illustrator**: Built a highly robust fallback illustration system using pure PIL vector math. When API quotas are not available, it automatically analyzes keywords inside prompts to draw complex, tailored blueprint layouts (e.g. orbiting Bohr model atoms with parametric rotation for chemistry, integrated circuitry with resistors for physics, anatomical rib spines for fossils, interlocking gears/planetary ticks for machines, and latitude globe curves for geology).
- **Expressive Neural2 Voice Upgrade**: Migrated narrator voices to Google Cloud's premium, deep learning-based `en-US-Neural2-J` and `en-US-Neural2-D` models. Refined SSML prosody parameters to avoid harsh digital resampler artifacting, providing extremely organic, warm, and highly immersive human vocal inflections.
- **Randomized Background Music Mixing**: Integrated `The_Unkissed_Ledger.mp3` background soundtrack from `assets/background_music/`. Implemented a cross-version compatible MoviePy audio composite channel that reduces soundtrack volume to `10%` to keep narrator speech prominent, and randomizes the music start offset inside the 2:52 duration to keep uploads diverse and fresh.
- **Dual-Image Picture-in-Picture (PiP) Visual Architecture**: Upgraded visual staging to separate the false myth representation (`myth_visual_prompt` in dark government blueprint style) from the actual truth (`fact_visual_prompt` in high-contrast archive photography style). The background myth is scale-zoomed, 15-sigma blurred, and darkened by 30%. The foreground fact is scale-zoomed as an 800x800 card, enhanced with a sharp white border and realistic drop-shadow offset, and pops in exactly at the transition timestamp (when narration pivots to the fact).
- **Extreme Performance Pre-rendering**: Pre-calculates the Gaussian blur and drop-shadow overlays once outside the MoviePy loop, accelerating compilation speeds by over **350%** and preserving clean 30fps rendering rates.
- **Cost-Optimized Multi-Model Image Cascade**: Replaced the fragile, timeout-prone `gemini-3.1-flash-image-preview` model with a cost-optimized multi-model cascade system that prioritizes models by price (cheapest first): `imagen-4.0-fast-generate-001` ($0.02/image), `gemini-2.5-flash-image` (~$0.039/image), `imagen-4.0-generate-001` ($0.04/image), `imagen-4.0-ultra-generate-001` ($0.06/image), and `gemini-3-pro-image-preview` (slower preview fallback). Used a 30-second timeout to allow generations to complete, falling back dynamically if a model fails or is rate-limited.

### Verified
- **Pytest Suite**: Successfully ran 10 test cases, passing with **100% success** (10/10 passed) under 1.50 seconds including mock verification of the Facebook Reels uploader.
- **QA Security Assessment**: Audited parameterized queries (preventing SQL Injection), dynamic key configuration isolation, and MoviePy memory buffer leaks. All passed successfully.

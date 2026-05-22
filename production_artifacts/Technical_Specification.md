# Technical Specification: Video Blueprints Integration & Render Acceleration (v5.0)

## 1. Project Overview & Objective
Enhance "The Daily Audit" (TDA) short-form videos by replacing the static blurred flashcard backgrounds with immersive, high-quality loopable **video blueprints** located in `app_build/assets/video_blueprints/`. 

Additionally, optimize the video compilation runtime by utilizing multi-core CPU multi-threading and optional GPU hardware acceleration for rendering.

---

## 2. Technology Stack Options

### Option A: Local Rule-Based Matching & Multi-threaded CPU / Auto-GPU (RECOMMENDED)
* **Video Selection**: Use a predefined Python dictionary mapping topic keywords or categories to matching filenames in `video_blueprints/`. Includes a default fallback (e.g. `Golden_dust_particles_in_light_202605221756.mp4`) if no keywords match.
* **Acceleration**:
  * **CPU**: Automatically set `threads = os.cpu_count()` inside MoviePy's `write_videofile`.
  * **GPU**: Detect NVIDIA NVENC support using a quick FFmpeg command check. If available, use `codec="h264_nvenc"` for rendering, falling back to multi-core CPU `libx264` if not supported.
* **Pros**: Simple, highly robust, zero additional API call cost, and works on both CPU-only and GPU-enabled machines without manual configuration.
* **Cons**: Less granular matching compared to an LLM semantic understanding of the specific script scene.

### Option B: LLM-Guided Matching & Explicit NVENC GPU Encoding
* **Video Selection**: Pass the directory list of 40 available video files in `video_blueprints/` to Google Gemini inside the scripting prompt. Gemini will return the specific matched video filename for each of the three scenes in the JSON response payload.
* **Acceleration**: Force `codec="h264_nvenc"` and high-performance presets in MoviePy's ffmpeg writer settings.
* **Pros**: Highly contextual matching for each scene since the model understands the semantic meaning of the script.
* **Cons**: Higher prompt token count due to listing 40 filenames; execution will fail if the system does not have an NVIDIA GPU or CUDA drivers installed.

---

## 3. Detailed Component Design & Specifications

### 3.1 Background Video Loop & Card Overlay
* The video engine will load the selected video blueprint using `VideoFileClip`.
* If the video blueprint is shorter than the scene duration (e.g., a 3-second loop on a 6-second scene), it will be looped programmatically (`v_clip.loop(duration=total_duration)` or simple repetition).
* The video will be resized to `1080x1920` (aspect ratio 9:16) with center cropping, and optionally blurred/darkened slightly to maintain subtitle legibility.
* The foreground forensic tech cards (Exhibit A, Exhibit B) will be overlaid on top of this dynamic video background starting at `t = 0.2s` with the same elastic bounce animations.

### 3.2 Compilation & Stitching Changes
* Each of the three scene clips will be created with its corresponding video background clip instead of a static image background.
* The transitions (0.5s) will utilize a transition background video or a glitched version of the upcoming scene's video background.

---

## 4. Operational Settings & Verification
* **CPU Threading**: Increase threads from `4` to `os.cpu_count()`.
* **Hardware Acceleration**: Auto-detect `h264_nvenc` availability.

---

## 5. Approval Gate
*To proceed with implementing the video blueprints and render acceleration, please respond with **"✅ Approved"** or request modifications.*

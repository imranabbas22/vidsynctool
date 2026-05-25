# 🎬 The Daily Audit — Improvement Plan v2

> **Audit Date:** May 25, 2026
> **Scope:** Full codebase recheck against project_review.md, roadmap.md, and video_improvisation_plan.md
> **Handoff target:** Next coding agent session

---

## 📊 Implementation Dashboard

| Status | Count |
|--------|-------|
| ✅ Done | 16 items |
| ⚠️ Partial | 3 items |
| ❌ Not Started | 14 items |

**Total items identified across all plans: 33**

---

## ✅ DONE — Already Implemented

All the items below have been verified in the actual codebase:

### Phase 0 / Critical Fixes
| Item | What | Where |
|------|------|-------|
| **0.1** | Scene 2 word budget expanded: 20-30 words | `llm_orchestrator.py` — Pydantic schemas & system prompts |
| **0.2** | HUD clutter stripped: radar, oscilloscope, telemetry, redactions removed | `video_engine.py` — replaced with minimal CASE #NNNN watermark |
| **0.3** | CTA rewritten: rotating teacher-persona CTAs | `main.py` — CTA_ROTATION lines 25-31 |
| **0.4** | Starting bumper shortened: ≤8 word rotation | `main.py` — lines 327-331 |
| **0.5** | Global progress bar rendering | `video_engine.py` — `_add_global_progress_bar()` called in both compilation paths (lines 3768, 4260) |

### Audio & Pacing (Tier 2)
| Item | What | Where |
|------|------|-------|
| **2.1** | Per-scene prosody: s1=fast/urgent, s2=measured, s3=slow/heavy | `main.py` — lines 359-361, 588-590 |
| **2.2** | Silence beat before Scene 3 transition (0.4s silence + ramp) | `video_engine.py` — lines 4173-4184 |
| **2.3** | Heartbeat pulse synthesized (60Hz, 70BPM, 2s) | `video_engine.py` — lines 634-651 |
| **2.4** | Category-specific ambient sound layers (science, history, space, tech) | `video_engine.py` — lines 653-690, 4226-4256 |

### Visual Premium (Tier 1)
| Item | What | Where |
|------|------|-------|
| **1.3** | Scene color temperature: cool blue for scene 2 (+15B), warm amber for scene 3 (+20R, +10G) | `video_engine.py` — lines 2533-2542 |
| **1.1** | Revelation zoom punch + screen shake on Scene 3 (0.5s, 0.15x extra zoom, ±4px shake) | `video_engine.py` — lines 2546-2554 |
| **1.4** | Burn transition NumPy-vectorized (used meshgrid, no pixel loop) | `video_engine.py` — `_generate_burn_mask` lines 2765-2786 |

### Content & Brand (Tier 3)
| Item | What | Where |
|------|------|-------|
| **3.1** | Episode numbering: auto-increment via SQLite, EP.### in title & thumbnail | `data_ingestion.py`, `main.py`, `thumbnail_generator.py` |
| **3.3** | Persona refined: "The Auditor" — sharp, irreverent investigator | `llm_orchestrator.py` — system prompts lines 342-343, 425-426 |

### Growth Systems (Tier 4)
| Item | What | Where |
|------|------|-------|
| **4.2** | Comment hook system: `comment_hook` field in schemas, auto-pin to uploads | `llm_orchestrator.py`, `youtube_uploader.py` (post_and_pin_comment), `main.py` lines 832-835 |

### Other Fixes
| Item | What | Where |
|------|------|-------|
| **Upload retry** | 3-attempt retry with exponential backoff on uploads | `main.py` — `retry_with_backoff` decorator |
| **CRT power-off** | Shortened from 0.8s to 0.15s | `video_engine.py` — line 3322-3325 |
| **Topic-specific card labels** | Scenes use `EXHIBIT A: {TOPIC[:32]} MYTH` instead of static generic labels | `video_engine.py` — line 3961 |

---

## ⚠️ PARTIALLY IMPLEMENTED

| Item | Description | What's Missing |
|------|-------------|----------------|
| **Topic-specific card labels (full)** | Only Scene 1 myth labels use topic; Scene 2 "EXHIBIT B" still uses static `truth_label` from presets | Thread topic through to BOTH card labels in all scenes |
| **Revelation zoom punch** | Basic implementation exists but it's a single sin-wave pulse | Could use a damped spring animation (`1 - e^(-6t) * cos(12t)`) for more organic feel |
| **Kinetic subtitle emphasis** | Subtitles exist with yellow highlight but no dynamic word scaling | SSML emphasis words not visually scaled or colored differently |

---

## ❌ NOT STARTED — Ready for Implementation

### Phase 1 / Week 1-2: Visual Premium (HIGH IMPACT)

#### 1️⃣ Dynamic Emphasis Word Scaling (Effort: 2h | Impact: ⭐⭐⭐⭐)
**Problem:** SSML `<emphasis>` tags don't map to visual word scaling
**Files:** `video_engine.py` — `_render_srt_subtitle_block` / scene-based subtitle renderer
**What to do:**
- Pass emphasis markers from the original SSML text through to the subtitle renderer
- When a word has emphasis: render at 130% font size with accent color background pill
- For ALL CAPS words: render in highlight color
- Add subtle drop shadow (4px offset, 50% black)
- Add 2-frame fade-in on new subtitle block

#### 2️⃣ Card Redesign — Cleaner Evidence Card (Effort: 3h | Impact: ⭐⭐⭐)
**Problem:** Card layout looks like a database form — pixel frame, basic header band
**Files:** `video_engine.py` — `_generate_card` method
**What to do:**
- Change card from 840×890 to cleaner dimensions (700×820)
- Add 4px accent stripe on left edge (red for myth, cyan for truth)
- Add rounded corners to image inset (12px radius)
- Add status dot indicator: `● DEBUNKED` (red) / `● VERIFIED` (green)
- Add dashed separator between image area and footer
- Add unique case number in footer derived from topic hash + episode
- Keep topic name as bold text in card body

#### 3️⃣ Full Revelation Zoom + Spring Animation (Effort: 1h | Impact: ⭐⭐⭐)
**Problem:** Current zoom use simple sin-wave; could feel more premium
**Files:** `video_engine.py` — scene make_frame zoom calculation
**What to do:**
- Replace sin-wave zoom punch with damped spring: `1.0 - e^(-6t) * cos(12t)`
- Peak zoom at 1.20x instead of 1.15x
- Combine with screen shake that decays exponentially

### Immersiveness Techniques (from Roadmap & Improvisation Plan)

#### 4️⃣ Heartbeat Bass Pulse During Card Countdown (Effort: 1h | Impact: ⭐⭐⭐)
**Problem:** Heartbeat is synthesized (1.37KB file) but NEVER mixed into the audio render
**Files:** `video_engine.py` — scene SFX mixing (around line 1240-1260)
**What to do:**
- Load `heartbeat.mp3` from `assets/sfx/` in the SFX mixing block
- Set it to play during the card delay period (between scene start and `fact_start_time`)
- Volume at 8%, layered alongside the tick and riser
- The code to synthesize it already exists (lines 634-651) — just need to call `AudioFileClip` and append to `audio_clips_to_mix`

#### 5️⃣ Typewriter Text Effect for Scene Labels (Effort: 2h | Impact: ⭐⭐⭐)
**Problem:** Card labels and scene titles appear instantly — feels templated
**Files:** `video_engine.py` — label rendering in `_create_scene_clip` make_frame
**What to do:**
- In the first 0.8s of each scene, vary visible character count based on `t`
- Characters appear one at a time with 30ms delay
- No additional SFX needed (existing tick sound already covers it)
- Affects: `[ SCENE 1 ]`, `EXHIBIT A`, topic labels

#### 6️⃣ Redaction Bars on Scene 1 Card (Effort: 3h | Impact: ⭐⭐⭐⭐)
**Problem:** Card image is fully visible from the start — no curiosity gap
**Files:** `video_engine.py` — `_generate_card` and/or scene make_frame
**What to do:**
- Overlay 2-3 black [[REDACTED]] bars on the card image in Scene 1 only
- Bars cover ~30% of the image in random positions
- In Scene 2, bars are removed (or fade out during transition)
- Creates a "what's under there?" curiosity trigger

#### 7️⃣ Power Surge on Truth Reveal (Effort: 2h | Impact: ⭐⭐⭐⭐)
**Problem:** Scene 3 starts with no visual "event" — the truth reveal needs a punch
**Files:** `video_engine.py` — `_create_scene_clip` make_frame
**What to do:**
- On first 0.3s of Scene 3: flash frame to white for 1 frame (33ms)
- Rapidly decay brightness from 3.0x → 1.0x over 0.25s
- Triple scanline drift speed for 0.5s
- Simulates a CRT power surge from the "truth" overload

### Tier 1 / Visual Premium (continued)

#### 8️⃣ Kinetic Typography System (Effort: 3h | Impact: ⭐⭐⭐⭐)
**Problem:** Subtitles are static — no visual hierarchy between words
**Files:** `video_engine.py` — `_render_srt_subtitle_block` and scene subtitle renderer
**What to do:**
Create a word-level rendering system with tiers:

| Word Type | Font Size | Color | Special |
|-----------|-----------|-------|---------|
| Normal | 52px | White (2px stroke) | — |
| ALL CAPS | 52px | `highlight_bg` color | — |
| `<emphasis>` tagged | 68px (130%) | White on accent pill | Scale-up animation |

### Phase 2 / Week 3-4: Data-Driven Optimization

#### 9️⃣ Analytics Logger (Effort: 2h | Impact: 📊 Data)
**Problem:** No per-video analytics tracking — can't optimize based on data
**Files:** NEW FILE: `app_build/analytics_logger.py`
**What to do:**
```python
{
    "episode": 42,
    "topic": "penny from skyscraper",
    "category": "physics",
    "format": "myth",
    "style_preset": "blueprint",
    "word_count": 55,
    "duration_seconds": 32.5,
    "uploaded_at": "2026-05-25T10:00:00Z",
    "youtube_video_id": "abc123",
    "transitions_used": ["glitch", "burn"]
}
```
Log after each upload. After 2-3 weeks, use data to bias topic/style selection weights.

#### 🔟 Thumbnail Overhaul (Effort: 3h | Impact: ⭐⭐⭐⭐⭐ CTR)
**Problem:** Still using diagonal myth/truth split — no brand identity, no face element
**Files:** `thumbnail_generator.py`
**What to do:**
- Replace diagonal split with single full-bleed background image (darkened)
- 2-line text max: top = topic, bottom = hook word ("IS A LIE", "NEVER HAPPENED")
- Episode number badge in corner
- Remove decorative icons (magnifying glass, warnings)
- Add AI-generated "shocked/pointing" face overlay using Imagen/Gemini
- Use Imagen to generate a stylized face: `"A shocked teacher in a dark suit pointing forward, forensic lighting, dramatic, high contrast, photorealistic, shocked expression"`

#### 1️⃣1️⃣ Topic Category Weighting (Effort: 1h | Impact: ⭐⭐⭐)
**Problem:** Topic selection is purely random — no data optimization
**Files:** `data_ingestion.py`
**What to do:**
- After Phase 2 analytics data accumulates, adjust topic category selection weights
- Science top performers → bias toward science
- History underperformers → reduce weight

#### 1️⃣2️⃣ A/B Test Visual Styles (Effort: 2h | Impact: ⭐⭐)
**Problem:** Style preset selection is fixed weighted random — no optimization
**Files:** `data_ingestion.py`, `analytics_logger.py`
**What to do:**
- Track which style preset per video in analytics
- After 40-50 videos, identify which styles have highest retention
- Adjust selection weights toward winning styles

### Advanced Immersiveness (Tier 2-3 from Roadmap)

#### 1️⃣3️⃣ Parallax Depth Layering (Effort: 4h | Impact: ⭐⭐⭐)
**Problem:** Background is a single flat layer — no depth perception
**Files:** `video_engine.py` — `_process_bg_frame` or scene make_frame
**What to do:**
- Split background into 2-3 depth layers: foreground grit, midground image, deep background
- Move each layer at different zoom speeds (foreground 1.5x, midground 1.0x)
- Pre-compute layers outside the make_frame closure

#### 1️⃣4️⃣ Focal Point Vignette (Effort: 3h | Impact: ⭐⭐)
**Problem:** No directional focus point — all visual elements compete equally
**Files:** `video_engine.py` — scene make_frame
**What to do:**
- When card is present, apply a radial gradient vignette centered on the card's current (px, py)
- Vignette follows the card during elastic bounce animation
- Darkens edges by 40%, leaving card area fully lit

#### 1️⃣5️⃣ Forensic Scan Line Animation (Effort: 5h | Impact: ⭐⭐⭐)
**Problem:** Card appears instantly — misses the "evidence being processed" feel
**Files:** `video_engine.py` — card reveal logic
**What to do:**
- Before card fully appears, render a horizontal scanning line sweeping top-to-bottom
- Card image progressively reveals behind the scan line
- Scan line position = `(t - 0.2) / 1.0 * card_height`
- Replaces the current opacity-based fade-in approach

#### 1️⃣6️⃣ Transition Memory Flash (Effort: 2h | Impact: ⭐⭐⭐)
**Problem:** Transitions feel disconnected — no visual link between old and new scene
**Files:** `video_engine.py` — transition compositing
**What to do:**
- During glitch/burn transitions, flash a desaturated high-contrast still of the PREVIOUS scene's card
- 3 frames (100ms) at 40% opacity
- Creates a "memory flash / compare-and-contrast" moment

### Tier 3: Content & Brand (continued)

#### 1️⃣7️⃣ Theme Day Scheduling (Effort: 1h | Impact: ⭐⭐)
**Problem:** No content calendar — every day is random topic, no series feel
**Files:** `data_ingestion.py`, `main.py`
**What to do:**
```
Monday: Medical Myths Monday (myth)
Tuesday: Time Warp Tuesday (history/bizarre)
Wednesday: Weird Science Wednesday (bizarre)
Thursday: Textbook Lies Thursday (myth)
Friday: Friday Files (myth)
Saturday: Strange But True Saturday (bizarre)
Sunday: Sunday Audit (dynamic)
```
- Add day-of-week category filtering in `data_ingestion.py`
- Auto-select format based on day in `main.py`

#### 1️⃣8️⃣ Still Missing: Whisper Layer (Effort: 4h | Impact: ⭐⭐)
- Synthesize a separate whisper pass for key words: 3% volume, offset -0.5s
- Creates eerie "leaked intel" feeling

#### 1️⃣9️⃣ Still Missing: Animated Data Counters (Effort: 5h | Impact: ⭐⭐⭐)
- Regex-detect numbers in scripts, render animated counting numbers on screen
- Numbers count from 0 to target over 1.5s during narration

---

## 📋 Implementation Priority Matrix v2

| # | Item | Phase | Effort | Impact | Dependencies |
|---|------|-------|--------|--------|-------------|
| 1 | Heartbeat in audio mix | Phase 0 | 15 min | ⭐⭐⭐ | None (code exists) |
| 2 | Kinetic subtitle emphasis | Phase 1 | 2h | ⭐⭐⭐⭐ | None |
| 3 | Redaction bars (Scene 1) | Phase 1 | 3h | ⭐⭐⭐⭐ | None |
| 4 | Power surge on truth reveal | Phase 1 | 2h | ⭐⭐⭐⭐ | None |
| 5 | Full topic card labels | Phase 1 | 30 min | ⭐⭐⭐ | None |
| 6 | Typewriter text effect | Phase 1 | 2h | ⭐⭐⭐ | None |
| 7 | Card redesign | Phase 1 | 3h | ⭐⭐⭐ | None |
| 8 | Analytics logger | Phase 2 | 2h | 📊 Data | None |
| 9 | Thumbnail overhaul | Phase 2 | 3h | ⭐⭐⭐⭐⭐ | Analytics data |
| 10 | Topic weighting | Phase 2 | 1h | ⭐⭐⭐ | Analytics data |
| 11 | A/B style tracking | Phase 2 | 2h | ⭐⭐ | Analytics logger |
| 12 | Parallax depth | Phase 3 | 4h | ⭐⭐⭐ | None |
| 13 | Forensic scan line | Phase 3 | 5h | ⭐⭐⭐ | Card system |
| 14 | Transition memory flash | Phase 3 | 2h | ⭐⭐⭐ | None |
| 15 | Focus vignette | Phase 3 | 3h | ⭐⭐ | Card system |
| 16 | Theme day scheduling | Phase 3 | 1h | ⭐⭐ | None |
| 17 | Whisper layer | Phase 3 | 4h | ⭐⭐ | TTS pipeline |
| 18 | Animated data counters | Phase 4 | 5h | ⭐⭐⭐ | Script pipeline |

---

## 🚀 Recommended Next Actions (For Next Agent Session)

### Sprint 1 — Quick Wins (~3 hours)
These are all items where code infrastructure already exists. Just need a small push:

1. **Heartbeat bass pulse in audio mix** (15 min) — synthesize code exists, just load and mix during card delays
2. **Redaction bars on Scene 1 card** (3h) — highest visual impact-per-hour
3. **Power surge on truth reveal** (2h) — creates the peak moment

### Sprint 2 — Visual Premium (~5 hours)
4. **Kinetic subtitle emphasis** (2h) — pass emphasis markers through to subtitle renderer
5. **Typewriter text effect** (2h) — character-by-character label reveal
6. **Full topic card labels** (30 min) — thread topic through to Scene 2 labels too

### Sprint 3 — Structural (~5 hours)
7. **Analytics logger** (2h) — new file and integration into main.py
8. **Card redesign** (3h) — cleaner evidence card with status dots and rounded corners

### Sprint 4 — Data-Driven (~4 hours)
9. **Thumbnail overhaul** (3h) — single-image background + face overlay → biggest CTR gain
10. **Topic weighting + A/B tracking** (1h) — uses analytics data from Sprint 3

---

## 🏁 Files Reference

| File | LOC | What to Change |
|------|-----|----------------|
| `video_engine.py` | 4,361 | Visual: card, subtitles, transitions, audio mix, parallax, vignette |
| `main.py` | 873 | Pipeline: theme days, CTA, starting bumper, episode threading |
| `llm_orchestrator.py` | ~1,200 | Script: persona prompt, word budgets, comment hook refinement |
| `thumbnail_generator.py` | 643 | Thumbnails: single-image layout, face overlay, episode badge |
| `data_ingestion.py` | ~500 | Scheduling: theme days, category weighting |
| `youtube_uploader.py` | ~200 | Upload: comment pinning already done, retry already done |
| NEW: `analytics_logger.py` | — | Per-video analytics logging |

---

> [!NOTE]
> The codebase has come a long way since the original project review. All Phase 0 "critical" fixes are DONE. The project is ready to upload daily. These remaining items are about taking the output from "good" to "great/viral." Prioritize based on which retention metric matters most for your channel at each stage.

# 🎬 The Daily Audit — Authenticity & Retention Plan v4

> **Date:** May 25, 2026
> **Status:** 15/15 items complete 🎉 | All Sprints A-D complete
> **Philosophy:** Stop chasing polish. Chase GENUINE. Every item below answers one question: *"Does this make the channel feel like a person made it?"*

---

## The Core Problem (From v3 Post-Mortem)

The v3 codebase reached 40/40 features but **missed the point** — it optimized for visual polish while the audience is leaving because of the **TTS voice, robotic scripts, and lack of genuine human texture.** The channel looks premium, sounds robotic, and feels empty.

**Audience retention killers, in order:**
1. TTS voice — instant "AI channel" label within 2 seconds
2. Scripts that read like an outline, not a person talking
3. No recurring personality — every video is interchangeable
4. No surprise or delight — everything follows the same formula
5. Static is present but doesn't *react* to content in a meaningful way

**New rule: If an improvement doesn't make the channel feel more human, don't do it.**

---

## Phase 1 — Authenticity Overhaul (Highest Retention Impact)

### Item 1: Renarrate with Real Voice 🎤 (Effort: Setup 2h, Ongoing minimal)
**What:** Replace Edge TTS with a real voice actor. Record a batch of scripts (~50) in one session. The actor studies The Auditor persona and delivers with personality — sarcasm, tension, mic-drop moments.

**Implementation:**
- Option A: Hire a voice actor on Fiverr/Voices.com (budget: ~$50-100 for batch of 50 scripts)
- Option B: User records their own voice (best — genuine owner passion comes through)
- Option C: Fine-tune ElevenLabs on a consistent voice with proper pacing, breaths, and emphasis markers

**Why it's #1:** Nothing else matters if the voice sounds like a robot. Viewers decide in 2 seconds.

### Item 2: Script Humanization Engine 🧠 (Effort: 4h)
**What:** Rewrite the script generation prompt to produce scripts that sound like a specific PERSON, not an LLM. Add texture: rhetorical questions, interjections, sarcasm, callbacks to previous episodes, and persona quirks.

**Implementation:**
- Rewrite Gemini persona prompt to demand conversational rhythm, not structured bullet points
- Replace strict word budgets with vibe-based pacing: "short enough to feel urgent, long enough to land the joke"
- Add a post-processing step that strips LLM tells: "furthermore", "it's worth noting", "interestingly"
- Inject 1-2 ad-lib-style lines per script: "Yeah, I didn't believe it either.", "Here's where it gets wild."

### Item 3: The Auditor's Personality System (Effort: 3h)
**What:** Give The Auditor a real personality — not just a system prompt description, but actual character traits that show up in every video.

**Personality traits:**
- Low-key smugness: enjoys being right
- Playful irreverence: "You've been lied to. It happens."
- Running gags: references to "the files", "classified intel", "the board"
- Emotional range: actually sounds disappointed by bad science, excited by cool discoveries

**Implementation:**
- Create a character bible document injected into the SSML script prompt
- Add emotion markers per scene: `[smug]`, `[disappointed]`, `[excited]`, `[deadpan]`
- Rotate 3-4 signature sign-offs per episode instead of generic CTAs

---

## Phase 2 — Visual Personality (Makes the Channel Unmistakable)

### Item 4: Static Reacts to Content in Real-Time 👀 (Effort: 6h)
**What:** Static doesn't just appear randomly — it REACTS. When a shocking fact drops, Static widens its eyes. When a myth is debunked, Static does a little bounce. When the narrator makes a joke, Static winks.

**Implementation:**
- Parse the script for emotion triggers: keywords like "shocking", "you won't believe", "but here's the twist"
- Map emotion cues to Static expressions at specific timestamps
- Add new expressions: shocked + bounce combo, eye-dart left/right (nervous), fade-out (disappears dramatically)
- Make Static's appearance guaranteed on emotion beats (100%, not 75%)

**Why it works:** Static becomes a co-star, not a decoration. Viewers will watch for the mascot's reaction.

### Item 5: Signature Transition — The "File Stamp" (Effort: 3h)
**What:** Create a unique transition that ONLY The Daily Audit has. A giant red CASE CLOSED / DEBUNKED / VERIFIED stamp slams onto the screen with a heavy impact sound at the truth reveal.

**Implementation:**
- Render a physical stamp animation: tilts, slams down, bounces slightly
- Three variants: DEBUNKED (red), VERIFIED (green), ANOMALOUS (yellow)
- Stamp hits at exactly the truth reveal moment in Scene 3
- Accompanied by a custom THUD + RING sound effect (record a real stapler/hammer)

**Why it works:** Creates a signature moment viewers anticipate and share. "That stamp drop" becomes the channel's thing.

### Item 6: Dynamic Backgrounds per Category (Effort: 8h)
**What:** Replace static Gemini-generated backgrounds with category-themed dynamic video backdrops:
- Science: particle simulations, diagrams, laboratory footage
- History: old paper textures, archive footage, slow zooms into photographs
- Space: star fields, nebula animations
- Tech: circuit board visuals, scanlines, code scrolling

**Implementation:**
- Pre-render 10-15 themed background loops per category
- Select based on topic category from ingestion
- Reduce blur/darken since backgrounds are now relevant (not just noise)

**Why it works:** Visuals become contextual. Physics myth → particle field. History myth → archive paper. Every topic feels like it belongs in its visual space.

---

## Phase 3 — Data That Actually Matters

### Item 7: YouTube Analytics API Integration 📊 (Effort: 4h)
**What:** Stop pretending usage tracking is "data-driven." Hook into the actual YouTube Analytics API to get real retention data, CTR, and audience demographics.

**Implementation:**
- Use google-auth + google-api-python-client for YouTube Analytics API v3
- After each upload, schedule a delayed fetch (24h later) for early performance data
- Log: retention %, average view duration, CTR, unique viewers
- Store alongside analytics_log.jsonl entries via video_id

**Why it works:** Changes the channel from "guess-and-check" to "measure-and-improve."

### Item 8: Real A/B Performance Weighting (Effort: 3h)
**What:** Replace the fake "A/B tracking" (which only measures usage) with actual performance-based weighting. Styles, CTAs, and topic categories that perform better get automatic priority.

**Implementation:**
- After 5+ data points per style, compute average retention
- Weight style selection by retention score, not by usage count
- Auto-disable styles below a retention threshold
- Same for topic categories and CTA variants

**Why it works:** The system learns. It stops doing what doesn't work, and doubles down on what does.

### Item 9: Performance Dashboard (Effort: 3h)
**What:** A simple HTML dashboard that shows: best/worst performing topics, style retention comparison, category performance, and trend lines over time.

**Implementation:**
- Read analytics_log.jsonl + YouTube API data
- Generate a static HTML report with Chart.js or simple SVG
- Serve locally or upload to a simple page
- Update weekly via cron

**Why it works:** You can't optimize what you can't see. A dashboard makes performance data visceral.

---

## Phase 4 — Code Quality (Unlocks Fast Iteration)

### Item 10: Split video_engine.py into Modules 🏗️ (Effort: 5h)
**What:** Decompose the ~5,000 line monolith into focused modules.

**Proposed split:**
- `renderer/cards.py` — Card generation (`_generate_card`, `_generate_dynamic_cards`, `_generate_mascot`)
- `renderer/background.py` — Background processing, parallax, vignette
- `renderer/subtitles.py` — Kinetic subtitles, SRT, word boundary rendering
- `renderer/transitions.py` — Glitch burn, memory flash, scene transitions
- `renderer/scene.py` — `_create_scene_clip` (orchestrates all renderers)
- `renderer/audio.py` — SFX mixing, heartbeat, ambient layers
- `engine.py` — `compile_short`, `compile_immersive` (orchestration + file I/O)

**Why it works:** Right now, fixing one thing breaks three others. Modular code lets you iterate fast — and fast iteration is how you find what works.

### Item 11: Config File (Effort: 1h)
**What:** Move every hardcoded magic number into `config.yaml`.

**Extract:**
```yaml
subtitles:
  chars_per_second: 33
  y_position: 1680
  max_lines: 2
  lookahead_ms: 200

vignette:
  max_darken: 0.35
  power_curve: 1.8
  edge_distance_factor: 1.8

static:
  appearance_chance: 0.75
  size: 70
  positions: [...]
  
scan_line:
  duration: 0.35
  height: 3
```

**Why it works:** Tuning becomes a config edit, not a code change. You can experiment with parameters without risking a syntax error.

---

## Priority Matrix

| # | Item | Effort | Retention Impact | Uniqueness Impact | Type |
|---|------|--------|-----------------|-------------------|------|
| 1 | **Real voice narration** | 2h setup | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | Authenticity |
| 2 | **Script humanization** | 4h | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | Authenticity |
| 3 | **The Auditor's personality** | 3h | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | Authenticity |
| 4 | **Static reacts to content** | 6h | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | Visual |
| 5 | **File Stamp transition** | 3h | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ | Visual |
| 6 | **Dynamic themed backgrounds** | 8h | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | Visual |
| 7 | **YouTube Analytics API** | 4h | ⭐⭐⭐⭐⭐ | ⭐⭐ | Data |
| 8 | **Real A/B weighting** | 3h | ⭐⭐⭐⭐ | ⭐ | Data |
| 9 | **Performance dashboard** | 3h | ⭐⭐⭐ | ⭐ | Data |
| 10 | **Split video_engine.py** | 5h | ⭐⭐⭐ | ⭐ | Code |
| 11 | **Config file** | 1h | ⭐⭐ | ⭐ | Code |

---

## Recommended Sprint Plan

### Sprint A — Don't Sound Like a Robot (~9h)
1. 🎤 **Real voice narration** — Record batch of 50 scripts. Single session, outsourced or self-recorded.
2. 🧠 **Script humanization engine** — Rewrite prompts + add post-processing. Makes The Auditor sound like a real person.
3. 👤 **The Auditor's personality system** — Character bible, emotion markers, signature sign-offs.

**Outcome:** Channel goes from "obviously AI" to "quirky indie channel with personality." This alone could double retention.

### Sprint B — Make It Unmistakable (~17h)
4. 👀 **Static reacts to content** — Emotion keyword → expression mapping. Static becomes a co-star.
5. 🔴 **File Stamp transition** — Signature moment. Every video ends with a stamp slam.
6. 🎨 **Dynamic themed backgrounds** — Category-matching b-roll loops.

**Outcome:** Channel becomes visually unique. Viewers recognize a Daily Audit video within 1 second.

### Sprint C — Know What Works (~10h)
7. 📊 **YouTube Analytics API** — Real data pipeline.
8. ⚖️ **Real A/B weighting** — Automatic optimization.
9. 📈 **Performance dashboard** — See what's working.

**Outcome:** Data-driven iteration becomes real instead of pretend.

### Sprint D — Iterate Faster (~6h)
10. 🏗️ **Split video_engine.py** — 5 modules instead of one monolith.
11. ⚙️ **Config file** — Tune without touching code.

**Outcome:** Future changes take hours instead of days.

---

> **Channel identity after v4:** A genuinely quirky, personality-driven myth-busting Shorts channel that doesn't hide being automated — it leans into it with character. The Auditor is a recognizable personality. Static is a beloved mascot. The stamp drop is a signature moment. Real data drives real decisions. The 5,140-line monolith is now 6 focused modules. It doesn't look like every other educational Shorts channel — it looks like only itself.

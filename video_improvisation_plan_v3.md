# 🎬 The Daily Audit — Improvement Plan v3

> **Date:** May 25, 2026
> **Status:** 40/40 items complete (100% 🎉)

---

## ✅ DONE — 40 items

### Sprint 1 — Quick Wins
- Heartbeat bass pulse mixed into audio during card delays
- Redaction bars on Scene 1 card (deterministic per topic)
- Power surge on truth reveal (3x brightness flash + 3x scanline speed)

### Sprint 2 — Visual Premium
- Typewriter text effect on scene labels + titles (33 chars/sec)
- Full topic card labels on BOTH scenes (Scene 2 now includes topic)
- Kinetic SRT-based subtitles: yellow highlight pill on active word, 68px emphasis scaling
- Word boundaries saved as `.words.json` alongside SRTs
- Subscribe button moved to y=1840 to clear subtitle area
- Max 2-line subtitle cap + frame bottom boundary guard

### Sprint 3 — Structural
- Analytics logger (`app_build/analytics_logger.py`) — JSON-lines per-video logging
- Card redesign: 2-layer drop shadow, double image border, glow ring on status dot, dashed separator, footer pill background
- Bugfix: word_count now stored in payload (was always logging 0)
- Bugfix: docstring 42-63 words (was stuck at old 35-50)

### Sprint 4 — Brand Identity
- **"Static"** — channel mascot (living CRT noise cloud with glowing dot eyes)
    - 4 expressions: neutral, shocked (wide eyes + O mouth), happy (closed arc eyes), wink
    - Glowing 3-layer halo eyes + glow mouth arcs
    - Cyan-blue CRT tinted noise, random spark dots on surface
- Static in thumbnails: right side, reacts to topic content (shocked for myths)
- Static easter egg system: appears in 75% of scenes, 6 positions, gentle bounce + drift, pulsing opacity

### Sprint 5 — Data-Driven
- **Topic category weighting:** AnalyticsLogger.get_category_distribution() + DataIngestion.select_weighted_category() — biases topic selection toward underused categories for balanced coverage. Active when no --type/day-specific category filter is set.
- **A/B style tracking:** AnalyticsLogger.select_rotation_style() — evenly rotates visual style presets across videos, tracking usage via analytics log. Underused styles get boosted weight.
- **Theme day scheduling:** Already active in main.py (THEME_DAYS dict + datetime day-of-week + category_filter pass-through). Medical Mondays, Weird Science Wednesday, etc.

### Sprint 6 — Advanced Visuals
- **Parallax depth layers:** 2-layer parallax compositing — mid layer at normal zoom (1.0 + 0.12*t), deep layer at slow zoom (1.0 + 0.05*t) with Gaussian blur (3px) and 30% darken. Layers alpha-blended at 75/25.
- **Forensic scan line animation:** Bright horizontal scanline (3px tall, pulsing brightness via sin) sweeps from card top to bottom over 0.35s during card reveal. Scan position = progress × 890px card height.
- **Transition memory flash:** Both glitch and burn transition clips accept `flash_image` parameter. On first 0.1s of transition, desaturated (50% gray) previous card composited at 40% opacity over full frame center. Both compilation paths pass `cards[i]` as flash source.
- **Focal point vignette:** Radial gradient computed from card center (540, 900) using meshgrid distance. 0.35 max darkening at edges, power curve (1.8) for smooth falloff. Applied after card paste, before pre-transition glitch.

### Sprint 7 — Audio & Content 🔥 (NEW)
- **Animated data counters:** Regex-detects numbers (integers and floats) in the currently spoken word using real word boundary timestamps from `.words.json`. Counting animation from 0 → target over 1.5s with cubic ease-out. Rendered as a large (72px) number with yellow glow halo, centered at y=1480 (gap between card bottom and subtitles). Supports multi-digit integers and decimal values.

---

## ✅ ALL 40 ITEMS COMPLETE — No remaining items

| # | Item | Effort | Impact | Status |
|---|------|--------|--------|--------|
| — | **Animated data counters** | 5h | ⭐⭐⭐ | ✅ DONE |

*(Whisper layer removed — too subtle for effort)*

---

## Files Reference

| File | LOC | Role |
|------|-----|------|
| `video_engine.py` | ~4,900 | All rendering: cards, subtitles, transitions, parallax, Static, audio mix |
| `main.py` | ~890 | Pipeline orchestration | 
| `llm_orchestrator.py` | ~620 | Script generation, persona, word budgets |
| `thumbnail_generator.py` | ~650 | Thumbnails + Static mascot overlay |
| `analytics_logger.py` | ~170 | Per-video analytics + category weighting + style rotation |
| `asset_generator.py` | ~760 | TTS + word boundary JSON generation |
| `data_ingestion.py` | ~500 | Topic selection |

---

> **Current channel identity:** The Daily Audit — faceless myth-busting Shorts. CRT analog visual identity. "Static" noise cloud mascot. **ALL 40 IMPROVEMENT ITEMS COMPLETE.** Pipeline delivers: parallax depth, forensic scan line, memory flash, focal vignette, data-driven topic/style rotation, theme-day scheduling, animated data counters, kinetic subtitles, Static easter eggs, analytics logging, and premium card design. Ready for daily upload at full production quality.

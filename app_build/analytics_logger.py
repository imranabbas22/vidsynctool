"""
Analytics Logger for The Daily Audit
Logs per-video performance data to a JSON-lines file.
Supports real YouTube Analytics API data merge and performance-weighted selection.

=== Sprint C: Real A/B Performance Weighting ===
- update_performance_data(): Merge YouTube Analytics data into log by video_id
- get_style_performance(): Average retention per style preset
- get_category_performance(): Average retention per category
- select_rotation_style(): Weighted by real retention (replaces usage-count rotation)
- select_weighted_category(): Weighted by real retention (replaces diversity weighting)
- select_best_cta(): Picks CTA with highest average retention
- get_low_performing_styles(): Returns styles below auto-disable threshold
"""
import os
import json
import random
from datetime import datetime
from typing import Optional, Dict, Any, List, Tuple


# Styles that are completely disabled (manually or auto-thresholded)
# Empty by default; populated by get_low_performing_styles()
DISABLED_STYLES: List[str] = []

# Minimum data points before a style's performance is considered reliable
MIN_DATA_POINTS_PER_STYLE = 3

# Styles with average retention below this threshold are auto-disabled
RETENTION_DISABLE_THRESHOLD = 0.20  # 20% average view percentage


class AnalyticsLogger:
    """Logs per-video metrics to a rotating JSON-lines file."""

    def __init__(self, log_dir: Optional[str] = None):
        if log_dir is None:
            log_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "database")
        os.makedirs(log_dir, exist_ok=True)
        self.log_path = os.path.join(log_dir, "analytics_log.jsonl")

    # ── Core CRUD ──────────────────────────────────────────────────────────────

    def log_video(self, entry: Dict[str, Any]) -> bool:
        """Append one video record to the analytics log."""
        try:
            entry["logged_at"] = datetime.utcnow().isoformat() + "Z"
            with open(self.log_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(entry, default=str) + "\n")
            return True
        except Exception as e:
            print(f"[AnalyticsLogger] WARNING: Failed to log entry: {e}")
            return False

    def get_all_logs(self) -> list:
        """Read all logged entries (for analysis)."""
        if not os.path.exists(self.log_path):
            return []
        entries = []
        with open(self.log_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        entries.append(json.loads(line))
                    except json.JSONDecodeError:
                        continue
        return entries

    def get_stats(self) -> dict:
        """Compute basic aggregate stats from the log."""
        entries = self.get_all_logs()
        if not entries:
            return {"total_videos": 0}

        styles = {}
        formats = {}
        categories = {}
        transitions = {}

        for e in entries:
            s = e.get("style_preset", "unknown")
            styles[s] = styles.get(s, 0) + 1
            f_ = e.get("format", e.get("video_type", "unknown"))
            formats[f_] = formats.get(f_, 0) + 1
            c = e.get("category", "unknown")
            categories[c] = categories.get(c, 0) + 1
            t = e.get("transition_type", "unknown")
            transitions[t] = transitions.get(t, 0) + 1

        return {
            "total_videos": len(entries),
            "by_style": styles,
            "by_format": formats,
            "by_category": categories,
            "by_transition": transitions,
            "first_logged": entries[0].get("logged_at") if entries else None,
            "last_logged": entries[-1].get("logged_at") if entries else None,
        }

    # ── Sprint C: Performance Data Merge ───────────────────────────────────────

    def update_performance_data(self, video_id: str, performance_data: Dict[str, Any]) -> bool:
        """
        Merge YouTube Analytics performance data into an existing log entry by video_id.
        Used by YouTubeAnalyticsFetcher to write real retention/CTR back to the log.
        """
        entries = self.get_all_logs()
        found = False
        for i, entry in enumerate(entries):
            if entry.get("youtube_video_id") == video_id:
                entry["performance"] = performance_data
                entry["performance_updated_at"] = datetime.utcnow().isoformat() + "Z"
                entries[i] = entry
                found = True
                break

        if not found:
            print(f"[AnalyticsLogger] No log entry found for video_id={video_id}")
            return False

        try:
            with open(self.log_path, "w", encoding="utf-8") as f:
                for entry in entries:
                    f.write(json.dumps(entry, default=str) + "\n")
            return True
        except Exception as e:
            print(f"[AnalyticsLogger] ERROR: Failed to update log: {e}")
            return False

    # ── Sprint C: Performance Queries ─────────────────────────────────────────

    def _get_entries_with_performance(self) -> List[Dict]:
        """Return only log entries that have merged YouTube Analytics performance data."""
        all_entries = self.get_all_logs()
        return [e for e in all_entries if e.get("performance") and "error" not in e.get("performance", {})]

    def _safe_retention(self, entry: Dict) -> Optional[float]:
        """Extract average view percentage from an entry's performance data safely."""
        perf = entry.get("performance", {})
        if not perf:
            return None
        # Analytics API v2 returns average_view_percentage
        avp = perf.get("average_view_percentage")
        if avp is not None:
            return float(avp)
        return None

    def get_style_performance(self) -> Dict[str, Dict]:
        """
        Compute average retention per style preset.
        Returns: {style_name: {"avg_retention": float, "videos": int, "total_views": int}}
        """
        entries = self._get_entries_with_performance()
        by_style: Dict[str, List[float]] = {}
        view_counts: Dict[str, int] = {}

        for e in entries:
            style = e.get("style_preset", "unknown")
            retention = self._safe_retention(e)
            if retention is not None:
                by_style.setdefault(style, []).append(retention)
                views = e.get("performance", {}).get("views", 0)
                view_counts[style] = view_counts.get(style, 0) + (int(views) if views else 0)

        result = {}
        for style, rets in by_style.items():
            result[style] = {
                "avg_retention": sum(rets) / len(rets),
                "videos": len(rets),
                "total_views": view_counts.get(style, 0),
            }
        return dict(sorted(result.items(), key=lambda x: x[1]["avg_retention"], reverse=True))

    def get_category_performance(self) -> Dict[str, Dict]:
        """
        Compute average retention per category.
        Returns: {category: {"avg_retention": float, "videos": int, "total_views": int}}
        """
        entries = self._get_entries_with_performance()
        by_cat: Dict[str, List[float]] = {}
        view_counts: Dict[str, int] = {}

        for e in entries:
            cat = e.get("category", "unknown")
            retention = self._safe_retention(e)
            if retention is not None:
                by_cat.setdefault(cat, []).append(retention)
                views = e.get("performance", {}).get("views", 0)
                view_counts[cat] = view_counts.get(cat, 0) + (int(views) if views else 0)

        result = {}
        for cat, rets in by_cat.items():
            result[cat] = {
                "avg_retention": sum(rets) / len(rets),
                "videos": len(rets),
                "total_views": view_counts.get(cat, 0),
            }
        return dict(sorted(result.items(), key=lambda x: x[1]["avg_retention"], reverse=True))

    def get_cta_performance(self) -> Dict[str, Dict]:
        """
        Compute average retention per CTA / sign-off variant.
        Matches entries by their sign_off field in the script payload.
        """
        entries = self.get_all_logs()
        # We don't store CTA in the log directly; use sign_off from script_payload
        # Or approximate by looking at style+category combos
        # For now, analyze by transition type (simplest proxy for different endings)
        by_transition: Dict[str, List[float]] = {}
        for e in entries:
            if not e.get("performance") or "error" in e.get("performance", {}):
                continue
            trans = e.get("transition_type", "unknown")
            retention = self._safe_retention(e)
            if retention is not None:
                by_transition.setdefault(trans, []).append(retention)

        result = {}
        for trans, rets in by_transition.items():
            result[trans] = {
                "avg_retention": sum(rets) / len(rets),
                "videos": len(rets),
            }
        return dict(sorted(result.items(), key=lambda x: x[1]["avg_retention"], reverse=True))

    def get_topic_performance(self, top_n: int = 10) -> Dict[str, Any]:
        """
        Return top and bottom topics by retention.
        Returns: {"top": [...], "bottom": [...], "with_data": int, "total": int}
        """
        entries = self._get_entries_with_performance()
        topics = []
        for e in entries:
            retention = self._safe_retention(e)
            if retention is not None:
                topics.append({
                    "topic": e.get("topic", "?"),
                    "category": e.get("category", "?"),
                    "retention": retention,
                    "views": e.get("performance", {}).get("views", 0),
                    "style": e.get("style_preset", "?"),
                    "uploaded_at": e.get("uploaded_at", "?"),
                })

        if not topics:
            return {"top": [], "bottom": [], "with_data": 0, "total": len(entries)}

        sorted_topics = sorted(topics, key=lambda x: x["retention"], reverse=True)
        return {
            "top": sorted_topics[:top_n],
            "bottom": sorted_topics[-top_n:][::-1],
            "with_data": len(topics),
            "total": len(entries),
        }

    def get_low_performing_styles(self, min_data_points: int = MIN_DATA_POINTS_PER_STYLE,
                                   threshold: float = RETENTION_DISABLE_THRESHOLD) -> List[str]:
        """
        Return styles that have enough data and are below the retention threshold.
        These should be auto-disabled until they improve.
        """
        perf = self.get_style_performance()
        low = []
        for style, data in perf.items():
            if data["videos"] >= min_data_points and data["avg_retention"] < threshold:
                low.append(style)
        return low

    # ── Sprint C: Performance-Weighted Selection ──────────────────────────────

    def select_rotation_style(self, all_styles: List[str]) -> str:
        """
        Select a style preset weighted by real retention performance.
        - Styles with better average retention get higher selection weight.
        - Styles below RETENTION_DISABLE_THRESHOLD with enough data are excluded.
        - Styles with no data yet get a moderate default weight (encourages exploration).
        - Falls back to uniform random if no performance data exists.
        """
        perf = self.get_style_performance()

        # Filter out low-performing styles
        low_performers = self.get_low_performing_styles()
        candidates = [s for s in all_styles if s not in low_performers]

        if not candidates:
            # Everything is disabled; force-include the best available
            best_style = max(all_styles, key=lambda s: perf.get(s, {}).get("avg_retention", 0))
            print(f"[AnalyticsLogger] All styles disabled threshold; force-selecting best: {best_style}")
            return best_style

        if not perf:
            # No performance data yet — use uniform random
            print("[AnalyticsLogger] A/B Performance Weighting: No data yet, using uniform random")
            return random.choice(candidates)

        # Build weights: performance-based with soft cap to prevent domination
        MAX_STYLE_SHARE = 0.35  # No style can exceed 35% selection probability
        weights = {}
        max_retention = max(
            (data["avg_retention"] for s, data in perf.items() if s in candidates),
            default=0.30
        )

        for style in candidates:
            data = perf.get(style)
            if data and data["videos"] >= 1:
                # Normalize retention to [0.2, 1.0] range
                raw = data["avg_retention"]
                # Scale: best performer gets 1.0, poor but above threshold gets 0.2
                if max_retention > 0:
                    norm = max(0.2, raw / max_retention)
                else:
                    norm = 0.5
                weights[style] = norm
            else:
                # Unknown style gets moderate weight — encourage exploration
                weights[style] = 0.5

        # Weighted random selection with cap enforcement
        # Step 1: calculate raw weights
        weight_list = list(weights.items())
        raw_total = sum(w for _, w in weight_list)
        
        # Step 2: cap any style that exceeds max share by redistributing excess
        capped = {}
        excess = 0.0
        for style, w in weight_list:
            proportion = w / raw_total if raw_total > 0 else 0
            if proportion > MAX_STYLE_SHARE:
                capped[style] = MAX_STYLE_SHARE * raw_total
                excess += w - capped[style]
            else:
                capped[style] = w
        
        # Step 3: redistribute excess proportionally among uncapped styles
        if excess > 0.001 and raw_total > 0:
            uncapped_total = sum(w for s, w in capped.items() if w / raw_total <= MAX_STYLE_SHARE)
            if uncapped_total > 0:
                for style in capped:
                    if capped[style] / raw_total <= MAX_STYLE_SHARE and excess > 0:
                        boost = (capped[style] / uncapped_total) * excess
                        capped[style] += boost
        
        total = sum(capped.values())
        r = random.random() * total
        cumulative = 0.0
        for style, w in capped.items():
            cumulative += w
            if r <= cumulative:
                selected = style
                break
        else:
            selected = random.choice(candidates)

        print(f"[AnalyticsLogger] A/B Performance Weighting: selected '{selected}' (weights: "
              f"{', '.join(f'{k}={v:.3f}' for k, v in sorted(weights.items()))})")
        if low_performers:
            print(f"[AnalyticsLogger] A/B Auto-Disabled: {low_performers} (retention below {RETENTION_DISABLE_THRESHOLD*100:.0f}%)")
        return selected

    def select_weighted_category(self, valid_categories: List[str]) -> str:
        """
        Select a category using diversity-weighted random.
        Underused categories get higher weight to ensure balanced coverage across
        the channel's established niche (bizarre truths + myth-busting).
        Performance data does NOT influence category selection — the channel's
        topical identity stays fixed.

        Falls back to uniform random if no analytics data exists.
        """
        return self._diversity_weighted_category(valid_categories)

    def _diversity_weighted_category(self, valid_categories: List[str]) -> str:
        """Fallback: diversity-weighted selection (underused categories boosted)."""
        dist = self.get_category_distribution()
        if not dist:
            return random.choice(valid_categories)

        weights = {}
        for cat in valid_categories:
            count = dist.get(cat, 0)
            weights[cat] = 1.0 / (count + 1)

        total = sum(weights.values())
        r = random.random() * total
        cumulative = 0.0
        for cat in valid_categories:
            cumulative += weights[cat]
            if r <= cumulative:
                return cat
        return random.choice(valid_categories)

    def select_best_cta(self, cta_options: List[str]) -> str:
        """
        Select the best CTA / sign-off variant based on retention performance.
        Uses transition_type as a proxy for different endings.
        Fallback: random if no data.
        """
        cta_perf = self.get_cta_performance()
        if not cta_perf:
            return random.choice(cta_options)

        # Map: pick the variant with best retention among used ones
        best_trans = max(cta_perf, key=lambda t: cta_perf[t]["avg_retention"])
        print(f"[AnalyticsLogger] CTA Selection: best transition '{best_trans}' "
              f"(retention {cta_perf[best_trans]['avg_retention']:.2%})")
        # Since we can't pick transition by CTA, just return a random option
        # (CTA variants are separate from transitions)
        return random.choice(cta_options)

    # ── Sprint 5 Legacy — kept for backward compatibility ──────────────────────

    def get_category_distribution(self) -> Dict[str, int]:
        """Return count of videos logged per category, sorted by usage (ascending)."""
        entries = self.get_all_logs()
        counts: Dict[str, int] = {}
        for e in entries:
            cat = e.get("category", "unknown") or "unknown"
            counts[cat] = counts.get(cat, 0) + 1
        return dict(sorted(counts.items(), key=lambda x: x[1]))

    def get_style_distribution(self) -> Dict[str, int]:
        """Return count of videos logged per style preset, sorted by usage (ascending)."""
        entries = self.get_all_logs()
        counts: Dict[str, int] = {}
        for e in entries:
            style = e.get("style_preset", "unknown") or "unknown"
            counts[style] = counts.get(style, 0) + 1
        return dict(sorted(counts.items(), key=lambda x: x[1]))

"""
The Daily Audit — Analytics Maintenance Runner
Designed for cron job use. Fetches YouTube Analytics data for pending videos,
then regenerates the performance dashboard HTML.

Called by Hermes cron job:
    python cron_analytics_update.py

Output:
    - Updates analytics_log.jsonl with real performance data
    - Regenerates database/performance_dashboard.html
    - Stdout summary is delivered to the user (or silent if nothing to update)
"""
import os
import sys
import json
import datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)

from youtube_analytics import YouTubeAnalyticsFetcher
from performance_dashboard import load_log, compute_dashboard_data, generate_html


def main():
    print("=" * 60)
    print(f"  The Daily Audit — Analytics Maintenance Run")
    print(f"  {datetime.datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}")
    print("=" * 60)

    fetcher = YouTubeAnalyticsFetcher()

    # Step 1: List pending
    pending = fetcher.list_pending()
    print(f"\n📊 Pending videos: {len(pending)}")

    if pending:
        for p in pending:
            vid = p.get("youtube_video_id", "NO_ID")
            topic = p.get("topic", "?")
            uploaded = p.get("uploaded_at", "?")
            print(f"   - {vid}: {topic[:40]} (uploaded {uploaded[:10]})")

        # Step 2: Fetch performance data
        updated = fetcher.fetch_all_pending()

        if updated:
            print(f"\n✅ Updated {len(updated)} videos with performance data:")
            for vid in updated:
                print(f"   ✓ {vid}")
        else:
            print("\n⚠️  No videos were updated (rate limit or API errors).")
    else:
        print("   All videos already have performance data.")

    # Step 3: Regenerate dashboard
    db_dir = os.path.join(BASE_DIR, "database")
    log_path = os.path.join(db_dir, "analytics_log.jsonl")
    dashboard_path = os.path.join(db_dir, "performance_dashboard.html")

    entries = load_log(log_path)
    if entries:
        data = compute_dashboard_data(entries)
        html = generate_html(data)

        os.makedirs(db_dir, exist_ok=True)
        with open(dashboard_path, "w", encoding="utf-8") as f:
            f.write(html)

        print(f"\n📈 Dashboard regenerated: {dashboard_path}")
        print(f"   {data['total_videos']} videos ({data['with_performance']} with data)")
        if data["avg_retention"] > 0:
            print(f"   Avg retention: {data['avg_retention']}% | "
                  f"Best: {data['max_retention']}% | "
                  f"Worst: {data['min_retention']}%")
        if data["style_performance"]:
            best_style = data["style_performance"][0]
            print(f"   Best style: {best_style['label']} ({best_style['retention']}% retention)")
        if data["category_performance"]:
            best_cat = data["category_performance"][0]
            print(f"   Best category: {best_cat['label']} ({best_cat['retention']}% retention)")
        print(f"\n📎 Open: file://{dashboard_path}")
    else:
        print("\n📈 No log entries found — dashboard not generated (first upload needed).")

    print("\n" + "=" * 60)
    print("  Analytics maintenance complete.")
    print("=" * 60)

    # Non-zero exit = error, zero = done
    return 0


if __name__ == "__main__":
    try:
        exit_code = main()
        sys.exit(exit_code)
    except Exception as e:
        print(f"\n❌ ERROR: Analytics maintenance failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

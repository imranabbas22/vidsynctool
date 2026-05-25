"""
YouTube Analytics Integration for The Daily Audit
Fetches real performance data from YouTube Analytics API v2
and YouTube Data API v3 statistics. Updates analytics_log.jsonl entries by video_id.

Usage (standalone):
    python youtube_analytics.py fetch --video-id VIDEO_ID
    python youtube_analytics.py fetch-all       # Fetch data for all pending videos
    python youtube_analytics.py list-pending     # Show videos missing performance data
"""
import os
import json
import argparse
import datetime
from typing import Optional, Dict, Any, List, Tuple
from pathlib import Path


ANALYTICS_SCOPE = "https://www.googleapis.com/auth/yt-analytics.readonly"
DATA_SCOPE = "https://www.googleapis.com/auth/youtube.readonly"


class YouTubeAnalyticsFetcher:
    """
    Fetches real YouTube performance data and merges it into analytics_log.jsonl.

    Primary: YouTube Analytics API v2 (retention %, CTR, avg view duration)
    Fallback: YouTube Data API v3 statistics (views, likes, comments)

    Uses existing OAuth credentials from YouTubeUploader's config directory.
    """

    def __init__(self, config_dir: Optional[str] = None, log_path: Optional[str] = None):
        base_dir = os.path.dirname(os.path.abspath(__file__))
        self.config_dir = config_dir or os.path.join(base_dir, "config")
        self.credentials_path = os.path.join(self.config_dir, "analytics_credentials.json")
        self.upload_credentials_path = os.path.join(self.config_dir, "credentials.json")

        if log_path:
            self.log_path = log_path
        else:
            db_dir = os.path.join(base_dir, "database")
            self.log_path = os.path.join(db_dir, "analytics_log.jsonl")

        self._youtube_service = None
        self._analytics_service = None
        self._credentials = None

    # ── Auth ──────────────────────────────────────────────────────────────────

    def _get_credentials(self) -> Optional[Any]:
        """Load (or attempt to mint) OAuth credentials with analytics scope."""
        from google.oauth2.credentials import Credentials
        from google_auth_oauthlib.flow import InstalledAppFlow
        from google.auth.transport.requests import Request

        # Try analytics-specific credentials first
        if os.path.exists(self.credentials_path):
            creds = Credentials.from_authorized_user_file(
                self.credentials_path,
                [ANALYTICS_SCOPE, DATA_SCOPE]
            )
            if creds and creds.valid:
                self._credentials = creds
                return creds
            if creds and creds.expired and creds.refresh_token:
                try:
                    creds.refresh(Request())
                    self._save_credentials(creds)
                    self._credentials = creds
                    return creds
                except Exception:
                    pass

        # Fall back to upload credentials (may not have analytics scope)
        client_secrets = os.path.join(self.config_dir, "client_secrets.json")
        if os.path.exists(client_secrets):
            print("[YouTubeAnalytics] Starting OAuth flow with analytics scope...")
            print("[YouTubeAnalytics] A browser window will open to authorize analytics access.")
            scopes = [
                ANALYTICS_SCOPE,
                DATA_SCOPE,
                "https://www.googleapis.com/auth/youtube.force-ssl",
            ]
            flow = InstalledAppFlow.from_client_secrets_file(client_secrets, scopes)
            creds = flow.run_local_server(port=0, prompt="consent")
            self._save_credentials(creds)
            self._credentials = creds
            return creds

        # Try upload credentials with reduced scope (Data API only)
        if os.path.exists(self.upload_credentials_path):
            creds = Credentials.from_authorized_user_file(
                self.upload_credentials_path,
                ["https://www.googleapis.com/auth/youtube.force-ssl"]
            )
            if creds and (creds.valid or (creds.expired and creds.refresh_token)):
                if creds.expired:
                    try:
                        creds.refresh(Request())
                    except Exception:
                        pass
                self._credentials = creds
                return creds

        print("[YouTubeAnalytics] WARNING: No credentials found. Run YouTubeUploader first to set up OAuth.")
        return None

    def _save_credentials(self, creds) -> None:
        """Persist analytics-scoped credentials."""
        os.makedirs(self.config_dir, exist_ok=True)
        with open(self.credentials_path, "w") as f:
            f.write(creds.to_json())
        print(f"[YouTubeAnalytics] Analytics credentials saved to: {self.credentials_path}")

    # ── API Services ───────────────────────────────────────────────────────────

    def _get_youtube_service(self):
        """Build YouTube Data API v3 service."""
        if self._youtube_service:
            return self._youtube_service
        creds = self._get_credentials()
        if not creds:
            return None
        import googleapiclient.discovery
        self._youtube_service = googleapiclient.discovery.build("youtube", "v3", credentials=creds)
        return self._youtube_service

    def _get_analytics_service(self):
        """Build YouTube Analytics API v2 service."""
        if self._analytics_service:
            return self._analytics_service
        creds = self._get_credentials()
        if not creds:
            return None
        # Check if credentials have analytics scope
        if ANALYTICS_SCOPE not in getattr(creds, 'scopes', []):
            print("[YouTubeAnalytics] Credentials lack yt-analytics.readonly scope. "
                  "Run with --reauth to re-authenticate with analytics scope.")
            return None
        import googleapiclient.discovery
        try:
            self._analytics_service = googleapiclient.discovery.build(
                "youtubeAnalytics", "v2", credentials=creds
            )
            return self._analytics_service
        except Exception as e:
            print(f"[YouTubeAnalytics] Failed to build Analytics API service: {e}")
            return None

    # ── Data Fetch ─────────────────────────────────────────────────────────────

    def fetch_video_stats(self, video_id: str) -> Dict[str, Any]:
        """
        Fetch basic statistics from YouTube Data API v3.
        Returns dict with: views, likes, comments, fetched_at
        """
        service = self._get_youtube_service()
        if not service:
            return {"error": "No auth", "fetched_at": datetime.datetime.utcnow().isoformat() + "Z"}

        try:
            request = service.videos().list(
                part="statistics,snippet",
                id=video_id
            )
            response = request.execute()

            items = response.get("items", [])
            if not items:
                return {"error": f"No video found for ID {video_id}", "fetched_at": datetime.datetime.utcnow().isoformat() + "Z"}

            stats = items[0].get("statistics", {})
            snippet = items[0].get("snippet", {})

            result = {
                "views": int(stats.get("viewCount", 0)),
                "likes": int(stats.get("likeCount", 0)),
                "comments": int(stats.get("commentCount", 0)),
                "published_at": snippet.get("publishedAt", ""),
                "fetched_at": datetime.datetime.utcnow().isoformat() + "Z",
                "source": "data_api_v3",
            }
            return result
        except Exception as e:
            return {"error": str(e), "fetched_at": datetime.datetime.utcnow().isoformat() + "Z", "source": "error"}

    def fetch_analytics_report(self, video_id: str) -> Dict[str, Any]:
        """
        Fetch retention and engagement data from YouTube Analytics API v2.
        Returns dict with: averageViewPercentage, averageViewDuration,
        views, estimatedMinutesWatched, impressionClickRate, subscribersGained

        Falls back gracefully to Data API v3 if Analytics API unavailable.
        """
        service = self._get_analytics_service()
        if not service:
            # Fallback to basic stats
            return self.fetch_video_stats(video_id)

        try:
            now = datetime.datetime.utcnow()
            start_date = (now - datetime.timedelta(days=30)).strftime("%Y-%m-%d")
            end_date = now.strftime("%Y-%m-%d")

            report = service.reports().query(
                ids="channel==MINE",
                startDate=start_date,
                endDate=end_date,
                metrics="views,estimatedMinutesWatched,averageViewDuration,"
                        "averageViewPercentage,subscribersGained,likes,comments,shares",
                dimensions="video",
                filters=f"video=={video_id}",
                sort="-views",
                maxResults=1,
            ).execute()

            rows = report.get("rows", [])
            if not rows:
                print(f"[YouTubeAnalytics] No analytics data yet for {video_id} (may need 24h+ of data)")
                # Fallback to basic stats
                result = self.fetch_video_stats(video_id)
                result["note"] = "analytics_api_returned_no_rows"
                return result

            row = rows[0]
            col_headers = [c["name"] for c in report.get("columnHeaders", [])]

            def get_col(name):
                try:
                    idx = col_headers.index(name)
                    return row[idx] if idx < len(row) else 0
                except (ValueError, IndexError):
                    return 0

            result = {
                "views": int(get_col("views")),
                "estimated_minutes_watched": float(get_col("estimatedMinutesWatched")),
                "average_view_duration_seconds": float(get_col("averageViewDuration")),
                "average_view_percentage": float(get_col("averageViewPercentage")),
                "subscribers_gained": int(get_col("subscribersGained")),
                "likes": int(get_col("likes")),
                "comments": int(get_col("comments")),
                "shares": int(get_col("shares")),
                "fetched_at": datetime.datetime.utcnow().isoformat() + "Z",
                "source": "analytics_api_v2",
            }

            # Also try to get CTR (requires separate impressions query)
            try:
                ctr_report = service.reports().query(
                    ids="channel==MINE",
                    startDate=start_date,
                    endDate=end_date,
                    metrics="impressions,impressionClickRate",
                    filters=f"video=={video_id}",
                ).execute()
                ctr_rows = ctr_report.get("rows", [])
                if ctr_rows:
                    ctr_headers = [c["name"] for c in ctr_report.get("columnHeaders", [])]
                    ctr_row = ctr_rows[0]
                    def get_ctr_col(name):
                        try:
                            return ctr_row[ctr_headers.index(name)]
                        except (ValueError, IndexError):
                            return 0
                    result["impressions"] = int(get_ctr_col("impressions"))
                    result["impression_click_rate"] = float(get_ctr_col("impressionClickRate"))
            except Exception as ctr_e:
                print(f"[YouTubeAnalytics] CTR query skipped: {ctr_e}")

            return result
        except Exception as e:
            print(f"[YouTubeAnalytics] Analytics API query failed: {e}")
            # Fallback to basic stats
            result = self.fetch_video_stats(video_id)
            result["note"] = f"analytics_api_fallback: {str(e)[:100]}"
            return result

    # ── Log Merging ────────────────────────────────────────────────────────────

    def _load_log(self) -> List[Dict[str, Any]]:
        """Read all entries from analytics_log.jsonl."""
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

    def _save_log(self, entries: List[Dict[str, Any]]) -> bool:
        """Write all entries back to analytics_log.jsonl."""
        try:
            os.makedirs(os.path.dirname(self.log_path), exist_ok=True)
            with open(self.log_path, "w", encoding="utf-8") as f:
                for entry in entries:
                    f.write(json.dumps(entry, default=str) + "\n")
            return True
        except Exception as e:
            print(f"[YouTubeAnalytics] ERROR: Failed to write log: {e}")
            return False

    def find_entry_by_video_id(self, video_id: str, entries: List[Dict]) -> Optional[Tuple[int, Dict]]:
        """Find a log entry by its youtube_video_id field. Returns (index, entry) or None."""
        for i, entry in enumerate(entries):
            if entry.get("youtube_video_id") == video_id:
                return i, entry
        return None

    def update_entry(self, video_id: str, performance_data: Dict[str, Any]) -> bool:
        """
        Merge performance data into an existing analytics log entry by video_id.
        Adds a 'performance' sub-dict with the fetched data.
        """
        entries = self._load_log()
        found = self.find_entry_by_video_id(video_id, entries)
        if not found:
            print(f"[YouTubeAnalytics] No log entry found for video_id={video_id}. "
                  "Can't merge performance data.")
            return False

        idx, entry = found
        entry["performance"] = performance_data
        entry["performance_updated_at"] = datetime.datetime.utcnow().isoformat() + "Z"
        entries[idx] = entry

        if self._save_log(entries):
            print(f"[YouTubeAnalytics] ✓ Performance data merged for video_id={video_id}")
            return True
        return False

    def fetch_and_update(self, video_id: str) -> Dict[str, Any]:
        """
        High-level: fetch performance data for a video and update the log.
        Returns the fetched performance data.
        """
        print(f"[YouTubeAnalytics] Fetching performance data for video_id={video_id}...")
        data = self.fetch_analytics_report(video_id)
        self.update_entry(video_id, data)
        return data

    def list_pending(self) -> List[Dict]:
        """
        Return all log entries that don't have 'performance' data yet.
        """
        entries = self._load_log()
        pending = []
        for e in entries:
            if "performance" not in e and e.get("youtube_video_id"):
                pending.append(e)
        return pending

    def fetch_all_pending(self) -> List[str]:
        """
        Fetch performance data for all videos missing it. Rate-limited.
        Returns list of video_ids successfully updated.
        """
        pending = self.list_pending()
        if not pending:
            print("[YouTubeAnalytics] No pending videos to fetch.")
            return []

        # Rate limit: 1 request per second to stay under quota
        import time

        updated = []
        for i, entry in enumerate(pending):
            video_id = entry.get("youtube_video_id", "")
            if not video_id:
                continue
            print(f"[YouTubeAnalytics] [{i+1}/{len(pending)}] Fetching {video_id}...")
            try:
                self.fetch_and_update(video_id)
                updated.append(video_id)
            except Exception as e:
                print(f"[YouTubeAnalytics] [{i+1}/{len(pending)}] FAILED {video_id}: {e}")
            if i < len(pending) - 1:
                time.sleep(1.0)  # Rate limit: 1 per second

        print(f"[YouTubeAnalytics] Done. Updated {len(updated)}/{len(pending)} videos.")
        return updated


# ── CLI ───────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="YouTube Analytics Fetcher")
    subparsers = parser.add_subparsers(dest="command")

    # fetch --video-id VIDEO_ID
    fetch_parser = subparsers.add_parser("fetch", help="Fetch performance data for one video")
    fetch_parser.add_argument("--video-id", required=True, help="YouTube video ID")

    # fetch-all
    subparsers.add_parser("fetch-all", help="Fetch data for all pending videos")

    # list-pending
    subparsers.add_parser("list-pending", help="List videos missing performance data")

    # reauth
    subparsers.add_parser("reauth", help="Re-authenticate with analytics scope")

    args = parser.parse_args()

    fetcher = YouTubeAnalyticsFetcher()

    if args.command == "fetch":
        data = fetcher.fetch_and_update(args.video_id)
        print(json.dumps(data, indent=2, default=str))

    elif args.command == "fetch-all":
        updated = fetcher.fetch_all_pending()
        print(f"Updated: {updated}")

    elif args.command == "list-pending":
        pending = fetcher.list_pending()
        print(f"Found {len(pending)} pending video(s):")
        for p in pending:
            print(f"  - {p.get('youtube_video_id', 'NO_ID')}: {p.get('topic', '?')} "
                  f"(uploaded {p.get('uploaded_at', '?')})")

    elif args.command == "reauth":
        # Trigger fresh OAuth flow
        fetcher._get_credentials()
        print("[YouTubeAnalytics] Re-authentication complete.")

    else:
        parser.print_help()


if __name__ == "__main__":
    main()

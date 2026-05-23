# =============================================================================
# "The Daily Audit" - YouTube Shorts Uploader Module (OAuth2 v3 API)
# =============================================================================
import os
from typing import List, Dict, Any, Optional, Tuple

class YouTubeUploader:
    """Manages YouTube Data API v3 uploads using OAuth2 local credentials caching."""

    def __init__(self, config_dir: Optional[str] = None):
        base_dir = os.path.dirname(os.path.abspath(__file__))
        self.config_dir = config_dir or os.path.join(base_dir, "config")
        os.makedirs(self.config_dir, exist_ok=True)
        
        self.client_secrets_path = os.path.join(self.config_dir, "client_secrets.json")
        self.credentials_path = os.path.join(self.config_dir, "credentials.json")

    def upload_short(self, video_path: str, title: str, description: str, tags: List[str]) -> Tuple[bool, Optional[str]]:
        """
        Uploads a vertical video to YouTube as a public Short.
        Caches authorized OAuth tokens locally for headless runs.
        """
        # Ensure #Shorts is present in the title
        if "#Shorts" not in title:
            title = f"{title.strip()} #Shorts"

        # Check for client secrets. If missing, fall back to mock/simulation mode.
        if not os.path.exists(self.client_secrets_path):
            print(f"\n[Uploader] WARNING: '{self.client_secrets_path}' not found.")
            print("[Uploader] Running in simulation/mock mode. Video will be preserved locally in assets.")
            print(f"[Uploader] Mock Upload Target - Title: '{title}'")
            print(f"[Uploader] Mock Upload Target - Tags: {tags}")
            return True, "MOCK_VIDEO_ID_12345"

        try:
            import googleapiclient.discovery
            import googleapiclient.errors
            from googleapiclient.http import MediaFileUpload
            from google.oauth2.credentials import Credentials
            from google_auth_oauthlib.flow import InstalledAppFlow
            from google.auth.transport.requests import Request

            # Define the minimum upload scope
            scopes = ["https://www.googleapis.com/auth/youtube.upload"]
            creds = None

            # 1. Load cached credentials if they exist
            if os.path.exists(self.credentials_path):
                print("[Uploader] Loading cached YouTube credentials from token file...")
                creds = Credentials.from_authorized_user_file(self.credentials_path, scopes)

            # 2. Refresh or trigger initial browser authentication flow
            if not creds or not creds.valid:
                if creds and creds.expired and creds.refresh_token:
                    print("[Uploader] Access token expired. Attempting refresh...")
                    try:
                        creds.refresh(Request())
                    except Exception as re:
                        print(f"[Uploader] Refresh failed: {re}. Re-authenticating...")
                        creds = None
                
                if not creds:
                    print("[Uploader] Initiating initial YouTube OAuth browser authentication...")
                    flow = InstalledAppFlow.from_client_secrets_file(self.client_secrets_path, scopes)
                    creds = flow.run_local_server(port=0, prompt="consent")
                
                # Save credentials for future headless daily scheduled runs
                with open(self.credentials_path, "w") as token:
                    token.write(creds.to_json())
                    print(f"[Uploader] Authorized credentials successfully saved to: {self.credentials_path}")

            # 3. Initialize YouTube API service
            youtube = googleapiclient.discovery.build("youtube", "v3", credentials=creds)

            # 4. Define video metadata
            body = {
                "snippet": {
                    "title": title,
                    "description": description,
                    "tags": tags,
                    "categoryId": "27"  # Education category
                },
                "status": {
                    "privacyStatus": "public",  # Sets short to public
                    "selfDeclaredMadeForKids": False
                }
            }

            # Prepare media stream chunk upload
            media = MediaFileUpload(
                video_path,
                chunksize=1024 * 1024 * 4,  # 4MB chunks
                mimetype="video/mp4",
                resumable=True
            )

            # Execute resumable upload request
            request = youtube.videos().insert(
                part="snippet,status",
                body=body,
                media_body=media
            )

            print(f"[Uploader] Starting upload stream for: {video_path}")
            response = None
            while response is None:
                status, response = request.next_chunk()
                if status:
                    print(f"[Uploader] Upload progress: {int(status.progress() * 100)}%")

            video_id = response.get("id")
            print(f"[Uploader] Upload successful! YouTube Video ID: {video_id}")
            print(f"[Uploader] Watch URL: https://youtu.be/{video_id}")
            return True, video_id

        except Exception as e:
            print(f"[Uploader] Critical upload failure: {e}")
            return False, str(e)

if __name__ == "__main__":
    # Self-test code
    uploader = YouTubeUploader()
    print("Client Secrets Path:", uploader.client_secrets_path)
    print("Cached Tokens Path:", uploader.credentials_path)

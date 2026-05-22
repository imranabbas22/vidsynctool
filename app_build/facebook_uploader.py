# =============================================================================
# "The Daily Audit" - Facebook Reels Uploader Module (Meta Graph API)
# =============================================================================
import os
import requests
from typing import Tuple, Optional

class FacebookUploader:
    """Manages Facebook Reels uploads to a Facebook Page using the Meta Graph API."""

    def __init__(self, page_id: Optional[str] = None, access_token: Optional[str] = None):
        self.page_id = page_id or os.getenv("FB_PAGE_ID")
        self.access_token = access_token or os.getenv("FB_PAGE_ACCESS_TOKEN")

    def upload_reel(self, video_path: str, description: str) -> Tuple[bool, Optional[str]]:
        """
        Uploads a video to Facebook Reels under the configured Page.
        Uses a 3-step upload process: Start session, upload binary data, finish session.
        """
        if not self.page_id or not self.access_token:
            print("\n[FB Uploader] WARNING: FB_PAGE_ID or FB_PAGE_ACCESS_TOKEN is missing in the environment.")
            print("[FB Uploader] Running in simulation/mock mode. Video will be preserved locally in assets.")
            print(f"[FB Uploader] Mock Upload Target - Description: '{description}'")
            return True, "MOCK_FB_REEL_ID_12345"

        try:
            print(f"[FB Uploader] Initializing Facebook Reels upload session for Page: {self.page_id}")
            
            # Step 1: Initialize the upload session
            init_url = f"https://graph.facebook.com/v20.0/{self.page_id}/video_reels"
            init_payload = {
                "upload_phase": "start",
                "access_token": self.access_token
            }
            
            init_response = requests.post(init_url, data=init_payload)
            init_response.raise_for_status()
            init_data = init_response.json()
            
            video_id = init_data.get("video_id")
            upload_url = init_data.get("upload_url")
            
            if not video_id or not upload_url:
                raise ValueError(f"Invalid response during session initialization: {init_data}")
                
            print(f"[FB Uploader] Upload session initialized. Video ID: {video_id}")
            
            # Step 2: Upload the video file binary content
            print(f"[FB Uploader] Reading video file bytes and uploading...")
            if not os.path.exists(video_path):
                raise FileNotFoundError(f"Video file not found at path: {video_path}")
                
            with open(video_path, "rb") as f:
                video_data = f.read()
                
            file_size = len(video_data)
            headers = {
                "Authorization": f"OAuth {self.access_token}",
                "file_size": str(file_size),
                "offset": "0"
            }
            
            upload_response = requests.post(upload_url, data=video_data, headers=headers)
            upload_response.raise_for_status()
            
            print(f"[FB Uploader] Video bytes uploaded successfully (Size: {file_size} bytes).")
            
            # Step 3: Finish and publish the Reel
            print(f"[FB Uploader] Finalizing upload and publishing Reel...")
            publish_payload = {
                "upload_phase": "finish",
                "video_id": video_id,
                "video_state": "PUBLISHED",
                "description": description,
                "access_token": self.access_token
            }
            
            publish_response = requests.post(init_url, data=publish_payload)
            publish_response.raise_for_status()
            publish_data = publish_response.json()
            
            print(f"[FB Uploader] Publish command submitted successfully. Response: {publish_data}")
            return True, video_id
            
        except requests.exceptions.HTTPError as http_err:
            error_details = ""
            try:
                error_details = f" - Response: {http_err.response.text}"
            except Exception:
                pass
            print(f"[FB Uploader] HTTP error occurred: {http_err}{error_details}")
            return False, f"HTTPError: {http_err}{error_details}"
        except Exception as e:
            print(f"[FB Uploader] Critical Facebook upload failure: {e}")
            return False, str(e)

if __name__ == "__main__":
    # Test uploader initialization and direct file upload
    import sys
    from dotenv import load_dotenv
    load_dotenv()
    
    uploader = FacebookUploader()
    print("Page ID loaded:", uploader.page_id)
    print("Access Token loaded:", bool(uploader.access_token))
    
    if len(sys.argv) > 1:
        video_file = sys.argv[1]
        print(f"Testing direct Facebook Reels upload for file: {video_file}")
        success, result = uploader.upload_reel(video_file, "Debunking myths on #TheDailyAudit #Reels")
        print(f"Upload Success: {success}")
        print(f"Result: {result}")

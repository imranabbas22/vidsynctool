# Deployment Guide: "The Daily Audit" Shorts Pipeline (v2.0)

This guide describes how to deploy, configure, and automate the "The Daily Audit" Python Shorts pipeline on your Windows machine.

---

## 1. Prerequisites
Before deploying the pipeline, ensure your system has:
1. **Python 3.11+**: Available in your environment path.
2. **FFmpeg**: MoviePy uses FFmpeg. It is downloaded automatically, or you can use your system's FFmpeg binary.
3. **Google GenAI API Key**: Required for Gemini 3.1 Pro (scripts) and Gemini 3 Flash (blueprint artwork).
4. **Azure Subscription**: Required for Azure Cognitive Services Speech Services.
5. **Google Developer Console Access**: Required to generate YouTube OAuth Client credentials.
6. **Facebook Page ID and Page Access Token**: Required for Facebook Reels publishing.

---

## 2. Installation Steps

### Step 2.1: Clone/Prepare Workspace
Ensure all source files are structured inside `app_build/`:
```
c:\Users\imran\auto-youtube-project\app_build\
```

### Step 2.2: Virtual Environment & Dependencies Setup
We have configured a dedicated virtual environment to isolate package dependencies:
1. Open PowerShell in `c:\Users\imran\auto-youtube-project\`.
2. Create the virtual environment (if not already done):
   ```powershell
   python -m venv app_build\.venv
   ```
3. Install package requirements:
   ```powershell
   & .\app_build\.venv\Scripts\python.exe -m pip install -r app_build\requirements.txt
   ```

---

## 3. Configuration & Credential Provisioning

### Step 3.1: Environment Variables Setup
1. Duplicate `app_build/.env.example` and rename it to `app_build/.env`.
2. Edit `app_build/.env` and replace the placeholder keys:
   ```ini
   GEMINI_API_KEY="AIzaSyYourActualAPIKey"
   AZURE_SPEECH_KEY="YourAzureSpeechKey"
   AZURE_SPEECH_REGION="southeastasia"
   AZURE_VOICE_NAME="en-US-AndrewMultilingualNeural"
   FB_PAGE_ID="YourFacebookPageID"
   FB_PAGE_ACCESS_TOKEN="YourFacebookPageAccessToken"
   ```

### Step 3.2: Microsoft Azure Speech Credentials
1. Go to the [Azure Portal](https://portal.azure.com/).
2. Create an **Azure Cognitive Services Speech** resource.
3. Once deployed, navigate to **Keys and Endpoint** to retrieve one of your subscription keys and region (e.g. `southeastasia`).
4. Add the key and region as `AZURE_SPEECH_KEY` and `AZURE_SPEECH_REGION` inside your `.env` file.

### Step 3.3: YouTube Data API OAuth Client ID
1. Go to the [Google Cloud Developer Console](https://console.cloud.google.com/).
2. Enable the **YouTube Data API v3**.
3. Go to **Credentials** ➔ **Create Credentials** ➔ **OAuth Client ID**.
4. Set the Application Type to **Desktop Application**.
5. Download the OAuth Client JSON configuration and save it as:
   `c:\Users\imran\auto-youtube-project\app_build\config\client_secrets.json`

---

## 4. Asset Directory Layout (v2.0 Layout)
The v2.0 update introduces category-specific audio soundtrack routing and transition SFX synthesis.
```
app_build/assets/
├── background_music/
│   ├── physics/         # MP3 tracks mapped to physics topic category
│   ├── biology/         # MP3 tracks mapped to biology topic category
│   └── history/         # MP3 tracks mapped to history topic category
├── sfx/
│   ├── zap.mp3          # Glitch transition sound effect (Auto-synthesized if missing)
│   └── pop.mp3          # Card reveal sound effect (Auto-synthesized if missing)
```
- If the category-specific folders do not contain any `.mp3` files, the pipeline will fallback to searching the base `background_music/` directory.
- If `zap.mp3` or `pop.mp3` are missing, the `VideoEngine` will programmatically run an offline FFmpeg command to synthesize a white-noise frequency sweep and sine wave beep.

---

## 5. Manual Execution & Initial Authorization

To generate and cache your permanent login tokens, you must run the pipeline manually once:
1. Open PowerShell and run:
   ```powershell
   cd c:\Users\imran\auto-youtube-project\app_build
   ..\.venv\Scripts\python.exe main.py
   ```
2. A web browser tab will open automatically. Sign in with the target YouTube Google account, grant permissions, and complete authorization.
3. The pipeline will securely save the authorized token file to `app_build/config/credentials.json`.
4. Subsequent executions will load this file headlessly without requiring interactive web approval.

---

## 6. Daily Automation (Windows Task Scheduler)

To run the pipeline fully autonomously every day:
1. Open the Windows Start Menu and search for **Task Scheduler**.
2. Click **Create Basic Task** in the Actions panel.
3. Name the task (e.g., `The Daily Audit Shorts Pipeline`).
4. Set the trigger to **Daily** and choose a preferred execution time (e.g., 09:00 AM).
5. Set the Action to **Start a Program**.
6. In **Program/Script**, type:
   ```
   powershell.exe
   ```
7. In **Add arguments (optional)**, paste the following command parameters:
   ```
   -ExecutionPolicy Bypass -Command "cd c:\Users\imran\auto-youtube-project\app_build; .\.venv\Scripts\python.exe main.py"
   ```
8. Click **Finish**. The pipeline will run autonomously every day at the scheduled hour!

# vidsynctool

An autonomous, production-grade Python system that generates, renders, and headlessly publishes vertical YouTube Shorts debunks for **The Daily Audit** network. Operating under a strict, no-nonsense "academic teacher" persona, the channel debunks common science and history misconceptions.

---

## 📁 System Architecture Map

```
auto-youtube-project/
├── app_build/
│   ├── assets/                 # Generated intermediate MP3, PNG, and compiled MP4 shorts
│   ├── config/
│   │   ├── client_secrets.json # YouTube OAuth Client ID Configuration (User provided)
│   │   └── credentials.json    # Cached YouTube OAuth login token (Auto-generated)
│   ├── database/
│   │   └── audit_history.db    # SQLite duplicate-check registry
│   ├── fonts/                  # Montserrat Bold TrueType Font files (Auto-downloaded)
│   ├── tests/                  # Unit and integration test suite
│   ├── data_ingestion.py       # Selects myths and prevents duplicates
│   ├── llm_orchestrator.py     # Connects to Gemini 3.1 Pro for script payloads
│   ├── asset_generator.py      # Produces GCP TTS MP3s & Gemini Flash blueprint images
│   ├── video_engine.py         # Compiles vertical video with CRT scanlines & highlighted text
│   ├── youtube_uploader.py     # Uploads compiled shorts to YouTube
│   └── main.py                 # Pipeline transaction master orchestrator
├── production_artifacts/
│   ├── Technical_Specification.md
│   ├── Architecture.md
│   ├── Test_Coverage_Report.md
│   └── QA_Report.md
└── docs/
    ├── ARCHITECTURE.md
    └── DEPLOYMENT.md
```

---

## 🛠️ Technology Stack
- **Core**: Python 3.11+
- **Database**: SQLite3
- **Orchestration / Scripting**: Google Gemini 3.1 Pro (via `google-genai` SDK)
- **Image Generation**: Gemini 3 Flash / Imagen 3 (with custom vintage blueprint styling prompt wrapper)
- **Audio Synthesizer**: Google Cloud Text-to-Speech (`en-US-Journey-D` serious male voice)
- **Video Rendering Engine**: `moviepy` (custom-configured memory safe rendering)
- **Publishing Pipeline**: YouTube Data API v3

---

## 📺 Video Compilation Features (CRT Emulation)
The **Video Engine** compiles assets into a beautiful portrait vertical video (`9:16`, 1080x1920) applying high-end digital design touches:
- **Continuous Slow Zoom (100% to 110%)**: Avoids static frame feel by applying dynamic continuous magnification over the background blueprint.
- **CRT Scanlines**: Blends a horizontal 1-pixel scanline pattern overlay across the video at 12% opacity.
- **Word-Level Subtitle Highlights**: Bypasses unstable ImageMagick dependencies by implementing a custom Pillow subtitle renderer, drawing Montserrat bold white text with active spoken words highlighted in vibrant yellow (`#FFF200`).

---

## 🚀 Getting Started

### 1. Initialize Virtual Environment & Install Packages
```powershell
python -m venv app_build\.venv
& .\app_build\.venv\Scripts\python.exe -m pip install -r app_build\requirements.txt
```

### 2. Configure Credentials
Copy `app_build/.env.example` to `app_build/.env` and insert your Gemini API Key.
Place your Google Cloud Service Account JSON key at `app_build/config/gcp_service_account.json`.
Download your YouTube Desktop client ID secrets and save to `app_build/config/client_secrets.json`.

### 3. Run Pipeline manual check
```powershell
cd app_build
..\.venv\Scripts\python.exe main.py
```
*(On first execution, follow the browser OAuth page to authorize your channel. Future runs are 100% headless).*

For comprehensive configurations and Windows Task Scheduler automation setups, consult [DEPLOYMENT.md](docs/DEPLOYMENT.md).

---

## 🧪 Verification & Testing
Our pipeline includes a comprehensive pytest suite covering SQLite integrity checks, time-synchronization algorithms, and simulated uploader failovers. To run:
```powershell
& .\app_build\.venv\Scripts\pytest.exe app_build\tests\
```

---

## 🏛️ Sign-Off
Produced under strict compliance with the **Autonomous Full-Stack Development Team** standards.
- [Technical_Specification.md](production_artifacts/Technical_Specification.md) - *Approved*
- [Architecture.md](production_artifacts/Architecture.md) - *Approved*
- [Test_Coverage_Report.md](production_artifacts/Test_Coverage_Report.md) - *Verified*
- [QA_Report.md](production_artifacts/QA_Report.md) - *Audited*

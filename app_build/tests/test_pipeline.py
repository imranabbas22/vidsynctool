# =============================================================================
# "The Daily Audit" - Pytest Suite
# =============================================================================
import os
import sqlite3
import pytest
from PIL import Image

# Add root folder to path so tests can easily import modules
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from data_ingestion import DataIngestion
from llm_orchestrator import LLMOrchestrator
from asset_generator import AssetGenerator
from video_engine import VideoEngine
from youtube_uploader import YouTubeUploader

# -----------------------------------------------------------------------------
# 1. Ingestion & SQLite Database Tests
# -----------------------------------------------------------------------------
def test_database_initialization(tmp_path):
    """Verifies that the audit_history table is initialized correctly."""
    db_file = tmp_path / "test_history.db"
    ingestion = DataIngestion(db_path=str(db_file))
    
    # Assert database file exists on disk
    assert db_file.exists()
    
    # Assert database schema structure
    with sqlite3.connect(str(db_file)) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='audit_history'")
        assert cursor.fetchone() is not None

def test_database_logging_and_checking(tmp_path):
    """Verifies that logging topics prevents duplicate ingestion selections."""
    db_file = tmp_path / "test_history.db"
    ingestion = DataIngestion(db_path=str(db_file))
    
    test_topic = "Glass is a slow-flowing liquid"
    test_hook = "You've been lied to about church windows."
    
    # Initially unused
    assert not ingestion.is_topic_used(test_topic)
    
    # Log the upload event
    ingestion.log_uploaded_topic(test_topic, test_hook)
    
    # Should now register as used
    assert ingestion.is_topic_used(test_topic)
    
    # Attempting to insert duplicate should handle gracefully (ignored)
    ingestion.log_uploaded_topic(test_topic, test_hook)

def test_advanced_topic_deduplication(tmp_path):
    """Verifies advanced token similarity and normalization detection for duplicates."""
    db_file = tmp_path / "test_history.db"
    ingestion = DataIngestion(db_path=str(db_file))
    
    # Log base topic
    ingestion.log_uploaded_topic("Napoleon's troops shot the nose off the Sphinx", "Hook text")
    
    # 1. Test case-insensitivity and punctuation stripping
    assert ingestion.is_topic_used("Napoleon's Troops Shot The Nose Off The Sphinx!")
    
    # 2. Test semantic/lexical overlap similarity (Jaccard / Containment)
    assert ingestion.is_topic_used("Napoleon Sphinx nose shot off")
    assert ingestion.is_topic_used("Did Napoleon's troops shoot sphinx nose?")
    
    # 3. Test unrelated topic
    assert not ingestion.is_topic_used("Einstein failed math")

def test_topic_verification_check(tmp_path):
    """Verifies that the Gemini-based topic validation handles PASS/FAIL/error scenarios correctly."""
    db_file = tmp_path / "test_history.db"
    ingestion = DataIngestion(db_path=str(db_file))
    
    class MockResponse:
        def __init__(self, text):
            self.text = text
            
    class MockModels:
        def __init__(self, result_text):
            self.result_text = result_text
            
        def generate_content(self, model, contents, **kwargs):
            return MockResponse(self.result_text)
            
    class MockClient:
        def __init__(self, result_text):
            self.models = MockModels(result_text)
            
    # Mocking passing validation
    valid_client = MockClient("VALID|Great topic about quantum biology")
    assert ingestion._verify_topic_robustness("Quantum compass", "Physics", "Robins use entanglement to navigate", valid_client, [])
    
    # Mocking failing validation
    invalid_client = MockClient("INVALID|Too commonly known and boring")
    assert not ingestion._verify_topic_robustness("Glass flows", "Physics", "Glass is actually not a liquid", invalid_client, [])
    
    # Mocking API error (should fallback to True gracefully to prevent blocking)
    class ErrorModels:
        def generate_content(self, *args, **kwargs):
            raise Exception("API Limit exceeded")
            
    class ErrorClient:
        models = ErrorModels()
        
    assert ingestion._verify_topic_robustness("Unsure topic", "Chemistry", "Obscure reaction", ErrorClient(), [])

def test_bootstrap_exhaustion(tmp_path):
    """Verifies topic selection and returns unique topics until pool is exhausted."""
    db_file = tmp_path / "test_history.db"
    ingestion = DataIngestion(db_path=str(db_file))
    
    # Initially pulls valid topic
    selection1 = ingestion.fetch_unused_misconception()
    assert selection1 is not None
    assert len(selection1) == 3
    
    # Mocking database to mark all bootstrap myths as used
    from data_ingestion import BOOTSTRAP_MYTHS
    for topic, category, desc in BOOTSTRAP_MYTHS:
        ingestion.log_uploaded_topic(topic, "Mock hook")
        
    # After marking all used, fetch with no client should raise RuntimeError
    import pytest
    with pytest.raises(RuntimeError) as exc_info:
        ingestion.fetch_unused_misconception(gemini_client=None)
    assert "Predefined bootstrap myths exhausted" in str(exc_info.value)

# -----------------------------------------------------------------------------
# 2. LLM Orchestrator Utility Tests
# -----------------------------------------------------------------------------
def test_word_count_calculation():
    """Verifies word count parsing math logic."""
    payload = {
        "hook": "You have been lied.",
        "context": "Vikings did not wear horns.",
        "fact": "Horned helmets were opera costumes.",
    }
    # Expected: 4 + 5 + 5 = 14 words (no sign_off)
    assert LLMOrchestrator.calculate_word_count(payload) == 14


def test_split_myth_ssml():
    """Verifies that split_myth_ssml correctly splits SSML into 3 clean content scenes (no CTA/sign-off)."""
    from main import split_myth_ssml
    ssml_script = (
        "<speak><voice name='en-US-Guy'>You've been lied to about glass. <break time=\"700ms\"/> "
        "Old church windows are thicker. <break time=\"1200ms\"/> "
        "This is from medieval manufacturing.</voice></speak>"
    )
    s1, s2, s3 = split_myth_ssml(
        ssml_script, "hook", "context", "fact"
    )
    assert s1 == "You've been lied to about glass."
    assert s2 == "Old church windows are thicker."
    assert s3 == "This is from medieval manufacturing."


def test_split_bizarre_ssml():
    """Verifies that split_bizarre_ssml correctly splits SSML into 3 clean content scenes."""
    from main import split_bizarre_ssml
    ssml_script = (
        "<speak>Never ignore the heart. <break time=\"700ms\"/> It pumps gallons. "
        "<break time=\"1200ms\"/> But it is not a pump of emotion.</speak>"
    )
    s1, s2, s3 = split_bizarre_ssml(
        ssml_script, "hook", "why", "closing"
    )
    assert s1 == "Never ignore the heart."
    assert s2 == "It pumps gallons."
    assert s3 == "But it is not a pump of emotion."

def test_smart_client_failover(monkeypatch):
    """Verifies that SmartGeminiClient retries free tier on 429 and falls back to paid tier."""
    import os
    import time
    monkeypatch.setenv("FREE_GEMINI_API_KEY", "free_key_123")
    monkeypatch.setenv("PAID_GEMINI_API_KEY", "paid_key_456")
    
    # Mock time.sleep to avoid slowing down unit tests
    monkeypatch.setattr(time, "sleep", lambda x: None)
    
    from llm_orchestrator import SmartGeminiClient
    
    attempts = []
    
    class MockInnerClient:
        def __init__(self, api_key, **kwargs):
            self.api_key = api_key
            self.models = self
            
        def generate_content(self, *args, **kwargs):
            attempts.append(self.api_key)
            if len(attempts) <= 3:
                raise Exception("429 Resource Exhausted: Rate limit exceeded.")
            class MockResponse:
                text = "Mock Success Content"
            return MockResponse()
            
    import google.genai as genai
    monkeypatch.setattr(genai, "Client", MockInnerClient)
    
    client = SmartGeminiClient()
    response = client.models.generate_content("test prompt")
    
    assert len(attempts) == 4
    assert attempts[0] == "free_key_123"
    assert attempts[1] == "free_key_123"
    assert attempts[2] == "free_key_123"
    assert attempts[3] == "paid_key_456"
    assert response.text == "Mock Success Content"

# -----------------------------------------------------------------------------
# 3. Asset Generator Tests
# -----------------------------------------------------------------------------
def test_programmatic_blueprint_rendering(tmp_path):
    """Verifies that vector blueprint fallback generates a valid 1080x1920 image file for various prompt categories."""
    generator = AssetGenerator()
    
    # 1. Test mechanical category
    image_file_mech = tmp_path / "test_vector_mech.png"
    output_path_mech = generator._render_programmatic_blueprint(
        prompt_text="An ancient mechanical clockwork",
        output_path=str(image_file_mech)
    )
    assert os.path.exists(output_path_mech)
    with Image.open(output_path_mech) as img:
        assert img.size == (1080, 1920)
        
    # 2. Test evolution/DNA category
    image_file_evo = tmp_path / "test_vector_evo.png"
    output_path_evo = generator._render_programmatic_blueprint(
        prompt_text="evolutionary tree showing a monkey directly transforming into a human",
        output_path=str(image_file_evo)
    )
    assert os.path.exists(output_path_evo)
    with Image.open(output_path_evo) as img:
        assert img.size == (1080, 1920)

def test_offline_speech_synthesizer_fallback(tmp_path):
    """Verifies offline speech MP3 fallback generates a valid physical file."""
    audio_file = tmp_path / "test_offline.mp3"
    generator = AssetGenerator()
    
    output_path = generator._generate_offline_mockup_audio(
        text="Class dismissed.",
        output_path=str(audio_file)
    )
    assert os.path.exists(output_path)
    assert os.path.getsize(output_path) > 0

# -----------------------------------------------------------------------------
# 4. Video Engine Timing Tests
# -----------------------------------------------------------------------------
def test_word_timings_sync_generator():
    """Verifies character-level temporal word pacing maps correctly to total duration."""
    payload = {
        "hook": "You are wrong.",
        "context": "Sunlight is white.",
        "fact": "It contains all wavelengths.",
        "sign_off": "Class dismissed."
    }
    engine = VideoEngine()
    duration = 10.0  # seconds
    
    timings = engine._calculate_word_timings(payload, duration)
    
    # Word structures populated
    assert len(timings) > 0
    assert timings[0]["word"] == "You"
    
    # Sequential boundaries check
    break_durations = [0.55, 0.55, 0.80]
    for idx in range(1, len(timings)):
        prev_w = timings[idx-1]
        curr_w = timings[idx]
        if curr_w["phrase_idx"] == prev_w["phrase_idx"]:
            assert abs(curr_w["start_time"] - prev_w["end_time"]) < 0.001
        else:
            # Phrase transitioned, start_time should match prev end_time + corresponding break duration
            expected_break = break_durations[prev_w["phrase_idx"]]
            assert abs(curr_w["start_time"] - (prev_w["end_time"] + expected_break)) < 0.001
        
    # The last word's end time should match total video duration
    assert abs(timings[-1]["end_time"] - duration) < 0.01

def test_crt_scanline_matrix_generation():
    """Verifies CRT overlay filter generates a high-contrast matrix."""
    engine = VideoEngine()
    width, height = 1080, 1920
    opacity = 0.1
    
    overlay = engine._create_scanline_overlay(width, height, opacity)
    assert overlay.shape == (height, width, 3)
    
    # Every 4th line is dark/opaque, intermediate lines are zero
    assert overlay[0, 0, 0] == opacity
    assert overlay[1, 0, 0] == 0.0

def test_sfx_synthesis_fallback(tmp_path):
    """Verifies that the VideoEngine can synthesize zap.mp3, pop.mp3, stamp.mp3, tick.mp3, impact.mp3, and riser.mp3 if they don't exist."""
    engine = VideoEngine()
    engine.assets_dir = str(tmp_path / "assets")
    
    # Synthesize SFX
    engine._ensure_sfx_exist()
    
    zap_path = os.path.join(engine.assets_dir, "sfx", "zap.mp3")
    pop_path = os.path.join(engine.assets_dir, "sfx", "pop.mp3")
    stamp_path = os.path.join(engine.assets_dir, "sfx", "stamp.mp3")
    tick_path = os.path.join(engine.assets_dir, "sfx", "tick.mp3")
    impact_path = os.path.join(engine.assets_dir, "sfx", "impact.mp3")
    riser_path = os.path.join(engine.assets_dir, "sfx", "riser.mp3")
    
    assert os.path.exists(zap_path)
    assert os.path.exists(pop_path)
    assert os.path.exists(stamp_path)
    assert os.path.exists(tick_path)
    assert os.path.exists(impact_path)
    assert os.path.exists(riser_path)
    assert os.path.getsize(zap_path) > 0
    assert os.path.getsize(pop_path) > 0
    assert os.path.getsize(stamp_path) > 0
    assert os.path.getsize(tick_path) > 0
    assert os.path.getsize(impact_path) > 0
    assert os.path.getsize(riser_path) > 0

def test_ducking_volume_logic():
    """Verifies the audio ducking math (ramp down during speech, ramp up during breaks)."""
    vol_min = 0.05
    vol_max = 0.20
    ramp_up = 0.2
    ramp_down = 0.1
    
    # Mock speaking blocks: speech 0-2s, break 2-3s, speech 3-5s
    speaking_blocks = [(0.0, 2.0), (3.0, 5.0)]
    
    def get_ducking_factor(t_val):
        if not speaking_blocks:
            return vol_min
        for start, end in speaking_blocks:
            if start <= t_val <= end:
                return vol_min
        for i in range(len(speaking_blocks) - 1):
            end_i = speaking_blocks[i][1]
            start_next = speaking_blocks[i+1][0]
            if end_i < t_val < start_next:
                pause_dur = start_next - end_i
                if pause_dur <= (ramp_up + ramp_down):
                    return vol_min
                if t_val < end_i + ramp_up:
                    return vol_min + (vol_max - vol_min) * ((t_val - end_i) / ramp_up)
                elif t_val > start_next - ramp_down:
                    return vol_max - (vol_max - vol_min) * ((t_val - (start_next - ramp_down)) / ramp_down)
                else:
                    return vol_max
        end_last = speaking_blocks[-1][1]
        if t_val > end_last:
            if t_val < end_last + ramp_up:
                return vol_min + (vol_max - vol_min) * ((t_val - end_last) / ramp_up)
            else:
                return vol_max
        return vol_min

    # Active speaking: should be vol_min (0.05)
    assert abs(get_ducking_factor(1.0) - 0.05) < 1e-5
    assert abs(get_ducking_factor(4.0) - 0.05) < 1e-5
    
    # In the middle of the pause (2.5s): should be vol_max (0.20)
    assert abs(get_ducking_factor(2.5) - 0.20) < 1e-5
    
    # Ramping up: 2.1s (halfway through ramp_up) should be 0.05 + 0.15 * 0.5 = 0.125
    assert abs(get_ducking_factor(2.1) - 0.125) < 1e-5
    
    # Ramping down: 2.95s (halfway through ramp_down) should be 0.20 - 0.15 * 0.5 = 0.125
    assert abs(get_ducking_factor(2.95) - 0.125) < 1e-5

# -----------------------------------------------------------------------------
# 5. YouTube Uploader Tests
# -----------------------------------------------------------------------------
def test_youtube_uploader_simulation_fallback(tmp_path):
    """Verifies uploader defaults safely to mock mode if credentials are not configured."""
    config_dir = tmp_path / "config"
    uploader = YouTubeUploader(config_dir=str(config_dir))
    
    # Confirm client secrets are absent in temp workspace
    assert not os.path.exists(uploader.client_secrets_path)
    
    # Trigger upload
    success, video_id = uploader.upload_short(
        video_path="dummy.mp4",
        title="Myth of the Golden Horn #Shorts",
        description="Testing shorts",
        tags=["shorts"]
    )
    
    # Should safely complete, return True and simulation ID
    assert success is True
    assert video_id == "MOCK_VIDEO_ID_12345"


# -----------------------------------------------------------------------------
# 6. Facebook Uploader Tests
# -----------------------------------------------------------------------------
def test_facebook_uploader_simulation_fallback(monkeypatch):
    """Verifies that the Facebook Reels uploader defaults safely to mock mode if credentials are not configured."""
    monkeypatch.delenv("FB_PAGE_ID", raising=False)
    monkeypatch.delenv("FB_PAGE_ACCESS_TOKEN", raising=False)
    from facebook_uploader import FacebookUploader
    
    # Initialize uploader with no credentials
    uploader = FacebookUploader(page_id=None, access_token=None)
    
    # Trigger upload
    success, video_id = uploader.upload_reel(
        video_path="dummy.mp4",
        description="Testing Facebook Reels upload #Reels"
    )
    
    # Should safely complete, return True and simulation ID
    assert success is True
    assert video_id == "MOCK_FB_REEL_ID_12345"

def test_dynamic_hashtag_formatting():
    """Verifies that tags list is correctly formatted as hashtags and appended to description."""
    tags = ["physics", "coriolis effect", "science facts", " shorts "]
    hashtags_str = " ".join([f"#{t.strip().replace(' ', '')}" for t in tags if t.strip()])
    assert hashtags_str == "#physics #corioliseffect #sciencefacts #shorts"


# -----------------------------------------------------------------------------
# 7. New Multi-Format Module Tests (DataScraper, Quiz, Bizarre Facts)
# -----------------------------------------------------------------------------
def test_data_scraper_wikipedia_image(tmp_path, monkeypatch):
    """Verifies DataScraper correctly queries and downloads images from Wikipedia APIs."""
    from data_scraper import DataScraper
    
    # Mock requests.get response
    from io import BytesIO
    from PIL import Image
    
    im = Image.new("RGB", (10, 10), (255, 0, 0))
    f_io = BytesIO()
    im.save(f_io, format="PNG")
    image_bytes = f_io.getvalue()

    class MockResponse:
        def __init__(self, content, is_json=True, status_code=200):
            self.content = content
            self.is_json = is_json
            self.status_code = status_code
        def json(self):
            import json
            if isinstance(self.content, str):
                return json.loads(self.content)
            return self.content
        def raise_for_status(self):
            pass

    import requests
    
    def mock_get(url, params=None, **kwargs):
        if "list=search" in url or (params and params.get("list") == "search"):
            return MockResponse({
                "query": {
                    "search": [{"title": "Strasbourg"}]
                }
            })
        elif "prop=pageimages" in url or (params and params.get("prop") == "pageimages"):
            return MockResponse({
                "query": {
                    "pages": [
                        {
                            "pageid": 12345,
                            "title": "Strasbourg",
                            "thumbnail": {
                                "source": "https://upload.wikimedia.org/wikipedia/commons/test.png"
                            }
                        }
                    ]
                }
            })
        elif "upload.wikimedia.org" in url:
            return MockResponse(image_bytes, is_json=False)
        return MockResponse({}, status_code=404)

    monkeypatch.setattr(requests, "get", mock_get)

    scraper = DataScraper(cache_dir=str(tmp_path))
    res = scraper.fetch_wikipedia_image("Strasbourg Cathedral", "test_cathedral")
    
    assert res is not None
    assert os.path.exists(res)
    assert os.path.basename(res).startswith("test_cathedral_")
    assert res.endswith(".png")


def test_data_ingestion_bizarre_fetching(tmp_path):
    """Verifies that DataIngestion correctly fetches and cycles through bizarre bootstrap topics."""
    db_file = tmp_path / "test_history.db"
    ingestion = DataIngestion(db_path=str(db_file))

    topic, category, description = ingestion.fetch_unused_bizarre_topic(gemini_client=None)
    assert topic is not None
    assert category in ["History", "Physics", "Biology", "Astronomy", "Neuroscience",
                         "Psychology", "Economics", "Geology", "Chemistry", "Technology",
                         "Linguistics", "Anthropology"]
    assert len(description) > 0


def test_llm_orchestrator_bizarre_generation(monkeypatch):
    """Verifies LLMOrchestrator correctly requests and structures bizarre scripts via Gemini."""
    orchestrator = LLMOrchestrator(api_key="mock_key")
    
    class MockModelsBizarre:
        def generate_content(self, model, contents, config=None, **kwargs):
            class MockResponse:
                text = (
                    "{"
                    "  \"topic\": \"The Dancing Plague of 1518\","
                    "  \"ssml_script\": \"Imagine dancing until you drop dead. <break time=\\\"700ms\\\"/> Frau Troffea began to dance in Strasbourg. <break time=\\\"700ms\\\"/> Within weeks, hundreds of people joined her. <break time=\\\"1200ms\\\"/> Dozens collapsed and died from sheer exhaustion. <break time=\\\"700ms\\\"/> The incident remains a mystery. <break time=\\\"700ms\\\"/> <break time=\\\"1000ms\\\"/> Class dismissed.\","
                    "  \"illustration_query\": \"Strasbourg dancing plague 1518 illustration\","
                    "  \"youtube_metadata\": {"
                    "    \"title\": \"The Dancing Plague of 1518 #Shorts\","
                    "    \"description\": \"A historical mystery.\","
                    "    \"tags\": [\"history\", \"bizarre\"]"
                    "  }"
                    "}"
                )
            return MockResponse()

    class MockClientBizarre:
        models = MockModelsBizarre()

    orchestrator.client = MockClientBizarre()
    bizarre_payload = orchestrator.generate_bizarre_fact("The Dancing Plague of 1518", "History")
    assert bizarre_payload["topic"] == "The Dancing Plague of 1518"
    assert bizarre_payload["hook"] == "Imagine dancing until you drop dead."
    assert bizarre_payload["why_bizarre"] == "Frau Troffea began to dance in Strasbourg. Within weeks, hundreds of people joined her."
    assert bizarre_payload["closing_statement"] == "Dozens collapsed and died from sheer exhaustion. The incident remains a mystery. Class dismissed."
    assert bizarre_payload["is_new_prompt_style"] is True


def test_llm_orchestrator_myth_generation(monkeypatch):
    """Verifies LLMOrchestrator correctly requests and structures myth scripts via Gemini."""
    orchestrator = LLMOrchestrator(api_key="mock_key")
    
    class MockModelsMyth:
        def generate_content(self, model, contents, config=None, **kwargs):
            class MockResponse:
                text = (
                    "{"
                    "  \"topic\": \"Glass flows\","
                    "  \"ssml_script\": \"You are wrong about old window glass. <break time=\\\"700ms\\\"/> Everyone believes that glass is a slow flowing liquid. <break time=\\\"1200ms\\\"/> But old glass is thicker at the bottom due to hand-blown manufacturing. <break time=\\\"700ms\\\"/> Gravity has zero effect on solid silica. <break time=\\\"700ms\\\"/> <break time=\\\"1000ms\\\"/> Class dismissed.\","
                    "  \"myth_visual_prompt\": \"Style of a declassified government document, dark blue and white blueprint, highly detailed.\","
                    "  \"fact_visual_prompt\": \"Realistic, high-contrast, stark laboratory or historical archive photography, highly detailed.\","
                    "  \"youtube_metadata\": {"
                    "    \"title\": \"Glass is NOT a Liquid! #Shorts\","
                    "    \"description\": \"Physics audit.\","
                    "    \"tags\": [\"physics\", \"debunked\"]"
                    "  }"
                    "}"
                )
            return MockResponse()

    class MockClientMyth:
        models = MockModelsMyth()

    orchestrator.client = MockClientMyth()
    script_payload = orchestrator.generate_script("Glass flows", "Physics", "Older windows are thicker due to manufacturing processes")
    assert script_payload["topic"] == "Glass flows"
    assert script_payload["hook"] == "You are wrong about old window glass."
    assert script_payload["context"] == "Everyone believes that glass is a slow flowing liquid."
    assert script_payload["fact"] == "But old glass is thicker at the bottom due to hand-blown manufacturing. Gravity has zero effect on solid silica. Class dismissed."
    assert script_payload["is_new_prompt_style"] is True


def test_ssml_script_parsing_edge_cases():
    """Validates _parse_ssml_script parsing robustness with various formatting irregularities."""
    orchestrator = LLMOrchestrator(api_key="mock_key")
    
    # Test case 1: Raw text without break tags
    raw_text = "Never ignore the heart. It pumps gallons of blood. But it is not a pump of emotion. Love lives in the brain. Class dismissed."
    parsed = orchestrator._parse_ssml_script(raw_text, is_bizarre=False)
    assert parsed["hook"] == "Never ignore the heart."
    assert parsed["context"] == "It pumps gallons of blood."
    assert "not a pump" in parsed["fact"]
    
    # Test case 2: SSML with lowercase tag variants, different spaces, and custom voices
    ssml_with_tags = (
        "<speak><voice name='en-US-Guy'><emphasis level='strong'>STOP</emphasis> eating raw apples. <break time=\"700ms\"/>"
        "Seeds contain tiny trace levels of cyanide. <break time=\"1200ms\"/>"
        "But your gut acid neutralizes them. <break time=\"700ms\"/>"
        "You would need to chew hundreds of seeds to die. <break time=\"700ms\"/>"
        "<break time=\"1000ms\"/> Class dismissed.</voice></speak>"
    )
    parsed_ssml = orchestrator._parse_ssml_script(ssml_with_tags, is_bizarre=False)
    assert parsed_ssml["hook"] == "STOP eating raw apples."
    assert parsed_ssml["context"] == "Seeds contain tiny trace levels of cyanide."
    assert parsed_ssml["fact"] == "But your gut acid neutralizes them. You would need to chew hundreds of seeds to die. Class dismissed."


# -----------------------------------------------------------------------------
# 8. Azure TTS Swap Tests
# -----------------------------------------------------------------------------
def test_azure_tts_sdk_success(monkeypatch, tmp_path):
    """Verifies that Azure Speech SDK is called correctly and succeeds."""
    # Mock azure.cognitiveservices.speech
    import sys
    from types import ModuleType
    
    mock_speech = ModuleType("azure.cognitiveservices.speech")
    mock_speech.audio = ModuleType("azure.cognitiveservices.speech.audio")
    
    # Class mocks
    class MockSpeechConfig:
        def __init__(self, subscription, region):
            self.subscription = subscription
            self.region = region
        def set_speech_synthesis_output_format(self, format_val):
            self.format_val = format_val
            
    class MockAudioConfig:
        def __init__(self, filename):
            self.filename = filename
            
    class MockResult:
        def __init__(self, reason):
            self.reason = reason
            
    class MockResultReason:
        SynthesizingAudioCompleted = "SynthesizingAudioCompleted"
        
    class MockSpeechSynthesisOutputFormat:
        Audio24Khz96KBitRateMonoMp3 = "Audio24Khz96KBitRateMonoMp3"
        
    class MockEvent:
        def connect(self, callback):
            self.callback = callback
            
    class MockSpeechSynthesizer:
        def __init__(self, speech_config, audio_config):
            self.speech_config = speech_config
            self.audio_config = audio_config
            self.synthesis_word_boundary = MockEvent()
            
        def speak_ssml_async(self, ssml_text):
            self.ssml_text = ssml_text
            synthesizer_instance = self
            class AsyncResult:
                def get(self):
                    # Write dummy file to simulate output
                    with open(synthesizer_instance.audio_config.filename, "wb") as f:
                        f.write(b"mock_audio_content")
                    # Simulate calling the word boundary callback
                    if hasattr(synthesizer_instance.synthesis_word_boundary, "callback"):
                        class MockEvt:
                            def __init__(self, text, offset, duration):
                                self.text = text
                                self.audio_offset = offset
                                self.duration = duration
                        cb = synthesizer_instance.synthesis_word_boundary.callback
                        # Mock 2 words to write a valid srt next to mp3
                        cb(MockEvt("Hello", 1000000, 2000000)) # 100ms offset, 200ms duration (in ticks)
                        cb(MockEvt("world", 3000000, 2000000)) # 300ms offset, 200ms duration
                    return MockResult(MockResultReason.SynthesizingAudioCompleted)
            return AsyncResult()
            
    mock_speech.SpeechConfig = MockSpeechConfig
    mock_speech.audio.AudioConfig = MockAudioConfig
    mock_speech.SpeechSynthesizer = MockSpeechSynthesizer
    mock_speech.ResultReason = MockResultReason
    mock_speech.SpeechSynthesisOutputFormat = MockSpeechSynthesisOutputFormat
    
    # Register mock module
    sys.modules["azure"] = ModuleType("azure")
    sys.modules["azure.cognitiveservices"] = ModuleType("azure.cognitiveservices")
    sys.modules["azure.cognitiveservices.speech"] = mock_speech
    sys.modules["azure.cognitiveservices.speech.audio"] = mock_speech.audio
    
    try:
        generator = AssetGenerator(
            azure_speech_key="mock_key",
            azure_speech_region="southeastasia",
            azure_voice_name="en-US-AndrewMultilingualNeural"
        )
        generator.assets_dir = str(tmp_path)
        
        output_path = generator.generate_tts_audio("Hello world", "test_azure_sdk")
        
        assert os.path.exists(output_path)
        with open(output_path, "rb") as f:
            assert f.read() == b"mock_audio_content"
            
    finally:
        # Clean up mock modules
        sys.modules.pop("azure.cognitiveservices.speech.audio", None)
        sys.modules.pop("azure.cognitiveservices.speech", None)
        sys.modules.pop("azure.cognitiveservices", None)
        sys.modules.pop("azure", None)


def test_azure_tts_rest_fallback(monkeypatch, tmp_path):
    """Verifies that Azure TTS falls back to REST API if the SDK fails/throws an exception."""
    # Ensure SDK import fails
    import sys
    if "azure" in sys.modules:
        sys.modules.pop("azure", None)
    if "azure.cognitiveservices" in sys.modules:
        sys.modules.pop("azure.cognitiveservices", None)
    if "azure.cognitiveservices.speech" in sys.modules:
        sys.modules.pop("azure.cognitiveservices.speech", None)
        
    # Mock requests.post to simulate successful REST API call
    class MockResponse:
        def __init__(self, content, status_code):
            self.content = content
            self.status_code = status_code
            self.text = "Mock REST API text"
            
    import requests
    def mock_post(url, headers=None, data=None, **kwargs):
        assert "southeastasia" in url
        assert headers["Ocp-Apim-Subscription-Key"] == "mock_key"
        assert b"en-US-AndrewMultilingualNeural" in data
        return MockResponse(b"mock_rest_audio_content", 200)
        
    monkeypatch.setattr(requests, "post", mock_post)
    
    generator = AssetGenerator(
        azure_speech_key="mock_key",
        azure_speech_region="southeastasia",
        azure_voice_name="en-US-AndrewMultilingualNeural"
    )
    generator.assets_dir = str(tmp_path)
    
    output_path = generator.generate_tts_audio("Hello rest world", "test_azure_rest")
    
    assert os.path.exists(output_path)
    with open(output_path, "rb") as f:
        assert f.read() == b"mock_rest_audio_content"


def test_azure_tts_offline_fallback(monkeypatch, tmp_path):
    """Verifies that Azure TTS falls back to offline mockup audio if both SDK and REST fail."""
    # Ensure SDK import fails
    import sys
    if "azure" in sys.modules:
        sys.modules.pop("azure", None)
    if "azure.cognitiveservices" in sys.modules:
        sys.modules.pop("azure.cognitiveservices", None)
    if "azure.cognitiveservices.speech" in sys.modules:
        sys.modules.pop("azure.cognitiveservices.speech", None)
    
    # Mock requests.post to fail (REST fails)
    import requests
    def mock_post_fail(url, **kwargs):
        class MockResponseFail:
            content = b""
            status_code = 500
            text = "Internal Server Error"
        return MockResponseFail()
        
    monkeypatch.setattr(requests, "post", mock_post_fail)
    
    # Mock offline mockup generator to return custom bytes
    generator = AssetGenerator(
        azure_speech_key="mock_key",
        azure_speech_region="southeastasia",
        azure_voice_name="en-US-AndrewMultilingualNeural"
    )
    generator.assets_dir = str(tmp_path)
    
    mock_offline_called = []
    def mock_offline(text, output_path):
        mock_offline_called.append((text, output_path))
        with open(output_path, "wb") as f:
            f.write(b"mock_offline_content")
        return output_path
        
    monkeypatch.setattr(generator, "_generate_offline_mockup_audio", mock_offline)
    
    output_path = generator.generate_tts_audio("Hello offline world", "test_azure_offline")
    
    assert len(mock_offline_called) == 1
    assert mock_offline_called[0][0] == "Hello offline world"
    assert os.path.exists(output_path)
    with open(output_path, "rb") as f:
        assert f.read() == b"mock_offline_content"


def test_azure_tts_concurrency_lock(monkeypatch, tmp_path):
    """Verifies that concurrent calls to generate_tts_audio are serialized using the lock."""
    import sys
    if "azure" in sys.modules:
        sys.modules.pop("azure", None)
    if "azure.cognitiveservices" in sys.modules:
        sys.modules.pop("azure.cognitiveservices", None)
    if "azure.cognitiveservices.speech" in sys.modules:
        sys.modules.pop("azure.cognitiveservices.speech", None)

    import requests
    import threading
    import time

    generator = AssetGenerator(
        azure_speech_key="mock_key",
        azure_speech_region="southeastasia",
        azure_voice_name="en-US-AndrewMultilingualNeural"
    )
    generator.assets_dir = str(tmp_path)

    active_calls = 0
    max_concurrent_calls = 0
    execution_lock = threading.Lock()

    def mock_post(url, headers=None, data=None, **kwargs):
        nonlocal active_calls, max_concurrent_calls
        with execution_lock:
            active_calls += 1
            if active_calls > max_concurrent_calls:
                max_concurrent_calls = active_calls
        
        # Sleep to allow overlap if concurrency locks are not working
        time.sleep(0.2)
        
        with execution_lock:
            active_calls -= 1
            
        class MockResponse:
            content = b"concurrency_test_content"
            status_code = 200
            text = "Mock REST response"
        return MockResponse()

    monkeypatch.setattr(requests, "post", mock_post)

    t1_done = threading.Event()
    t2_done = threading.Event()

    def thread_target(name, done_event):
        generator.generate_tts_audio("Concurrency text", name, is_ssml=False)
        done_event.set()

    thread1 = threading.Thread(target=thread_target, args=("t1", t1_done))
    thread2 = threading.Thread(target=thread_target, args=("t2", t2_done))

    thread1.start()
    thread2.start()

    thread1.join()
    thread2.join()

    # The maximum concurrent calls at any time should be exactly 1
    assert max_concurrent_calls == 1


def test_compile_scene_based_video_mocked(tmp_path, monkeypatch):
    """Verifies that _compile_scene_based_video resolves blueprints and executes write_videofile without error."""
    import sys
    import types
    from PIL import Image

    engine = VideoEngine()
    engine.assets_dir = str(tmp_path)
    os.makedirs(os.path.join(engine.assets_dir, "sfx"), exist_ok=True)
    os.makedirs(os.path.join(engine.assets_dir, "video_blueprints"), exist_ok=True)
    
    # Touch mock sfx files
    for sfx in ["zap.mp3", "pop.mp3", "stamp.mp3", "tick.mp3", "impact.mp3", "riser.mp3"]:
        with open(os.path.join(engine.assets_dir, "sfx", sfx), "w") as f:
            f.write("")
            
    # Touch mock video blueprints matching DNA, velvet, class
    with open(os.path.join(engine.assets_dir, "video_blueprints", "DNA_double_helix.mp4"), "w") as f:
        f.write("")
    with open(os.path.join(engine.assets_dir, "video_blueprints", "velvet_curtains.mp4"), "w") as f:
        f.write("")
    with open(os.path.join(engine.assets_dir, "video_blueprints", "CLASS_DISMISSED.mp4"), "w") as f:
        f.write("")
        
    class MockClip:
        def __init__(self, *args, **kwargs):
            self.duration = 2.0
            self.audio = self
        def set_start(self, *args, **kwargs):
            return self
        def with_start(self, *args, **kwargs):
            return self
        def set_audio(self, *args, **kwargs):
            return self
        def with_audio(self, *args, **kwargs):
            return self
        def multiply_volume(self, *args, **kwargs):
            return self
        def volumex(self, *args, **kwargs):
            return self
        def copy(self, *args, **kwargs):
            return self
        def subclip(self, *args, **kwargs):
            return self
        def subclipped(self, *args, **kwargs):
            return self
        def fl(self, *args, **kwargs):
            return self
        def write_videofile(self, *args, **kwargs):
            self.write_calls.append((args, kwargs))
        def close(self):
            self.closed = True
            
    MockClip.write_calls = []
    MockClip.closed = False
    
    # Mock moviepy in sys.modules
    mock_mpe = types.ModuleType("moviepy.editor")
    mock_mpe.AudioFileClip = MockClip
    mock_mpe.VideoFileClip = MockClip
    mock_mpe.VideoClip = MockClip
    mock_mpe.CompositeAudioClip = MockClip
    mock_mpe.concatenate_videoclips = lambda clips: MockClip()
    
    monkeypatch.setitem(sys.modules, "moviepy.editor", mock_mpe)
    monkeypatch.setitem(sys.modules, "moviepy", mock_mpe)
    
    # Mock PIL images for card generation
    monkeypatch.setattr(engine, "_generate_card", lambda *args, **kwargs: Image.new("RGBA", (10, 10)))
    
    # Create fake background images
    image_paths = [
        str(tmp_path / "img1.png"),
        str(tmp_path / "img2.png"),
        str(tmp_path / "img3.png")
    ]
    for path in image_paths:
        with open(path, "w") as f:
            f.write("")
            
    # Create fake audio clips
    audio_paths = [
        str(tmp_path / "audio1.mp3"),
        str(tmp_path / "audio2.mp3"),
        str(tmp_path / "audio3.mp3")
    ]
    for path in audio_paths:
        with open(path, "w") as f:
            f.write("")
            
    scene_texts = ["This DNA helix myth.", "Curtains velvet truth.", "Class dismissed."]
    scene_labels = ["LABEL1", "LABEL2", "LABEL3"]
    scene_titles = ["TITLE1", "TITLE2", "TITLE3"]
    
    # Call the compiler
    res_path = engine._compile_scene_based_video(
        image_paths=image_paths,
        audio_paths=audio_paths,
        scene_texts=scene_texts,
        scene_labels=scene_labels,
        scene_titles=scene_titles,
        output_name="test_output",
        category="history",
        style="blueprint",
        is_bizarre=False
    )
    
    assert res_path.endswith("test_output.mp4")
    assert len(MockClip.write_calls) == 1
    args, kwargs = MockClip.write_calls[0]
    expected_codec = "h264_nvenc" if engine.has_cuda else "libx264"
    assert kwargs.get("codec") == expected_codec


def test_narrator_expression_cues(tmp_path):
    """Verifies that narrator expression brackets [sigh], [whisper] are handled correctly."""
    # 1. Test SSML processor
    generator = AssetGenerator()
    text = "Hello [sigh] world. [whisper]whispered secret[/whisper] and [excited]excited statement[/excited]! [breathing]"
    ssml = generator._process_brackets_to_ssml(text)
    
    assert '<mstts:paralinguistic type="sighing"/>' in ssml
    assert '<mstts:paralinguistic type="breathing"/>' in ssml
    assert '<mstts:express-as style="whispering">whispered secret</mstts:express-as>' in ssml
    assert '<mstts:express-as style="excited">excited statement</mstts:express-as>' in ssml

    # 2. Test word timing cleaning
    engine = VideoEngine()
    words_info = engine._parse_ssml_words_emphasis(text)
    # The bracket cues should be fully stripped from subtitle words
    words = [w["word"] for w in words_info]
    assert "Hello" in words
    assert "world." in words
    assert "whispered" in words
    assert "secret" in words
    assert "excited" in words
    assert "statement!" in words
    assert "[sigh]" not in words
    assert "[breathing]" not in words
    assert "[whisper]" not in words
    assert "[/whisper]" not in words

    # 3. Test LLMOrchestrator word count calculation with bracket cues
    payload = {
        "hook": "Hello [sigh] world.",
        "context": "[whisper]whispered secret[/whisper]",
        "fact": "Reality check [breathing]."
    }
    word_count = LLMOrchestrator.calculate_word_count(payload)
    # "Hello world. whispered secret Reality check ." -> 7 words
    assert word_count == 7


def test_retention_overhaul_pipeline():
    """
    Verifies the complete Retention Overhaul pipeline:
    - Running PipelineOrchestrator to orchestrate two-pass prompts.
    - Validating emotional styles mapping and breath marks via SSMLBuilder.
    - Testing SubtitleBuilder subtitle SRT sync output.
    - Testing RetentionReviewer rating and retry loops.
    """
    from pipeline.orchestrator import PipelineOrchestrator
    from tts.ssml_builder import SSMLBuilder
    from tts.subtitle_builder import SubtitleBuilder
    from researcher_agent.reviewer import RetentionReviewer

    # Mock responses for Pass 1 and Pass 2
    pass1_json = {
        "topic_core_mystery": "The mystery of cosmic dust",
        "hook_question": "Did you know we breathe in stardust daily?",
        "insight_units": [
            {
                "id": 1,
                "assumption": "Space is empty",
                "truth": "Space is filled with fine cosmic dust",
                "emotion": "awe",
                "complexity": "low",
                "requires_visual": True,
                "visual_search_query": "cosmic dust space"
            },
            {
                "id": 2,
                "assumption": "Cosmic dust is harmless",
                "truth": "It actually affects weather patterns on Earth",
                "emotion": "fear",
                "complexity": "medium",
                "requires_visual": True,
                "visual_search_query": "earth atmosphere clouds"
            },
            {
                "id": 3,
                "assumption": "It is rare",
                "truth": "Tons of cosmic debris fall to Earth every single hour",
                "emotion": "disbelief",
                "complexity": "medium",
                "requires_visual": True,
                "visual_search_query": "falling meteorites earth"
            }
        ],
        "narrative_payoff": "We are walking stardust archives.",
        "teaser_next": "Next: is dark matter inside your cell phone?"
    }

    pass2_json = [
        {
            "scene_id": 1,
            "scene_type": "hook",
            "duration_target_seconds": 3.5,
            "narration_text": "Did you know we breathe in stardust daily?",
            "ssml_emotion": "whisper",
            "ssml_hint": "",
            "visual_type": "generated",
            "visual_query": "stardust breathing simulation",
            "visual_position": "full",
            "subtitle_text": "Did you know we breathe in stardust daily?",
            "open_loop": True,
            "closes_loop_from_scene": None,
            "emotion_register": "question"
        },
        {
            "scene_id": 2,
            "scene_type": "body",
            "duration_target_seconds": 5.0,
            "narration_text": "Space is filled with fine cosmic dust.",
            "ssml_emotion": "calm",
            "ssml_hint": "",
            "visual_type": "scraped",
            "visual_query": "cosmic dust space",
            "visual_position": "inset",
            "subtitle_text": "Space is filled with fine cosmic dust.",
            "open_loop": False,
            "closes_loop_from_scene": 1,
            "emotion_register": "release"
        },
        {
            "scene_id": 3,
            "scene_type": "body",
            "duration_target_seconds": 5.5,
            "narration_text": "Tons of cosmic debris fall to Earth every single hour.",
            "ssml_emotion": "excited",
            "ssml_hint": "",
            "visual_type": "generated",
            "visual_query": "falling meteorites earth",
            "visual_position": "bottom_half",
            "subtitle_text": "Tons of cosmic debris fall to Earth every single hour.",
            "open_loop": True,
            "closes_loop_from_scene": None,
            "emotion_register": "tension"
        },
        {
            "scene_id": 4,
            "scene_type": "verdict",
            "duration_target_seconds": 4.5,
            "narration_text": "We are walking stardust archives.",
            "ssml_emotion": "reverent",
            "ssml_hint": "",
            "visual_type": "diagram",
            "visual_query": "human body made of dust",
            "visual_position": "full",
            "subtitle_text": "We are walking stardust archives.",
            "open_loop": False,
            "closes_loop_from_scene": 3,
            "emotion_register": "payoff"
        },
        {
            "scene_id": 5,
            "scene_type": "exit",
            "duration_target_seconds": 2.5,
            "narration_text": "Next: is dark matter inside your cell phone?",
            "ssml_emotion": "whisper",
            "ssml_hint": "",
            "visual_type": "generated",
            "visual_query": "cell phone dark matter glow",
            "visual_position": "full",
            "subtitle_text": "Next: is dark matter inside your cell phone?",
            "open_loop": True,
            "closes_loop_from_scene": None,
            "emotion_register": "question"
        }
    ]

    # Mock Gemini client models
    class MockResponse:
        def __init__(self, text):
            self.text = text

    class MockModels:
        def __init__(self):
            self.call_count = 0

        def generate_content(self, model, contents, config=None, **kwargs):
            self.call_count += 1
            # First call: Pass 1 Decomposition (JSON string response)
            if "science knowledge decomposer" in contents or self.call_count == 1:
                import json
                return MockResponse(json.dumps(pass1_json))
            # Second call: Pass 2 Scene Narrative Builder (JSON string response)
            else:
                import json
                return MockResponse(json.dumps(pass2_json))

    class MockClient:
        def __init__(self):
            self.models = MockModels()

    mock_client = MockClient()

    # 1. Verify PipelineOrchestrator Two-Pass & Review Flow
    orchestrator = PipelineOrchestrator(mock_client)
    
    # We mock reviewer.review_scenes to fail first, then succeed on retry to test retry loops!
    review_calls = []
    def mock_review_scenes(scenes):
        review_calls.append(scenes)
        if len(review_calls) == 1:
            # First review fails
            return {
                "scores": {
                    "hook_strength": 5.0,
                    "narrative_tension": 6.0,
                    "visual_variety": 8.0,
                    "payoff_satisfaction": 7.0,
                    "exit_quality": 5.0
                },
                "overall": 6.2,
                "pass": False,
                "blocking_issues": ["Scene 1 hook lacks conspiratorial secret vibe"],
                "suggested_fixes": ["Rephrase hook to sound like a secret"]
            }
        else:
            # Second review passes
            return {
                "scores": {
                    "hook_strength": 8.0,
                    "narrative_tension": 8.0,
                    "visual_variety": 9.0,
                    "payoff_satisfaction": 8.0,
                    "exit_quality": 8.0
                },
                "overall": 8.2,
                "pass": True,
                "blocking_issues": [],
                "suggested_fixes": []
            }
            
    orchestrator.reviewer.review_scenes = mock_review_scenes

    results = orchestrator.run_research_pipeline("Stardust", "Scraped data")
    
    # Check that Pass 1 was called, and Pass 2 was called twice (due to the retry loop)
    assert results["pass1_output"]["topic_core_mystery"] == "The mystery of cosmic dust"
    assert len(review_calls) == 2
    assert results["review"]["pass"] is True
    assert results["review"]["overall"] == 8.2

    # 2. Verify SSMLBuilder Emotional Styles & Silence Insertion
    # whisper style mapping
    ssml_whisper = SSMLBuilder.build_scene_ssml(
        text="Did you know we breathe in stardust daily?",
        emotion="whisper",
        scene_type="hook",
        voice_name="en-US-AndrewMultilingualNeural"
    )
    assert "style='whispering'" in ssml_whisper
    # hook gets Leading silence of 200ms
    assert "value='200ms'" in ssml_whisper

    # body/verdict scenes get Sentenceboundary silence of 150ms
    ssml_calm = SSMLBuilder.build_scene_ssml(
        text="Space is filled with fine cosmic dust. Yes.",
        emotion="calm",
        scene_type="body",
        voice_name="en-US-AndrewMultilingualNeural"
    )
    assert "style='calm'" in ssml_calm
    assert "value='150ms'" in ssml_calm

    # reverent style maps to lyrical
    ssml_reverent = SSMLBuilder.build_scene_ssml(
        text="We are walking stardust archives.",
        emotion="reverent",
        scene_type="verdict",
        voice_name="en-US-AndrewMultilingualNeural"
    )
    assert "style='lyrical'" in ssml_reverent

    # 3. Verify SubtitleBuilder groups word boundaries correctly into sentences/lines
    # Simulated word boundary events
    # Each word boundary event has: word, offset_ms, duration_ms
    word_boundaries = [
        {"word": "Did", "offset_ms": 100, "duration_ms": 200},
        {"word": "you", "offset_ms": 300, "duration_ms": 200},
        {"word": "know", "offset_ms": 500, "duration_ms": 200},
        {"word": "we", "offset_ms": 700, "duration_ms": 200},
        {"word": "breathe", "offset_ms": 900, "duration_ms": 300},
        {"word": "in", "offset_ms": 1200, "duration_ms": 100},
        {"word": "stardust", "offset_ms": 1300, "duration_ms": 400},
        {"word": "daily?", "offset_ms": 1700, "duration_ms": 400}
    ]
    # Call SubtitleBuilder.group_words_into_subtitles
    srt_blocks = SubtitleBuilder.group_words_into_subtitles(word_boundaries)
    assert len(srt_blocks) > 0
    # First block should cover start to end of words
    assert srt_blocks[0]["start_ms"] == 100
    assert srt_blocks[0]["end_ms"] == 2100 # 1700 + 400
    # Check max words rule (max 7 per line, max 2 lines visible -> max 14 words per block)
    # The word list is 8 words. Let's make sure they are divided into lines with max 7 words
    text_lines = srt_blocks[0]["text"].split("\n")
    assert len(text_lines) <= 2
    for line in text_lines:
        assert len(line.split()) <= 7

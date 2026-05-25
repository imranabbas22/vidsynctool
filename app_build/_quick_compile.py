"""Generate valid TTS assets and compile sample video."""
import os, json, subprocess, re, random
from video_engine import VideoEngine

BASE = r"C:\Users\imran\auto-youtube-project\app_build"
ASSETS = os.path.join(BASE, "assets")
TS = "demo_001"

# Clean up any broken files from partial run
for f in os.listdir(ASSETS):
    if TS in f:
        os.remove(os.path.join(ASSETS, f))

# The generated script
scenes = [
    ("start", "Declassified. Watch carefully.", 2.0),
    ("s1", "Okay, let's talk about your family tree. No, WAY further back. You've seen that classic picture, right? The ape that slowly stands up and turns into a human walking down the street. It's everywhere.", 12.0),
    ("s2", "So everyone just assumes we evolved FROM modern chimps, like they're our fuzzy, knuckle-walking grandparents who just... stopped evolving. But get this, chimpanzees have been on their own evolutionary journey for the exact same amount of time we have.", 14.0),
    ("s3", "We didn't evolve from them. We share a common ancestor. They're our cousins, not our grandparents. Big difference.", 5.0),
    ("end", "Case closed. Follow for tomorrow's declassified truth. CLASS DISMISSED.", 3.0),
]

# Step 1: Generate valid silent MP3s + SRTs + words.json
print("[Setup] Generating audio assets...")
for label, text, duration in scenes:
    mp3_path = os.path.join(ASSETS, f"tts_{TS}_{label}.mp3")
    srt_path = os.path.join(ASSETS, f"tts_{TS}_{label}.srt")
    words_path = os.path.join(ASSETS, f"tts_{TS}_{label}.words.json")

    # Generate silent MP3 with proper duration
    subprocess.run([
        "ffmpeg", "-y",
        "-f", "lavfi", "-i", f"anullsrc=r=24000:cl=mono",
        "-t", str(duration),
        "-c:a", "libmp3lame", "-b:a", "96k",
        mp3_path
    ], capture_output=True, timeout=15)

    # Generate SRT
    srt_lines = []
    srt_lines.append("1")
    srt_lines.append(f"00:00:00,000 --> 00:00:{int(duration):02d},000")
    srt_lines.append(text)
    srt_lines.append("")
    with open(srt_path, "w", encoding="utf-8") as f:
        f.write("\n".join(srt_lines))

    # Generate words.json with even pacing
    words = text.split()
    word_duration = (duration * 1000) / len(words) if words else duration * 1000
    word_entries = []
    for i, w in enumerate(words):
        word_entries.append({
            "word": w,
            "offset_ms": i * word_duration,
            "duration_ms": word_duration
        })
    with open(words_path, "w", encoding="utf-8") as f:
        json.dump(word_entries, f)

    print(f"  ✓ {label}: {duration}s, {len(words)} words")

# Step 2: Find the generated images
img_myth = os.path.join(ASSETS, "background_myth_1779679449_3446.png")
img_truth = os.path.join(ASSETS, "foreground_fact_1779679449_3446.png")

if not os.path.exists(img_myth):
    from PIL import Image
    Image.new("RGB", (1080, 1920), (20, 25, 45)).save(img_myth)
    print(f"  Created fallback myth image")
if not os.path.exists(img_truth):
    from PIL import Image
    Image.new("RGB", (1080, 1080), (45, 38, 25)).save(img_truth)
    print(f"  Created fallback truth image")

print(f"  Myth image: {os.path.getsize(img_myth)} bytes")
print(f"  Truth image: {os.path.getsize(img_truth)} bytes")

# Step 3: Build script payload
script_payload = {
    "hook": scenes[1][1],
    "context": scenes[2][1],
    "fact": scenes[3][1],
    "hook_ssml": f"<prosody pitch='-0.5st' rate='0.97'>{scenes[1][1][:80]}</prosody>",
    "context_ssml": f"<prosody pitch='-1.0st' rate='0.88'>{scenes[2][1][:80]}</prosody>",
    "fact_ssml": f"<prosody pitch='-1.5st' rate='0.85'>{scenes[3][1][:80]}</prosody>",
    "s1_ssml": f"<prosody pitch='-0.5st' rate='0.97'>{scenes[1][1][:80]}</prosody>",
    "s2_ssml": f"<prosody pitch='-1.0st' rate='0.88'>{scenes[2][1][:80]}</prosody>",
    "s3_ssml": f"<prosody pitch='-1.5st' rate='0.85'>{scenes[3][1][:80]}</prosody>",
    "word_count": sum(len(s[1].split()) for s in scenes),
    "episode_num": 1,
    "sign_off": "Class dismissed.",
    "cta": scenes[4][1],
    "starting_text": scenes[0][1],
    "ending_text": scenes[4][1],
    "youtube_metadata": {
        "title": "EP.1 — You're Not Descended From Monkeys! #Shorts",
        "description": "Debunking the myth that humans evolved from modern chimpanzees.",
        "tags": ["biology", "evolution", "mythbusting"]
    }
}

audio_paths = [
    os.path.join(ASSETS, f"tts_{TS}_start.mp3"),
    os.path.join(ASSETS, f"tts_{TS}_s1.mp3"),
    os.path.join(ASSETS, f"tts_{TS}_s2.mp3"),
    os.path.join(ASSETS, f"tts_{TS}_s3.mp3"),
    os.path.join(ASSETS, f"tts_{TS}_end.mp3"),
]

# Step 4: Compile!
print("\n[Compile] Initializing VideoEngine...")
eng = VideoEngine()
video_name = f"daily_audit_sample_{TS}"

print("[Compile] This will take a few minutes...")
video_path = eng.compile_short(
    img_myth, img_truth, audio_paths,
    script_payload, video_name, "Biology",
    style="blueprint", video_type="myth"
)
print(f"\n✅ Video compiled: {video_path}")
print(f"   Size: {os.path.getsize(video_path) / 1024 / 1024:.1f} MB")

# Step 5: Thumbnail
print("[Compile] Generating thumbnail...")
eng.generate_thumbnail(
    "Humans evolved from chimpanzees",
    script_payload["hook"], video_name,
    style="blueprint",
    img_myth_path=img_myth, img_truth_path=img_truth,
    episode_num=1
)
print("✅ Done!")

#!/usr/bin/env python3
"""Generate fresh topics for The Daily Audit pipeline. All 88 existing topics are locked."""
import os, sys, sqlite3, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Load API key from .env
env_path = os.path.join(os.path.dirname(__file__), '.env')
if os.path.exists(env_path):
    with open(env_path) as f:
        for line in f:
            line = line.strip()
            if line.startswith('FREE_GEMINI_API_KEY='):
                key = line.split('=', 1)[1].strip().strip('"').strip("'")
                os.environ['FREE_GEMINI_API_KEY'] = key
                os.environ['GEMINI_API_KEY'] = key
                print(f"Loaded API key: {key[:8]}...")
                break

from google import genai
from data_ingestion import DataIngestion

# Init Gemini client
client = genai.Client(api_key=os.environ['GEMINI_API_KEY'])

# Init ingestion
ingestion = DataIngestion()

# Check current state
db_path = ingestion.db_path
conn = sqlite3.connect(db_path)
cur = conn.cursor()
cur.execute("SELECT COUNT(*) FROM audit_history WHERE published_to_yt = 1")
published = cur.fetchone()[0]
cur.execute("SELECT COUNT(*) FROM audit_history WHERE published_to_yt = 0")
unpublished = cur.fetchone()[0]
print(f"Current: {published} published, {unpublished} unpublished")

# Generate topics
NUM_TOPICS = 20
generated = 0
attempts = 0

print(f"\nGenerating {NUM_TOPICS} new topics...\n")

while generated < NUM_TOPICS and attempts < NUM_TOPICS * 3:
    attempts += 1
    try:
        # Alternate between myth and bizarre
        if generated % 3 == 0:
            print(f"\n[{generated+1}/{NUM_TOPICS}] Asking Gemini for BIZARRE topic...")
            result = ingestion.fetch_unused_bizarre_topic(gemini_client=client)
        else:
            print(f"\n[{generated+1}/{NUM_TOPICS}] Asking Gemini for MYTH topic...")
            result = ingestion.fetch_unused_misconception(gemini_client=client)
        
        if result:
            topic, category, desc = result
            # Insert into DB
            content_type = 'bizarre_truth' if generated % 3 == 0 else 'myth'
            try:
                cur.execute("""
                    INSERT INTO audit_history (topic, script_hook, content_type, published_to_yt, pipeline_version)
                    VALUES (?, ?, ?, 0, 'unified_v1')
                """, (topic, f"{category}: {desc}", content_type))
                conn.commit()
                generated += 1
                print(f"  ✓ GENERATED: [{content_type}] {topic[:70]}")
                print(f"    Category: {category} | {desc[:80]}...")
            except sqlite3.IntegrityError as e:
                if 'UNIQUE' in str(e):
                    print(f"  ✗ DUPLICATE (skipped): {topic[:50]}...")
                else:
                    print(f"  ✗ DB ERROR: {e}")
        else:
            print(f"  ✗ Gemini returned None (attempt {attempts})")
        
        # Rate limit: wait 2s between calls
        time.sleep(2)
        
    except Exception as e:
        print(f"  ✗ ERROR: {e}")
        time.sleep(5)

conn.close()
print(f"\n{'='*60}")
print(f"Generated {generated} new topics in {attempts} attempts.")
print(f"Run the pipeline with: python main_local.py")

#!/usr/bin/env python3
"""
DB cleanup and rebuild for The Daily Audit unified pipeline.
1. Cross-reference YouTube videos against DB topics (fuzzy matching)
2. Remove duplicate topics (keep canonical entry)
3. Adjust schema for DailyAuditScriptPayload
"""
import sqlite3
import json
import re
from difflib import SequenceMatcher
from datetime import datetime

DB = 'app_build/database/audit_history.db'

# YouTube videos from the API call (Daily Audit only, not gaming/covers)
YT_VIDEOS = [
    ("EP.17 — Hollywood LIED to You About the Pyramids", "private"),
    ("EP.18 — Why That Raise Won't Make You Work Harder", "private"),
    ("EP.15 — You're Not Left-Brained or Right-Brained.", "private"),
    ("EP.16 — Your Diamond is NOT Made of Coal", "private"),
    ("EP.14 — The 10% Brain Myth is Total BS", "private"),
    ("EP.13 — Your Toilet is Lying to You", "private"),
    ("EP.11 — You Have Been Lied to About the 5-Second Rule", "public"),
    ("EP.10 — They Lied To You About Bats", "public"),
    ("The CIA's UNCRACKABLE Code: Kryptos", "public"),
    ("The UNEXPLAINED 'Wow! Signal' from Space!", "public"),
    ("Mind-Controlling Parasite: The Ant's Suicidal Climb!", "public"),
    ("The Chemical Imbalance Lie You Were Fed", "public"),
    ("The Lie About Blind Bats Is Exposed", "public"),
    ("You're Made of DEAD Stars?!", "public"),
    ("The Lethal Penny Myth is a LIE", "public"),
    ("The Mystery of the Dancing Mice!", "public"),
    ("The Great Wall Space Lie DEBUNKED", "public"),
    ("The Chemical Reaction That NEVER Stops Changing!", "public"),
    ("The Pyramid Slave Lie DEBUNKED", "public"),
    ("Extinct for 375 Million Years... UNTIL NOW!", "public"),
    ("The Great Toilet Flush LIE Exposed", "public"),
    ("Can You Be Blind But Think You See? Anton's Syndrome!", "public"),
    ("The Biggest Lie About Your Paycheck", "public"),
    ("The Experiment That Takes 100 Years!", "public"),
    ("You're WRONG About Diamonds!", "public"),
    ("The Language That Breaks All Rules!", "public"),
    ("The Ostrich Head-Burying Lie DEBUNKED", "public"),
    ("The 'Dark Side' of the Moon is a LIE", "public"),
    ("The Woman Who Thought She Was DEAD!", "public"),
    ("You've Been LIED To About Knuckle Cracking", "public"),
    ("The Evolution Lie You Still Believe", "public"),
    ("The Left-Brain/Right-Brain Lie DEBUNKED", "public"),
    ("Earth's Secret Nuclear Reactor?!", "public"),
    ("It Rained MEAT in Kentucky!", "public"),
    ("Virus Eats Virus?! Meet Sputnik Virophage!", "public"),
    ("You've Been Lied to About Your Brain", "public"),
    ("The Laughing Death: Kuru Disease Explained", "public"),
    ("Exoplanet IQ Test: Are You an Astrobiology Expert?", "public"),
    ("You Use 100% Of Your Brain. Here's The Proof.", "public"),
    ("The Siberian Mystery Blast with NO Crater!", "public"),
    ("The 5-Second Rule is a DANGEROUS Lie", "public"),
    ("Birds Use QUANTUM PHYSICS to Navigate?!", "public"),
    ("Did 300 Years of History VANISH?!", "public"),
    ("Tectonic Trivia: Can You Master Earth's Dynamics?", "public"),
    ("Shaving Does NOT Thicken Hair. You've Been Fooled.", "public"),
    ("Did Aliens Send Us This Message? The Wow! Signal Mystery", "public"),
    ("When London Drowned in BEER!", "public"),
    ("Birds Use QUANTUM Physics to Navigate?!", "public"),  # DUPLICATE on YT
    ("300 Years of HISTORY Are FAKE?!", "public"),  # DUPLICATE on YT
    ("The 52-Hertz Whale: The Loneliest Sound in the Ocean?", "public"),
    ("CIA's UNBROKEN Code: The Kryptos Mystery", "public"),  # DUPLICATE on YT
    ("Shroud of Turin: Carbon Dating DEBUNKED? The True Age Mystery!", "public"),
    ("The Tongue Map Was A LIE", "public"),
    ("Can YOU Master Semiconductor Logic?", "public"),
    ("They LIED About Napoleon and the Sphinx", "public"),
    ("The Man From a Non-Existent Country Vanished!", "public"),
    ("Are You Smarter Than These Biases?", "public"),
    ("You DON'T Have Five Senses", "public"),
    ("The 1518 Dancing Plague: Unexplained Mass Hysteria?", "public"),
    ("Roman Empire: Test Your Knowledge of Ancient Achievements!", "public"),
    ("Radiation Exposure MYTHS DEBUNKED", "public"),
    ("Astrophysics IQ Test: Can You Pass This Cosmic Challenge?", "public"),
    ("Washington's TEETH weren't WOOD!", "public"),
    ("They WEREN'T Burned in Salem", "public"),
    ("The REAL Reason for Seasons DEBUNKED", "public"),
    ("The ZERO-G Lie DEBUNKED", "public"),
    ("Your Blood Was NEVER Blue.", "public"),
    ("The 'Sugar Rush' is a SCAM", "public"),
    ("Columbus DID NOT Discover America", "public"),
    ("Goldfish Memory is a LIE.", "public"),
    ("Your HAT is a LIE", "public"),
    ("Humans Evolved From Monkeys? Debunked!", "public"),
    ("The TRUTH Behind Cracking Your Knuckles", "public"),
    ("Your Microwave is Lying to You", "public"),
    ("Water ISN'T Conductive? DEBUNKED.", "public"),
    ("The Chameleon Camouflage Deception", "public"),
    ("The DEAFENING Silence of Space", "public"),
    ("The Tongue Map is a COMPLETE LIE", "public"),
    ("Your Sink Drain is a LIE", "public"),
    ("Napoleon Wasn't Short. You Were Fooled.", "public"),
    ("The BIGGEST Lie About the Middle Ages", "public"),
    ("That Skyscraper Penny Myth is FALSE", "public"),
    ("The Left-Brain/Right-Brain Lie DEBUNKED", "public"),  # DUPLICATE on YT
    ("You're WRONG About Lightning Strikes", "public"),
    ("Vikings NEVER Wore Horned Helmets", "public"),
    ("The 10% Brain Myth is WRONG", "public"),
    ("Einstein FAILED Math? Think Again.", "public"),
    ("The Iron Maiden is a LIE.", "public"),
    ("Your Pencil is a Chemical LIE", "public"),
]

def normalize(t):
    """Strip punctuation, lowercase, remove common words for matching."""
    t = t.lower()
    t = re.sub(r'[^a-z0-9\s]', '', t)
    t = re.sub(r'\b(the|is|a|an|in|of|to|and|that|are|was|for|you|your|this|its|not|has|been|have|can|does|did|with|from|about|all|but|just|like|our|out|than|then|we|were|will|also|its)\b', '', t)
    return ' '.join(t.split())

def similarity(a, b):
    """Fuzzy topic similarity."""
    return SequenceMatcher(None, normalize(a), normalize(b)).ratio()

def extract_keywords(s):
    """Extract key topic words."""
    s = normalize(s)
    return set(w for w in s.split() if len(w) > 2)

print("=" * 60)
print("PHASE 1: Cross-reference YouTube videos → DB topics")
print("=" * 60)

conn = sqlite3.connect(DB)
conn.row_factory = sqlite3.Row
cur = conn.cursor()

# Get all DB topics
cur.execute("SELECT id, topic, video_type, date_uploaded FROM audit_history ORDER BY id")
db_rows = cur.fetchall()

# For each YouTube video, find matching DB topic(s)
matched_db_ids = set()
match_results = []

for yt_title, yt_status in YT_VIDEOS:
    yt_keywords = extract_keywords(yt_title)
    best_match = None
    best_score = 0
    
    for row in db_rows:
        if row['id'] in matched_db_ids:
            continue
        score = similarity(yt_title, row['topic'])
        # Also check keyword overlap
        db_keywords = extract_keywords(row['topic'])
        kw_overlap = len(yt_keywords & db_keywords) / max(len(yt_keywords | db_keywords), 1)
        combined = score * 0.7 + kw_overlap * 0.3
        
        if combined > best_score and combined > 0.35:
            best_score = combined
            best_match = row
    
    if best_match:
        matched_db_ids.add(best_match['id'])
        match_results.append((best_match['id'], best_match['topic'], yt_title, yt_status, best_score))
        print(f"  MATCH [{best_score:.2f}]: DB#{best_match['id']} '{best_match['topic'][:50]}' → YT '{yt_title[:60]}' ({yt_status})")
    else:
        print(f"  NO MATCH: YT '{yt_title[:60]}' ({yt_status})")

# Mark matched topics as published on YouTube
for db_id, db_topic, yt_title, yt_status, score in match_results:
    cur.execute("""
        UPDATE audit_history 
        SET video_type = CASE WHEN video_type IS NULL OR video_type = '' THEN 'published' ELSE video_type END,
            date_uploaded = datetime('now')
        WHERE id = ?
    """, (db_id,))

print(f"\nMatched {len(match_results)} YouTube videos to DB topics")

print("\n" + "=" * 60)
print("PHASE 2: Identify & remove duplicate DB topics")
print("=" * 60)

# Get all remaining topics
cur.execute("SELECT id, topic, video_type, date_uploaded FROM audit_history ORDER BY id")
all_rows = cur.fetchall()

# Find duplicates using fuzzy matching
dupes_to_remove = []
seen_topics = {}  # canonical_topic → canonical_id

for row in all_rows:
    n = normalize(row['topic'])
    found_dupe = False
    
    for canon_topic, canon_id in list(seen_topics.items()):
        score = similarity(row['topic'], canon_topic)
        if score > 0.65:
            dupes_to_remove.append((row['id'], row['topic'], canon_id, canon_topic, score))
            found_dupe = True
            break
    
    if not found_dupe:
        seen_topics[n] = row['id']

print(f"Found {len(dupes_to_remove)} duplicate topics to remove:")
for did, dtopic, cid, ctopic, score in dupes_to_remove:
    print(f"  REMOVE DB#{did} '{dtopic[:55]}' (dup of DB#{cid} '{ctopic[:55]}', score={score:.2f})")

# Remove duplicates
for did, _, _, _, _ in dupes_to_remove:
    cur.execute("DELETE FROM audit_history WHERE id = ?", (did,))

removed = len(dupes_to_remove)
print(f"\nRemoved {removed} duplicates")

print("\n" + "=" * 60)
print("PHASE 3: Adjust schema for unified DailyAuditScriptPayload")
print("=" * 60)

# Add new columns for the unified schema
new_columns = [
    ("content_type", "TEXT", "myth"),        # myth, bizarre_truth, hidden_truth, paradox
    ("beat_structure", "TEXT", None),         # JSON: 5 beats with hook, context, reveal, mechanism, reframe
    ("research_context", "TEXT", None),       # JSON: scraped Wikipedia + DuckDuckGo results
    ("pipeline_version", "TEXT", "unified_v1"),  # Track which pipeline version generated this
    ("published_to_yt", "INTEGER", "0"),      # 0=no, 1=yes
    ("yt_video_id", "TEXT", None),            # YouTube video ID
    ("word_count", "INTEGER", None),          # Actual word count of generated script
    ("generated_at", "TIMESTAMP", None),      # When the script was generated
]

existing_cols = set()
cur.execute("PRAGMA table_info(audit_history)")
for col in cur.fetchall():
    existing_cols.add(col['name'])

for col_name, col_type, default_val in new_columns:
    if col_name not in existing_cols:
        if default_val is not None:
            sql = f"ALTER TABLE audit_history ADD COLUMN {col_name} {col_type} DEFAULT '{default_val}'"
        else:
            sql = f"ALTER TABLE audit_history ADD COLUMN {col_name} {col_type}"
        try:
            cur.execute(sql)
            print(f"  ADDED column: {col_name} ({col_type})")
        except Exception as e:
            print(f"  SKIP {col_name}: {e}")
    else:
        print(f"  EXISTS: {col_name}")

# Mark previously published topics based on YouTube match
cur.execute("UPDATE audit_history SET published_to_yt = 1 WHERE id IN ({})".format(
    ','.join(str(m[0]) for m in match_results)
))
# Also mark the original 6 that had video_type set
cur.execute("""
    UPDATE audit_history SET published_to_yt = 1 
    WHERE video_type IN ('myth', 'bizarre') AND date_uploaded IS NOT NULL
""")

print("\n" + "=" * 60)
print("PHASE 4: Verify and report")
print("=" * 60)

# Count stats
cur.execute("SELECT COUNT(*) FROM audit_history")
total = cur.fetchone()[0]

cur.execute("SELECT COUNT(*) FROM audit_history WHERE published_to_yt = 1")
published = cur.fetchone()[0]

cur.execute("SELECT COUNT(*) FROM audit_history WHERE published_to_yt = 0")
unpublished = cur.fetchone()[0]

print(f"Total topics: {total}")
print(f"Published to YouTube: {published}")
print(f"Unpublished (available): {unpublished}")

print("\n--- Published topics ---")
cur.execute("SELECT id, topic, content_type FROM audit_history WHERE published_to_yt = 1 ORDER BY id")
for row in cur.fetchall():
    print(f"  DB#{row['id']} | {row['content_type']:12s} | {row['topic'][:60]}")

print("\n--- Unpublished topics (first 15) ---")
cur.execute("SELECT id, topic, content_type FROM audit_history WHERE published_to_yt = 0 ORDER BY id LIMIT 15")
for row in cur.fetchall():
    print(f"  DB#{row['id']} | {row['content_type']:12s} | {row['topic'][:60]}")

# Show full column list
print("\n--- New schema ---")
cur.execute("PRAGMA table_info(audit_history)")
for col in cur.fetchall():
    print(f"  {col['name']:25s} {col['type']:15s} default={col['dflt_value']}")

conn.commit()
conn.close()

print(f"\nDone. Removed {removed} duplicates. DB ready for unified pipeline.")

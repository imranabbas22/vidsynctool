#!/usr/bin/env python3
"""Fix false matches and add missing YouTube entries to the DB."""
import sqlite3

DB = 'app_build/database/audit_history.db'
conn = sqlite3.connect(DB)
cur = conn.cursor()

print("=== FIX FALSE MATCHES ===")

# DB#83 "You've Been Lied to About Your Brain" wrongly matched to EP.17 Pyramids
# Actually: DB#83 is a dupe of "10% Brain" topic. EP.17 is "Hollywood LIED About Pyramids" which is DB#60/DB#12
# Fix: unmark DB#83 (it was removed as dupe anyway, so skip)
# Fix: DB#12 shouldn't be matched to EP.10 Bats

# 1. DB#12 "Napoleon and the Sphinx" ≠ "They Lied About Bats"
cur.execute("UPDATE audit_history SET published_to_yt = 0, yt_video_id = NULL WHERE id = 12")
print("FIXED: DB#12 unmarked (was wrong match to EP.10 Bats)")

# 2. DB#45 "Lightning Strikes" ≠ "EP.15 Left-Brained"
cur.execute("UPDATE audit_history SET published_to_yt = 0, yt_video_id = NULL WHERE id = 45")
print("FIXED: DB#45 unmarked (was wrong match to EP.15 Left-Brain)")

# 3. DB#67 "They WEREN'T Burned in Salem" ≠ "Napoleon and the Sphinx"
cur.execute("UPDATE audit_history SET published_to_yt = 0, yt_video_id = NULL WHERE id = 67")
print("FIXED: DB#67 unmarked (was wrong match to Napoleon/Sphinx)")

# 4. DB#66 "100% Brain" ≠ "You've Been Lied to About Your Brain"
cur.execute("UPDATE audit_history SET published_to_yt = 0, yt_video_id = NULL WHERE id = 66")
print("FIXED: DB#66 unmarked (was wrong match)")

# 5. DB#22 "The About Blind Bats Is" — this IS correctly matched. Keep it.
# But the topic title is garbled. Fix the title.
cur.execute("UPDATE audit_history SET topic = 'Blind Bats Myth Debunked' WHERE id = 22")
print("FIXED: DB#22 title cleaned")

print("\n=== ADD MISSING YT VIDEOS AS NEW DB ENTRIES ===")

missing = [
    ("EP.18 — Why That Raise Won't Make You Work Harder", "myth"),
    ("EP.16 — Your Diamond is NOT Made of Coal", "myth"),
    ("The Left-Brain/Right-Brain Lie DEBUNKED", "myth"),
    ("You Use 100% Of Your Brain. Here's The Proof.", "myth"),
    ("They WEREN'T Burned in Salem", "myth"),
    ("You're WRONG About Lightning Strikes", "myth"),
    ("The 10% Brain Myth is WRONG", "myth"),
    ("The Great Toilet Flush LIE Exposed", "myth"),
]

for title, ctype in missing:
    # Skip if topic already exists (UNIQUE constraint)
    cur.execute("SELECT id FROM audit_history WHERE topic = ?", (title,))
    if cur.fetchone():
        # Mark existing as published instead
        cur.execute("UPDATE audit_history SET published_to_yt = 1 WHERE topic = ?", (title,))
        print(f"SKIP (exists): '{title}' — marked published")
        continue
    cur.execute("""
        INSERT INTO audit_history (topic, script_hook, content_type, published_to_yt, pipeline_version, date_uploaded)
        VALUES (?, '', ?, 1, 'unified_v1', datetime('now'))
    """, (title, ctype))
    print(f"ADDED: '{title}' ({ctype})")

print("\n=== FIX CONTENT TYPES ===")

# Known bizarre topics that got marked as myth
bizarre_topics = {
    1: "The Wow! Signal",
    3: "Kryptos — The Unsolved Sculpture Cipher",
    26: "The UNEXPLAINED Wow Signal",
    27: "The Man From a Non-Existent Country Vanished",
    30: "CIA's UNBROKEN Code The Kryptos Mystery",
    38: "The 52-Hertz Whale",
    40: "Anton's Syndrome",
    42: "Mind-Controlling Parasite",
    47: "The Laughing Death Kuru Disease",
    48: "Earth's Secret Nuclear Reactor",
    49: "The Mystery of the Dancing Mice",
    52: "Extinct for 375 Million Years",
    62: "When London Drowned in BEER",
    76: "The 1518 Dancing Plague",
    77: "The Siberian Mystery Blast",
    84: "The Woman Who Thought She Was DEAD",
    91: "It Rained MEAT in Kentucky",
}

for db_id, topic in bizarre_topics.items():
    cur.execute("UPDATE audit_history SET content_type = 'bizarre_truth' WHERE id = ?", (db_id,))
    print(f"FIXED: DB#{db_id} '{topic}' → bizarre_truth")

# Known paradox topics
paradox_topics = {
    28: "Are You Smarter Than These Biases",
    34: "Virus Eats Virus Sputnik Virophage",
    56: "The Chemical Reaction That NEVER Stops",
    64: "The Experiment That Takes 100 Years",
    86: "The Language That Breaks All Rules",
}

for db_id, topic in paradox_topics.items():
    cur.execute("UPDATE audit_history SET content_type = 'paradox' WHERE id = ?", (db_id,))
    print(f"FIXED: DB#{db_id} '{topic}' → paradox")

# Clean up truncated titles (add proper endings)
truncated_fixes = [
    (13, "Your Sink Drain is a LIE", "Your Sink Drain is a LIE"),
    (17, "The Tongue Map is a COMPLETE LIE", "The Tongue Map is a COMPLETE LIE"),
    (21, "That Skyscraper Penny Myth is FALSE", "That Skyscraper Penny Myth is FALSE"),
    (29, "Your Pencil is a Chemical LIE", "Your Pencil is a Chemical LIE"),
    (33, "The Iron Maiden is a LIE", "The Iron Maiden is a LIE"),
    (35, "Your HAT is a LIE", "Your HAT is a LIE"),
    (41, "The Lethal Penny Myth is a LIE", "The Lethal Penny Myth is a LIE"),
    (46, "The 10% Brain Myth is DEBUNKED", "The 10% Brain Myth is DEBUNKED"),
    (53, "The Sugar Rush is a SCAM", "The Sugar Rush is a SCAM"),
    (55, "The ZERO-G Lie DEBUNKED", "The ZERO-G Lie DEBUNKED"),
    (87, "The Dark Side of the Moon is a LIE", "The Dark Side of the Moon is a LIE"),
]

for db_id, new_title, _ in truncated_fixes:
    cur.execute("UPDATE audit_history SET topic = ? WHERE id = ?", (new_title, db_id))
    print(f"FIXED: DB#{db_id} title → '{new_title}'")

# Also clean the "About" pattern (e.g., "The About Blind Bats Is" → fixed above)
about_fixes = [
    (37, "The BIGGEST Lie About the Middle Ages"),
    (74, "The Biggest Lie About Your Paycheck"),
    (73, "You're WRONG About Diamonds"),
]

for db_id, new_title in about_fixes:
    cur.execute("UPDATE audit_history SET topic = ? WHERE id = ?", (new_title, db_id))
    print(f"FIXED: DB#{db_id} title → '{new_title}'")

conn.commit()

print("\n=== FINAL STATS ===")
cur.execute("SELECT COUNT(*) FROM audit_history")
total = cur.fetchone()[0]
cur.execute("SELECT COUNT(*) FROM audit_history WHERE published_to_yt = 1")
pub = cur.fetchone()[0]
cur.execute("SELECT COUNT(*) FROM audit_history WHERE published_to_yt = 0")
unpub = cur.fetchone()[0]
cur.execute("SELECT content_type, COUNT(*) FROM audit_history GROUP BY content_type")
ct_counts = cur.fetchall()

print(f"Total: {total} | Published: {pub} | Unpublished: {unpub}")
for ct, cnt in ct_counts:
    print(f"  {ct}: {cnt}")

conn.close()
print("Done.")

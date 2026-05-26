#!/usr/bin/env python3
"""Import bootstrap lists as locked DB entries and remove duplicate generated topics."""
import os, sys, sqlite3
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from data_ingestion import DataIngestion, BOOTSTRAP_MYTHS, BOOTSTRAP_BIZARRE

DB = 'database/audit_history.db'
conn = sqlite3.connect(DB)
cur = conn.cursor()

print("=== PHASE 1: Import bootstrap lists as locked DB entries ===\n")

imported = 0
for topic, category, desc in BOOTSTRAP_MYTHS + BOOTSTRAP_BIZARRE:
    # Check if already in DB
    cur.execute("SELECT id FROM audit_history WHERE topic = ?", (topic,))
    if cur.fetchone():
        # Already exists — ensure it's marked published
        cur.execute("UPDATE audit_history SET published_to_yt = 1 WHERE topic = ?", (topic,))
        print(f"  EXISTS (marked published): {topic[:55]}")
    else:
        ctype = 'bizarre_truth' if (topic, category, desc) in BOOTSTRAP_BIZARRE else 'myth'
        try:
            cur.execute("""
                INSERT INTO audit_history (topic, script_hook, content_type, published_to_yt, pipeline_version)
                VALUES (?, ?, ?, 1, 'bootstrap_v1')
            """, (topic, f"{category}: {desc}", ctype))
            imported += 1
            print(f"  IMPORTED [{ctype}]: {topic[:55]}")
        except sqlite3.IntegrityError as e:
            print(f"  SKIP (constraint): {topic[:40]} — {e}")

conn.commit()
print(f"\nImported {imported} new bootstrap entries as locked/published.\n")

print("=== PHASE 2: Identify and remove duplicate generated topics ===\n")

# Get all unpublished topics
cur.execute("SELECT id, topic, content_type FROM audit_history WHERE published_to_yt = 0")
unpublished = cur.fetchall()

# Known dupes (generated topics that match published content)
dupes_to_remove = []

for uid, utopic, uctype in unpublished:
    # Check against published topics using simple keyword overlap
    cur.execute("SELECT id, topic FROM audit_history WHERE published_to_yt = 1")
    for pid, ptopic in cur.fetchall():
        # Very aggressive: if >50% of significant words overlap
        def sig_words(s):
            stop = {'the','is','a','an','in','of','to','and','that','are','was','for','you','your','this','its','not','has','been','have','can','does','did','with','from','about','all','but','just','like','our','out','than','then','we','were'}
            return {w.lower() for w in s.split() if w.lower() not in stop and len(w) > 2}
        uw = sig_words(utopic)
        pw = sig_words(ptopic)
        if uw and pw and len(uw & pw) / len(uw) > 0.5:
            dupes_to_remove.append((uid, utopic, pid, ptopic))
            break

if dupes_to_remove:
    print(f"Found {len(dupes_to_remove)} duplicate generated topics to remove:")
    for uid, utopic, pid, ptopic in dupes_to_remove:
        print(f"  REMOVE #{uid} '{utopic[:55]}'")
        print(f"    → duplicate of #{pid} '{ptopic[:55]}'")
        cur.execute("DELETE FROM audit_history WHERE id = ?", (uid,))
    conn.commit()
    print(f"\nRemoved {len(dupes_to_remove)} duplicates.")
else:
    print("No duplicates found!")

print("\n=== FINAL STATE ===")
cur.execute("SELECT COUNT(*), published_to_yt FROM audit_history GROUP BY published_to_yt")
for cnt, pub in cur.fetchall():
    label = "LOCKED (never reuse)" if pub else "AVAILABLE for pipeline"
    print(f"  {label}: {cnt}")

cur.execute("SELECT COUNT(*) FROM audit_history")
total = cur.fetchone()[0]
print(f"  TOTAL: {total}")

print("\n--- Available topics ---")
cur.execute("SELECT id, topic, content_type FROM audit_history WHERE published_to_yt = 0 ORDER BY id")
for r in cur.fetchall():
    print(f"  #{r[0]:3d} | {r[2]:15s} | {r[1][:70]}")

conn.close()
print("\nDone.")

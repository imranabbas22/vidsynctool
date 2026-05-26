import sqlite3
DB = r'C:\Users\imran\auto-youtube-project\app_build\database\audit_history.db'
conn = sqlite3.connect(DB)
cur = conn.cursor()

# B5: Cleopatra
cur.execute("INSERT INTO audit_history (topic, script_hook, content_type, published_to_yt, pipeline_version) VALUES (?,?,?,?,?)",
    ('Cleopatra Lived Closer to the Moon Landing Than to the Pyramids',
     'Bizarre Truths: Great Pyramid ~2560 BC. Cleopatra ~30 BC. Moon landing 1969 AD.',
     'bizarre_truth', 0, 'user_curated_v1'))
print('ADDED B5: Cleopatra')

# B14: Great Fire of London
cur.execute("INSERT INTO audit_history (topic, script_hook, content_type, published_to_yt, pipeline_version) VALUES (?,?,?,?,?)",
    ('The Great Fire of London Officially Killed Only 6 People',
     'Bizarre Truths: 1666 fire destroyed 13000 houses yet only 6 deaths recorded.',
     'bizarre_truth', 0, 'user_curated_v1'))
print('ADDED B14: Great Fire of London')

conn.commit()

cur.execute('SELECT COUNT(*) FROM audit_history WHERE published_to_yt = 0')
print(f'Available: {cur.fetchone()[0]}')

conn.close()

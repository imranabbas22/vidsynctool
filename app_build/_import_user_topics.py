#!/usr/bin/env python3
"""Import user-provided topics from JSON into the DB."""
import json, sqlite3, sys, os

DB = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'database', 'audit_history.db')

topics_json = r'''
{
  "content_topics": {
    "myths_and_truths": [
      {"id": "S1", "category": "Space", "type": "myth", "myth": "Astronauts float because they've escaped Earth's gravity", "truth": "They're in free fall around Earth. The ISS experiences ~90% of Earth's surface gravity.", "wikipedia_title": "Weightlessness", "wikipedia_url": "https://en.wikipedia.org/wiki/Weightlessness"},
      {"id": "S2", "category": "Space", "type": "myth", "myth": "The dark side of the Moon is always dark", "truth": "It gets the same sunlight as the near side. It's 'dark' only in the sense that it was unseen, not unlit.", "wikipedia_title": "Far side of the Moon", "wikipedia_url": "https://en.wikipedia.org/wiki/Far_side_of_the_Moon"},
      {"id": "S3", "category": "Space", "type": "myth", "myth": "Black holes suck everything in like a cosmic vacuum", "truth": "A black hole has the same gravitational pull as any equal-mass object at the same distance.", "wikipedia_title": "Black hole", "wikipedia_url": "https://en.wikipedia.org/wiki/Black_hole"},
      {"id": "S4", "category": "Space", "type": "myth", "myth": "Seasons happen because Earth is closer to the Sun in summer", "truth": "Seasons are caused by Earth's 23.4° axial tilt, not orbital distance. Earth is actually closest to the Sun in January.", "wikipedia_title": "Season", "wikipedia_url": "https://en.wikipedia.org/wiki/Season"},
      {"id": "S5", "category": "Space", "type": "myth", "myth": "The Sun is yellow", "truth": "Outside Earth's atmosphere, the Sun emits white light. Atmospheric scattering makes it appear yellow.", "wikipedia_title": "Sun", "wikipedia_url": "https://en.wikipedia.org/wiki/Sun"},
      {"id": "S6", "category": "Space", "type": "myth", "myth": "Tang, Velcro, and Teflon were invented by NASA", "truth": "None of these were NASA inventions. Memory foam and space blankets were.", "wikipedia_title": "NASA spinoff technologies", "wikipedia_url": "https://en.wikipedia.org/wiki/NASA_spinoff_technologies"},
      {"id": "S7", "category": "Space", "type": "myth", "myth": "NASA wasted millions developing a space pen while Soviets used pencils", "truth": "The pen was privately funded by Paul Fisher for $1M of his own money. Pencils were dangerous — graphite flakes are a fire and inhalation hazard.", "wikipedia_title": "Fisher Space Pen", "wikipedia_url": "https://en.wikipedia.org/wiki/Fisher_Space_Pen"},
      {"id": "S8", "category": "Space", "type": "myth", "myth": "The Great Wall of China is visible from space", "truth": "It's too narrow (~5m wide) to see with the naked eye. Astronaut Leroy Chiao only captured it in 2004 with a telephoto lens.", "wikipedia_title": "Great Wall of China", "wikipedia_url": "https://en.wikipedia.org/wiki/Great_Wall_of_China"},
      {"id": "P1", "category": "Physics", "type": "myth", "myth": "Meteors burn up from friction with the atmosphere", "truth": "The heat comes from adiabatic compression of air in front of the object, not friction.", "wikipedia_title": "Atmospheric entry", "wikipedia_url": "https://en.wikipedia.org/wiki/Atmospheric_entry"},
      {"id": "P2", "category": "Physics", "type": "myth", "myth": "Lightning never strikes the same place twice", "truth": "Tall structures like the Empire State Building are struck 20–100 times per year.", "wikipedia_title": "Lightning", "wikipedia_url": "https://en.wikipedia.org/wiki/Lightning"},
      {"id": "P3", "category": "Physics", "type": "myth", "myth": "A compass needle points to Earth's geographic North Pole", "truth": "The magnetic north pole is a magnetic south pole in physics terms, and it drifts over time.", "wikipedia_title": "North magnetic pole", "wikipedia_url": "https://en.wikipedia.org/wiki/North_magnetic_pole"},
      {"id": "P4", "category": "Physics", "type": "myth", "myth": "You can balance an egg only on the spring equinox", "truth": "Eggs can be balanced on any day of the year with enough patience.", "wikipedia_title": "Egg balancing", "wikipedia_url": "https://en.wikipedia.org/wiki/Egg_balancing"},
      {"id": "P5", "category": "Physics", "type": "myth", "myth": "Centrifugal force is a real force", "truth": "It's a fictitious pseudo-force that appears in rotating reference frames — it doesn't exist in an inertial frame.", "wikipedia_title": "Centrifugal force", "wikipedia_url": "https://en.wikipedia.org/wiki/Centrifugal_force"},
      {"id": "C1", "category": "Chemistry", "type": "myth", "myth": "Glass is a slow-flowing liquid (old windows are thick at the bottom)", "truth": "Glass is an amorphous solid. Old windows were uneven due to manufacturing, not flow.", "wikipedia_title": "Glass", "wikipedia_url": "https://en.wikipedia.org/wiki/Glass"},
      {"id": "C2", "category": "Chemistry", "type": "myth", "myth": "Water conducts electricity", "truth": "Pure water is a very poor conductor. It's dissolved salts and minerals that conduct electricity.", "wikipedia_title": "Electrical resistivity and conductivity", "wikipedia_url": "https://en.wikipedia.org/wiki/Electrical_resistivity_and_conductivity"},
      {"id": "C3", "category": "Chemistry", "type": "myth", "myth": "Diamonds are forever because they're the hardest substance", "truth": "Hardness does not equal durability. Diamonds are brittle and can shatter with a hammer blow. Graphite is the more thermodynamically stable form of carbon at room temperature.", "wikipedia_title": "Diamond", "wikipedia_url": "https://en.wikipedia.org/wiki/Diamond"},
      {"id": "C4", "category": "Chemistry", "type": "myth", "myth": "Cold fusion was proven in 1989", "truth": "The Pons–Fleischmann experiment could not be replicated. It was a false alarm that triggered a global scientific frenzy.", "wikipedia_title": "Cold fusion", "wikipedia_url": "https://en.wikipedia.org/wiki/Cold_fusion"},
      {"id": "C5", "category": "Chemistry", "type": "myth", "myth": "Mixing bleach and ammonia just makes a stronger cleaner", "truth": "It creates chloramine vapors, which are toxic and potentially lethal.", "wikipedia_title": "Chloramine", "wikipedia_url": "https://en.wikipedia.org/wiki/Chloramine"},
      {"id": "H1", "category": "History", "type": "myth", "myth": "The Egyptian pyramids were built by slaves", "truth": "Archaeological evidence shows they were built by paid laborers and farmers, rewarded with food and tax exemptions.", "wikipedia_title": "Egyptian pyramids", "wikipedia_url": "https://en.wikipedia.org/wiki/Egyptian_pyramids"},
      {"id": "H2", "category": "History", "type": "myth", "myth": "Julius Caesar was born by caesarean section", "truth": "This would have killed his mother — she was alive when Caesar was 45. The term's origin is debated.", "wikipedia_title": "Caesarean section", "wikipedia_url": "https://en.wikipedia.org/wiki/Caesarean_section"},
      {"id": "H3", "category": "History", "type": "myth", "myth": "'Et tu, Brute?' were Caesar's last words", "truth": "There's no historical evidence of this. It comes from Shakespeare's play. He likely said nothing, or 'καὶ σύ, τέκνον?' (You too, child?).", "wikipedia_title": "Last words of Julius Caesar", "wikipedia_url": "https://en.wikipedia.org/wiki/Last_words_of_Julius_Caesar"},
      {"id": "H4", "category": "History", "type": "myth", "myth": "Romans used vomitoriums to purge food during feasts", "truth": "A vomitorium was a stadium exit passageway. Romans did not routinely vomit between courses.", "wikipedia_title": "Vomitorium", "wikipedia_url": "https://en.wikipedia.org/wiki/Vomitorium"},
      {"id": "H5", "category": "History", "type": "myth", "myth": "Medieval people died in their 30s on average", "truth": "Life expectancy at birth was ~35 due to child mortality. A 21-year-old medieval Englishman could expect to reach age 64.", "wikipedia_title": "Life expectancy", "wikipedia_url": "https://en.wikipedia.org/wiki/Life_expectancy"},
      {"id": "H6", "category": "History", "type": "myth", "myth": "The 'Dark Ages' were dark", "truth": "Modern historians reject the term. The era had significant intellectual, cultural, and religious activity.", "wikipedia_title": "Dark Ages (historiography)", "wikipedia_url": "https://en.wikipedia.org/wiki/Dark_Ages_(historiography)"},
      {"id": "H7", "category": "History", "type": "myth", "myth": "King Canute arrogantly tried to command the sea", "truth": "He did it to prove to sycophants that even kings have limits — it was an act of humility, not delusion.", "wikipedia_title": "King Canute and the tide", "wikipedia_url": "https://en.wikipedia.org/wiki/King_Canute_and_the_tide"},
      {"id": "H8", "category": "History", "type": "myth", "myth": "Einstein failed mathematics as a child", "truth": "He excelled at math. The myth stems from Switzerland using an inverted grading scale vs. Germany's.", "wikipedia_title": "Albert Einstein", "wikipedia_url": "https://en.wikipedia.org/wiki/Albert_Einstein"},
      {"id": "H9", "category": "History", "type": "myth", "myth": "King Tut's tomb had a deadly curse inscribed on it", "truth": "No curse inscription exists. The 'curse' was a tabloid invention by 20th-century journalists.", "wikipedia_title": "Curse of the pharaohs", "wikipedia_url": "https://en.wikipedia.org/wiki/Curse_of_the_pharaohs"},
      {"id": "H10", "category": "History", "type": "myth", "myth": "The Roman salute (outstretched arm) was used in ancient Rome", "truth": "It was invented by a French painter in 1784 (Jacques-Louis David) and later adopted by the Nazis.", "wikipedia_title": "Roman salute", "wikipedia_url": "https://en.wikipedia.org/wiki/Roman_salute"},
      {"id": "T1", "category": "Technology", "type": "myth", "myth": "Incognito mode makes you anonymous online", "truth": "It only hides local browsing history. Your ISP, employer, and websites still see your activity.", "wikipedia_title": "Private browsing", "wikipedia_url": "https://en.wikipedia.org/wiki/Private_browsing"},
      {"id": "T2", "category": "Technology", "type": "myth", "myth": "More megapixels = better camera", "truth": "Sensor size, aperture, and processing matter far more. Megapixels only affect print size.", "wikipedia_title": "Image sensor", "wikipedia_url": "https://en.wikipedia.org/wiki/Image_sensor"},
      {"id": "T3", "category": "Technology", "type": "myth", "myth": "Macs don't get viruses", "truth": "Macs are susceptible to malware — they simply had fewer attacks historically due to lower market share, not inherent immunity.", "wikipedia_title": "macOS malware", "wikipedia_url": "https://en.wikipedia.org/wiki/macOS_malware"},
      {"id": "T4", "category": "Technology", "type": "myth", "myth": "Charging your phone overnight ruins the battery", "truth": "Modern smartphones have battery management chips that stop charging at 100%. Most now have optimized charging features.", "wikipedia_title": "Lithium-ion battery", "wikipedia_url": "https://en.wikipedia.org/wiki/Lithium-ion_battery"},
      {"id": "T5", "category": "Technology", "type": "myth", "myth": "The internet and the World Wide Web are the same thing", "truth": "The internet is the physical infrastructure (cables, servers). The Web is one application that runs on it.", "wikipedia_title": "World Wide Web", "wikipedia_url": "https://en.wikipedia.org/wiki/World_Wide_Web"},
      {"id": "B1", "category": "Bizarre Truths", "type": "bizarre_truth", "topic": "The Dancing Plague of 1518", "truth": "Hundreds of people in Strasbourg danced uncontrollably for weeks — some until they died of exhaustion, heart attacks, or strokes. No one has fully explained why.", "wikipedia_title": "Dancing Plague of 1518", "wikipedia_url": "https://en.wikipedia.org/wiki/Dancing_plague_of_1518"},
      {"id": "B2", "category": "Bizarre Truths", "type": "bizarre_truth", "topic": "The Cadaver Synod (897 AD)", "truth": "Pope Stephen VI dug up his predecessor's rotting corpse, dressed it in papal robes, and put it on trial. The corpse was found guilty, its fingers cut off, and it was thrown in the Tiber River.", "wikipedia_title": "Cadaver Synod", "wikipedia_url": "https://en.wikipedia.org/wiki/Cadaver_Synod"},
      {"id": "B3", "category": "Bizarre Truths", "type": "bizarre_truth", "topic": "Australia Lost a War to Emus", "truth": "In 1932, the Australian military deployed soldiers with machine guns against emus invading farmland. The emus won. The army retreated in embarrassment.", "wikipedia_title": "Emu War", "wikipedia_url": "https://en.wikipedia.org/wiki/Emu_War"},
      {"id": "B4", "category": "Bizarre Truths", "type": "bizarre_truth", "topic": "Napoleon Was Routed by Rabbits", "truth": "After Waterloo, Napoleon organized a celebratory rabbit hunt. The rabbits — domesticated, not wild — charged at his army en masse. He fled.", "wikipedia_title": "Napoleon's rabbit hunt", "wikipedia_url": "https://en.wikipedia.org/wiki/Napoleon%27s_rabbit_hunt"},
      {"id": "B5", "category": "Bizarre Truths", "type": "bizarre_truth", "topic": "Cleopatra Lived Closer to the Moon Landing Than to the Pyramids", "truth": "The Great Pyramid was built ~2560 BC. Cleopatra lived ~30 BC. The Moon landing was 1969 AD. She's separated from the pyramids by ~2,500 years, from Apollo 11 by only ~2,000.", "wikipedia_title": "Cleopatra", "wikipedia_url": "https://en.wikipedia.org/wiki/Cleopatra"},
      {"id": "B6", "category": "Bizarre Truths", "type": "bizarre_truth", "topic": "The Universe Smells Like Rum and Raspberries", "truth": "A molecular cloud near the Milky Way's center, Sagittarius B2, contains ethyl formate — the compound responsible for the smell of raspberries and the taste of rum.", "wikipedia_title": "Sagittarius B2", "wikipedia_url": "https://en.wikipedia.org/wiki/Sagittarius_B2"},
      {"id": "B7", "category": "Bizarre Truths", "type": "bizarre_truth", "topic": "Bananas Are Berries. Strawberries Are Not.", "truth": "A true botanical berry comes from a single ovary. Bananas qualify. Strawberries, raspberries, and blackberries are all technically 'false fruits'.", "wikipedia_title": "Berry (botany)", "wikipedia_url": "https://en.wikipedia.org/wiki/Berry_(botany)"},
      {"id": "B8", "category": "Bizarre Truths", "type": "bizarre_truth", "topic": "Oxford University Is Older Than the Aztec Empire", "truth": "Teaching at Oxford began around 1096 AD. The Aztec Empire was founded in 1428 AD. Oxford is over 300 years older than the empire that built Tenochtitlan.", "wikipedia_title": "University of Oxford", "wikipedia_url": "https://en.wikipedia.org/wiki/University_of_Oxford"},
      {"id": "B9", "category": "Bizarre Truths", "type": "bizarre_truth", "topic": "The Eiffel Tower Was Meant to Be Torn Down", "truth": "Built as a temporary structure for the 1889 World's Fair, it was saved only because it could function as a radio antenna. It was scheduled for demolition in 1909.", "wikipedia_title": "Eiffel Tower", "wikipedia_url": "https://en.wikipedia.org/wiki/Eiffel_Tower"},
      {"id": "B10", "category": "Bizarre Truths", "type": "bizarre_truth", "topic": "Humans Share 60% of Their DNA With Bananas", "truth": "Due to shared cellular machinery like energy production and DNA replication, humans and bananas share roughly 60% of their genetic code.", "wikipedia_title": "Banana", "wikipedia_url": "https://en.wikipedia.org/wiki/Banana#Genetics"},
      {"id": "B11", "category": "Bizarre Truths", "type": "bizarre_truth", "topic": "The Mechanical Turk: A Chess Robot That Was Actually a Human", "truth": "In 1770, Wolfgang von Kempelen unveiled a machine that could beat grandmasters at chess. It toured Europe for 84 years. It was a hoax — a hidden chess master inside the cabinet made every move.", "wikipedia_title": "The Turk", "wikipedia_url": "https://en.wikipedia.org/wiki/The_Turk"},
      {"id": "B12", "category": "Bizarre Truths", "type": "bizarre_truth", "topic": "Lobsters Were Once Considered Garbage Food — Fed to Prisoners", "truth": "In 17th–18th century America, lobster was so abundant and low-status it was used as fertilizer and fed to prisoners. Inmates reportedly rioted over being served it too often.", "wikipedia_title": "Lobster", "wikipedia_url": "https://en.wikipedia.org/wiki/Lobster#As_food"},
      {"id": "B13", "category": "Bizarre Truths", "type": "bizarre_truth", "topic": "Pluto Has Not Completed One Orbit Since Its Discovery", "truth": "Pluto takes 248 Earth years to orbit the Sun. Discovered in 1930, it won't complete its first full orbit since discovery until 2178.", "wikipedia_title": "Pluto", "wikipedia_url": "https://en.wikipedia.org/wiki/Pluto"},
      {"id": "B14", "category": "Bizarre Truths", "type": "bizarre_truth", "topic": "The Great Fire of London Officially Killed Only 6 People", "truth": "The 1666 fire destroyed 13,000 houses, 87 churches, and St. Paul's Cathedral — yet official death records list only 6 fatalities. Historians suspect the real toll was far higher but the poor went unrecorded.", "wikipedia_title": "Great Fire of London", "wikipedia_url": "https://en.wikipedia.org/wiki/Great_Fire_of_London"}
    ]
  }
}
'''

data = json.loads(topics_json)
items = data['content_topics']['myths_and_truths']

conn = sqlite3.connect(DB)
cur = conn.cursor()

imported = 0
skipped_dupe = 0
skipped_published = 0
errors = 0

# Get all existing topics for dedup
cur.execute("SELECT id, topic FROM audit_history WHERE published_to_yt = 1")
published_topics = {row[1].lower(): row[0] for row in cur.fetchall()}

def sig_words(s):
    stop = {'the','is','a','an','in','of','to','and','that','are','was','for','you','your','this','its','not','has','been','have','can','does','did','with','from','about','all','but','just','like','our','out','than','then','we','were','they','them','their','its','also','very','only','more','less','much','many','some','any','each','every','both','few','most','other','such','no','nor','or','so','if','at','by','on','up','off','over','under','again','further','then','once','here','there','when','where','why','how','which','who','whom','what'}
    return {w.lower().rstrip('s') for w in s.replace("'", "").replace('"', '').replace(',', '').replace('.', '').replace('!', '').replace('?', '').split() if w.lower() not in stop and len(w) > 2}

print(f"Processing {len(items)} topics...\n")

for item in items:
    item_id = item.get('id', '?')
    ctype = item['type']
    category = item['category']
    
    # Get topic name
    topic = item.get('myth') or item.get('topic', '')
    truth = item.get('truth', '')
    wiki = item.get('wikipedia_title', '')
    
    # Check against published topics
    tw = sig_words(topic)
    is_dupe = False
    for ptopic, pid in published_topics.items():
        pw = sig_words(ptopic)
        if tw and pw and len(tw & pw) / min(len(tw), len(pw)) > 0.4:
            is_dupe = True
            print(f"  [{item_id}] SKIP (duplicate): '{topic[:60]}'")
            print(f"       → matches published #{pid}: '{ptopic[:60]}'")
            skipped_published += 1
            break
    
    if is_dupe:
        continue
    
    # Check if already in DB
    cur.execute("SELECT id FROM audit_history WHERE topic = ?", (topic,))
    existing = cur.fetchone()
    if existing:
        # Update to unpublished if it was accidentally locked
        cur.execute("UPDATE audit_history SET published_to_yt = 0, content_type = ? WHERE id = ?", (ctype, existing[0]))
        print(f"  [{item_id}] EXISTS (unlocked): '{topic[:60]}'")
        imported += 1
        continue
    
    # Insert
    script_hook = f"{category}: {truth[:200]}"
    try:
        cur.execute("""
            INSERT INTO audit_history (topic, script_hook, content_type, published_to_yt, pipeline_version)
            VALUES (?, ?, ?, 0, 'user_curated_v1')
        """, (topic, script_hook, ctype))
        conn.commit()
        imported += 1
        print(f"  [{item_id}] IMPORTED [{ctype}]: '{topic[:60]}'")
    except sqlite3.IntegrityError as e:
        print(f"  [{item_id}] ERROR: {e}")
        errors += 1

conn.close()
print(f"\n{'='*60}")
print(f"Imported: {imported} | Skipped (published dupe): {skipped_published} | Errors: {errors}")
print(f"Total new available: {imported}")

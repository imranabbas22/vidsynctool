# =============================================================================
# "The Daily Audit" - Data Ingestion & Topic Selection Module
# =============================================================================
import os
import sqlite3
import random
from typing import List, Tuple, Optional

# Predefined premium academic misconceptions to bootstrap the system
# Curated for surprising, counterintuitive debunks that educated adults genuinely believe.
# Categories expanded beyond Physics/Biology/History to include Astronomy, Neuroscience,
# Economics, Psychology, Technology, Chemistry, Geology, Linguistics, and Anthropology.
BOOTSTRAP_MYTHS = [
    ("Napoleon's troops shot the nose off the Sphinx", "History", "The Sphinx's nose was documented missing in 15th-century drawings by Frederic Louis Norden — two centuries before Napoleon was born, likely removed by iconoclastic Sufi zealot Muhammad Sa'im al-Dahr in 1378."),
    ("The Pyramids were built by slaves", "History", "Archaeological excavations of worker tombs and bakeries near the pyramids prove the builders were paid Egyptian laborers, not slaves — they worked in rotating seasonal shifts."),
    ("The brain is hardwired and does not change after childhood", "Neuroscience", "Neuroplasticity research since the 1980s demonstrates the brain continuously rewires itself — London taxi drivers grow larger hippocampi from memorizing streets."),
    ("Humans have five senses", "Neuroscience", "Humans possess at least nine senses including proprioception (body position), thermoception (temperature), nociception (pain), equilibrioception (balance), and interoception (internal organ state)."),
    ("Diamonds are formed from compressed coal", "Geology", "Most natural diamonds formed 1-3 billion years ago at depths of 150-200 km, long before terrestrial plants existed. Coal is sedimentary rock; diamonds are crystallized mantle carbon from ancient magma."),
    ("Bats are blind", "Biology", "All bat species have functional eyes, and many fruit bats have excellent night vision. The phrase 'blind as a bat' is biologically false — microbats use echolocation but can see."),
    ("The Great Wall of China is the only man-made structure visible from space", "Astronomy", "The Great Wall is invisible from low Earth orbit. Many man-made structures are visible: city grids, airports, dams, and the Palm Islands in Dubai."),
    ("There is a dark side of the Moon", "Astronomy", "The Moon has a 'far side' constantly facing away from Earth, but it receives equal sunlight. No permanently dark hemisphere exists — both sides experience 14 Earth-day days and nights."),
    ("Ostriches bury their heads in the sand", "Biology", "Ostriches do not bury their heads. When threatened, they lie flat against the ground to blend in. The myth originated from Roman naturalist Pliny the Elder's inaccurate observations."),
    ("Toilet water flushes backward in the Southern Hemisphere", "Physics", "The Coriolis effect only influences large-scale weather systems (thousands of km). Toilet water direction is determined by bowl shape, jet angles, and turbulence — not the Earth's rotation."),
    ("Humans only use 10 percent of the brain", "Neuroscience", "Functional MRI and PET scans show nearly all brain regions have identifiable functions. Even during rest, the default mode network is active. The 10% myth is a self-help motivational fiction."),
    ("The 'five-second rule' makes dropped food safe", "Biology", "Bacteria transfer to food nearly instantaneously on contact. In a 2016 Rutgers study, some foods showed contamination within one second. Moisture content and surface type matter far more than timing."),
    ("Shaving causes hair to grow back thicker", "Biology", "Shaved hair has a blunt tip, making it feel coarser when growing back. Actual hair thickness and color are determined by the follicle bulb — shaving has no effect on follicle structure."),
    ("Different tongue regions detect different tastes", "Neuroscience", "The tongue map is debunked by Virginia Collings' 1974 study. All taste qualities (sweet, sour, salty, bitter, umami) are detected across all tongue regions via distributed taste bud receptors."),
    ("Money is the primary motivator at work", "Economics", "Dan Pink's research synthesizing 50 years of behavioral science shows autonomy, mastery, and purpose drive performance. Beyond a threshold, more money does not increase motivation — it decreases it."),
    ("Goldfish have a three-second memory", "Biology", "Goldfish demonstrate long-term memory in controlled studies — they can be trained to push levers for food and remember the task months later. The myth originated from 19th-century carnival speculation."),
    ("Cracking your knuckles causes arthritis", "Biology", "Dr. Donald Unger cracked the knuckles of his left hand twice daily for 50 years while never cracking his right. A 2011 study of 215 people confirmed no correlation between cracking and arthritis."),
    ("Left-brained people are logical, right-brained are creative", "Neuroscience", "Functional imaging shows both hemispheres cooperate on all tasks. The left-right personality dichotomy was exaggerated from Roger Sperry's split-brain studies and has no basis in modern neuroscience."),
    ("Humans evolved from chimpanzees", "Biology", "Humans and chimpanzees share a common ancestor 6-8 million years ago. Modern chimps evolved separately. We are not descended from chimps any more than chimps are descended from us."),
    ("Dropping a penny from a skyscraper can kill someone", "Physics", "A penny's terminal velocity is only about 30-50 km/h due to air resistance and low mass. At that speed, it might sting but cannot penetrate skin or crack bone."),
]

BOOTSTRAP_BIZARRE = [
    ("The Taured Man", "Anthropology", "In 1954, a well-dressed man arrived at Tokyo's Haneda Airport from a country called 'Taured' that does not exist on any map. He showed passports from this nation, was detained, and mysteriously vanished overnight."),
    ("The Wow! Signal", "Astronomy", "In 1977, astronomer Jerry Ehman detected a 72-second narrowband radio signal from the Sagittarius constellation so precisely matching SETI's expected signature that he circled it and wrote 'Wow!' on the printout. It has never been detected again."),
    ("Kryptos — The Unsolved Sculpture Cipher", "Technology", "In 1990, the CIA unveiled a copper sculpture at Langley containing a 865-character encrypted message. Three of its four sections have been decrypted; the final 97-character passage remains unsolved, and the CIA itself has not released the solution."),
    ("The Great London Beer Flood", "History", "On October 17, 1814, a 15-meter-tall wooden fermentation vat at the Meux Brewery ruptured, causing a chain reaction that released over 1.4 million liters of beer. The wave destroyed two houses and killed eight people."),
    ("The Phantom Time Hypothesis", "History", "A fringe theory proposed by German historian Heribert Illig argues that the years 614–911 AD (297 years) were fabricated by Holy Roman Emperor Otto III and Pope Sylvester II to align their reigns with the millennium."),
    ("Quantum Biology — The Avian Compass", "Physics", "European robins and other migratory birds detect Earth's magnetic field using a quantum mechanical process in their eyes. Cryptochrome proteins create entangled radical pairs whose chemical yield changes with magnetic orientation — quantum coherence at room temperature."),
    ("The Loneliest Whale", "Biology", "Known as '52-Hertz,' a whale has been tracked since 1989 calling at 52 Hz — far above the 15-25 Hz of blue whales and the 50 Hz of fin whales. It has been called the loneliest whale because no other whale can hear its song."),
    ("Gypsy Moth Pheromone Infestation Catastrophe", "Biology", "In an attempt to eradicate the gypsy moth in the 1860s, French biologist Leopold Trouvelot imported European specimens to Massachusetts. Some escaped, leading to an ongoing multi-billion-dollar invasive infestation still spanning the entire northeastern United States today."),
    ("The Tunguska Event", "Geology", "On June 30, 1908, a 50-80 meter asteroid or comet exploded 5-10 km above the Podkamennaya Tunguska River in Siberia, flattening 2,000 square kilometers of forest. The blast was 1,000 times more powerful than Hiroshima. No impact crater was ever found."),
    ("The Shroud of Turin Carbon Dating Controversy", "Physics", "The 1988 radiocarbon dating of the Shroud of Turin gave a 1260-1390 AD date, but subsequent peer-reviewed papers argue the sample was taken from a 16th-century repair patch. In 2005, a chemical analysis found vanillin levels suggesting a much older age."),
]

class DataIngestion:
    """Manages SQLite database logging and selects unique scientific/historical misconceptions."""
    
    def __init__(self, db_path: Optional[str] = None):
        if db_path is None:
            # Place database in app_build/database/
            base_dir = os.path.dirname(os.path.abspath(__file__))
            db_dir = os.path.join(base_dir, "database")
            os.makedirs(db_dir, exist_ok=True)
            self.db_path = os.path.join(db_dir, "audit_history.db")
        else:
            self.db_path = db_path
            
        self._init_db()

    def _init_db(self):
        """Initializes the audit_history table if it does not exist."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS audit_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    topic TEXT NOT NULL UNIQUE,
                    script_hook TEXT NOT NULL,
                    style_preset TEXT DEFAULT '',
                    video_type TEXT DEFAULT '',
                    transition_type TEXT DEFAULT '',
                    date_uploaded TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)
            # Migrate existing tables: add columns if missing
            cursor.execute("PRAGMA table_info(audit_history)")
            existing_cols = {row[1] for row in cursor.fetchall()}
            for col, definition in [
                ("style_preset", "TEXT DEFAULT ''"),
                ("video_type", "TEXT DEFAULT ''"),
                ("transition_type", "TEXT DEFAULT ''"),
            ]:
                if col not in existing_cols:
                    try:
                        cursor.execute(f"ALTER TABLE audit_history ADD COLUMN {col} {definition}")
                        print(f"[Ingestion] Migrated database: added column '{col}'")
                    except Exception as e:
                        print(f"[Ingestion] Migration note: could not add column '{col}': {e}")
            conn.commit()

    def _normalize_topic_tokens(self, text: str) -> set:
        """Normalizes text by lowercasing, removing punctuation, and filtering common stopwords."""
        import re
        stopwords = {
            'a', 'about', 'above', 'after', 'again', 'against', 'all', 'am', 'an', 'and', 'any', 'are', 'aren', 't',
            'as', 'at', 'be', 'because', 'been', 'before', 'being', 'below', 'between', 'both', 'but', 'by', 'can',
            'cannot', 'could', 'couldn', 'did', 'didn', 'do', 'does', 'doesn', 'doing', 'don', 'down', 'during',
            'each', 'few', 'for', 'from', 'further', 'had', 'hadn', 'has', 'hasn', 'have', 'haven', 'having', 'he',
            'her', 'here', 'hers', 'herself', 'him', 'himself', 'his', 'how', 'i', 'if', 'in', 'into', 'is', 'isn',
            'it', 'its', 'itself', 'me', 'more', 'most', 'must', 'my', 'myself', 'no', 'nor', 'not', 'of', 'off',
            'on', 'once', 'only', 'or', 'other', 'our', 'ours', 'ourselves', 'out', 'over', 'own', 'same', 'she',
            'should', 'shouldn', 'so', 'some', 'such', 'than', 'that', 'the', 'their', 'theirs', 'them', 'themselves',
            'then', 'there', 'these', 'they', 'this', 'those', 'through', 'to', 'too', 'under', 'until', 'up', 'very',
            'was', 'wasn', 'we', 'were', 'weren', 'what', 'when', 'where', 'which', 'while', 'who', 'whom', 'why',
            'with', 'won', 'would', 'wouldn', 'you', 'your', 'yours', 'yourself', 'yourselves'
        }
        # Lowercase and replace non-alphanumeric chars with spaces
        text_clean = re.sub(r'[^a-zA-Z0-9\s]', ' ', text.lower())
        tokens = [w.strip() for w in text_clean.split() if w.strip()]
        # Filter stopwords
        content_tokens = {w for w in tokens if w not in stopwords}
        return content_tokens

    def _is_similar(self, topic1: str, topic2: str) -> bool:
        """Determines if two topics are semantically or lexically similar based on token overlaps."""
        tokens1 = self._normalize_topic_tokens(topic1)
        tokens2 = self._normalize_topic_tokens(topic2)
        if not tokens1 or not tokens2:
            return False
        
        intersection = tokens1.intersection(tokens2)
        union = tokens1.union(tokens2)
        
        jaccard = len(intersection) / len(union) if len(union) > 0 else 0
        min_len = min(len(tokens1), len(tokens2))
        containment = len(intersection) / min_len if min_len > 0 else 0
        
        # Deduplicate if Jaccard similarity is > 0.45 or Containment is > 0.70 (with at least 2 tokens)
        if jaccard > 0.45:
            return True
        if containment > 0.70 and len(intersection) >= 2:
            return True
        return False

    def is_topic_used(self, topic: str, check_bootstrap: bool = False) -> bool:
        """Checks if a topic has already been logged (normalizes unicode dashes/quotes)."""
        normalized = topic.replace('\u2014', ' - ').replace('\u2013', ' - ').replace('\u2019', "'").strip()
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT topic FROM audit_history")
            db_topics = [row[0] for row in cursor.fetchall()]
            
        target_lower = topic.lower().strip()
        target_norm_lower = normalized.lower().strip()
        
        # Check against database history
        for db_topic in db_topics:
            db_lower = db_topic.lower().strip()
            db_norm = db_topic.replace('\u2014', ' - ').replace('\u2013', ' - ').replace('\u2019', "'").strip().lower()
            if db_lower == target_lower or db_norm == target_norm_lower:
                return True
            if self._is_similar(topic, db_topic):
                return True
                
        # Optional: check against bootstrap lists to prevent duplicating preset options
        if check_bootstrap:
            bootstrap_topics = [t for t, _, _ in BOOTSTRAP_MYTHS] + [t for t, _, _ in BOOTSTRAP_BIZARRE]
            for bs_topic in bootstrap_topics:
                bs_lower = bs_topic.lower().strip()
                bs_norm = bs_topic.replace('\u2014', ' - ').replace('\u2013', ' - ').replace('\u2019', "'").strip().lower()
                if bs_lower == target_lower or bs_norm == target_norm_lower:
                    return True
                if self._is_similar(topic, bs_topic):
                    return True
                    
        return False

    def log_uploaded_topic(self, topic: str, hook: str,
                            style_preset: str = "", video_type: str = "",
                            transition_type: str = ""):
        """
        Logs a topic to prevent duplicates. Updates hook if already logged.
        Records A/B test metadata (style preset, video type, transition type)
        for correlation with analytics data.
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """INSERT INTO audit_history (topic, script_hook, style_preset, video_type, transition_type)
                   VALUES (?, ?, ?, ?, ?)
                   ON CONFLICT(topic) DO UPDATE SET
                       script_hook = excluded.script_hook,
                       style_preset = COALESCE(NULLIF(excluded.style_preset, ''), style_preset),
                       video_type = COALESCE(NULLIF(excluded.video_type, ''), video_type),
                       transition_type = COALESCE(NULLIF(excluded.transition_type, ''), transition_type)
                   WHERE excluded.script_hook != ''""",
                (topic, hook, style_preset, video_type, transition_type)
            )
            conn.commit()

    def get_next_bootstrap_topic(self) -> Optional[Tuple[str, str, str]]:
        """Retrieves the next unused misconception from the pre-defined bootstrap list."""
        shuffled = list(BOOTSTRAP_MYTHS)  # Copy to avoid mutating shared global
        random.shuffle(shuffled)
        for topic, category, description in shuffled:
            if not self.is_topic_used(topic):
                return topic, category, description
        return None

    def fetch_unused_misconception(self, gemini_client=None) -> Tuple[str, str, str]:
        """
        Main interface to fetch the next unused misconception.
        If all bootstrap myths are exhausted, it utilizes the Gemini Client to generate
        a set of new unique academic myths. If that fails, it raises an exception to end the script.
        """
        bootstrap = self.get_next_bootstrap_topic()
        if bootstrap:
            return bootstrap

        # Fallback: bootstrap registry exhausted, generate dynamic topic using Gemini
        if gemini_client is None:
            raise RuntimeError(
                "[Ingestion] Predefined bootstrap myths are exhausted, but no Gemini Client was provided "
                "to generate new topics dynamically."
            )

        print("[Ingestion] Predefined myths exhausted. Autonomously generating a new myth using Gemini...")
        try:
            new_myth = self._generate_dynamic_myth_via_gemini(gemini_client)
            if new_myth:
                return new_myth
            else:
                raise RuntimeError(
                    "[Ingestion] Gemini returned an empty or invalid myth format (expected Topic|Category|Description)."
                )
        except Exception as e:
            raise RuntimeError(f"[Ingestion] Autonomously generating a new myth failed: {e}") from e

    def _verify_topic_robustness(self, topic: str, category: str, description: str, gemini_client) -> bool:
        """
        Uses Gemini to verify that the generated topic is factually true, scientifically/historically robust,
        highly engaging, and not a trivial or commonly known fact.
        """
        prompt = (
            f"You are a strict, elite fact-checker and content quality editor.\n"
            f"Analyze the following proposed topic for an educational video:\n"
            f"Topic: {topic}\n"
            f"Category: {category}\n"
            f"Description: {description}\n\n"
            f"Evaluate based on these rules:\n"
            f"1. Is the debunk or claim 100% factually correct and supported by solid historical or scientific evidence? (It must contain truth, no pseudoscience or unverified speculation).\n"
            f"2. Is it a 'genius' topic? (i.e. is it counterintuitive, highly surprising, and intellectually stimulating, rather than boring or common knowledge?)\n"
            f"3. Is the topic description clear, accurate, and direct?\n\n"
            f"Respond strictly in one of these two formats:\n"
            f"VALID|Reason why this is a high-quality, verified, and surprising topic.\n"
            f"INVALID|Reason why it fails (e.g. factually incorrect, too common, boring, or speculative).\n"
            f"Do not include any other markdown, labels, or formatting."
        )
        try:
            response = gemini_client.models.generate_content(
                model='gemini-2.5-flash',
                contents=prompt
            )
            text = response.text.strip()
            if text.startswith("VALID|"):
                print(f"[Ingestion] Topic validation PASSED: {text[6:]}")
                return True
            else:
                reason = text[8:] if text.startswith("INVALID|") else text
                print(f"[Ingestion] Topic validation FAILED: {reason}")
                return False
        except Exception as e:
            # If the validation API call fails, we log it and fallback to True so we don't block execution
            print(f"[Ingestion] Topic validation failed to execute API call: {e}. Defaulting to True.")
            return True

    def _generate_dynamic_myth_via_gemini(self, gemini_client) -> Optional[Tuple[str, str, str]]:
        """Invokes Gemini to generate a novel historical/scientific myth not present in database."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT topic FROM audit_history")
            used_topics = [row[0] for row in cursor.fetchall()]

        # Include both DB and bootstrap lists in exclusions
        bootstrap_topics = [t for t, _, _ in BOOTSTRAP_MYTHS] + [t for t, _, _ in BOOTSTRAP_BIZARRE]
        all_exclusions = used_topics + bootstrap_topics
        exclusion_str = ", ".join(all_exclusions) if all_exclusions else "None"
        
        prompt = (
            f"Generate a single extremely robust, intellectually premium ('genius'), and counterintuitive misconception "
            f"that educated adults genuinely believe, which contains clear scientific or historical truth. "
            f"Choose from: Physics, Biology, History, Astronomy, Neuroscience, Psychology, Economics, Geology, Chemistry, Technology, Linguistics, Anthropology.\n"
            f"Requirements:\n"
            f"1. Absolutely must NOT be semantically similar to or cover the same subject/event as any of these topics: [{exclusion_str}]\n"
            f"2. The misconception must be rigorously true and backed by verifiable academic sources (science or history).\n"
            f"3. Avoid cliché, overused, or simple myths (e.g. Einstein failing math, 10% brain myth, goldfish memory, glass flowing, toilet flush Coriolis effect, humans having 5 senses, pyramids built by slaves, Napoleon's sphinx nose).\n"
            f"4. Output strictly in the format: Topic|Category|ShortDescription\n"
            f"5. Do not include markdown, wrappers, or extra explanation."
        )
        
        for attempt in range(3):
            response = gemini_client.models.generate_content(
                model='gemini-2.5-flash',
                contents=prompt
            )
            text = response.text.strip()
            parts = text.split('|')
            if len(parts) >= 3:
                topic, category, description = parts[0].strip(), parts[1].strip(), parts[2].strip()
                normalized = topic.replace('\u2014', ' - ').replace('\u2013', ' - ').replace('\'', "'").strip()
                if not self.is_topic_used(normalized, check_bootstrap=True) and not self.is_topic_used(topic, check_bootstrap=True):
                    if self._verify_topic_robustness(topic, category, description, gemini_client):
                        return topic, category, description
        
        return None

    def fetch_unused_bizarre_topic(self, gemini_client=None) -> Tuple[str, str, str]:
        """
        Retrieves the next unused bizarre fact anomaly. If bootstrap list is exhausted,
        it utilizes Gemini to discover a novel bizarre fact/anomaly.
        """
        shuffled = list(BOOTSTRAP_BIZARRE)  # Copy to avoid mutating shared global
        random.shuffle(shuffled)
        for topic, category, description in shuffled:
            if not self.is_topic_used(topic):
                return topic, category, description

        if gemini_client is None:
            raise RuntimeError("[Ingestion] Predefined bootstrap bizarre facts are exhausted, but no Gemini Client was provided.")

        print("[Ingestion] Predefined bizarre facts exhausted. Autonomously generating a new anomaly topic using Gemini...")
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT topic FROM audit_history")
            used_topics = [row[0] for row in cursor.fetchall()]

        bootstrap_topics = [t for t, _, _ in BOOTSTRAP_MYTHS] + [t for t, _, _ in BOOTSTRAP_BIZARRE]
        all_exclusions = used_topics + bootstrap_topics
        exclusion_str = ", ".join(all_exclusions) if all_exclusions else "None"
        
        prompt = (
            f"Find a single bizarre, obscure, but rigorously verified scientific or historical anomaly "
            f"that most educated adults have never heard of. "
            f"Choose from: Physics, Biology, History, Astronomy, Neuroscience, Psychology, Economics, Geology, Chemistry, Technology, Linguistics, Anthropology.\n"
            f"Requirements:\n"
            f"1. Absolutely must NOT be semantically similar to or cover the same subject/event as any of these topics: [{exclusion_str}]\n"
            f"2. The anomaly must contain verifiable truth and have specific names, dates, or academic sources.\n"
            f"3. Avoid cliché anomalies (e.g. the Dancing Plague, Emu War, Coelacanth, Vela Incident, Tunguska Event, Taured Man, Wow! Signal, Kryptos sculpture, London Beer Flood, Phantom Time Hypothesis).\n"
            f"4. Output strictly in the format: AnomalyName|Category|Brief 1-sentence description\n"
            f"5. Do not include markdown, wrappers, or extra explanation."
        )
        for attempt in range(3):
            response = gemini_client.models.generate_content(
                model='gemini-2.5-flash',
                contents=prompt
            )
            text = response.text.strip()
            parts = text.split('|')
            if len(parts) >= 3:
                topic, category, description = parts[0].strip(), parts[1].strip(), parts[2].strip()
                if not self.is_topic_used(topic, check_bootstrap=True):
                    if self._verify_topic_robustness(topic, category, description, gemini_client):
                        return topic, category, description
        
        # Fallback with dynamic suffix to prevent repeats
        fallback_topic = f"Bizarre Anomaly #{len(used_topics) + 1}"
        return fallback_topic, "Physics", "A dynamically generated mystery awaiting investigation."


if __name__ == "__main__":
    # Self-test database creation
    ingestion = DataIngestion()
    print("Database absolute path:", ingestion.db_path)
    topic = ingestion.fetch_unused_misconception()
    print("Selected Misconception:", topic)

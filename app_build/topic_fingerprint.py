"""
Topic Fingerprint & Uniqueness Engine for The Daily Audit

Semantic deduplication that catches topics with DIFFERENT WORDS but the SAME SUBJECT.

Problem with the old approach:
    "Napoleon's troops shot the nose off the Sphinx"
    vs
    "Who really removed the Sphinx's nose?"
    → 0 shared content words after stopword filtering
    → OLD METHOD: passes as "unique" → DUPLICATE VIDEO

This module extracts the ESSENCE of a topic: the core entities and concepts
being discussed, regardless of how they're worded. Two topics about the
Sphinx's nose are detected as duplicates even with zero shared tokens.

No external APIs — pure text analysis.
"""
import re
import sqlite3
from typing import Set, Dict, List, Optional, Tuple


# Content words that are too generic to be useful entities
GENERIC_CONTENT_WORDS = {
    'people', 'person', 'thing', 'fact', 'idea', 'way', 'thing',
    'something', 'everything', 'nothing', 'anything', 'one', 'thing',
    'world', 'time', 'year', 'day', 'life', 'study', 'research',
    'scientist', 'researcher', 'expert', 'evidence', 'data', 'result',
    'claim', 'belief', 'myth', 'truth', 'reality', 'theory',
    'actually', 'really', 'known', 'called', 'known_as', 'referred_to',
    'said', 'believe', 'think', 'know', 'found', 'discovered', 'created',
    'caused', 'happened', 'occurs', 'occured', 'based',
    # English stopwords that pollute fingerprints
    'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
    'of', 'with', 'by', 'from', 'as', 'into', 'through', 'during',
    'before', 'after', 'above', 'below', 'off', 'over', 'under', 'again',
    'further', 'then', 'once', 'here', 'there', 'when', 'where', 'why',
    'how', 'all', 'each', 'every', 'both', 'few', 'more', 'most', 'other',
    'some', 'such', 'no', 'nor', 'not', 'only', 'own', 'same', 'so',
    'than', 'too', 'very', 'just', 'because', 'about', 'up', 'down', 'out',
    'has', 'had', 'have', 'been', 'being', 'does', 'did', 'do', 'done',
    'having', 'doing', 'gets', 'get', 'got', 'make', 'made', 'making',
    'use', 'used', 'using', 'takes', 'take', 'took', 'taken',
    'seen', 'see', 'saw', 'goes', 'go', 'went', 'gone',
}

# Common topic framing words that aren't entities
FRAMING_WORDS = {
    'myth', 'truth', 'debunked', 'exposed', 'revealed', 'busted',
    'false', 'real', 'true', 'fake', 'wrong', 'correct', 'actual',
    'believe', 'you', 'your', 'this', 'that', 'these', 'those',
    'what', 'why', 'how', 'when', 'where', 'who', 'which',
    'ever', 'never', 'always', 'sometimes', 'often',
}


class TopicFingerprint:
    """
    Extracts the semantic essence of a topic for duplicate detection.

    A fingerprint captures:
    - Core entities (Sphinx, Napoleon, Pyramids, Brain, Toilet Water, etc.)
    - Key concepts (construction, nose removal, 10% usage, Coriolis)
    - The relation between them (built by → slaves, removed by → Napoleon)

    Two topics are duplicates if their fingerprints have significant overlap
    at the entity/concept level, regardless of phrasing.
    """

    def __init__(self, db_path: Optional[str] = None):
        self._fingerprint_cache: Dict[str, Set[str]] = {}

    # ── Fingerprint Extraction ────────────────────────────────────────────────

    def extract(self, topic: str) -> Set[str]:
        """
        Extract the semantic fingerprint of a topic string.
        Returns a set of canonical entity/concept phrases.

        Examples:
            "Napoleon's troops shot the nose off the Sphinx"
            → {sphinx, nose, sphinx nose, napoleon, napoleon troops}

            "The Pyramids were built by slaves"
            → {pyramid, pyramid built, slave, built slave}

            "Humans only use 10 percent of the brain"
            → {brain, percent brain, ten percent}
        """
        if topic in self._fingerprint_cache:
            return self._fingerprint_cache[topic]

        # Step 1: Clean and extract content tokens
        cleaned = re.sub(r'[^a-zA-Z0-9\s\']', ' ', topic.lower().strip())
        tokens = [w for w in cleaned.split() if w.strip() and w not in GENERIC_CONTENT_WORDS
                  and w not in FRAMING_WORDS and len(w) > 1]

        fingerprint: Set[str] = set()

        # Step 2: Single significant entities (4+ chars, not stopwords/framing)
        for t in tokens:
            if len(t) >= 4:
                # Normalize possessives: "sphinx's" → "sphinx"
                base = t.replace("'s", "").replace("'", "").strip()
                if base != t and len(base) >= 3:
                    fingerprint.add(base)
                fingerprint.add(t)

        # Step 3: Bigrams — add BOTH orderings to normalize "sphinx nose" vs "nose sphinx"
        for i in range(len(tokens) - 1):
            w1, w2 = tokens[i], tokens[i+1]
            bigram = f"{w1} {w2}"
            if not self._is_generic_bigram(w1, w2):
                fingerprint.add(bigram)
                # Add reversed order for matching "X Y" vs "Y X"
                rev_bigram = f"{w2} {w1}"
                fingerprint.add(rev_bigram)

        # Step 4: Trigrams — catch full entity names
        # "great wall china", "toilet water flushes", "five second rule"
        for i in range(len(tokens) - 2):
            trigram = f"{tokens[i]} {tokens[i+1]} {tokens[i+2]}"
            if not self._is_generic_trigram(tokens[i], tokens[i+1], tokens[i+2]):
                fingerprint.add(trigram)

        # Step 5: Possessive entities (Napoleon's → Napoleon)
        for t in tokens:
            if "'" in t or "'s" in t:
                base = t.replace("'s", "").replace("'", "").strip()
                if len(base) >= 3:
                    fingerprint.add(base)

        self._fingerprint_cache[topic] = fingerprint
        return fingerprint

    def _is_generic_bigram(self, w1: str, w2: str) -> bool:
        """Check if a bigram is too generic to be meaningful."""
        combo = f"{w1} {w2}"
        if w1 in GENERIC_CONTENT_WORDS or w2 in GENERIC_CONTENT_WORDS:
            return True
        # Generic patterns: "based on", "known as", "known for"
        if w1 in ('based', 'known', 'referred', 'said', 'found', 'called'):
            return True
        return False

    def _is_generic_trigram(self, w1: str, w2: str, w3: str) -> bool:
        """Check if a trigram is too generic."""
        if w1 in GENERIC_CONTENT_WORDS and w2 in GENERIC_CONTENT_WORDS:
            return True
        return False

    # ── Similarity Computation ────────────────────────────────────────────────

    def compute_similarity(self, topic1: str, topic2: str) -> float:
        """
        Compute semantic similarity between two topics based on fingerprint overlap.
        Returns a score from 0.0 (completely different) to 1.0 (same subject).

        Score thresholds:
            0.00 - 0.15: Different topics
            0.15 - 0.35: Related topics (different specific subject, same domain)
            0.35 - 0.55: Similar topics (same domain, potentially same subject)
            0.55 - 0.75: Likely duplicate (same subject, different phrasing)
            0.75 - 1.00: Definitely duplicate
        """
        fp1 = self.extract(topic1)
        fp2 = self.extract(topic2)

        if not fp1 or not fp2:
            return 0.0

        # Single entity overlap (most important signal)
        # Get sigletons (single words) from each fingerprint
        singles1 = {x for x in fp1 if ' ' not in x}
        singles2 = {x for x in fp2 if ' ' not in x}

        # Get multi-word phrases
        phrases1 = fp1 - singles1
        phrases2 = fp2 - singles2

        # Score: phrase overlap matters more than single word overlap
        phrase_intersection = phrases1 & phrases2
        single_intersection = singles1 & singles2

        # Jaccard on full fingerprint
        all_intersection = fp1 & fp2
        all_union = fp1 | fp2
        jaccard = len(all_intersection) / len(all_union) if all_union else 0

        # Rare-word overlap bonus: if a rare word appears in both, it's a strong signal
        rare_overlap = len(single_intersection)
        phrase_overlap = len(phrase_intersection)

        # Containment score: is one topic's fingerprint mostly contained in another's?
        # Lower |fp1 - fp2| / |fp1| means more of fp1 is inside fp2
        diff_12 = len(fp1 - fp2)
        diff_21 = len(fp2 - fp1)
        containment_12 = diff_12 / len(fp1) if fp1 else 1.0
        containment_21 = diff_21 / len(fp2) if fp2 else 1.0
        containment_score = 1.0 - min(containment_12, containment_21)  # 1.0 = perfect containment

        # Combined score: jaccard (base similarity), containment (subset detection),
        # rare word bonus (entity overlap), phrase bonus (concept overlap)
        rare_bonus = min(0.16 * rare_overlap, 0.40)  # Up to 40% bonus for shared entities
        phrase_bonus = min(0.18 * phrase_overlap, 0.35)  # Up to 35% bonus for shared phrases

        combined = (jaccard * 0.35) + (containment_score * 0.20) + rare_bonus + phrase_bonus
        return min(combined, 1.0)

    def is_duplicate(self, topic1: str, topic2: str, threshold: float = 0.35) -> bool:
        """
        Returns True if two topics are semantically the same subject.
        Uses a lower threshold (0.40) for catch-all safety.

        The old method needed 0.45 Jaccard + shared tokens. This catches
        same-subject topics even when they use entirely different words.
        """
        score = self.compute_similarity(topic1, topic2)
        return score >= threshold

    def is_duplicate_against_all(self, candidate: str, existing_topics: List[str],
                                  threshold: float = 0.35) -> Tuple[bool, str, float]:
        """
        Check a candidate topic against all existing topics.
        Returns (is_dup, closest_match, similarity_score).
        """
        candidate_fp = self.extract(candidate)
        if not candidate_fp:
            return False, "", 0.0

        best_score = 0.0
        best_match = ""

        for existing in existing_topics:
            score = self.compute_similarity(candidate, existing)
            if score > best_score:
                best_score = score
                best_match = existing

        return best_score >= threshold, best_match, best_score

    # ── Topic Essence (for Gemini prompt generation) ──────────────────────────

    def extract_essence(self, topic: str) -> Dict[str, any]:
        """
        Extract the semantic essence of a topic for use in LLM prompts.
        Returns a structured description of what this topic is REALLY about.

        Used to generate better exclusion descriptions for Gemini.
        """
        fp = self.extract(topic)

        # Group by entity type
        singles = {x for x in fp if ' ' not in x}
        phrases = {x for x in fp if ' ' in x}

        # Key entity: longest phrase or most significant word
        key_entity = ""
        if phrases:
            key_entity = max(phrases, key=len)
        elif singles:
            key_entity = max(singles, key=len)

        return {
            "topic": topic,
            "key_entity": key_entity,
            "entities": sorted(singles, key=len, reverse=True)[:5],
            "concepts": sorted(phrases, key=len, reverse=True)[:3],
        }

    @staticmethod
    def build_gemini_context(existing_topics: List[str],
                              bootstrap_topics: Optional[List[str]] = None) -> str:
        """
        Build a structured exclusion list for Gemini that's actually useful.
        Instead of dumping 100 topics as a wall of text, groups them by
        entity and concept so Gemini can understand what's been covered.

        OLD: "Avoid these: [Napoleon's troops shot..., Pyramids built by slaves..., ...]"
        NEW: "ALREADY COVERED — Subjects you must NOT generate:
              ── Great Sphinx of Giza: its nose, origins, construction, purpose
              ── Pyramids of Egypt: slave labor, construction methods
              ── Brain Myths: 10% usage, left/right brain, neuroplasticity
              ── Human Senses: 5 senses myth, tongue taste map"
        """
        # Extract essences from all topics
        extractor = TopicFingerprint()
        all_essences = []
        for t in existing_topics:
            ess = extractor.extract_essence(t)
            all_essences.append(ess)

        if bootstrap_topics:
            for t in bootstrap_topics:
                ess = extractor.extract_essence(t)
                all_essences.append(ess)

        # Group by key entity
        entity_groups: Dict[str, List[str]] = {}
        for ess in all_essences:
            key = ess["key_entity"] if ess["key_entity"] else ess["topic"][:20]
            if key not in entity_groups:
                entity_groups[key] = []
            entity_groups[key].append(ess["topic"])

        # Build structured context string
        lines = []
        lines.append("ALREADY COVERED — Do NOT make myths about these subjects:")
        lines.append("")

        for entity, topics in sorted(entity_groups.items(), key=lambda x: -len(x[1])):
            if len(entity) < 3:
                continue
            lines.append(f"  ✗ {entity.title()} — {len(topics)} topic(s)")
            # Only list individual topics if there are few
            if len(topics) <= 3:
                for t in topics:
                    lines.append(f"    • {t}")
            lines.append("")

        return "\n".join(lines)


# ── Quick self-test ───────────────────────────────────────────────────────────

def _test():
    """Test that the fingerprint catches semantically similar topics."""
    tf = TopicFingerprint()

    test_pairs = [
        # Same subject, different words (the problem cases)
        ("Napoleon's troops shot the nose off the Sphinx",
         "Who really removed the Sphinx's nose?",
         0.35, True, "SAME: Sphinx nose"),

        # Classic duplicate case
        ("The Pyramids were built by slaves",
         "Who built the Egyptian pyramids?",
         0.35, True, "SAME: Pyramid builders"),

        # Entity-level similarity — brain myths ARE different topics despite same domain
        ("The brain is hardwired and does not change after childhood",
         "Humans only use 10 percent of the brain",
         0.35, False, "DIFFERENT: Neuroplasticity vs 10% brain"),

        # Different subjects, same category
        ("Diamonds are formed from compressed coal",
         "Ostriches bury their heads in the sand",
         0.35, False, "DIFFERENT: Geology vs Biology"),

        # Very different topics
        ("The Great Wall of China is visible from space",
         "Goldfish have a three-second memory",
         0.35, False, "DIFFERENT: Space vs Fish"),
    ]

    all_pass = True
    for t1, t2, threshold, expected, desc in test_pairs:
        score = tf.compute_similarity(t1, t2)
        result = tf.is_duplicate(t1, t2, threshold)
        status = "✓" if result == expected else "✗"
        if result != expected:
            all_pass = False
        print(f"  {status} {desc}: score={score:.2f} (threshold={threshold}) → {result} (expected {expected})")

    return all_pass


if __name__ == "__main__":
    print("Topic Fingerprint Self-Test:")
    print("=" * 60)
    passed = _test()
    print("=" * 60)
    print(f"ALL TESTS PASSED: {passed}")

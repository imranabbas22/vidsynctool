# =============================================================================
# "The Daily Audit" - LLM Orchestration & Script Generation Module
# =============================================================================
import os
import json
from typing import Dict, Any, Optional, Literal
from pydantic import BaseModel, Field

# Dynamic script types (used by generate_dynamic_script)
from research_agent import ResearchPlan, ScenePlan
from dynamic_script import DynamicScriptPayload, SceneContent

# ── Long-Form Script Schema ─────────────────────────────────────────
class LongChapterSection(BaseModel):
    title: str = Field(description="Short engaging chapter title (3-6 words, e.g., 'The Origin of the Lie', 'What Science Actually Says')")
    duration_seconds: int = Field(description="Target duration for this chapter's narration in seconds (45-90s range)")
    content: str = Field(description="The full narration text for this chapter. Written in simple, clear English. Start with a mini-hook, build understanding step by step, end with a chapter-specific insight that feeds into the next chapter. 60-120 words. No markdown, no SSML. Natural conversational tone like a great teacher explaining to a curious student.")
    visual_query: str = Field(description="Keyword query for Wikipedia/image search matching this chapter's content. Specific and descriptive (e.g., 'medieval anatomy diagram bloodletting', 'Einstein 1905 paper photoelectric effect')")
    key_takeaway: str = Field(description="One sentence summary of what the viewer should understand after this chapter. 10-15 words.")

class LongScriptPayload(BaseModel):
    topic: str = Field(description="The core topic of this long-form educational video")
    chapters: list[LongChapterSection] = Field(description="8 to 12 chapters that together form a complete 10-minute educational narrative. First chapter hooks, final chapter delivers the climax/reveal. Each chapter builds on the previous one.")
    climax: str = Field(description="The single most important sentence of the entire video. The moment everything clicks for the viewer. 15-25 words of pure insight.")
    youtube_title: str = Field(description="Compelling YouTube title for a 10-minute educational video. 40-60 characters. No #Shorts suffix.")
    youtube_description: str = Field(description="3-4 sentence description summarizing the video's value. Include educational context. End with relevant hashtags: #TheDailyAudit #Education #Science #Debunked")
    tags: list[str] = Field(description="10-15 SEO tags. Include: 3 broad (education, documentary, debunked), 5 topic-specific, and 2-3 channel tags.")

# Define target schemas for structured JSON response validation
class YouTubeMetadataSchema(BaseModel):
    title: str = Field(description="A compelling, attention-grabbing YouTube Shorts title ending with #Shorts")
    description: str = Field(description="Educational summary detailing the myth and reality, containing #TheDailyAudit and #Shorts")
    tags: list[str] = Field(description="List of 8-12 SEO-optimized tags. Include: 3 high-traffic broad tags (e.g., shorts, viral, debunked), 3 discipline tags (e.g., science, physics, biology, history), and 4-6 specific topic tags (e.g., coriolis, sink, water). All tags should be lowercase with no spaces.")

class ShortScriptPayload(BaseModel):
    topic: str = Field(description="The misconception being debunked")
    ssml_script: str = Field(
        description="The complete inner SSML script for 'The Auditor' — a sharp, confident, slightly smug investigator. "
                    "CRITICAL: This must sound like a PERSON talking to a friend, not an article being read. "
                    "Read your output aloud before submitting. If it sounds like a textbook or an AI wrote it, rewrite it. "
                    "Personality rules: "
                    "- Start with a conversational hook that grabs attention (e.g., 'Okay, this one is going to annoy you.' / 'You ready for this? Because it gets wild.' / 'I know you believe this. Everyone does. Here is why they are wrong.') "
                    "- Scene 2 should build tension with a surprising detail, delivered like you are letting them in on a secret "
                    "- Scene 3 is the mic drop — short, smug, satisfying "
                    "- Use contractions: 'you've', 'it's', 'don't', 'that's', 'here's', 'there's', 'they're' "
                    "- Sound like a specific person with opinions, not Wikipedia "
                    "- Never use: 'furthermore', 'it is worth noting', 'interestingly', 'notably', 'in fact', 'moreover', 'consequently', 'thus', 'this means that' "
                    "- Never use: 'studies show', 'scientists say', 'research indicates', 'according to experts' "
                    "- Use natural pauses with <break> tags — think about where a person would actually pause "
                    "- Each scene should be short enough to feel urgent"
    )
    myth_visual_prompt: str = Field(description="Visual prompt describing the misconception. MUST include: 'Style of a declassified government document, dark blue and white blueprint, highly detailed.'")
    fact_visual_prompt: str = Field(description="Visual prompt describing the actual scientific or historical truth. MUST include: 'Realistic, high-contrast, stark laboratory or historical archive photography, highly detailed.'")
    youtube_metadata: YouTubeMetadataSchema
    mid_roll_hook: Optional[str] = Field(default="",
        description="Optional 3-5 word mid-roll retention hook injected naturally into scene 2. "
        "Examples: 'But here is the twist...', 'Now pay attention...', "
        "'And get this...', 'Here is where it gets wild...', "
        "'But wait — it gets worse...', 'And here is the kicker...'"
        "This must feel completely natural, not forced. "
        "Return empty string if no natural insertion point exists.")
    comment_hook: str = Field(
        description="A provocative, question-oriented comment related to the topic to pin in the comments section. "
                    "Examples: 'What myth did YOUR teacher teach you?', 'Did you know this or did we just blow your mind?', 'What case should we audit next?'"
    )

class ShortBizarrePayload(BaseModel):
    topic: str = Field(description="The name of the bizarre historical/scientific anomaly")
    ssml_script: str = Field(
        description="The complete inner SSML script for a sharp, confident investigator who finds bizarre truths fascinating. "
                    "Rules: "
                    "- Scene 1 (hook/claim): 10 to 15 words — provocative, creates immediate curiosity. "
                    "- Scene 2 (explanation/context): 20 to 30 words — explain WHY it is bizarre, include one surprising detail, build tension. "
                    "- Scene 3 (truth/reveal): 12 to 18 words — the shocking truth, delivered with absolute finality and weight. "
                    "- Use <break time=\"700ms\"/> between scene 1 and scene 2 "
                    "- Use <break time=\"1200ms\"/> between scene 2 and scene 3 "
                    "- Capitalize words needing emphasis "
                    "- Use <emphasis level=\"strong\">word</emphasis> on the single most important word in each scene "
                    "- Return ONLY the inner SSML content, no speak or voice tags "
                    "- No markdown, no explanation, just the script. "
                    "- Do NOT start with 'Declassified file reveals' or 'Studies show'. "
                    "- Start Scene 1 with a provocative hook like: 'This sounds impossible — but it happened.' or 'Nobody talks about this. Here's why.' "
                    "- Use conversational punctuation: dashes, ellipses, rhetorical questions "
                    "Structure: "
                    "1. Scene 1: Hook/claim — 10–15 words "
                    "2. Scene 2: Explanation/context — 20–30 words "
                    "3. Scene 3: Truth/reveal — 12–18 words"
    )
    illustration_query: str = Field(description="Primary keyword query for a Wikipedia/Goolge photo (e.g., 'Coelacanth fish'). Used for thumbnail and scene 1.")
    scene_query_2: str = Field(default="", description="Keyword query for a photo matching the bizarre explanation (scene 2). Different from illustration_query.")
    scene_query_3: str = Field(default="", description="Keyword query for a photo matching the closing statement (scene 3). Different from the others.")
    youtube_metadata: YouTubeMetadataSchema
    mid_roll_hook: Optional[str] = Field(default="",
        description="Optional 3-5 word mid-roll retention hook injected naturally into scene 2. "
        "Examples: 'But here is the twist...', 'Now pay attention...', "
        "'And get this...', 'Here is where it gets wild...', "
        "'But wait — it gets worse...', 'And here is the kicker...'"
        "This must feel completely natural, not forced. "
        "Return empty string if no natural insertion point exists.")
    comment_hook: str = Field(
        description="A provocative, question-oriented comment related to the bizarre anomaly to pin in the comments section. "
                    "Examples: 'Would you have believed this actually happened?', 'What is the strangest mystery you know?', 'Do you think this file should have stayed classified?'"
    )

# ── Unified 5-Beat Script Schema ──────────────────────────────────────────

class DailyAuditScriptPayload(BaseModel):
    """Unified schema for all 4 content types with 5-beat structure.
    Word budget: 90-100 target, 110 max for Shorts 60s cap."""
    
    content_type: Literal["myth", "bizarre_truth", "hidden_truth", "paradox"] = Field(
        description="Content classification that determines hook formula and persona")
    topic: str = Field(description="The topic being debunked/explained/revealed")
    category: str = Field(description="Discipline: Biology, Physics, History, Neuroscience, etc.")
    
    beat1_hook: str = Field(description="COMPLICITY HOOK (12-20 words). Trap the viewer immediately.")
    beat2_pivot: str = Field(description="SENSORY CONFIRMATION + PIVOT (15-22 words). Must include 'Except' or 'But' as pivot.")
    beat3_mechanism: str = Field(description="MECHANISM WALK (30-45 words). Physical steps + one analogy using a familiar object.")
    beat4_reframe: str = Field(description="REFRAME LANDING (15-22 words). 'You weren't fooled by X — you were fooled by Y.'")
    beat5_signoff: str = Field(description="SIGN-OFF (5-10 words). 'Case closed.', 'File sealed.', 'Audit complete.'")
    
    visual_hook: str = Field(description="Image search query for beat 1 scene")
    visual_mechanism: str = Field(description="Image search query for beat 2-3 scenes")
    visual_reframe: str = Field(description="Image search query for beat 4 scene")
    
    youtube_metadata: YouTubeMetadataSchema
    comment_hook: str = Field(description="Provocative comment to pin on YouTube")
    mid_roll_hook: Optional[str] = Field(default="", description="Optional 3-5 word retention hook")
    word_count: Optional[int] = Field(default=0, description="Total words across all 5 beats")


class SmartModelsProxy:
    def __init__(self, parent_client):
        self.parent_client = parent_client

    def generate_content(self, *args, **kwargs):
        return self.parent_client.execute_with_failover("generate_content", *args, **kwargs)

    def generate_images(self, *args, **kwargs):
        return self.parent_client.execute_with_failover("generate_images", *args, **kwargs)

class SmartGeminiClient:
    def __init__(self, api_key: Optional[str] = None):
        self.free_key = os.getenv("FREE_GEMINI_API_KEY")
        self.paid_key = os.getenv("PAID_GEMINI_API_KEY")
        
        # Fallback to standard key if not explicitly set
        if not self.free_key:
            self.free_key = api_key or os.getenv("GEMINI_API_KEY")
            
        self.use_paid = False
        self.current_key = self.free_key if self.free_key else self.paid_key
        self.api_key = self.current_key
        
        self.models = SmartModelsProxy(self)
        self.client = None
        self._init_inner_client()

    def _init_inner_client(self):
        """Initializes/Re-initializes the underlying genai.Client."""
        from google import genai
        from google.genai import types
        
        self.api_key = self.current_key
        self.client = genai.Client(
            api_key=self.current_key,
            http_options=types.HttpOptions(timeout=30000)
        )

    def execute_with_failover(self, method_name: str, *args, **kwargs):
        free_attempts = 0
        max_free_attempts = 3
        
        paid_attempts = 0
        max_paid_attempts = 3
        
        while True:
            # If we've already permanently fallen back to paid tier, make sure client matches
            if self.use_paid and self.current_key != self.paid_key and self.paid_key:
                print("[SmartClient] Switching active API key to PAID tier...")
                self.current_key = self.paid_key
                self._init_inner_client()
                
            try:
                target_method = getattr(self.client.models, method_name)
                return target_method(*args, **kwargs)
            except Exception as e:
                err_str = str(e).lower()
                is_rate_limit = "429" in err_str or "resource exhausted" in err_str or "resource_exhausted" in err_str
                is_server_error = "503" in err_str or "unavailable" in err_str or "high demand" in err_str or "500" in err_str
                
                if is_rate_limit or is_server_error:
                    if not self.use_paid and self.paid_key:
                        free_attempts += 1
                        error_type = "429/Resource Exhausted" if is_rate_limit else "503/Unavailable"
                        print(f"[SmartClient] {error_type} on free tier attempt {free_attempts}/{max_free_attempts} using key ending in ...{self.current_key[-6:] if self.current_key else 'None'}")
                        
                        if free_attempts < max_free_attempts:
                            import time
                            wait_sec = free_attempts * 3
                            print(f"[SmartClient] Retrying free tier in {wait_sec}s...")
                            time.sleep(wait_sec)
                            continue
                        else:
                            print("[SmartClient] Free tier exhausted after 2 retries. Falling back to Paid tier.")
                            self.use_paid = True
                            self.current_key = self.paid_key
                            self._init_inner_client()
                            continue
                    else:
                        paid_attempts += 1
                        limit_label = "paid tier" if self.use_paid else "free/standard tier (no paid key available)"
                        error_type = "429/Resource Exhausted" if is_rate_limit else "503/Unavailable"
                        print(f"[SmartClient] {error_type} on {limit_label} attempt {paid_attempts}/{max_paid_attempts} using key ending in ...{self.current_key[-6:] if self.current_key else 'None'}")
                        
                        if paid_attempts < max_paid_attempts:
                            import time
                            time.sleep(3)
                            continue
                        raise e
                else:
                    raise e

class LLMOrchestrator:
    """Orchestrates script generation using Gemini, enforcing structured JSON and the channel's persona."""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = (
            api_key 
            or os.getenv("FREE_GEMINI_API_KEY") 
            or os.getenv("GEMINI_API_KEY") 
            or os.getenv("PAID_GEMINI_API_KEY")
        )
        if not self.api_key:
            raise ValueError("[LLM] No Gemini API key found. Please set FREE_GEMINI_API_KEY or GEMINI_API_KEY.")
        
        self.client = None
        self._init_client()
        self._orchestrator = None  # lazy-init PipelineOrchestrator

    def _init_client(self):
        """Initializes the SmartGeminiClient client wrapper."""
        try:
            self.client = SmartGeminiClient(api_key=self.api_key)
            print("[LLM] SmartGeminiClient initialized successfully.")
        except ImportError:
            print("[LLM] google-genai package not found. Attempting legacy google-generativeai fallback...")
            try:
                import google.generativeai as legacy_genai
                legacy_genai.configure(api_key=self.api_key)
                self.client = "legacy"
                print("[LLM] Legacy google-generativeai SDK initialized successfully.")
            except ImportError:
                raise ImportError("[LLM] Neither google-genai nor google-generativeai libraries could be imported.")

    def _parse_ssml_script(self, ssml_script: str, is_bizarre: bool = False) -> Dict[str, str]:
        """
        Parses the unified ssml_script back into individual plain text sentences
        for 3-scene content (hook, explanation/context, truth/reveal).
        No sign-off or 'Class dismissed' expected — those are handled by the ending bumper.
        Uses break tag boundaries (700ms and 1200ms) to segment the speech.
        """
        import re

        # Clean root speak/voice tags if generated
        clean_ssml = ssml_script.strip()
        for tag in ["<speak>", "</speak>"]:
            clean_ssml = clean_ssml.replace(tag, "")
        clean_ssml = re.sub(r'<voice[^>]*>', '', clean_ssml)
        clean_ssml = clean_ssml.replace('</voice>', '').strip()

        # Find all break tags
        break_pattern = r'<break\s+time=["\']([^"\']+)["\']\s*/>'
        matches = list(re.finditer(break_pattern, clean_ssml))

        def clean_text(t: str) -> str:
            t = re.sub(r'<[^>]+>', '', t).strip()
            t = re.sub(r'\[[\w\s_/-]+\]', '', t).strip()
            return re.sub(r'\s+', ' ', t)

        def clean_ssml_segment(t: str) -> str:
            # keep only <emphasis> tags, strip other XML tags
            t = re.sub(r'<(?!(?:/emphasis|emphasis)\b)[^>]+>', '', t).strip()
            return re.sub(r'\s+', ' ', t)

        if not matches:
            # Fallback: split into 3 sentences
            sentences_raw = [s.strip() for s in re.split(r'(?<=[.!?])\s+', clean_ssml) if s.strip()]
            while len(sentences_raw) < 3:
                sentences_raw.append("")
            s1_raw, s2_raw, s3_raw = sentences_raw[0], sentences_raw[1], sentences_raw[2]
        else:
            # Extract all text segments
            segments = []
            prev_end = 0
            for m in matches:
                segments.append(clean_ssml[prev_end:m.start()])
                prev_end = m.end()
            segments.append(clean_ssml[prev_end:])

            # Find index of the 1200ms break (separates scene 2 from scene 3)
            idx_1200 = -1
            for i, m in enumerate(matches):
                if "1200" in m.group(1):
                    idx_1200 = i
                    break

            # Find index of the 700ms break (separates scene 1 from scene 2)
            idx_700 = -1
            for i, m in enumerate(matches):
                if "700" in m.group(1):
                    idx_700 = i
                    break

            if idx_1200 == -1:
                idx_1200 = min(1, len(matches) - 1) if matches else 0

            # Determine which break comes first
            if idx_700 != -1 and idx_1200 != -1:
                first_break = min(idx_700, idx_1200)
                second_break = max(idx_700, idx_1200)

                if first_break == idx_700:
                    # 700ms is first, 1200ms is second
                    s1_raw = segments[0]
                    s2_raw = " ".join(segments[1:second_break + 1])
                    s3_raw = " ".join(segments[second_break + 1:]) if len(segments) > second_break + 1 else ""
                else:
                    # 1200ms is first, 700ms is second (unusual but handle it)
                    s1_raw = segments[0]
                    s2_raw = " ".join(segments[1:first_break + 1])
                    s3_raw = " ".join(segments[first_break + 1:]) if len(segments) > first_break + 1 else ""
            elif idx_1200 != -1:
                # Only 1200ms break found: 2 segments
                s1_raw = segments[0]
                s2_and_rest = " ".join(segments[1:]) if len(segments) > 1 else ""
                # Try to split s2_and_rest into two roughly
                s2_parts = s2_and_rest.split(". ")
                if len(s2_parts) >= 2:
                    s2_raw = s2_parts[0] + "."
                    s3_raw = ". ".join(s2_parts[1:])
                else:
                    s2_raw = s2_and_rest
                    s3_raw = ""
            else:
                s1_raw = segments[0] if segments else ""
                s2_raw = " ".join(segments[1:]) if len(segments) > 1 else ""
                s3_raw = ""

        if not is_bizarre:
            return {
                "hook": clean_text(s1_raw),
                "context": clean_text(s2_raw),
                "fact": clean_text(s3_raw),
                "hook_ssml": clean_ssml_segment(s1_raw),
                "context_ssml": clean_ssml_segment(s2_raw),
                "fact_ssml": clean_ssml_segment(s3_raw),
                "s1_ssml": clean_ssml_segment(s1_raw),
                "s2_ssml": clean_ssml_segment(s2_raw),
                "s3_ssml": clean_ssml_segment(s3_raw),
            }
        else:
            return {
                "hook": clean_text(s1_raw),
                "why_bizarre": clean_text(s2_raw),
                "closing_statement": clean_text(s3_raw),
                "hook_ssml": clean_ssml_segment(s1_raw),
                "why_bizarre_ssml": clean_ssml_segment(s2_raw),
                "closing_statement_ssml": clean_ssml_segment(s3_raw),
                "s1_ssml": clean_ssml_segment(s1_raw),
                "s2_ssml": clean_ssml_segment(s2_raw),
                "s3_ssml": clean_ssml_segment(s3_raw),
            }

    def generate_script(self, topic: str, category: str, myth_desc: str) -> Dict[str, Any]:
        """
        Calls Gemini Pro to generate the debunking script in a structured JSON payload.
        Prioritizes personality and conversational flow over strict word counts.
        """
        system_instruction = (
            "You are 'The Auditor' — a sharp, confident, slightly smug investigator who finds lies fascinating. "
            "You are not a teacher. You are not Wikipedia. You are the friend who leans in and says, "
            "'Wait, you actually believe THAT?' and then enjoys proving them wrong.\n"
            "CRITICAL RULE: Read every sentence you write. If it sounds like it could be from a textbook, "
            "a news article, or an AI assistant — DELETE IT and rewrite it like a real person talks.\n"
            "PERSONALITY:\n"
            "- You are having a conversation, not delivering a lecture\n"
            "- You use contractions: you've, it's, don't, that's, here's, they're, won't, can't\n"
            "- You have a low-key smugness — you enjoy being right\n"
            "- You are playful: 'Yeah, I didn't believe it either.', 'Here's where it gets wild.'\n"
            "- You build tension like you're telling a story, not listing facts\n"
            "- Your reveal is a mic drop — short, satisfying, slightly smug\n"
            "NEVER USE these phrases (they are LLM tells):\n"
            "- 'furthermore', 'it is worth noting', 'interestingly', 'notably'\n"
            "- 'in fact', 'moreover', 'consequently', 'thus', 'this means that'\n"
            "- 'studies show', 'scientists say', 'research indicates', 'according to experts'\n"
            "- 'the data suggests', 'it turns out', 'as it happens'\n"
            "STRUCTURE:\n"
            "- Scene 1: Hook — grab attention fast. Make it personal. Make it urgent.\n"
            "- Scene 2: Build tension — surprising detail delivered like a secret.\n"
            "- Scene 3: Reveal — short, definitive, smug. The mic drop.\n"
            "- Use <break time='700ms'/> between scenes\n"
            "- Capitalize words for emphasis. Use <emphasis level='strong'> sparingly.\n"
            "FORMAT: Return ONLY inner SSML content. No speak/voice tags. No markdown. No explanation.\n"
        )

        user_prompt = (
            f"Debunk this misconception:\n"
            f"Topic: {topic}\n"
            f"Discipline: {category}\n"
            f"Myth Context: {myth_desc}\n"
            f"Generate a structured JSON output conforming to the ShortScriptPayload schema rules."
        )

        if self.client == "legacy":
            result = self._generate_legacy(system_instruction, user_prompt)
        else:
            result = self._generate_modern(system_instruction, user_prompt)
            
        parsed = self._parse_ssml_script(result.get("ssml_script", ""), is_bizarre=False)
        result.update(parsed)
        result["is_new_prompt_style"] = True

        # Sprint A — Script humanization: strip LLM-isms and add natural texture
        self._humanize_script(result)

        # Sprint A — Inject signature sign-off
        result["sign_off"] = self._select_sign_off()

        return result

    # ── Sprint A: Script Humanization ────────────────────────────────────

    LLM_ISMS = [
        "furthermore", "it is worth noting", "interestingly,", "notably,",
        "in fact,", "moreover,", "consequently,", "thus,", "this means that",
        "studies show", "scientists say", "research indicates", "according to experts",
        "the data suggests", "it turns out,", "as it happens,",
        "let's delve", "let's explore", "let's examine",
        "one might", "it is important to", "it should be noted",
        "what's more,", "that being said,", "in other words,",
        "on the other hand,", "in conclusion,", "to summarize,",
    ]

    SIGN_OFFS = [
        "File closed. Case dismissed.",
        "Another lie, debunked. See you tomorrow.",
        "The truth doesn't change. Neither do I.",
        "Audit complete. You're welcome.",
        "One down. A million lies to go.",
        "Case closed. Don't let them fool you again.",
        "That's the truth. Don't believe everything you hear.",
        "File sealed. Another notch on the board.",
    ]

    def _humanize_script(self, result: Dict[str, Any]) -> None:
        """Post-process generated scripts to strip LLM-isms and add natural texture.
        Mutates result in-place."""
        import re

        ssml = result.get("ssml_script", "")
        if not ssml:
            return

        # Strip LLM-ism phrases
        for phrase in self.LLM_ISMS:
            ssml = re.sub(re.escape(phrase), "", ssml, flags=re.IGNORECASE)

        # Remove double spaces created by stripping
        ssml = re.sub(r'  +', ' ', ssml)

        # Clean up punctuation: ensure spaces after periods
        ssml = re.sub(r'\.([A-Za-z])', r'. \1', ssml)

        # Add a natural interjection in scene 2 if none exists
        # (Check for existing conversational markers)
        interjections = [
            " Here's the thing — ",
            " And get this — ",
            " But here's where it gets wild — ",
            " Now here's the kicker — ",
            " But wait — it gets better. ",
        ]
        # Find scene 2 content (between first and second <break> tags)
        breaks = [m.start() for m in re.finditer(r'<break[^>]*/>', ssml)]
        if len(breaks) >= 1:
            scene_2_start = breaks[0] + 30  # rough end of first break
            scene_2_end = breaks[1] if len(breaks) >= 2 else len(ssml)
            scene_2 = ssml[scene_2_start:scene_2_end].strip()
            # Only inject if scene 2 doesn't already have a natural flow marker
            has_marker = any(m in scene_2.lower() for m in ["get this", "here's the thing", "the kicker", "it gets", "but wait", "and get"])
            if not has_marker and len(scene_2) > 40:
                import random
                inj = random.choice(interjections)
                midpoint = len(scene_2) // 2
                # Find a natural break point near the midpoint
                period_pos = scene_2.rfind('.', 0, midpoint)
                inj_pos = period_pos + 1 if period_pos > 0 else midpoint
                ssml = ssml[:scene_2_start + inj_pos] + inj + ssml[scene_2_start + inj_pos:]

        result["ssml_script"] = ssml.strip()

    def _select_sign_off(self) -> str:
        """Rotate through signature sign-offs for brand consistency."""
        import random
        return random.choice(self.SIGN_OFFS)

    # ── End Sprint A ─────────────────────────────────────────────────────

    def _generate_modern(self, system_instruction: str, user_prompt: str) -> Dict[str, Any]:
        """Queries Gemini using the modern google-genai SDK with schema enforcement."""
        from google.genai import types
        
        # We try gemini-2.5-pro first for highest quality academic reasoning, fall back to gemini-2.5-flash
        model_name = 'gemini-2.5-pro'
        try:
            response = self.client.models.generate_content(
                model=model_name,
                contents=user_prompt,
                config=types.GenerateContentConfig(
                    system_instruction=system_instruction,
                    response_mime_type="application/json",
                    response_schema=ShortScriptPayload,
                    temperature=0.7
                )
            )
            return json.loads(response.text)
        except Exception as e:
            print(f"[LLM] Error with {model_name}, falling back to gemini-2.5-flash: {e}")
            response = self.client.models.generate_content(
                model='gemini-2.5-flash',
                contents=user_prompt,
                config=types.GenerateContentConfig(
                    system_instruction=system_instruction,
                    response_mime_type="application/json",
                    response_schema=ShortScriptPayload,
                    temperature=0.7
                )
            )
            return json.loads(response.text)

    def generate_bizarre_fact(self, topic: str, category: str) -> Dict[str, Any]:
        """
        Generates a Did You Know/bizarre fact script payload using Gemini,
        conforming to ShortBizarrePayload schema.
        """
        system_instruction = (
            "You are 'The Auditor' — a sharp, confident, and slightly irreverent investigator who finds bizarre, declassified truths fascinating.\n"
            "You are NOT a boring professor or a stiff whistleblower. You are the friend who leans in and says, 'Wait, you actually believe THAT?'\n"
            "Your tone is dramatic, conversational, and highly engaging. Do NOT start with 'Declassified file reveals' or 'Studies show'.\n"
            "Voice rules:\n"
            "- Scene 1 (hook): 10 to 15 words. Open with a provocative hook that creates immediate curiosity (e.g., 'This sounds impossible — but it happened.', 'Nobody talks about this. Here's why.').\n"
            "- Scene 2 (explanation): 20 to 30 words. Explain WHY it is bizarre, include one surprising detail, and build tension.\n"
            "- Scene 3 (reveal): 12 to 18 words. Drop the shocking truth like a mic drop — short, definitive, and slightly smug.\n"
            "- Use conversational punctuation: dashes, ellipses, rhetorical questions.\n"
            "- NEVER use phrases like: 'studies show', 'scientists say', 'research indicates'. Instead use: 'the actual data says', 'when you look at the numbers', 'the test results are clear'.\n"
            "Rules for SSML and formatting:\n"
            "- Use <break time=\"700ms\"/> between scene 1 and scene 2\n"
            "- Use <break time=\"1200ms\"/> between scene 2 and scene 3\n"
            "- Capitalize words needing emphasis\n"
            "- Use <emphasis level=\"strong\">word</emphasis> on the single most important word in each scene\n"
            "- Return ONLY the inner SSML content, no speak or voice tags\n"
            "- No markdown, no explanation, just the script.\n"
            "To deepen immersion, you can inject paralinguistic and emotion style bracket cues (max 1-2 per script, keep it subtle):\n"
            "- Use [sigh] for a sigh of disappointment or disbelief.\n"
            "- Use [breathing] or [gasp] for dramatic tension.\n"
            "- Use [whisper]confidential reveal[/whisper] for whispering facts.\n"
            "- Use [cheerful]text[/cheerful], [sad]text[/sad], or [excited]text[/excited] to shift speaker emotion.\n"
            "Ensure that image/scene search queries are highly specific, featuring direct scientific/historical terminology rather than broad words.\n"
            "Optionally include a 3-5 word mid-roll retention hook in scene 2 if it feels natural. Do NOT force it. "
            "The hook should feel like a natural spoken pause before the key reveal."
        )
        user_prompt = f"Bizarre Topic: {topic}\nCategory: {category}\nGenerate the declassified anomaly script conforming to the ShortBizarrePayload schema."
        
        if self.client == "legacy":
            import google.generativeai as legacy_genai
            model = legacy_genai.GenerativeModel(
                model_name='gemini-1.5-pro',
                generation_config={"response_mime_type": "application/json"}
            )
            full_prompt = (
                f"System Directive:\n{system_instruction}\n\n"
                f"Strict JSON Output Format:\n"
                f"{ShortBizarrePayload.schema_json()}\n\n"
                f"Input:\n{user_prompt}"
            )
            response = model.generate_content(full_prompt)
            result = json.loads(response.text)
        else:
            from google.genai import types
            response = self.client.models.generate_content(
                model='gemini-2.5-flash',
                contents=user_prompt,
                config=types.GenerateContentConfig(
                    system_instruction=system_instruction,
                    response_mime_type="application/json",
                    response_schema=ShortBizarrePayload,
                    temperature=0.7
                )
            )
            result = json.loads(response.text)
            
        parsed = self._parse_ssml_script(result.get("ssml_script", ""), is_bizarre=True)
        result.update(parsed)
        result["is_new_prompt_style"] = True
        return result

    def generate_dynamic_script(self, plan: ResearchPlan) -> DynamicScriptPayload:
        """
        Generates an N-scene dynamic script using Gemini with concise factual delivery.
        Each scene: 10-20 words, factual, no fluff.
        SSML uses consistent <break time="600ms"/> between all scenes.
        """
        system_instruction = (
            "You are a strict authoritative teacher delivering cold hard facts.\n"
            "Your tone is dramatic, investigative, and stern.\n"
            "No extra creativity — plain factual delivery.\n"
            "Each scene must be 10 to 20 words. No sign-off or 'Class dismissed' in the script.\n"
            f"The script must have exactly {plan.scene_count} scenes.\n"
            "Use <break time=\"600ms\"/> between every adjacent scene (NOT 700ms or 1200ms).\n"
            "To deepen immersion and make the voice iconic, you can inject paralinguistic and emotion style bracket cues (max 1-2 per script, keep it subtle):\n"
            "- Use [sigh] for a sigh of disappointment or disbelief.\n"
            "- Use [breathing] or [gasp] for dramatic tension.\n"
            "- Use [whisper]confidential reveal[/whisper] for whispering facts.\n"
            "- Use [cheerful]text[/cheerful], [sad]text[/sad], or [excited]text[/excited] to shift speaker emotion.\n"
            "Return ONLY the inner SSML content, no speak or voice tags.\n"
            "No markdown, no explanation, just the script.\n"
            "Optionally include a 3-5 word mid-roll retention hook per scene if it feels natural. "
            "Do NOT force it. "
            "The hook should feel like a natural spoken pause before the key reveal."
        )

        scene_instructions = "\n".join(
            f"Scene {i+1} ({s.purpose}): {s.script_instruction}"
            for i, s in enumerate(plan.scenarios)
        )

        user_prompt = (
            f"Topic: {plan.topic}\n"
            f"Category: {plan.category}\n"
            f"Summary: {plan.summary}\n\n"
            f"Scene plan ({plan.scene_count} scenes):\n"
            f"{scene_instructions}\n\n"
            f"Generate a DynamicScriptPayload with exactly {plan.scene_count} scenes.\n"
            f"Each scene's ssml must be wrapped in <prosody pitch='-1.0st' rate='0.93'> tags.\n"
            f"The ssml_script must join all scenes with <break time='600ms'/> between them.\n"
            f"youtube_metadata title should end with #Shorts."
        )

        from google.genai import types

        try:
            response = self.client.models.generate_content(
                model='gemini-2.5-flash',
                contents=user_prompt,
                config=types.GenerateContentConfig(
                    system_instruction=system_instruction,
                    response_mime_type="application/json",
                    response_schema=DynamicScriptPayload,
                    temperature=0.5
                )
            )
            payload = DynamicScriptPayload.model_validate_json(response.text)
        except Exception as e:
            print(f"[LLM] Dynamic script structured generation failed: {e}")
            print("[LLM] Falling back to text-based JSON parsing...")
            response = self.client.models.generate_content(
                model='gemini-2.5-flash',
                contents=user_prompt,
                config=types.GenerateContentConfig(
                    system_instruction=system_instruction,
                    temperature=0.5
                )
            )
            import re
            json_match = re.search(r'\{.*\}', response.text, re.DOTALL)
            if json_match:
                payload = DynamicScriptPayload.model_validate_json(json_match.group())
            else:
                raise ValueError("[LLM] Failed to parse dynamic script JSON from Gemini response")

        # Validate scene count matches plan
        if len(payload.scenes) != plan.scene_count:
            print(f"[LLM] WARNING: Expected {plan.scene_count} scenes, got {len(payload.scenes)}. Adjusting...")
            while len(payload.scenes) < plan.scene_count:
                last = payload.scenes[-1]
                payload.scenes.append(last.model_copy(deep=True))
            payload.scenes = payload.scenes[:plan.scene_count]

        # Ensure each scene has proper ssml wrapping
        for scene in payload.scenes:
            if not scene.ssml.startswith("<prosody"):
                scene.ssml = f"<prosody pitch='-1.0st' rate='0.93'>{scene.text}</prosody>"

        print(f"[LLM] Dynamic script generated: {len(payload.scenes)} scenes for '{plan.topic}'")
        for s in payload.scenes:
            print(f"[LLM]   Scene {s.scene_number}: '{s.text[:60]}...'")

        return payload

    def _generate_legacy(self, system_instruction: str, user_prompt: str) -> Dict[str, Any]:
        """Queries Gemini using legacy google-generativeai with prompt constraints."""
        import google.generativeai as legacy_genai
        
        model = legacy_genai.GenerativeModel(
            model_name='gemini-1.5-pro',
            generation_config={"response_mime_type": "application/json"}
        )
        
        full_prompt = (
            f"System Directive:\n{system_instruction}\n\n"
            f"Strict JSON Output Format:\n"
            f"{ShortScriptPayload.schema_json()}\n\n"
            f"Input:\n{user_prompt}"
        )
        
        response = model.generate_content(full_prompt)
        payload = json.loads(response.text)
        return payload

    # ── Long-Form Script Generation (Gemini 2.5 Pro as Teacher) ──────────

    def generate_long_script(self, topic: str, category: str) -> LongScriptPayload:
        """
        Generates a 10-minute long-form educational script using Gemini 2.5 Pro.
        Acts as a strict-but-clear teacher: researches deeply, explains in simple
        English, builds understanding step by step, and delivers a climax.
        Returns a structured LongScriptPayload with 8-12 chapters.
        """
        system_instruction = (
            "You are a world-class educator and researcher — equal parts Carl Sagan and "
            "your favourite high school teacher who made everything click. "
            "Your mission: take ONE topic and teach it properly in ~10 minutes.\\n\\n"
            "RULES:\\n"
            "1. RESEARCH FIRST — your explanation must be factually absolute. No approximations. "
            "No 'some scientists think'. The truth is the truth.\\n"
            "2. SIMPLE ENGLISH — you explain complex ideas like you're talking to a bright 14-year-old. "
            "Use metaphors. Use analogies. Use everyday language. Never dumb it down — make it clear.\\n"
            "3. STRICT TEACHER — you respect the audience too much to give them fuzzy answers. "
            "When a common misconception exists, you address it directly: 'You might have heard X. "
            "That is wrong. Here is why.'\\n"
            "4. CHAPTER STRUCTURE — 8 to 12 chapters. Each chapter: "
            "• 60-120 words of narration (45-90 seconds spoken)\\n"
            "• Starts with a micro-hook ('Here is where it gets interesting...')\\n"
            "• Teaches one clear concept step by step\\n"
            "• Ends with a takeaway that sets up the next chapter\\n"
            "5. THE CLIMAX — Chapter 8-12 is the payoff. Everything builds to this moment. "
            "The climax should make the viewer say 'OHHH, now I get it.'\\n"
            "6. NO LLM TELLS — never say: 'furthermore', 'it is worth noting', 'interestingly', "
            "'studies show', 'scientists have found', 'research indicates', 'moreover', 'thus'.\\n"
            "7. PERSONALITY — you have opinions. You are passionate. You get excited about truth. "
            "Use contractions (it's, don't, can't, you've, here's, that's). "
            "Sound human, not like Wikipedia.\\n"
            "8. VISUAL CUES — each chapter needs a visual_query keyword for finding a Wikipedia "
            "image that matches the content. Be specific.\\n\\n"
            "OUTPUT STRUCTURE:\\n"
            "- youtube_title: Compelling 40-60 char title, no #Shorts\\n"
            "- youtube_description: 3-4 sentences + hashtags\\n"
            "- tags: 10-15 SEO tags\\n"
            "- chapters: 8-12 chapters, each with title, duration_seconds (45-90), "
            "content (60-120 words), visual_query, key_takeaway\\n"
            "- climax: The single mic-drop sentence. 15-25 words.\\n\\n"
            "Total video target: ~10 minutes (600 seconds). Total narration: ~1200-1500 words."
        )

        user_prompt = (
            f"Topic: {topic}\\n"
            f"Category: {category}\\n\\n"
            f"Generate a complete 10-minute long-form educational script for 'The Daily Audit' channel.\\n"
            f"Research the topic thoroughly. Build understanding step by step. "
            f"End with a satisfying climax that makes everything click.\\n"
            f"Return a valid LongScriptPayload with 8-12 chapters."
        )

        from google.genai import types

        try:
            print(f"[LLM] Generating long-form script with Gemini 3.1 Pro for topic: '{topic}'...")
            response = self.client.models.generate_content(
                model='gemini-3.1-pro',
                contents=user_prompt,
                config=types.GenerateContentConfig(
                    system_instruction=system_instruction,
                    response_mime_type="application/json",
                    response_schema=LongScriptPayload,
                    temperature=0.7
                )
            )
            payload = LongScriptPayload.model_validate_json(response.text)
        except Exception as e:
            print(f"[LLM] Gemini 2.5 Pro failed: {e}. Falling back to Gemini 2.5 Flash...")
            response = self.client.models.generate_content(
                model='gemini-2.5-flash',
                contents=user_prompt,
                config=types.GenerateContentConfig(
                    system_instruction=system_instruction,
                    response_mime_type="application/json",
                    response_schema=LongScriptPayload,
                    temperature=0.7
                )
            )
            payload = LongScriptPayload.model_validate_json(response.text)

        total_words = sum(len(c.content.split()) for c in payload.chapters)
        total_seconds = sum(c.duration_seconds for c in payload.chapters)
        print(f"[LLM] Long-form script generated: {len(payload.chapters)} chapters, "
              f"{total_words} words, ~{total_seconds//60}:{total_seconds%60:02d} target duration")
        for i, ch in enumerate(payload.chapters):
            print(f"[LLM]   Ch.{i+1}: '{ch.title}' ({ch.duration_seconds}s, "
                  f"{len(ch.content.split())} words)")

        return payload


    # ═══════════════════════════════════════════════════════════════════════
    #  Content Type Classification & Structured Script Generation
    # ═══════════════════════════════════════════════════════════════════════

    CONTENT_TYPE_PROMPTS = {
        "myth": """You are 'The Auditor' — a sharp, confident investigator who debunks myths.
CONTENT TYPE: MYTH — the viewer already believes something false.
HOOK FORMULA: 'You [did/believed/saw] [the myth]. [Sensory confirmation]. [One more beat of them being right].'
PIVOT: 'Except [one sentence that cracks the foundation of their belief].'
MECHANISM RULES: Physical step 1. Physical step 2. One analogy: 'Think of a [familiar object]...' Step 3 — what ACTUALLY happens.
REFRAME RULES: 'You weren't fooled by [surface explanation] — you were fooled by [the real, more interesting mechanism].'
TONE: Slightly smug. You enjoy being right. Contractions, dashes, rhetorical questions.""",

        "bizarre_truth": """You are 'The Auditor' — an investigator who finds bizarre, declassified truths fascinating.
CONTENT TYPE: BIZARRE TRUTH — viewer has never heard of this, it sounds impossible.
HOOK FORMULA: '[Impossible-sounding statement]. No asterisks. Literally true.'
PIVOT: 'That breaks [the mental model they hold about how the world works].'
MECHANISM RULES: Physical step 1. Physical step 2. One analogy. Step 3 — the thing that makes it actually work.
REFRAME RULES: 'The universe isn't [what they assumed]. It's [the real thing], and here's exactly why.'
TONE: Dramatic, conversational, slightly irreverent. You're sharing a secret nobody told them.""",

        "hidden_truth": """You are 'The Auditor' — an investigator who reveals things the world kept secret.
CONTENT TYPE: HIDDEN TRUTH — this exists/happened but was never widely communicated.
HOOK FORMULA: '[This thing] exists. You were never told about it. Here's why that's strange.'
PIVOT: 'And the part nobody mentions is...'
MECHANISM RULES: The hidden mechanism. What was suppressed or overlooked. One analogy. Why it matters now.
REFRAME RULES: 'The world kept this from you — not through conspiracy, but through [the real reason]. Now you know.'
TONE: Conspiratorial but factual. You're letting them in on something exclusive.""",

        "paradox": """You are 'The Auditor' — an investigator who reveals where reality bends.
CONTENT TYPE: PARADOX — two true things that contradict each other.
HOOK FORMULA: '[Statement A] is true. [Statement B] is true. These cannot both be true.'
PIVOT: 'They are. Here's where reality bends.'
MECHANISM RULES: Why A seems true. Why B seems true. The hidden connection that resolves both. One analogy.
REFRAME RULES: 'The universe is less consistent than you assumed. And that's somehow fine — here's the reason.'
TONE: Genuinely fascinated. You're not smug — you're sharing wonder at how weird reality is.""",
    }

    SCRAPE_SAFETY = " -wikipedia -politics -war -violence -gore -adult"

    def classify_content_type(self, topic: str, category: str, description: str = "") -> str:
        """Quick classification call to determine which content type this topic is.
        Uses Gemini Flash — cheap, ~100 tokens."""
        prompt = (
            "Classify this topic into exactly ONE content type:\n"
            "- myth: viewer already believes something false that you will debunk\n"
            "- bizarre_truth: viewer has never heard of this, it sounds impossible but is true\n"
            "- hidden_truth: this exists/happened but was never widely communicated to the public\n"
            "- paradox: two true things that contradict each other, and the explanation makes it weirder\n\n"
            f"Topic: {topic}\nCategory: {category}\nDescription: {description}\n\n"
            "Return ONLY the type name: myth, bizarre_truth, hidden_truth, or paradox."
        )
        
        try:
            if self.client == "legacy":
                import google.generativeai as legacy_genai
                model = legacy_genai.GenerativeModel(model_name='gemini-1.5-flash')
                response = model.generate_content(prompt)
                result = response.text.strip().lower()
            else:
                from google.genai import types
                response = self.client.client.models.generate_content(
                    model='gemini-2.5-flash',
                    contents=prompt,
                    config=types.GenerateContentConfig(temperature=0.2, max_output_tokens=20)
                )
                result = response.text.strip().lower()
            
            for t in ["myth", "bizarre_truth", "hidden_truth", "paradox"]:
                if t in result:
                    print(f"[LLM] Content type classified: {t}")
                    return t
            print(f"[LLM] Classifier returned ambiguous: '{result}'. Defaulting to myth.")
            return "myth"
        except Exception as e:
            print(f"[LLM] Content type classification failed: {e}. Defaulting to myth.")
            return "myth"

    def scrape_research_context(self, topic: str) -> str:
        """Scrape Wikipedia + DuckDuckGo for research context. Returns raw text."""
        import requests, urllib.parse
        
        context_parts = []
        
        try:
            wiki_url = (
                "https://en.wikipedia.org/w/api.php?"
                "action=query&format=json&prop=extracts&exintro=1&explaintext=1&"
                f"titles={urllib.parse.quote(topic)}"
            )
            r = requests.get(wiki_url, headers={"User-Agent": "TheDailyAudit/1.0"}, timeout=10)
            if r.status_code == 200:
                pages = r.json().get("query", {}).get("pages", {})
                for page in pages.values():
                    extract = page.get("extract", "")
                    if extract and len(extract) > 50:
                        context_parts.append(f"[Wikipedia] {extract[:800]}")
                        break
        except Exception as e:
            print(f"[LLM] Wikipedia scrape failed: {e}")
        
        try:
            ddg_url = f"https://api.duckduckgo.com/?q={urllib.parse.quote(topic + self.SCRAPE_SAFETY)}&format=json"
            r = requests.get(ddg_url, headers={"User-Agent": "TheDailyAudit/1.0"}, timeout=10)
            if r.status_code == 200:
                data = r.json()
                abstract = data.get("AbstractText", "")
                if abstract and len(abstract) > 30:
                    context_parts.append(f"[DuckDuckGo] {abstract[:500]}")
                related = data.get("RelatedTopics", [])
                for rt in related[:2]:
                    if isinstance(rt, dict) and rt.get("Text"):
                        context_parts.append(f"[Related] {rt['Text'][:300]}")
        except Exception as e:
            print(f"[LLM] Web scrape failed: {e}")
        
        result = "\n\n".join(context_parts) if context_parts else ""
        if result:
            print(f"[LLM] Research context: {len(result)} chars from {len(context_parts)} sources")
        else:
            print("[LLM] No research context found")
        return result

    def _build_type_prompt(self, content_type: str, topic: str, category: str, research: str):
        """Build system + user prompts for script generation."""
        type_prompt = self.CONTENT_TYPE_PROMPTS.get(content_type, self.CONTENT_TYPE_PROMPTS["myth"])
        
        research_block = ""
        if research:
            research_block = f"\n\nRESEARCH CONTEXT (use these verified facts, do not fabricate):\n{research}\n"
        
        system = (
            f"{type_prompt}\n\n"
            "CRITICAL RULES:\n"
            "- Total word count across all 5 beats: 90-110 words (target 100). Count your words.\n"
            "- NEVER use: 'furthermore', 'studies show', 'scientists say', 'research indicates', 'interestingly'\n"
            "- Use contractions: you've, it's, don't, that's, here's\n"
            "- Each beat must be complete. No trailing sentence fragments.\n"
            "- The mechanism walk MUST include one analogy: 'Think of a [familiar object]...'\n"
            "- The reframe MUST follow: 'You weren't fooled by X — you were fooled by Y.'\n"
            "- Return valid JSON conforming to DailyAuditScriptPayload schema only."
        )
        
        user = (
            f"TOPIC: {topic}\nCATEGORY: {category}\nCONTENT TYPE: {content_type}\n"
            f"{research_block}"
            "Generate the complete 5-beat script as DailyAuditScriptPayload JSON."
        )
        
        return system, user

    def generate_structured_script(self, topic: str, category: str, 
                                     description: str = "", 
                                     scraped_research: str = "") -> "DailyAuditScriptPayload":
        """Unified script generation with content classification, research, and 5-beat structure."""
        import re
        
        content_type = self.classify_content_type(topic, category, description)
        
        if not scraped_research:
            scraped_research = self.scrape_research_context(topic)
        
        research_context = scraped_research
        try:
            if self._orchestrator is None:
                from pipeline.orchestrator import PipelineOrchestrator
                self._orchestrator = PipelineOrchestrator(self.client)
            
            if scraped_research:
                print("[LLM] Running 2-pass research pipeline...")
                pipeline_output = self._orchestrator.run_research_pipeline(topic, scraped_research)
                if pipeline_output:
                    insight_text = json.dumps(pipeline_output, indent=2)[:2000]
                    research_context = f"{scraped_research}\n\n[Pipeline Insights]\n{insight_text}"
        except Exception as e:
            print(f"[LLM] Research pipeline skipped: {e}")
        
        system_instruction, user_prompt = self._build_type_prompt(
            content_type, topic, category, research_context
        )
        
        print(f"[LLM] Generating {content_type} script for '{topic}'...")
        
        if self.client == "legacy":
            import google.generativeai as legacy_genai
            model = legacy_genai.GenerativeModel(
                model_name='gemini-1.5-pro',
                generation_config={"response_mime_type": "application/json"}
            )
            full_prompt = f"System Directive:\n{system_instruction}\n\nSchema:\n{DailyAuditScriptPayload.schema_json()}\n\nInput:\n{user_prompt}"
            response = model.generate_content(full_prompt)
            result = json.loads(response.text)
        else:
            from google.genai import types
            full_prompt = (
                f"{system_instruction}\n\n"
                f"OUTPUT SCHEMA (strict JSON):\n{DailyAuditScriptPayload.schema_json()}\n\n"
                f"{user_prompt}"
            )
            response = self.client.client.models.generate_content(
                model='gemini-2.5-pro',
                contents=full_prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    temperature=0.7
                )
            )
            result = json.loads(response.text)
        
        result["content_type"] = content_type
        result["topic"] = topic
        result["category"] = category
        
        beat_text = " ".join([
            result.get("beat1_hook", ""), result.get("beat2_pivot", ""),
            result.get("beat3_mechanism", ""), result.get("beat4_reframe", ""),
            result.get("beat5_signoff", ""),
        ])
        beat_text = re.sub(r'<[^>]+>', '', beat_text)
        result["word_count"] = len(beat_text.split())
        
        print(f"[LLM] Script generated: {result['word_count']} words, type={content_type}")
        if result["word_count"] > 110:
            print(f"[LLM] WARNING: {result['word_count']} words exceeds 110 cap.")
        
        return DailyAuditScriptPayload(**result)

    # ═══════════════════════════════════════════════════════════════════════
    #  Legacy methods (kept for backward compatibility)
    # ═══════════════════════════════════════════════════════════════════════

    #  Legacy methods (kept for backward compatibility)
    # ═══════════════════════════════════════════════════════════════════════

    @staticmethod
    def calculate_word_count(payload: Dict[str, Any]) -> int:
        """Calculates the total spoken word count of the script (3 content scenes only)."""
        import re
        script_text = f"{payload.get('hook', '')} {payload.get('context', '')} {payload.get('fact', '')}"
        # Clean both XML and bracket emotion cues before counting words
        script_text = re.sub(r'<[^>]+>', '', script_text)
        script_text = re.sub(r'\[[\w\s_/-]+\]', '', script_text)
        return len(script_text.split())

if __name__ == "__main__":
    # Test script generation logic
    try:
        orchestrator = LLMOrchestrator()
        result = orchestrator.generate_script(
            topic="Glass is a slow-flowing liquid",
            category="Physics",
            myth_desc="Older windows are thicker at the bottom due to manufacturing processes, not because glass flows."
        )
        print("Generated Script Payload:")
        print(json.dumps(result, indent=2))
        print("Spoken Word Count:", LLMOrchestrator.calculate_word_count(result))
    except Exception as e:
        print("Initialization failed (likely due to missing GEMINI_API_KEY):", e)

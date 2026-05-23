# =============================================================================
# "The Daily Audit" - LLM Orchestration & Script Generation Module
# =============================================================================
import os
import json
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field

# Dynamic script types (used by generate_dynamic_script)
from research_agent import ResearchPlan, ScenePlan
from dynamic_script import DynamicScriptPayload, SceneContent

# Define target schemas for structured JSON response validation
class YouTubeMetadataSchema(BaseModel):
    title: str = Field(description="A compelling, attention-grabbing YouTube Shorts title ending with #Shorts")
    description: str = Field(description="Educational summary detailing the myth and reality, containing #TheDailyAudit and #Shorts")
    tags: list[str] = Field(description="List of 8-12 SEO-optimized tags. Include: 3 high-traffic broad tags (e.g., shorts, viral, debunked), 3 discipline tags (e.g., science, physics, biology, history), and 4-6 specific topic tags (e.g., coriolis, sink, water). All tags should be lowercase with no spaces.")

class ShortScriptPayload(BaseModel):
    topic: str = Field(description="The misconception being debunked")
    ssml_script: str = Field(
        description="The complete inner SSML script for a strict authoritative teacher delivering cold hard facts. "
                    "Rules: "
                    "- Scene 1 and Scene 3 must be 8 to 12 words total. Scene 2 (explanation/context) must be 12 to 18 words total. "
                    "- Use <break time=\"700ms\"/> between scene 1 and scene 2 "
                    "- Use <break time=\"1200ms\"/> between scene 2 and scene 3 "
                    "- Capitalize words needing emphasis "
                    "- Use <emphasis level=\"strong\">word</emphasis> on the single most important word "
                    "- Return ONLY the inner SSML content, no speak or voice tags "
                    "- No markdown, no explanation, just the script. "
                    "Structure: "
                    "1. Scene 1: Hook/claim (the myth or bizarre statement) — 8–12 words "
                    "2. Scene 2: Explanation/context (why people believe it) — 12–18 words "
                    "3. Scene 3: Truth/reveal (the debunk) — 8–12 words"
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

class ShortBizarrePayload(BaseModel):
    topic: str = Field(description="The name of the bizarre historical/scientific anomaly")
    ssml_script: str = Field(
        description="The complete inner SSML script for a strict authoritative teacher delivering cold hard facts. "
                    "Rules: "
                    "- Scene 1 and Scene 3 must be 8 to 12 words total. Scene 2 (explanation/context) must be 12 to 18 words total. "
                    "- Use <break time=\"700ms\"/> between scene 1 and scene 2 "
                    "- Use <break time=\"1200ms\"/> between scene 2 and scene 3 "
                    "- Capitalize words needing emphasis "
                    "- Use <emphasis level=\"strong\">word</emphasis> on the single most important word "
                    "- Return ONLY the inner SSML content, no speak or voice tags "
                    "- No markdown, no explanation, just the script. "
                    "Structure: "
                    "1. Scene 1: Hook/claim (the bizarre statement) — 8–12 words "
                    "2. Scene 2: Explanation/context (why it is bizarre) — 12–18 words "
                    "3. Scene 3: Truth/reveal (the shocking truth) — 8–12 words"
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
        Ensures persona enforcement and strict word count (35-50 words total).
        """
        system_instruction = (
            "You are a strict whistleblower whistleblower analyst revealing hidden anomalies.\n"
            "Your tone is dramatic, investigative, and stern, using evocative, high-vocabulary forensic whistleblower language.\n"
            "Start hooks strictly using whistleblower, declassified document, or whistleblower file references (e.g., 'The file they tried to bury...', 'Declassified file 942 reveals...').\n"
            "Make the debunk genuinely surprising — the audience should feel foolish for having believed the myth.\n"
            "Scene 1 and Scene 3 must be 8 to 12 words. Scene 2 must be 12 to 18 words. No sign-off or 'Class dismissed' in the script.\n"
            "Ensure the visual prompts are highly descriptive, specific, and specify raw concrete details for Wikipedia/Commons image matching.\n"
            "You must generate the complete inner SSML script conforming to the teacher prompt rules, and also supply visual prompts and youtube metadata.\n"
            "Optionally include a 3-5 word mid-roll retention hook in scene 2 if it feels natural. "
            "Do NOT force it — if the scene flows well without it, leave mid_roll_hook empty. "
            "The hook should feel like a natural spoken pause before the key reveal."
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
        return result

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
            "You are a strict whistleblower whistleblower analyst revealing hidden anomalies.\n"
            "Your tone is dramatic, investigative, and stern, using evocative, high-vocabulary forensic whistleblower language.\n"
            "Start hooks strictly using whistleblower, declassified document, or whistleblower file references (e.g., 'The file they tried to bury...', 'Declassified file 942 reveals...').\n"
            "Make the bizarre twist genuinely surprising.\n"
            "Scene 1 and Scene 3 must be 8 to 12 words. Scene 2 must be 12 to 18 words. No sign-off or 'Class dismissed' in the script.\n"
            "Ensure that image/scene search queries are highly specific, featuring direct scientific/historical terminology rather than broad words.\n"
            "You must generate the complete inner SSML script conforming to the teacher prompt rules, and also supply scene queries and youtube metadata.\n"
            "Optionally include a 3-5 word mid-roll retention hook in scene 2 if it feels natural. "
            "Do NOT force it — if the scene flows well without it, leave mid_roll_hook empty. "
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

    @staticmethod
    def calculate_word_count(payload: Dict[str, Any]) -> int:
        """Calculates the total spoken word count of the script (3 content scenes only)."""
        script_text = f"{payload.get('hook', '')} {payload.get('context', '')} {payload.get('fact', '')}"
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

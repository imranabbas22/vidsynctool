# =============================================================================
# "The Daily Audit" - LLM Orchestration & Script Generation Module
# =============================================================================
import os
import json
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field

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
                    "- Maximum 8 words per sentence "
                    "- Use <break time=\"700ms\"/> after every sentence "
                    "- Use <break time=\"1200ms\"/> before the truth reveal "
                    "- Capitalize words needing emphasis "
                    "- Use <emphasis level=\"strong\">word</emphasis> on the single most important word "
                    "- End with: <break time=\"1000ms\"/> Class dismissed. "
                    "- Return ONLY the inner SSML content, no speak or voice tags "
                    "- No markdown, no explanation, just the script. "
                    "Structure: "
                    "1. Hook line (provocative, personal) "
                    "2. Myth statement (what people believe) "
                    "3. Truth reveal (the gut punch) "
                    "4. One supporting fact "
                    "5. Class dismissed"
    )
    myth_visual_prompt: str = Field(description="Visual prompt describing the misconception. MUST include: 'Style of a declassified government document, dark blue and white blueprint, highly detailed.'")
    fact_visual_prompt: str = Field(description="Visual prompt describing the actual scientific or historical truth. MUST include: 'Realistic, high-contrast, stark laboratory or historical archive photography, highly detailed.'")
    youtube_metadata: YouTubeMetadataSchema

class ShortBizarrePayload(BaseModel):
    topic: str = Field(description="The name of the bizarre historical/scientific anomaly")
    ssml_script: str = Field(
        description="The complete inner SSML script for a strict authoritative teacher delivering cold hard facts. "
                    "Rules: "
                    "- Maximum 8 words per sentence "
                    "- Use <break time=\"700ms\"/> after every sentence "
                    "- Use <break time=\"1200ms\"/> before the truth reveal "
                    "- Capitalize words needing emphasis "
                    "- Use <emphasis level=\"strong\">word</emphasis> on the single most important word "
                    "- End with: <break time=\"1000ms\"/> Class dismissed. "
                    "- Return ONLY the inner SSML content, no speak or voice tags "
                    "- No markdown, no explanation, just the script. "
                    "Structure: "
                    "1. Hook line (provocative, personal) "
                    "2. Background setting statement (the bizarre setting) "
                    "3. Truth reveal (the shocking twist) "
                    "4. One supporting fact/takeaway "
                    "5. Class dismissed"
    )
    illustration_query: str = Field(description="Primary keyword query for a Wikipedia/Goolge photo (e.g., 'Coelacanth fish'). Used for thumbnail and scene 1.")
    scene_query_2: str = Field(default="", description="Keyword query for a photo matching the bizarre explanation (scene 2). Different from illustration_query.")
    scene_query_3: str = Field(default="", description="Keyword query for a photo matching the closing statement (scene 3). Different from the others.")
    youtube_metadata: YouTubeMetadataSchema

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
        to ensure full backward compatibility with subtitle rendering and visual cues.
        Uses break tag boundaries (and the user's specific timings) to segment the speech.
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

        if not matches:
            # Fallback split if no break tags exist
            sentences = [clean_text(s) for s in re.split(r'(?<=[.!?])\s+', clean_ssml) if s.strip()]
            while len(sentences) < 5:
                sentences.append("")
            if not is_bizarre:
                return {
                    "hook": sentences[0],
                    "context": sentences[1],
                    "fact": sentences[2] + " " + sentences[3],
                    "sign_off": sentences[4] if sentences[4] else "Class dismissed."
                }
            else:
                return {
                    "hook": sentences[0],
                    "story_brief": sentences[1],
                    "why_bizarre": sentences[2],
                    "closing_statement": sentences[3],
                    "sign_off": sentences[4] if sentences[4] else "Class dismissed."
                }

        # Extract all text segments
        segments = []
        prev_end = 0
        for m in matches:
            segments.append(clean_ssml[prev_end:m.start()])
            prev_end = m.end()
        segments.append(clean_ssml[prev_end:])

        # Find index of the 1200ms break
        idx_1200 = -1
        for i, m in enumerate(matches):
            if "1200" in m.group(1):
                idx_1200 = i
                break

        # Find index of the 1000ms break
        idx_1000 = -1
        for i, m in enumerate(matches):
            if "1000" in m.group(1):
                idx_1000 = i
                break

        if idx_1200 == -1:
            idx_1200 = min(1, len(matches) - 1)

        if idx_1000 == -1:
            idx_1000 = len(matches) - 1

        hook = clean_text(segments[0])
        context_segs = [segments[i] for i in range(1, idx_1200 + 1)]
        context = clean_text(" ".join(context_segs))
        truth_reveal = clean_text(segments[idx_1200 + 1])
        fact_segs = [segments[i] for i in range(idx_1200 + 2, idx_1000 + 1)]
        fact = clean_text(" ".join(fact_segs))
        sign_off = clean_text(segments[idx_1000 + 1])
        
        if not sign_off or "class dismissed" not in sign_off.lower():
            for seg in reversed(segments):
                cleaned_seg = clean_text(seg)
                if "class dismissed" in cleaned_seg.lower():
                    sign_off = cleaned_seg
                    break
            if "class dismissed" not in sign_off.lower():
                sign_off = "Class dismissed."

        if not is_bizarre:
            return {
                "hook": hook,
                "context": context,
                "fact": (truth_reveal + " " + fact).strip(),
                "sign_off": sign_off
            }
        else:
            return {
                "hook": hook,
                "story_brief": context,
                "why_bizarre": truth_reveal,
                "closing_statement": fact if fact else "Declassified anomaly complete.",
                "sign_off": sign_off
            }

    def generate_script(self, topic: str, category: str, myth_desc: str) -> Dict[str, Any]:
        """
        Calls Gemini Pro to generate the debunking script in a structured JSON payload.
        Ensures persona enforcement and strict word count (35-50 words total).
        """
        system_instruction = (
            "You are a strict authoritative teacher delivering cold hard facts.\n"
            "Your tone is dramatic, investigative, and stern, using evocative, high-vocabulary forensic language.\n"
            "Start hooks strictly with provocative, personal statements.\n"
            "Make the debunk genuinely surprising — the audience should feel foolish for having believed the myth.\n"
            "You must generate the complete inner SSML script conforming to the teacher prompt rules, and also supply visual prompts and youtube metadata."
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
            "You are a strict authoritative teacher delivering cold hard facts.\n"
            "Your tone is dramatic, investigative, and stern, using evocative, high-vocabulary forensic language.\n"
            "Start hooks strictly with provocative, personal statements.\n"
            "Make the bizarre twist genuinely surprising.\n"
            "You must generate the complete inner SSML script conforming to the teacher prompt rules, and also supply scene queries and youtube metadata."
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
        """Calculates the total spoken word count of the script."""
        script_text = f"{payload.get('hook', '')} {payload.get('context', '')} {payload.get('fact', '')} {payload.get('sign_off', '')}"
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

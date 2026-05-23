# =============================================================================
# "The Daily Audit" - Dynamic Research Agent Module
# =============================================================================
import os
import json
import re
from typing import Optional
from pydantic import BaseModel, Field


class ScenePlan(BaseModel):
    title: str = Field(description="Scene title")
    purpose: str = Field(description="Scene purpose: hook, explanation, evidence, implication, conclusion, etc.")
    script_instruction: str = Field(description="What this scene should cover (2-3 sentences max)")
    image_search_query: str = Field(description="Search query for finding an image for this scene")


class ResearchPlan(BaseModel):
    topic: str = Field(description="Core topic/subject")
    category: str = Field(description="e.g., Science, History, Technology")
    scene_count: int = Field(description="Dynamically determined number of scenes (1-8)")
    scenarios: list[ScenePlan] = Field(description="Per-scene plans")
    summary: str = Field(description="One-sentence summary of the answer")


class ResearchAgent:
    """Analyzes a user prompt and determines topic structure using Gemini."""

    def __init__(self, gemini_client):
        self.client = gemini_client

    def analyze_prompt(self, user_prompt: str) -> ResearchPlan:
        """Uses Gemini to analyze a prompt and produce a structured ResearchPlan."""
        system_instruction = (
            "You are a research analyst. Analyze the user query and produce a structured plan.\n"
            "Output must conform exactly to the ResearchPlan JSON schema."
        )

        scene_prompt = (
            f"Analyze this user query and determine the minimum number of video scenes "
            f"needed to explain it concisely but thoroughly:\n\n"
            f"User Query: \"{user_prompt}\"\n\n"
            f"Rules:\n"
            f"- Return 1 scene ONLY if the topic is a simple single fact (e.g., 'What color is the sky?')\n"
            f"- Return 2-3 scenes for moderately complex topics (most common)\n"
            f"- Return 4-6 scenes for complex multi-faceted topics needing evidence breakdowns\n"
            f"- NEVER exceed 8 scenes\n"
            f"- Each scene must be substantive (not filler)\n"
            f"- Scene types can include: hook, explanation, evidence_1, evidence_2, implication, counter_argument, conclusion\n"
            f"- Output must be the ResearchPlan JSON schema\n"
            f"- For scene_count, determine the MINIMUM number of scenes needed (not the maximum)\n"
            f"- Each scene's image_search_query should be a concise keyword query for finding a relevant photo"
        )

        from google.genai import types

        try:
            response = self.client.models.generate_content(
                model='gemini-2.5-flash',
                contents=scene_prompt,
                config=types.GenerateContentConfig(
                    system_instruction=system_instruction,
                    response_mime_type="application/json",
                    response_schema=ResearchPlan,
                    temperature=0.4
                )
            )
            plan = ResearchPlan.model_validate_json(response.text)
        except Exception as e:
            print(f"[ResearchAgent] Gemini structured generation failed: {e}")
            print("[ResearchAgent] Falling back to text-based JSON parsing...")
            response = self.client.models.generate_content(
                model='gemini-2.5-flash',
                contents=scene_prompt,
                config=types.GenerateContentConfig(
                    system_instruction=system_instruction,
                    temperature=0.4
                )
            )
            plan = self._parse_json_fallback(response.text)

        # Guardrails
        if plan.scene_count < 1:
            print(f"[ResearchAgent] Invalid scene_count={plan.scene_count}, defaulting to 1")
            plan.scene_count = 1

        if plan.scene_count > 8:
            print(f"[ResearchAgent] scene_count={plan.scene_count} exceeds max 8, clamping")
            plan.scene_count = 8

        if not plan.scenarios or len(plan.scenarios) == 0:
            print("[ResearchAgent] No scenarios returned, creating single default scene")
            plan.scenarios = [
                ScenePlan(
                    title=plan.topic,
                    purpose="explanation",
                    script_instruction=f"Explain {plan.topic} concisely.",
                    image_search_query=plan.topic
                )
            ]
            plan.scene_count = 1

        # Trim or pad scenarios to match scene_count
        if len(plan.scenarios) > plan.scene_count:
            plan.scenarios = plan.scenarios[:plan.scene_count]
        elif len(plan.scenarios) < plan.scene_count:
            last = plan.scenarios[-1] if plan.scenarios else ScenePlan(title="", purpose="", script_instruction="", image_search_query="")
            while len(plan.scenarios) < plan.scene_count:
                plan.scenarios.append(last.model_copy(deep=True))

        print(f"[ResearchAgent] Plan generated: topic='{plan.topic}', category='{plan.category}', scenes={plan.scene_count}")
        for i, s in enumerate(plan.scenarios):
            print(f"[ResearchAgent]   Scene {i+1}: '{s.title}' ({s.purpose}) query='{s.image_search_query}'")

        return plan

    def fetch_research_materials(self, plan: ResearchPlan) -> dict:
        """Fetches images for each scene using DataScraper."""
        from data_scraper import DataScraper

        scraper = DataScraper()
        images = []
        timestamp = str(int(__import__('time').time()))

        for i, scene in enumerate(plan.scenarios):
            query = scene.image_search_query.strip()
            if not query:
                query = plan.topic
            try:
                path = scraper.fetch_image_multi_source(query, f"dynamic_{timestamp}_scene{i}")
                if path:
                    images.append(path)
                else:
                    print(f"[ResearchAgent] No image found for scene {i} query '{query}', using blueprint fallback")
                    images.append(self._generate_fallback_image(query, f"dynamic_fallback_{timestamp}_scene{i}"))
            except Exception as e:
                print(f"[ResearchAgent] Image fetch failed for scene {i}: {e}")
                images.append(self._generate_fallback_image(query, f"dynamic_fallback_{timestamp}_scene{i}"))

        # Ensure at least 1 image
        if not images:
            fallback = self._generate_fallback_image(plan.topic, f"dynamic_fallback_{timestamp}_0")
            images = [fallback]

        return {"images": images}

    def _generate_fallback_image(self, query: str, name: str) -> str:
        """Generates a programmatic blueprint fallback image."""
        try:
            from asset_generator import AssetGenerator
            gen = AssetGenerator()
            return gen._render_programmatic_blueprint(query, os.path.join(gen.assets_dir, f"{name}.png"))
        except Exception:
            # Ultra fallback: create a blank image
            from PIL import Image
            base_dir = os.path.dirname(os.path.abspath(__file__))
            assets_dir = os.path.join(base_dir, "assets")
            os.makedirs(assets_dir, exist_ok=True)
            path = os.path.join(assets_dir, f"{name}.png")
            Image.new("RGB", (1080, 1920), (10, 24, 47)).save(path)
            return path

    def _parse_json_fallback(self, text: str) -> ResearchPlan:
        """Parse JSON from Gemini text response when structured output fails."""
        # Try to extract JSON block
        json_match = re.search(r'\{.*\}', text, re.DOTALL)
        if json_match:
            try:
                data = json.loads(json_match.group())
                return ResearchPlan(**data)
            except Exception:
                pass

        # Default fallback
        return ResearchPlan(
            topic="Unknown Topic",
            category="General",
            scene_count=1,
            scenarios=[
                ScenePlan(
                    title="Explanation",
                    purpose="explanation",
                    script_instruction=f"Explain the topic.",
                    image_search_query="general"
                )
            ],
            summary="No summary available."
        )

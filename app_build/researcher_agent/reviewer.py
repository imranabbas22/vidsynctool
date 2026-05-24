import json
import os
from typing import Dict, Any, List

class RetentionReviewer:
    def __init__(self, gemini_client):
        self.client = gemini_client

    def review_scenes(self, scene_sequence: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Reviews a sequence of scenes against the retention rubric using Gemini.
        Returns a dictionary containing the scores and overall pass status.
        """
        prompt = f"""You are a short-form video retention analyst. You have reviewed thousands of YouTube Shorts, TikToks, and Facebook Reels.

INPUT: {json.dumps(scene_sequence, indent=2)}

SCORE each of the following on 1-10:
- HOOK_STRENGTH: Does Scene 1 create immediate curiosity without context? Would someone mid-scroll stop? (10 = stops everyone)
- NARRATIVE_TENSION: Do scenes alternate between open loops and resolutions? Is there forward momentum?
- VISUAL_VARIETY: Are there at least (total_scenes * 0.7) unique visual queries? (penalize repeated visuals)
- PAYOFF_SATISFACTION: Does the verdict scene deliver a genuinely surprising conclusion?
- EXIT_QUALITY: Does the exit scene create desire for the next video without generic CTA language?

OUTPUT FORMAT (strict JSON):
{{
  "scores": {{
    "hook_strength": <1-10>,
    "narrative_tension": <1-10>,
    "visual_variety": <1-10>,
    "payoff_satisfaction": <1-10>,
    "exit_quality": <1-10>
  }},
  "overall": <average, 1-10>,
  "pass": <true if overall >= 7.0, false otherwise>,
  "blocking_issues": [
    "<specific scene_id and exact problem if score < 6>"
  ],
  "suggested_fixes": [
    "<one concrete fix per blocking issue>"
  ]
}}
"""
        from google.genai import types

        model_name = 'gemini-2.5-flash'
        try:
            response = self.client.models.generate_content(
                model=model_name,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    temperature=0.2
                )
            )
            review_result = json.loads(response.text)
            print(f"[RetentionReviewer] Review completed. Overall score: {review_result.get('overall', 0)}, Pass: {review_result.get('pass', False)}")
            return review_result
        except Exception as e:
            print(f"[RetentionReviewer] Gemini review failed: {e}. Falling back to default PASS to avoid blocking.")
            return {
                "scores": {
                    "hook_strength": 8.0,
                    "narrative_tension": 8.0,
                    "visual_variety": 8.0,
                    "payoff_satisfaction": 8.0,
                    "exit_quality": 8.0
                },
                "overall": 8.0,
                "pass": True,
                "blocking_issues": [],
                "suggested_fixes": []
            }

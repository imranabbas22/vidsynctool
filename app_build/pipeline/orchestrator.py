import os
import json
from typing import Dict, Any, List, Optional
from researcher_agent.reviewer import RetentionReviewer

class PipelineOrchestrator:
    def __init__(self, gemini_client):
        self.client = gemini_client
        self.reviewer = RetentionReviewer(gemini_client)
        
        # Load prompt templates
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.pass1_path = os.path.join(base_dir, "researcher_agent", "prompts", "pass1_decompose.txt")
        self.pass2_path = os.path.join(base_dir, "researcher_agent", "prompts", "pass2_scenes.txt")

    def _read_prompt(self, path: str) -> str:
        with open(path, "r", encoding="utf-8") as f:
            return f.read()

    def run_research_pipeline(self, topic: str, scraped_research_data: str) -> Dict[str, Any]:
        """
        Runs the two-pass research agent prompt chain and validates the output using the Retention Reviewer.
        Retries Pass 2 up to 2 times if the review fails.
        """
        from google.genai import types

        # --- PASS 1: Knowledge Decomposition ---
        print(f"[Orchestrator] Starting PASS 1 - Knowledge Decomposition for topic: '{topic}'")
        pass1_template = self._read_prompt(self.pass1_path)
        pass1_prompt = pass1_template.format(
            topic=topic,
            scraped_research_data=scraped_research_data
        )

        try:
            response = self.client.models.generate_content(
                model='gemini-2.5-flash',
                contents=pass1_prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    temperature=0.4
                )
            )
            pass1_output = json.loads(response.text)
            print("[Orchestrator] PASS 1 completed successfully.")
        except Exception as e:
            print(f"[Orchestrator] CRITICAL: PASS 1 generation failed: {e}")
            raise RuntimeError(f"PASS 1 failed: {e}")

        # --- PASS 2 & REVIEW LOOP ---
        pass2_template = self._read_prompt(self.pass2_path)
        pass1_json_str = json.dumps(pass1_output, indent=2)
        
        max_retries = 2
        attempt = 0
        blocking_issues = []
        scene_sequence = []
        review_result = {}

        while attempt <= max_retries:
            print(f"[Orchestrator] Starting PASS 2 - Scene Narrative Builder (Attempt {attempt + 1}/{max_retries + 1})")
            
            # Format blocking issues clause if retrying
            if attempt > 0 and blocking_issues:
                blocking_issues_clause = (
                    f"\nCRITICAL: The previous scene sequence failed verification with the following blocking issues:\n"
                    f"{json.dumps(blocking_issues, indent=2)}\n"
                    f"You MUST rewrite the scenes to completely fix these issues."
                )
            else:
                blocking_issues_clause = ""

            pass2_prompt = pass2_template.format(
                pass1_json_output=pass1_json_str,
                blocking_issues_clause=blocking_issues_clause
            )

            try:
                response = self.client.models.generate_content(
                    model='gemini-2.5-flash',
                    contents=pass2_prompt,
                    config=types.GenerateContentConfig(
                        response_mime_type="application/json",
                        temperature=0.7
                    )
                )
                scene_sequence = json.loads(response.text)
            except Exception as e:
                print(f"[Orchestrator] PASS 2 generation failed on attempt {attempt + 1}: {e}")
                if attempt == max_retries:
                    raise e
                attempt += 1
                continue

            # Validate scene array format
            if not isinstance(scene_sequence, list) or len(scene_sequence) == 0:
                print(f"[Orchestrator] PASS 2 output is not a valid list. Attempt {attempt + 1} failed.")
                attempt += 1
                continue

            # Review the scenes
            print("[Orchestrator] Calling Retention Reviewer to score the scene sequence...")
            review_result = self.reviewer.review_scenes(scene_sequence)
            
            if review_result.get("pass", False):
                print(f"[Orchestrator] Scene sequence passed review with overall score {review_result.get('overall')}.")
                break
            else:
                blocking_issues = review_result.get("blocking_issues", [])
                print(f"[Orchestrator] Review failed on attempt {attempt + 1}. Scores: {json.dumps(review_result.get('scores'))}")
                print(f"[Orchestrator] Blocking issues found: {blocking_issues}")
                
                if attempt == max_retries:
                    print("[Orchestrator] Maximum retries reached. Proceeding with last scene sequence despite failing review.")
                    break
                
                attempt += 1

        return {
            "pass1_output": pass1_output,
            "scene_sequence": scene_sequence,
            "review": review_result
        }

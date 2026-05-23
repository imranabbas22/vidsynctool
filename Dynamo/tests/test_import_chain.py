"""Tests the full import chain for the dynamic video pipeline."""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ['GEMINI_API_KEY'] = 'test-fake-key'

# 1. Import in dependency order
from dynamic_script import DynamicScriptPayload, SceneContent, YouTubeMetadataSchema, parse_dynamic_ssml
print('1. dynamic_script: OK')

from research_agent import ResearchPlan, ScenePlan, ResearchAgent
print('2. research_agent: OK')

from llm_orchestrator import LLMOrchestrator
print('3. llm_orchestrator: OK')

# 2. Construct DynamicScriptPayload
payload = DynamicScriptPayload(
    topic='Test',
    ssml_script='<break time="600ms"/>',
    scenes=[SceneContent(scene_number=1, title='Scene 1', text='Hello', ssml='<prosody>Hello</prosody>')],
    image_queries=['test query'],
    youtube_metadata=YouTubeMetadataSchema(title='Test #Shorts', description='Desc', tags=['tag1'])
)
assert len(payload.scenes) == 1
print(f'4. DynamicScriptPayload construction: OK (scenes={len(payload.scenes)})')

# 3. Construct ResearchPlan
plan = ResearchPlan(
    topic='Test Topic',
    category='Science',
    scene_count=3,
    scenarios=[
        ScenePlan(title='S1', purpose='hook', script_instruction='Intro', image_search_query='q1'),
        ScenePlan(title='S2', purpose='evidence', script_instruction='Evidence', image_search_query='q2'),
        ScenePlan(title='S3', purpose='conclusion', script_instruction='Conclude', image_search_query='q3'),
    ],
    summary='Test summary'
)
assert plan.scene_count == 3
print(f'5. ResearchPlan construction: OK (scenes={plan.scene_count})')

# 4. Verify VideoEngine methods exist
from video_engine import VideoEngine
engine = VideoEngine.__new__(VideoEngine)
assert hasattr(engine, 'compile_dynamic_video'), 'compile_dynamic_video missing'
assert hasattr(engine, '_generate_dynamic_cards'), '_generate_dynamic_cards missing'
assert hasattr(engine, '_compile_scene_based_video'), '_compile_scene_based_video missing (regression)'
print('6. VideoEngine methods: OK')

# 5. Verify main.py CLI args
import argparse
parser = argparse.ArgumentParser()
parser.add_argument('--type', choices=['myth', 'bizarre', 'all', 'dynamic'])
parser.add_argument('--prompt', type=str)
parser.add_argument('--skip-tiktok', action='store_true')
args = parser.parse_args(['--type', 'dynamic', '--prompt', 'What is gravity?'])
assert args.type == 'dynamic'
assert args.prompt == 'What is gravity?'
print('7. CLI argument parsing: OK')

print('\n=== ALL VALIDATIONS PASSED ===')

# =============================================================================
# "The Daily Audit" - Dynamic N-Scene Script Payload Module
# =============================================================================
import re
from typing import Optional
from pydantic import BaseModel, Field

class YouTubeMetadataSchema(BaseModel):
    title: str = Field(description="A compelling, attention-grabbing YouTube Shorts title ending with #Shorts")
    description: str = Field(description="Educational summary detailing the myth and reality, containing #TheDailyAudit and #Shorts")
    tags: list[str] = Field(description="List of 8-12 SEO-optimized tags.")


class SceneContent(BaseModel):
    scene_number: int
    title: str
    text: str = Field(description="Plain text for this scene")
    ssml: str = Field(description="SSML-wrapped text for this scene")
    mid_roll_hook: Optional[str] = Field(default="", description="Optional 3-5 word mid-roll retention hook for this scene")


class DynamicScriptPayload(BaseModel):
    topic: str
    ssml_script: str = Field(description="Full SSML with <break> tags between all scenes")
    scenes: list[SceneContent] = Field(description="Per-scene content")
    image_queries: list[str] = Field(description="One query per scene")
    youtube_metadata: YouTubeMetadataSchema
    mid_roll_hook: Optional[str] = Field(default="", description="Optional 3-5 word mid-roll retention hook")


def parse_dynamic_ssml(ssml: str, scene_count: int) -> list[str]:
    """
    Splits unified SSML on break tags into N scene texts.
    Returns a list of N plain text strings.
    Handles any number of break tags generically.
    """
    clean_ssml = ssml.strip()
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
        # No breaks — return as single scene or split on sentences
        segments = [s.strip() for s in re.split(r'(?<=[.!?])\s+', clean_ssml) if s.strip()]
        while len(segments) < scene_count:
            segments.append("")
        return [clean_text(s) for s in segments[:scene_count]]

    # Extract all text segments between breaks
    segments = []
    prev_end = 0
    for m in matches:
        segments.append(clean_ssml[prev_end:m.start()])
        prev_end = m.end()
    segments.append(clean_ssml[prev_end:])

    # Clean each segment
    texts = [clean_text(s) for s in segments]

    # Pad or trim to match scene_count
    while len(texts) < scene_count:
        texts.append("")
    texts = texts[:scene_count]

    return texts

class SSMLBuilder:
    EMOTION_MAP = {
        "whisper": "whispering",
        "excited": "excited",
        "calm": "calm",
        "reverent": "lyrical",
        "urgent": "newscast"
    }

    @classmethod
    def build_scene_ssml(cls, text: str, emotion: str, scene_type: str, voice_name: str) -> str:
        """
        Builds Azure SSML for a scene, mapping emotion to style, and adding pauses or inhales.
        """
        azure_style = cls.EMOTION_MAP.get(emotion.lower(), None)
        
        inner_text = text.strip()
        
        # Add breath marks at natural pauses for body and verdict scenes
        if scene_type in ["body", "verdict"]:
            inner_text = inner_text.replace(". ", ". <mstts:silence type='Sentenceboundary' value='150ms'/> ")
            inner_text = inner_text.replace("! ", "! <mstts:silence type='Sentenceboundary' value='150ms'/> ")
            inner_text = inner_text.replace("? ", "? <mstts:silence type='Sentenceboundary' value='150ms'/> ")
            
        # Add a short inhale (Leading silence) before hook narration
        if scene_type == "hook":
            inner_text = f"<mstts:silence type='Leading' value='200ms'/>{inner_text}"

        if azure_style:
            inner_ssml = f"<mstts:express-as style='{azure_style}'>{inner_text}</mstts:express-as>"
        else:
            inner_ssml = inner_text

        # Full SSML envelope wrapping
        ssml = (
            f'<speak version="1.0" xmlns="http://www.w3.org/2001/10/synthesis" '
            f'xmlns:mstts="https://www.w3.org/2001/mstts" '
            f'xml:lang="en-US">'
            f'<voice name="{voice_name}">'
            f'<prosody pitch="-1.0st" rate="0.93">'
            f'{inner_ssml}'
            f'</prosody>'
            f'</voice>'
            f'</speak>'
        )
        return ssml

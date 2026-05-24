import os
from typing import List, Dict, Any

class SubtitleBuilder:
    @staticmethod
    def ms_to_srt_time(ms: float) -> str:
        """Converts milliseconds to SRT timestamp format (HH:MM:SS,mmm)."""
        s = ms / 1000.0
        hours = int(s // 3600)
        minutes = int((s % 3600) // 60)
        seconds = int(s % 60)
        milliseconds = int(round((s % 1) * 1000))
        # Ensure values are within normal ranges
        if milliseconds >= 1000:
            milliseconds = 999
        return f"{hours:02d}:{minutes:02d}:{seconds:02d},{milliseconds:03d}"

    @staticmethod
    def ms_to_vtt_time(ms: float) -> str:
        """Converts milliseconds to VTT timestamp format (HH:MM:SS.mmm)."""
        s = ms / 1000.0
        hours = int(s // 3600)
        minutes = int((s % 3600) // 60)
        seconds = int(s % 60)
        milliseconds = int(round((s % 1) * 1000))
        if milliseconds >= 1000:
            milliseconds = 999
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}.{milliseconds:03d}"

    @classmethod
    def group_words_into_subtitles(cls, word_boundaries: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Groups word boundary events into subtitle lines.
        Rules:
        - Group by sentence (split at '.', '!', '?')
        - Max 2 lines visible at once
        - Max 7 words per line
        - Start time of block = first word offset_ms
        - End time of block = last word offset_ms + duration_ms
        """
        if not word_boundaries:
            return []

        # 1. Group into sentences
        sentences = []
        current_sentence = []
        for wb in word_boundaries:
            current_sentence.append(wb)
            word = wb["word"]
            # Check if this word ends a sentence
            if word and any(word.endswith(p) for p in [".", "!", "?", ".\""]):
                sentences.append(current_sentence)
                current_sentence = []
        if current_sentence:
            sentences.append(current_sentence)

        # 2. Chunk each sentence into subtitle blocks (max 14 words: max 2 lines of max 7 words)
        blocks = []
        for sentence_wbs in sentences:
            if not sentence_wbs:
                continue
            
            # Chunk the sentence words into groups of at most 14 words
            chunk_size = 14
            for i in range(0, len(sentence_wbs), chunk_size):
                chunk = sentence_wbs[i:i + chunk_size]
                
                # Split chunk into at most 2 lines of max 7 words
                line1_wbs = chunk[:7]
                line2_wbs = chunk[7:14]
                
                line1_text = " ".join(w["word"] for w in line1_wbs)
                line2_text = " ".join(w["word"] for w in line2_wbs)
                
                combined_text = line1_text
                if line2_text:
                    combined_text += "\n" + line2_text
                
                start_ms = chunk[0]["offset_ms"]
                end_ms = chunk[-1]["offset_ms"] + chunk[-1]["duration_ms"]
                
                blocks.append({
                    "start_ms": start_ms,
                    "end_ms": end_ms,
                    "text": combined_text
                })

        # 3. Create index for blocks
        subtitle_items = []
        for idx, block in enumerate(blocks):
            subtitle_items.append({
                "index": idx + 1,
                "start_ms": block["start_ms"],
                "end_ms": block["end_ms"],
                "text": block["text"]
            })
            
        return subtitle_items

    @classmethod
    def build_srt(cls, subtitle_items: List[Dict[str, Any]]) -> str:
        """Generates raw SRT file content from subtitle items."""
        lines = []
        for item in subtitle_items:
            start_str = cls.ms_to_srt_time(item["start_ms"])
            end_str = cls.ms_to_srt_time(item["end_ms"])
            lines.append(str(item["index"]))
            lines.append(f"{start_str} --> {end_str}")
            lines.append(item["text"])
            lines.append("")  # Empty line separator
        return "\n".join(lines)

    @classmethod
    def build_vtt(cls, subtitle_items: List[Dict[str, Any]]) -> str:
        """Generates raw VTT file content from subtitle items."""
        lines = ["WEBVTT", ""]
        for item in subtitle_items:
            start_str = cls.ms_to_vtt_time(item["start_ms"])
            end_str = cls.ms_to_vtt_time(item["end_ms"])
            lines.append(str(item["index"]))
            lines.append(f"{start_str} --> {end_str}")
            lines.append(item["text"])
            lines.append("")
        return "\n".join(lines)

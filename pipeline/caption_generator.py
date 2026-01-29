from dataclasses import dataclass, field
from pathlib import Path
from typing import List

import whisper

from config import Config


@dataclass
class WordTimestamp:
    word: str
    start: float
    end: float


@dataclass
class CaptionResult:
    words: List[WordTimestamp] = field(default_factory=list)


class CaptionGenerator:
    def __init__(self, config: Config):
        self.config = config
        self.model = whisper.load_model("base")

    def generate(self, audio_path: Path) -> CaptionResult:
        result = self.model.transcribe(
            str(audio_path),
            word_timestamps=True,
            language="en",
        )

        words: List[WordTimestamp] = []
        for segment in result.get("segments", []):
            for w in segment.get("words", []):
                words.append(WordTimestamp(
                    word=w["word"].strip(),
                    start=w["start"],
                    end=w["end"],
                ))

        return CaptionResult(words=words)

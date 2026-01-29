import asyncio
import re
from dataclasses import dataclass
from pathlib import Path

import edge_tts
from pydub import AudioSegment

from config import Config


@dataclass
class VoiceResult:
    audio_path: Path
    duration: float  # seconds


class VoiceGenerator:
    def __init__(self, config: Config):
        self.config = config

    def generate(self, script: str) -> VoiceResult:
        return asyncio.run(self._generate_async(script))

    async def _generate_async(self, script: str) -> VoiceResult:
        output_path = self.config.cache_dir / "voiceover.wav"

        # Split on "..." to insert pauses
        segments = re.split(r'\.{3,}', script)
        segments = [s.strip() for s in segments if s.strip()]

        if len(segments) <= 1:
            # No pauses, generate directly
            await self._tts_to_file(script, output_path)
        else:
            # Generate each segment, concatenate with pauses
            combined = AudioSegment.empty()
            pause = AudioSegment.silent(duration=700)  # 700ms pause

            for i, segment in enumerate(segments):
                seg_path = self.config.cache_dir / f"voice_seg_{i}.mp3"
                await self._tts_to_file(segment, seg_path)
                seg_audio = AudioSegment.from_file(seg_path)
                combined += seg_audio
                if i < len(segments) - 1:
                    combined += pause
                seg_path.unlink(missing_ok=True)

            combined.export(str(output_path), format="wav")

        audio = AudioSegment.from_file(output_path)
        duration = len(audio) / 1000.0

        return VoiceResult(audio_path=output_path, duration=duration)

    async def _tts_to_file(self, text: str, output_path: Path):
        communicate = edge_tts.Communicate(
            text,
            voice=self.config.voice,
            rate=self.config.speech_rate,
        )
        await communicate.save(str(output_path))

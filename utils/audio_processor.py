from pathlib import Path

from moviepy import AudioFileClip, CompositeAudioClip
from pydub import AudioSegment


def normalize_audio(audio_path: Path, target_dbfs: float = -20.0) -> Path:
    """Normalize audio volume to target dBFS."""
    audio = AudioSegment.from_file(audio_path)
    change = target_dbfs - audio.dBFS
    normalized = audio.apply_gain(change)
    out_path = audio_path.parent / f"norm_{audio_path.name}"
    normalized.export(str(out_path), format="wav")
    return out_path


def mix_audio(
    voice_clip: AudioFileClip,
    music_path: str,
    music_volume: float,
    target_duration: float,
) -> CompositeAudioClip:
    """Mix voice with background music at given volume ratio."""
    music = AudioFileClip(music_path)

    # Loop music if shorter than target
    if music.duration < target_duration:
        loops_needed = int(target_duration / music.duration) + 1
        from moviepy import concatenate_audioclips
        music = concatenate_audioclips([music] * loops_needed)

    music = music.subclipped(0, target_duration)
    music = music.with_volume_scaled(music_volume)

    return CompositeAudioClip([voice_clip, music])

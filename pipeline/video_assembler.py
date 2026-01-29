import re
import textwrap
from pathlib import Path
from typing import Optional

import numpy as np
from moviepy import (
    AudioFileClip,
    CompositeAudioClip,
    CompositeVideoClip,
    VideoFileClip,
    concatenate_videoclips,
)
from PIL import Image, ImageDraw, ImageFont

from config import Config
from pipeline.caption_generator import CaptionResult
from pipeline.visual_sourcer import VisualResult
from pipeline.voice_generator import VoiceResult
from utils.audio_processor import mix_audio, normalize_audio
from utils.video_effects import apply_ken_burns


class VideoAssembler:
    def __init__(self, config: Config):
        self.config = config

    def assemble(
        self,
        visual_result: VisualResult,
        voice_result: VoiceResult,
        caption_result: CaptionResult,
        music_path: Optional[str],
        topic: str,
    ) -> Path:
        target_duration = voice_result.duration
        w, h = self.config.width, self.config.height

        # Build video track from clips
        video_clips = []
        total_clip_dur = 0.0

        for vc in visual_result.clips:
            clip = VideoFileClip(str(vc.path))
            # Resize to fill 9:16 frame
            clip = self._resize_to_fill(clip, w, h)

            # Determine how long to use this clip
            remaining = target_duration - total_clip_dur
            if remaining <= 0:
                clip.close()
                break
            use_dur = min(clip.duration, remaining, 8.0)
            if use_dur < 0.5:
                clip.close()
                break
            clip = clip.subclipped(0, use_dur)

            # Apply Ken Burns
            clip = apply_ken_burns(clip, w, h)

            video_clips.append(clip)
            total_clip_dur += use_dur

        if not video_clips:
            raise RuntimeError("No video clips to assemble")

        # If we don't have enough footage, loop
        while total_clip_dur < target_duration:
            for vc_orig in video_clips.copy():
                if total_clip_dur >= target_duration:
                    break
                remaining = target_duration - total_clip_dur
                use_dur = min(vc_orig.duration, remaining)
                looped = vc_orig.subclipped(0, use_dur)
                video_clips.append(looped)
                total_clip_dur += use_dur

        # Concatenate with crossfade
        if len(video_clips) > 1:
            final_video = concatenate_videoclips(video_clips, method="compose")
        else:
            final_video = video_clips[0]

        final_video = final_video.subclipped(0, min(final_video.duration, target_duration))

        # Caption overlay
        if caption_result.words:
            final_video = self._add_captions(final_video, caption_result)

        # Audio: voice + optional music
        voice_audio = AudioFileClip(str(voice_result.audio_path))

        if music_path and Path(music_path).exists():
            final_audio = mix_audio(voice_audio, music_path, self.config.music_volume, target_duration)
        else:
            final_audio = voice_audio

        final_video = final_video.with_audio(final_audio)

        # Export
        safe_topic = re.sub(r'[^\w\s-]', '', topic)[:40].strip().replace(' ', '_')
        output_path = self.config.output_dir / f"{safe_topic}.mp4"

        codec = "h264_nvenc" if self.config.use_nvenc else "libx264"
        try:
            final_video.write_videofile(
                str(output_path),
                fps=self.config.fps,
                codec=codec,
                audio_codec="aac",
                preset="fast" if self.config.use_nvenc else "medium",
                threads=4,
                logger=None,
            )
        except Exception:
            # Fallback to CPU encoding if nvenc fails
            if self.config.use_nvenc:
                final_video.write_videofile(
                    str(output_path),
                    fps=self.config.fps,
                    codec="libx264",
                    audio_codec="aac",
                    preset="medium",
                    threads=4,
                    logger=None,
                )
            else:
                raise

        final_video.close()
        return output_path

    def _resize_to_fill(self, clip, target_w, target_h):
        """Resize clip to fill target dimensions (crop overflow)."""
        cw, ch = clip.size
        scale = max(target_w / cw, target_h / ch)
        clip = clip.resized(scale)
        # Center crop
        nw, nh = clip.size
        x_off = (nw - target_w) // 2
        y_off = (nh - target_h) // 2
        clip = clip.cropped(x1=x_off, y1=y_off, width=target_w, height=target_h)
        return clip

    def _add_captions(self, video, caption_result: CaptionResult):
        """Overlay word-by-word captions using Pillow rendering."""
        w, h = self.config.width, self.config.height

        # Group words into caption chunks
        chunks = self._chunk_words(caption_result.words)

        def make_frame_with_caption(get_frame, t):
            frame = get_frame(t)

            # Find active chunk
            active_chunk = None
            for chunk in chunks:
                if chunk["start"] <= t <= chunk["end"]:
                    active_chunk = chunk
                    break

            if not active_chunk:
                return frame

            # Render caption with Pillow
            img = Image.fromarray(frame)
            draw = ImageDraw.Draw(img)

            try:
                font = ImageFont.truetype(self.config.font_path, self.config.font_size)
            except (OSError, IOError):
                font = ImageFont.load_default()

            text = active_chunk["text"]
            padding = int(w * 0.08)  # 8% horizontal padding
            max_text_w = w - padding * 2

            # Wrap text to fit within padded area
            wrapped = textwrap.fill(text, width=self.config.caption_max_chars)

            # Measure text
            bbox = draw.textbbox((0, 0), wrapped, font=font)
            tw = bbox[2] - bbox[0]
            th = bbox[3] - bbox[1]

            # Clamp text width: re-wrap tighter if it exceeds padded area
            if tw > max_text_w:
                ratio = max_text_w / tw
                narrower = max(10, int(self.config.caption_max_chars * ratio))
                wrapped = textwrap.fill(text, width=narrower)
                bbox = draw.textbbox((0, 0), wrapped, font=font)
                tw = bbox[2] - bbox[0]
                th = bbox[3] - bbox[1]

            # Center horizontally and vertically
            x = (w - tw) // 2
            y = (h - th) // 2

            # Draw stroke
            sw = self.config.caption_stroke_width
            for dx in range(-sw, sw + 1):
                for dy in range(-sw, sw + 1):
                    if dx * dx + dy * dy <= sw * sw:
                        draw.text(
                            (x + dx, y + dy),
                            wrapped,
                            font=font,
                            fill=self.config.caption_stroke_color,
                        )

            # Draw text
            draw.text((x, y), wrapped, font=font, fill=self.config.caption_color)

            return np.array(img)

        return video.transform(make_frame_with_caption)

    def _chunk_words(self, words, max_words=4):
        """Group words into display chunks of max_words."""
        chunks = []
        i = 0
        while i < len(words):
            end = min(i + max_words, len(words))
            chunk_words = words[i:end]
            chunks.append({
                "text": " ".join(w.word for w in chunk_words),
                "start": chunk_words[0].start,
                "end": chunk_words[-1].end,
            })
            i = end
        return chunks

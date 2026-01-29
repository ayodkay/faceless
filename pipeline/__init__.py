from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

from config import Config
from pipeline.script_generator import ScriptGenerator, ScriptResult
from pipeline.voice_generator import VoiceGenerator, VoiceResult
from pipeline.caption_generator import CaptionGenerator, CaptionResult
from pipeline.visual_sourcer import VisualSourcer, VisualResult
from pipeline.video_assembler import VideoAssembler

console = Console()


def run_pipeline(
    topic: str,
    config: Config,
    niche: str = "general",
    music_path: Optional[str] = None,
) -> Path:
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        # Stage 1: Script
        task = progress.add_task("Generating script...", total=None)
        script_gen = ScriptGenerator(config)
        script_result = script_gen.generate(topic, niche)
        console.print(f"[green]✓[/] Script: {len(script_result.text.split())} words")
        progress.remove_task(task)

        # Stage 2: Voice
        task = progress.add_task("Generating voiceover...", total=None)
        voice_gen = VoiceGenerator(config)
        voice_result = voice_gen.generate(script_result.text)
        console.print(f"[green]✓[/] Voice: {voice_result.duration:.1f}s")
        progress.remove_task(task)

        # Stage 3: Captions
        task = progress.add_task("Generating captions...", total=None)
        caption_gen = CaptionGenerator(config)
        caption_result = caption_gen.generate(voice_result.audio_path)
        console.print(f"[green]✓[/] Captions: {len(caption_result.words)} words")
        progress.remove_task(task)

        # Stage 4: Visuals
        task = progress.add_task("Sourcing visuals...", total=None)
        visual_sourcer = VisualSourcer(config)
        visual_result = visual_sourcer.source(script_result.text, voice_result.duration)
        console.print(f"[green]✓[/] Visuals: {len(visual_result.clips)} clips")
        progress.remove_task(task)

        # Stage 5: Assembly
        task = progress.add_task("Assembling video...", total=None)
        assembler = VideoAssembler(config)
        output_path = assembler.assemble(
            visual_result=visual_result,
            voice_result=voice_result,
            caption_result=caption_result,
            music_path=music_path,
            topic=topic,
        )
        console.print(f"[green]✓[/] Output: {output_path}")
        progress.remove_task(task)

    return output_path

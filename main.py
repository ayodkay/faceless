#!/usr/bin/env python3
"""Faceless Video Generator — Create short-form videos from a topic."""

import argparse
import sys

from rich.console import Console

from config import Config
from pipeline import run_pipeline

console = Console()


def main():
    parser = argparse.ArgumentParser(
        description="Generate faceless short-form videos from a topic.",
    )
    parser.add_argument("topic", help="Video topic (e.g. 'The Dyatlov Pass incident')")
    parser.add_argument("--niche", default="general", help="Content niche (default: general)")
    parser.add_argument("--voice", default=None, help="Edge-TTS voice name")
    parser.add_argument("--duration", type=int, default=60, help="Target duration in seconds (default: 60)")
    parser.add_argument("--music", default=None, help="Path to background music file")
    parser.add_argument("--output", default=None, help="Output directory")
    parser.add_argument("--source", default=None, choices=["pexels", "pixabay", "both"],
                        help="Video source: pexels, pixabay, or both (default: from .env or pexels)")
    parser.add_argument("--no-gpu", action="store_true", help="Disable GPU acceleration")

    args = parser.parse_args()

    config = Config()
    config.target_duration = args.duration

    if args.voice:
        config.voice = args.voice
    if args.source:
        config.video_source = args.source
    if args.output:
        from pathlib import Path
        config.output_dir = Path(args.output)
        config.output_dir.mkdir(exist_ok=True)
    if args.no_gpu:
        config.use_nvenc = False

    # Validate API keys for chosen source
    source = config.video_source.lower()
    if source in ("pexels", "both") and not config.pexels_api_key:
        console.print("[red]Error:[/] PEXELS_API_KEY not set. Add it to .env file.")
        sys.exit(1)
    if source in ("pixabay", "both") and not config.pixabay_api_key:
        console.print("[red]Error:[/] PIXABAY_API_KEY not set. Add it to .env file.")
        sys.exit(1)

    console.print(f"[bold]Generating video:[/] {args.topic}")
    console.print(f"  Niche: {args.niche} | Duration: {args.duration}s | Voice: {config.voice} | Source: {config.video_source}")
    console.print()

    try:
        output_path = run_pipeline(
            topic=args.topic,
            config=config,
            niche=args.niche,
            music_path=args.music,
        )
        console.print()
        console.print(f"[bold green]Done![/] Video saved to: {output_path}")
    except KeyboardInterrupt:
        console.print("\n[yellow]Cancelled.[/]")
        sys.exit(1)
    except Exception as e:
        console.print(f"\n[red]Error:[/] {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

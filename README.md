# Faceless Video Generator

Generate short-form vertical (9:16) videos from a text topic using AI-generated scripts, text-to-speech narration, stock footage, and word-level captions.

## Prerequisites

Before starting, make sure you have:

- **Python 3.13+** (tested on 3.14)
- **FFmpeg** installed and on PATH ([download](https://ffmpeg.org/download.html))
- **Ollama** running locally with a model pulled ([install](https://ollama.ai))
- **Pexels API key** (free at [pexels.com/api](https://www.pexels.com/api/))
- **NVIDIA GPU** (optional, used for faster video encoding and Whisper transcription)

## Setup

### 1. Clone and enter the project

```bash
cd faceless
```

### 2. Create a virtual environment

```bash
python -m venv .venv
```

Activate it:

```bash
# Windows
.venv\Scripts\activate

# Linux/macOS
source .venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Set up Ollama

Install Ollama from [ollama.ai](https://ollama.ai), then pull a model:

```bash
ollama pull llama3
```

Make sure the Ollama server is running (it starts automatically after install, or run `ollama serve`).

### 5. Configure environment variables

Copy the example env file and fill in your API key:

```bash
cp .env.example .env
```

Edit `.env`:

```
PEXELS_API_KEY=your_actual_pexels_api_key
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3
```

| Variable | Required | Description |
|---|---|---|
| `PEXELS_API_KEY` | Yes | Your Pexels API key for stock video |
| `OLLAMA_BASE_URL` | No | Ollama server URL (default: `http://localhost:11434`) |
| `OLLAMA_MODEL` | No | Model to use for script/keyword generation (default: `llama3`) |

### 6. (Optional) Add background music

Place any `.mp3` or `.wav` file in `assets/music/`. You'll reference it with the `--music` flag.

## Usage

### Basic usage

```bash
python main.py "The Dyatlov Pass incident"
```

This generates a ~60 second video using default settings and saves it to `output/`.

### Full options

```bash
python main.py "Your topic here" \
  --niche history \
  --voice en-US-BrianNeural \
  --duration 90 \
  --music assets/music/ambient.mp3 \
  --output my_videos \
  --no-gpu
```

| Flag | Default | Description |
|---|---|---|
| `topic` (positional) | *required* | The video topic/subject |
| `--niche` | `general` | Content niche (e.g. `history`, `science`, `crime`, `nature`) |
| `--voice` | `en-US-ChristopherNeural` | Edge-TTS voice (see list below) |
| `--duration` | `120` | Target video duration in seconds |
| `--music` | none | Path to a background music file |
| `--output` | `output/` | Output directory for the final video |
| `--no-gpu` | off | Disable NVIDIA GPU encoding (use CPU instead) |

### Examples

Short science explainer:
```bash
python main.py "Why is the sky blue" --niche science --duration 30
```

Longer true crime video with music and female voice:
```bash
python main.py "The disappearance of DB Cooper" --niche crime --duration 120 --voice en-US-EmmaNeural --music assets/music/dark-ambient.mp3
```

History short with custom output:
```bash
python main.py "The fall of the Roman Empire" --niche history --output my_exports
```

## Available Voices

Common English (US) voices:

| Voice | Gender |
|---|---|
| `en-US-ChristopherNeural` | Male |
| `en-US-BrianNeural` | Male |
| `en-US-AndrewNeural` | Male |
| `en-US-EricNeural` | Male |
| `en-US-GuyNeural` | Male |
| `en-US-RogerNeural` | Male |
| `en-US-EmmaNeural` | Female |
| `en-US-AriaNeural` | Female |
| `en-US-AvaNeural` | Female |
| `en-US-JennyNeural` | Female |
| `en-US-MichelleNeural` | Female |

List all available voices:
```bash
python -c "import edge_tts, asyncio; voices = asyncio.run(edge_tts.list_voices()); [print(v['ShortName'], '-', v['Gender']) for v in voices]"
```

## How It Works

The pipeline runs 5 stages in sequence:

### Stage 1 — Script Generation
Sends your topic to Ollama and gets back a narration script in JSON format. The prompt targets a specific word count based on your `--duration` setting (~2.5 words/second). The script includes dramatic pauses marked with `...`.

### Stage 2 — Voice Generation
Converts the script to speech using Microsoft Edge TTS. Pause markers (`...`) are split into separate TTS calls with 700ms silence inserted between them. Output is a WAV file.

### Stage 3 — Caption Generation
Runs OpenAI Whisper on the generated audio to extract word-level timestamps. Each word gets a precise start and end time, which is used to display captions in sync with speech.

### Stage 4 — Visual Sourcing
Extracts visual keywords from the script (using Ollama), then searches the Pexels API for portrait-oriented stock video clips matching those keywords. Clips are downloaded and cached in `cache/videos/` so repeat runs with similar topics reuse footage.

### Stage 5 — Video Assembly
Combines everything into a final 1080x1920 (9:16) MP4:
- Stock clips are resized to fill the frame (center-cropped)
- Ken Burns effect (slow zoom/pan) applied to each clip
- Word-by-word captions rendered with Pillow (Montserrat Bold, white text with black stroke)
- Voice audio set as primary track
- Background music mixed at 10% volume (if provided)
- Encoded with h264_nvenc (GPU) or libx264 (CPU fallback)

## Project Structure

```
faceless/
├── main.py                      # CLI entry point
├── config.py                    # Settings and configuration
├── requirements.txt             # Python dependencies
├── .env.example                 # Environment variable template
├── pipeline/
│   ├── __init__.py              # Pipeline orchestrator
│   ├── script_generator.py      # Stage 1: Ollama script generation
│   ├── voice_generator.py       # Stage 2: Edge-TTS voice synthesis
│   ├── caption_generator.py     # Stage 3: Whisper word timestamps
│   ├── visual_sourcer.py        # Stage 4: Pexels video search/download
│   └── video_assembler.py       # Stage 5: MoviePy composition + export
├── utils/
│   ├── text_processor.py        # Keyword extraction from scripts
│   ├── video_effects.py         # Ken Burns effect
│   └── audio_processor.py       # Volume normalization, audio mixing
├── assets/
│   ├── fonts/
│   │   └── Montserrat-Bold.ttf  # Caption font
│   └── music/                   # Place background music here
├── output/                      # Generated videos saved here
└── cache/                       # Cached audio, video clips, metadata
```

## Troubleshooting

**"PEXELS_API_KEY not set"**
Create a `.env` file from `.env.example` and add your key. Get one free at [pexels.com/api](https://www.pexels.com/api/).

**"Could not source any video clips"**
Check that your Pexels API key is valid. Try a simpler topic. Check your internet connection.

**"Script too short"**
The Ollama model produced fewer words than expected. Try a different model (`OLLAMA_MODEL=llama3.1` in `.env`) or a more specific topic.

**Video encoding fails with nvenc error**
Your GPU may not support NVENC. Use `--no-gpu` to fall back to CPU encoding.

**`ModuleNotFoundError: No module named 'audioop'`**
You're on Python 3.13+. Install the compatibility shim: `pip install audioop-lts`.

**FFmpeg not found**
Install FFmpeg and make sure it's on your PATH. On Windows, download from [ffmpeg.org](https://ffmpeg.org/download.html) and add the `bin` folder to your system PATH.

**Ollama connection refused**
Make sure Ollama is running: `ollama serve`. Check that `OLLAMA_BASE_URL` in `.env` matches your setup.

import os
from dataclasses import dataclass, field
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).parent


@dataclass
class Config:
    # API
    pexels_api_key: str = field(default_factory=lambda: os.getenv("PEXELS_API_KEY", ""))
    pixabay_api_key: str = field(default_factory=lambda: os.getenv("PIXABAY_API_KEY", ""))
    video_source: str = field(default_factory=lambda: os.getenv("VIDEO_SOURCE", "pexels"))  # pexels, pixabay, or both
    ollama_base_url: str = field(default_factory=lambda: os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"))
    ollama_model: str = field(default_factory=lambda: os.getenv("OLLAMA_MODEL", "llama3"))

    # Video
    width: int = 1080
    height: int = 1920
    fps: int = 30
    target_duration: int = 60  # seconds

    # Voice
    voice: str = "en-US-ChristopherNeural"
    speech_rate: str = "+0%"

    # Captions
    font_path: str = str(BASE_DIR / "assets" / "fonts" / "Montserrat-Bold.ttf")
    font_size: int = 70
    caption_color: str = "white"
    caption_stroke_color: str = "black"
    caption_stroke_width: int = 4
    caption_max_chars: int = 30
    caption_y_position: float = 0.70  # fraction from top

    # Music
    music_volume: float = 0.10  # relative to voice

    # Paths
    output_dir: Path = field(default_factory=lambda: BASE_DIR / "output")
    cache_dir: Path = field(default_factory=lambda: BASE_DIR / "cache")

    # Encoding
    use_nvenc: bool = True

    def __post_init__(self):
        self.output_dir.mkdir(exist_ok=True)
        self.cache_dir.mkdir(exist_ok=True)

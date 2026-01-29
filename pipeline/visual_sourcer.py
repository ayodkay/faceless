import hashlib
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import List

import requests

from config import Config
from utils.text_processor import extract_keywords


@dataclass
class VideoClip:
    path: Path
    duration: float
    keyword: str


@dataclass
class VisualResult:
    clips: List[VideoClip] = field(default_factory=list)


class VisualSourcer:
    PEXELS_VIDEO_SEARCH = "https://api.pexels.com/videos/search"

    def __init__(self, config: Config):
        self.config = config
        self.video_cache_dir = config.cache_dir / "videos"
        self.video_cache_dir.mkdir(exist_ok=True)

    def source(self, script: str, target_duration: float) -> VisualResult:
        keywords = extract_keywords(script, self.config)
        if not keywords:
            keywords = ["nature", "abstract", "landscape"]

        clips: List[VideoClip] = []
        total_duration = 0.0
        clip_target = 5.0  # seconds per clip roughly
        needed_clips = max(3, int(target_duration / clip_target))

        keyword_index = 0
        while total_duration < target_duration and keyword_index < len(keywords) * 2:
            keyword = keywords[keyword_index % len(keywords)]
            keyword_index += 1

            clip = self._search_and_download(keyword, orientation="portrait")
            if clip:
                clips.append(clip)
                total_duration += clip.duration
                if len(clips) >= needed_clips and total_duration >= target_duration:
                    break

        if not clips:
            raise RuntimeError(
                "Could not source any video clips. Check your Pexels API key."
            )

        return VisualResult(clips=clips)

    def _search_and_download(self, keyword: str, orientation: str = "portrait") -> VideoClip | None:
        cache_key = hashlib.md5(keyword.encode()).hexdigest()
        meta_path = self.video_cache_dir / f"{cache_key}.json"

        # Check cache
        if meta_path.exists():
            meta = json.loads(meta_path.read_text())
            video_path = Path(meta["path"])
            if video_path.exists():
                return VideoClip(
                    path=video_path,
                    duration=meta["duration"],
                    keyword=keyword,
                )

        headers = {"Authorization": self.config.pexels_api_key}
        params = {
            "query": keyword,
            "orientation": orientation,
            "per_page": 5,
            "size": "medium",
        }

        try:
            resp = requests.get(self.PEXELS_VIDEO_SEARCH, headers=headers, params=params, timeout=15)
            resp.raise_for_status()
            data = resp.json()
        except requests.RequestException:
            return None

        videos = data.get("videos", [])
        if not videos:
            return None

        # Pick first video that has an HD file
        for video in videos:
            duration = video.get("duration", 0)
            video_files = video.get("video_files", [])

            # Prefer HD quality, portrait-ish
            best_file = None
            for vf in video_files:
                w = vf.get("width", 0)
                h = vf.get("height", 0)
                if h >= 720 and (best_file is None or h > best_file.get("height", 0)):
                    best_file = vf

            if not best_file:
                best_file = video_files[0] if video_files else None

            if not best_file:
                continue

            download_url = best_file["link"]
            video_path = self.video_cache_dir / f"{cache_key}.mp4"

            try:
                dl = requests.get(download_url, timeout=60, stream=True)
                dl.raise_for_status()
                with open(video_path, "wb") as f:
                    for chunk in dl.iter_content(chunk_size=8192):
                        f.write(chunk)
            except requests.RequestException:
                continue

            # Save metadata
            meta = {"path": str(video_path), "duration": duration, "keyword": keyword}
            meta_path.write_text(json.dumps(meta))

            return VideoClip(path=video_path, duration=duration, keyword=keyword)

        return None

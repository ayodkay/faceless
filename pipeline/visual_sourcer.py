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
    PIXABAY_VIDEO_SEARCH = "https://pixabay.com/api/videos/"

    def __init__(self, config: Config):
        self.config = config
        self.video_cache_dir = config.cache_dir / "videos"
        self.video_cache_dir.mkdir(exist_ok=True)

        source = config.video_source.lower()
        self._sources: List[str] = []
        if source == "both":
            if config.pexels_api_key:
                self._sources.append("pexels")
            if config.pixabay_api_key:
                self._sources.append("pixabay")
        elif source == "pixabay":
            self._sources.append("pixabay")
        else:
            self._sources.append("pexels")

        if not self._sources:
            raise RuntimeError(
                "No video source configured. Set PEXELS_API_KEY or PIXABAY_API_KEY in .env"
            )

    def source(self, script: str, target_duration: float) -> VisualResult:
        keywords = extract_keywords(script, self.config)
        if not keywords:
            keywords = ["nature", "abstract", "landscape"]

        clips: List[VideoClip] = []
        total_duration = 0.0
        clip_target = 5.0
        needed_clips = max(3, int(target_duration / clip_target))

        keyword_index = 0
        while total_duration < target_duration and keyword_index < len(keywords) * 2:
            keyword = keywords[keyword_index % len(keywords)]
            keyword_index += 1

            # Alternate between sources when using "both"
            source = self._sources[keyword_index % len(self._sources)]
            clip = self._search_and_download(keyword, source=source)
            if clip:
                clips.append(clip)
                total_duration += clip.duration
                if len(clips) >= needed_clips and total_duration >= target_duration:
                    break

        if not clips:
            raise RuntimeError(
                "Could not source any video clips. Check your API keys."
            )

        return VisualResult(clips=clips)

    def _search_and_download(self, keyword: str, source: str = "pexels") -> VideoClip | None:
        cache_key = hashlib.md5(f"{source}:{keyword}".encode()).hexdigest()
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

        if source == "pixabay":
            return self._search_pixabay(keyword, cache_key, meta_path)
        return self._search_pexels(keyword, cache_key, meta_path)

    # ── Pexels ──

    def _search_pexels(self, keyword: str, cache_key: str, meta_path: Path) -> VideoClip | None:
        headers = {"Authorization": self.config.pexels_api_key}
        params = {
            "query": keyword,
            "orientation": "portrait",
            "per_page": 5,
            "size": "medium",
        }

        try:
            resp = requests.get(self.PEXELS_VIDEO_SEARCH, headers=headers, params=params, timeout=15)
            resp.raise_for_status()
            data = resp.json()
        except requests.RequestException:
            return None

        for video in data.get("videos", []):
            duration = video.get("duration", 0)
            video_files = video.get("video_files", [])

            best_file = None
            for vf in video_files:
                h = vf.get("height", 0)
                if h >= 720 and (best_file is None or h > best_file.get("height", 0)):
                    best_file = vf

            if not best_file:
                best_file = video_files[0] if video_files else None
            if not best_file:
                continue

            download_url = best_file["link"]
            return self._download_clip(download_url, keyword, duration, cache_key, meta_path)

        return None

    # ── Pixabay ──

    def _search_pixabay(self, keyword: str, cache_key: str, meta_path: Path) -> VideoClip | None:
        params = {
            "key": self.config.pixabay_api_key,
            "q": keyword,
            "video_type": "film",
            "per_page": 5,
            "safesearch": "true",
        }

        try:
            resp = requests.get(self.PIXABAY_VIDEO_SEARCH, params=params, timeout=15)
            resp.raise_for_status()
            data = resp.json()
        except requests.RequestException:
            return None

        for hit in data.get("hits", []):
            duration = hit.get("duration", 0)
            videos = hit.get("videos", {})

            # Prefer "large" then "medium" then "small"
            best = videos.get("large") or videos.get("medium") or videos.get("small")
            if not best or not best.get("url"):
                continue

            download_url = best["url"]
            return self._download_clip(download_url, keyword, duration, cache_key, meta_path)

        return None

    # ── Shared download ──

    def _download_clip(
        self, url: str, keyword: str, duration: float, cache_key: str, meta_path: Path
    ) -> VideoClip | None:
        video_path = self.video_cache_dir / f"{cache_key}.mp4"

        try:
            dl = requests.get(url, timeout=60, stream=True)
            dl.raise_for_status()
            with open(video_path, "wb") as f:
                for chunk in dl.iter_content(chunk_size=8192):
                    f.write(chunk)
        except requests.RequestException:
            return None

        meta = {"path": str(video_path), "duration": duration, "keyword": keyword}
        meta_path.write_text(json.dumps(meta))

        return VideoClip(path=video_path, duration=duration, keyword=keyword)

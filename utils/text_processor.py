import json
from typing import List

import requests

from config import Config


def extract_keywords(script: str, config: Config, count: int = 10) -> List[str]:
    """Use Ollama to extract visual search keywords from the script."""
    prompt = f"""Extract {count} visual search keywords from this script for finding stock video footage.
Return ONLY a JSON array of strings. Each keyword should be 1-3 words, concrete and visual.
Example: ["ocean waves", "mountain sunset", "city traffic"]

Script:
{script}"""

    try:
        resp = requests.post(
            f"{config.ollama_base_url}/api/generate",
            json={
                "model": config.ollama_model,
                "prompt": prompt,
                "stream": False,
                "format": "json",
            },
            timeout=60,
        )
        resp.raise_for_status()
        raw = resp.json()["response"]

        # Parse — Ollama may wrap in {"keywords": [...]} or return bare [...]
        data = json.loads(raw)
        if isinstance(data, list):
            return [str(k) for k in data[:count]]
        if isinstance(data, dict):
            for v in data.values():
                if isinstance(v, list):
                    return [str(k) for k in v[:count]]

        return _fallback_keywords(script)
    except Exception:
        return _fallback_keywords(script)


def _fallback_keywords(script: str) -> List[str]:
    """Simple fallback: extract nouns-ish words by length and frequency."""
    stop_words = {
        "the", "a", "an", "is", "are", "was", "were", "be", "been", "being",
        "have", "has", "had", "do", "does", "did", "will", "would", "could",
        "should", "may", "might", "shall", "can", "to", "of", "in", "for",
        "on", "with", "at", "by", "from", "as", "into", "about", "but",
        "not", "or", "and", "if", "then", "than", "that", "this", "these",
        "those", "it", "its", "they", "them", "their", "we", "our", "you",
        "your", "he", "she", "his", "her", "my", "me", "so", "no", "up",
        "out", "just", "also", "very", "all", "how", "what", "when", "where",
        "who", "which", "there", "here", "more", "some", "any", "each",
        "every", "both", "few", "most", "other", "over", "such", "only",
    }
    words = script.lower().split()
    words = [w.strip(".,!?;:\"'()-") for w in words]
    words = [w for w in words if len(w) > 3 and w not in stop_words]

    # Frequency-based
    freq = {}
    for w in words:
        freq[w] = freq.get(w, 0) + 1

    sorted_words = sorted(freq.keys(), key=lambda w: freq[w], reverse=True)
    return sorted_words[:10]

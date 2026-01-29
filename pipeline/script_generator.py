import json
from dataclasses import dataclass

import requests

from config import Config


@dataclass
class ScriptResult:
    text: str
    title: str


PROMPT_TEMPLATE = """You are a viral short-form video scriptwriter. Write a script for a {niche} video about: {topic}

Requirements:
- Target length: {word_count} words (approximately {duration} seconds of speech)
- Write ONLY the narration text. No stage directions, no [brackets], no scene descriptions.
- Start with a strong hook in the first sentence.
- Use "..." for dramatic pauses.
- Keep sentences short and punchy.
- End with a memorable closing line.
- Do NOT include a title, intro, or sign-off.

Also provide a short video title (max 8 words).

Respond in this exact JSON format:
{{"title": "Your Title Here", "script": "Your narration script here..."}}
"""


class ScriptGenerator:
    def __init__(self, config: Config):
        self.config = config

    def generate(self, topic: str, niche: str = "general") -> ScriptResult:
        words_per_second = 2.5
        target_words = int(self.config.target_duration * words_per_second)

        prompt = PROMPT_TEMPLATE.format(
            niche=niche,
            topic=topic,
            word_count=target_words,
            duration=self.config.target_duration,
        )

        response = requests.post(
            f"{self.config.ollama_base_url}/api/generate",
            json={
                "model": self.config.ollama_model,
                "prompt": prompt,
                "stream": False,
                "format": "json",
            },
            timeout=120,
        )
        response.raise_for_status()

        raw = response.json()["response"]
        data = json.loads(raw)

        script_text = data.get("script", raw)
        title = data.get("title", topic)

        # Validate word count — warn but don't fail
        word_count = len(script_text.split())
        if word_count < target_words * 0.5:
            raise ValueError(
                f"Script too short: {word_count} words (expected ~{target_words}). "
                "Try a different model or topic."
            )

        return ScriptResult(text=script_text, title=title)

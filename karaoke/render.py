from __future__ import annotations

import json
import subprocess
from pathlib import Path

from .models import TimedText


def write_lyrics_json(lyrics: list[TimedText], destination: Path) -> Path:
    """Cria legendas editáveis para a sobreposição em tempo real do WebApp."""
    destination.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema_version": 1,
        "lyrics": [
            {"start": round(item.start, 3), "end": round(item.end, 3), "text": item.text}
            for item in lyrics
        ],
    }
    destination.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return destination


def render_video(video: Path, instrumental: Path, destination: Path) -> Path:
    """Substitui o áudio original pelo instrumental, sem queimar legendas."""
    destination.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        [
            "ffmpeg", "-y", "-i", str(video), "-i", str(instrumental),
            "-map", "0:v:0", "-map", "1:a:0",
            "-map_metadata", "0", "-c:v", "libx264", "-c:a", "aac", "-shortest", str(destination),
        ],
        check=True,
    )
    return destination

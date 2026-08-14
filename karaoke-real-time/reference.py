from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

VIDEO_EXTENSIONS = {".mp4", ".mkv", ".mov", ".webm", ".avi"}


@dataclass(frozen=True)
class ReferenceNote:
    start: float
    end: float
    midi: int
    hz: float
    note_name: str
    lyric: str


def load_reference(path: Path) -> list[ReferenceNote]:
    """Lê as notas produzidas pelo audit.json do pipeline offline."""
    payload = json.loads(path.read_text(encoding="utf-8"))
    return [
        ReferenceNote(
            start=float(item["start"]),
            end=float(item["end"]),
            midi=int(item["midi"]),
            hz=float(item["hz"]),
            note_name=item.get("note_name", f"MIDI {item['midi']}"),
            lyric=item.get("lyric", ""),
        )
        for item in payload.get("notes", [])
    ]


def note_at(notes: list[ReferenceNote], elapsed: float) -> ReferenceNote | None:
    """Obtém a nota de referência ativa no relógio do vídeo."""
    return next((note for note in notes if note.start <= elapsed < note.end), None)


def audit_path_for(video: Path) -> Path:
    """Retorna o arquivo de auditoria pareado a um vídeo final."""
    return video.with_suffix(".audit.json")


def find_videos(library: Path) -> list[Path]:
    """Lista os vídeos de uma biblioteca local em ordem alfabética."""
    return sorted((item for item in library.iterdir() if item.is_file() and item.suffix.lower() in VIDEO_EXTENSIONS), key=lambda item: item.name.lower())

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from .models import SungNote, TimedText

PITCH_CLASSES = ("C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B")


def midi_to_note_name(midi: int) -> str:
    """Converte MIDI em nome cromático internacional, como C4 ou F#3."""
    if not 0 <= midi <= 127:
        raise ValueError(f"MIDI fora do intervalo válido: {midi}")
    return f"{PITCH_CLASSES[midi % 12]}{midi // 12 - 1}"


def write_audit_json(
    destination: Path,
    source_video: Path,
    lyrics: list[TimedText],
    notes: list[SungNote],
) -> Path:
    """Registra a linha do tempo detectada para auditoria de sincronização."""
    lyric_events = [
        {"type": "lyric", "start": round(item.start, 3), "end": round(item.end, 3), "text": item.text}
        for item in lyrics
    ]
    note_events = [
        {
            "type": "note",
            "start": round(item.start, 3),
            "end": round(item.end, 3),
            "midi": item.midi,
            "note_name": midi_to_note_name(item.midi),
            "hz": round(item.hz, 3),
            "lyric": item.lyric,
        }
        for item in notes
    ]
    timeline = sorted(lyric_events + note_events, key=lambda item: (item["start"], item["type"]))
    payload = {
        "schema_version": 1,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source_video": str(source_video),
        "lyrics": lyric_events,
        "notes": note_events,
        "timeline": timeline,
    }
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return destination

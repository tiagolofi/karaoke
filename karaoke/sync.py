from __future__ import annotations

from .models import SungNote, TimedText


def synchronize(lyrics: list[TimedText], notes: list[SungNote]) -> list[SungNote]:
    """Associa cada nota ao segmento de letra com maior sobreposição temporal."""
    result: list[SungNote] = []
    for note in notes:
        best = max(lyrics, key=lambda item: max(0.0, min(note.end, item.end) - max(note.start, item.start)), default=None)
        lyric = best.text if best and best.start < note.end and best.end > note.start else ""
        result.append(SungNote(note.start, note.end, note.midi, note.hz, lyric))
    return result

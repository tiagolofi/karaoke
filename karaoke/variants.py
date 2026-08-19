from __future__ import annotations

from pathlib import Path

from .models import SungNote

VARIANT_SEMITONES = tuple(range(-3, 4))


def variant_label(semitones: int) -> str:
    """Nome estável para a variante musical dentro da coleção."""
    if semitones == 0:
        return "original"
    return f"transpose{semitones:+d}"


def variant_directory(variants_dir: Path, collection_name: str, semitones: int) -> Path:
    return variants_dir / collection_name / variant_label(semitones)


def transpose_notes(notes: list[SungNote], semitones: int) -> list[SungNote]:
    """Desloca notas e frequências sem alterar seus tempos ou letras."""
    shifted: list[SungNote] = []
    frequency_ratio = 2 ** (semitones / 12)
    for note in notes:
        midi = note.midi + semitones
        if not 0 <= midi <= 127:
            raise ValueError(f"Transpose de {semitones:+d} coloca a nota fora do intervalo MIDI: {note.midi}")
        shifted.append(SungNote(note.start, note.end, midi, note.hz * frequency_ratio, note.lyric))
    return shifted

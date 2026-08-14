from __future__ import annotations

import librosa
import numpy as np

from .models import SungNote


def detect_notes(vocals_path: str, frame_length: int = 2048, hop_length: int = 256) -> list[SungNote]:
    """Detecta trechos vocais afinados por pYIN e consolida notas adjacentes."""
    y, sr = librosa.load(vocals_path, sr=None, mono=True)
    f0, voiced, _ = librosa.pyin(y, fmin=librosa.note_to_hz("C2"), fmax=librosa.note_to_hz("C7"), sr=sr,
                                 frame_length=frame_length, hop_length=hop_length)
    times = librosa.times_like(f0, sr=sr, hop_length=hop_length)
    notes: list[SungNote] = []
    active: list[float] = []
    start = 0.0
    last_midi: int | None = None
    for t, hz, is_voiced in zip(times, f0, voiced):
        midi = int(round(librosa.hz_to_midi(hz))) if is_voiced and not np.isnan(hz) else None
        if midi is not None and midi == last_midi:
            active.append(float(hz))
            continue
        if last_midi is not None and active:
            notes.append(SungNote(start, float(t), last_midi, float(np.median(active))))
        if midi is None:
            active, last_midi = [], None
        else:
            start, active, last_midi = float(t), [float(hz)], midi
    if last_midi is not None and active:
        notes.append(SungNote(start, float(times[-1]), last_midi, float(np.median(active))))
    return [note for note in notes if note.end - note.start >= 0.10]

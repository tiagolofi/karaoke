from __future__ import annotations

import librosa
import numpy as np

from .models import SungNote


def median_filter_pitch(frequencies: np.ndarray, voiced: np.ndarray, window_size: int = 5) -> np.ndarray:
    """Suaviza frequências vocais com mediana local antes de quantizá-las em notas."""
    if window_size < 1 or window_size % 2 == 0:
        raise ValueError("A janela da mediana deve ser um número ímpar positivo.")
    filtered = np.array(frequencies, dtype=float, copy=True)
    radius = window_size // 2
    for index, frequency in enumerate(frequencies):
        if not voiced[index] or np.isnan(frequency):
            continue
        start = max(0, index - radius)
        end = min(len(frequencies), index + radius + 1)
        window = frequencies[start:end]
        valid = voiced[start:end] & ~np.isnan(window)
        if np.any(valid):
            filtered[index] = float(np.median(window[valid]))
    return filtered


def detect_notes(vocals_path: str, frame_length: int = 2048, hop_length: int = 256) -> list[SungNote]:
    """Detecta trechos vocais afinados por pYIN e consolida notas adjacentes."""
    y, sr = librosa.load(vocals_path, sr=None, mono=True)
    f0, voiced, _ = librosa.pyin(y, fmin=librosa.note_to_hz("C2"), fmax=librosa.note_to_hz("C7"), sr=sr,
                                 frame_length=frame_length, hop_length=hop_length)
    f0 = median_filter_pitch(f0, voiced)
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

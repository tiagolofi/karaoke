from __future__ import annotations

import librosa
import numpy as np


def detect_pitch(samples: np.ndarray, sample_rate: int) -> float | None:
    """Retorna o pitch vocal predominante de um bloco do microfone."""
    if np.max(np.abs(samples), initial=0.0) < 0.01:
        return None
    frequencies = librosa.yin(
        samples,
        fmin=librosa.note_to_hz("C2"),
        fmax=librosa.note_to_hz("C6"),
        sr=sample_rate,
    )
    valid = frequencies[np.isfinite(frequencies)]
    return float(np.median(valid)) if valid.size else None

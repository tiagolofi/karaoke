from __future__ import annotations

from pathlib import Path

from .models import TimedText


def transcribe(audio: Path, model_size: str = "small", language: str | None = None) -> list[TimedText]:
    """Transcreve com timestamps por segmento usando faster-whisper."""
    from faster_whisper import WhisperModel

    model = WhisperModel(model_size, device="auto", compute_type="int8")
    segments, _ = model.transcribe(
        str(audio),
        language=language,
        vad_filter=False,
        condition_on_previous_text=False,
    )
    return [TimedText(segment.text.strip(), segment.start, segment.end) for segment in segments if segment.text.strip()]

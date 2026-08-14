from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class TimedText:
    text: str
    start: float
    end: float


@dataclass(frozen=True)
class SungNote:
    start: float
    end: float
    midi: int
    hz: float
    lyric: str = ""

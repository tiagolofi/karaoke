from __future__ import annotations

import math
from dataclasses import dataclass

from reference import ReferenceNote


def cents_difference(actual_hz: float, expected_hz: float) -> float:
    return 1200 * math.log2(actual_hz / expected_hz)


@dataclass
class PitchScore:
    evaluated: int = 0
    correct: int = 0

    @property
    def rate(self) -> float:
        return 100 * self.correct / self.evaluated if self.evaluated else 0.0

    def evaluate(self, detected_hz: float | None, expected: ReferenceNote | None, tolerance_cents: float) -> float | None:
        """Conta um bloco comparável; silêncio não é considerado acerto."""
        if expected is None or detected_hz is None:
            return None
        deviation = cents_difference(detected_hz, expected.hz)
        self.evaluated += 1
        if abs(deviation) <= tolerance_cents:
            self.correct += 1
        return deviation
